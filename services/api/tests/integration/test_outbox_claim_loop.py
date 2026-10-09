# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Outbox worker loop against real PostgreSQL (each test uses its own lane)."""

import uuid

import pytest
from sqlalchemy import select, text

from app.core.outbox import emit
from app.models.platform import OutboxEvent
from app.worker.handler_registry import InfraError
from app.worker.outbox_claim_loop import MAX_LOGIC_ATTEMPTS, claim_batch, drain_once
from app.workflow.flowable_client import FlowableUnavailableError

pytestmark = pytest.mark.integration


def _emit(session_factory, lane: str, event_type: str = "test.ping", n: int = 1) -> list[int]:
    with session_factory() as session:
        events = [emit(session, event_type, {"n": i}, lane=lane) for i in range(n)]  # type: ignore[arg-type]
        session.commit()
        return [e.id for e in events]


def _row(session_factory, event_id: int) -> OutboxEvent:
    with session_factory() as session:
        return session.scalar(select(OutboxEvent).where(OutboxEvent.id == event_id))


def _make_due(session_factory, event_id: int) -> None:
    with session_factory() as session, session.begin():
        session.execute(text("UPDATE outbox_event SET next_attempt_at = now() WHERE id = :id"), {"id": event_id})


def test_successful_handler_marks_processed(session_factory):
    lane = f"t-{uuid.uuid4().hex[:8]}"
    [event_id] = _emit(session_factory, lane)
    seen = []
    with session_factory() as session:
        assert drain_once(session, lane, {"test.ping": seen.append}) == 1
    assert [m.id for m in seen] == [event_id]
    assert _row(session_factory, event_id).processed_at is not None


def test_claimed_rows_are_skipped_by_a_concurrent_worker(session_factory):
    lane = f"t-{uuid.uuid4().hex[:8]}"
    _emit(session_factory, lane, n=3)
    with session_factory() as first, session_factory() as second:
        assert len(claim_batch(first, lane)) == 3
        assert claim_batch(second, lane) == []


def test_infra_error_retries_with_backoff_and_never_fails(session_factory):
    lane = f"t-{uuid.uuid4().hex[:8]}"
    [event_id] = _emit(session_factory, lane)

    def flaky(_message):
        raise InfraError("flowable down")

    for _ in range(MAX_LOGIC_ATTEMPTS + 2):
        with session_factory() as session:
            drain_once(session, lane, {"test.ping": flaky})
        _make_due(session_factory, event_id)
    row = _row(session_factory, event_id)
    assert row.failed_at is None and row.processed_at is None
    assert row.attempts == MAX_LOGIC_ATTEMPTS + 2
    assert "flowable down" in row.last_error


def test_flowable_outage_is_retried_not_failed(session_factory):
    lane = f"t-{uuid.uuid4().hex[:8]}"
    [event_id] = _emit(session_factory, lane)

    def flowable_down(_message):
        raise FlowableUnavailableError("connection refused")

    for _ in range(MAX_LOGIC_ATTEMPTS + 1):
        with session_factory() as session:
            drain_once(session, lane, {"test.ping": flowable_down})
        _make_due(session_factory, event_id)
    assert _row(session_factory, event_id).failed_at is None


def test_logic_error_fails_after_max_attempts(session_factory):
    lane = f"t-{uuid.uuid4().hex[:8]}"
    [event_id] = _emit(session_factory, lane)

    def broken(_message):
        raise ValueError("bad payload")

    for _ in range(MAX_LOGIC_ATTEMPTS):
        with session_factory() as session:
            drain_once(session, lane, {"test.ping": broken})
        _make_due(session_factory, event_id)
    row = _row(session_factory, event_id)
    assert row.failed_at is not None
    assert row.attempts == MAX_LOGIC_ATTEMPTS


def test_unknown_event_type_is_a_logic_error(session_factory):
    lane = f"t-{uuid.uuid4().hex[:8]}"
    [event_id] = _emit(session_factory, lane, event_type="test.unknown")
    with session_factory() as session:
        drain_once(session, lane, {})
    assert "no handler" in _row(session_factory, event_id).last_error
