# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Hash chain against real PostgreSQL: append, verify, detect tampering, role limits."""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from app.core.audit_hash_chain import append_audit, chain_head, verify_chain
from tests.integration.conftest import owner_execute

pytestmark = pytest.mark.integration


def _append(session, n: int, tag: str) -> list[int]:
    seqs = []
    for i in range(n):
        event = append_audit(
            session,
            actor="pytest",
            action="test.event",
            entity_type="test",
            entity_id=f"{tag}-{i}",
            payload={"i": i, "price": 12.5, "món": "Canh chua", "id": uuid.uuid4()},
        )
        seqs.append(event.seq)
    session.commit()
    return seqs


def test_appended_events_verify_including_payload_round_trip(app_session):
    _append(app_session, 3, "ok")
    result = verify_chain(app_session)
    assert result.ok, result
    assert result.head_seq == chain_head(app_session)[0]


def test_numbers_that_jsonb_normalises_still_verify(app_session):
    # jsonb rewrites -0.0 as 0.0 and 1e16 as 10000000000000000; the hash must match what is stored.
    append_audit(
        app_session,
        actor="pytest",
        action="test.numbers",
        entity_type="test",
        entity_id="numbers",
        payload={"t": round(-0.04, 1), "big": 1e16, "nested": [{"x": 1.10}]},
    )
    app_session.commit()
    assert verify_chain(app_session).ok


def test_nan_is_rejected_before_it_reaches_the_chain(app_session):
    with pytest.raises(ValueError):
        append_audit(
            app_session, actor="pytest", action="t", entity_type="t", entity_id="nan", payload={"x": float("nan")}
        )
    app_session.rollback()


def test_anchor_detects_matching_and_rewritten_history(app_session):
    seqs = _append(app_session, 2, "anchor")
    anchor = (seqs[-1], chain_head(app_session)[1])
    assert verify_chain(app_session, anchor).ok
    assert verify_chain(app_session, (anchor[0], "f" * 64)).reason == "anchor mismatch"


def test_tampering_with_one_row_is_reported_at_that_seq(app_session, owner_engine):
    seqs = _append(app_session, 3, "tamper")
    victim = seqs[1]
    owner_execute(
        owner_engine, "UPDATE audit_event SET payload = jsonb_set(payload, '{i}', '99') WHERE seq = :s", s=victim
    )
    try:
        result = verify_chain(app_session)
        assert not result.ok
        assert result.first_bad_seq == victim
    finally:
        owner_execute(
            owner_engine, "UPDATE audit_event SET payload = jsonb_set(payload, '{i}', '1') WHERE seq = :s", s=victim
        )
    assert verify_chain(app_session).ok


@pytest.mark.parametrize("statement", ["UPDATE audit_event SET actor = 'evil'", "DELETE FROM audit_event"])
def test_runtime_role_cannot_rewrite_or_delete_audit(app_engine, statement):
    with app_engine.connect() as conn, pytest.raises(ProgrammingError, match="permission denied"):
        conn.execute(text(statement))
