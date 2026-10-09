# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Tamper-evident audit log: each event hashes its content plus the previous hash.

Written in the SAME transaction as the business change. The runtime DB role
cannot UPDATE/DELETE audit rows; the chain head (seq, hash) is anchored outside
the database (PDF footers, recall notices) so a rewritten chain is detectable.
This is tamper-evidence, not a digital signature.
"""

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.canonical_json import canonical_json
from app.models.platform import AuditEvent

GENESIS_HASH = "0" * 64
CHAIN_LOCK_KEY = 42001  # pg_advisory_xact_lock key that serialises appends


def _event_hash(
    at: datetime, actor: str, action: str, entity_type: str, entity_id: str, payload: Any, prev: str
) -> str:
    body = canonical_json(
        {
            "at": at.astimezone(UTC).isoformat(timespec="microseconds"),
            "actor": actor,
            "action": action,
            "entity": [entity_type, entity_id],
            "payload": payload,
            "prev": prev,
        }
    )
    return hashlib.sha256(body.encode()).hexdigest()


def append_audit(
    session: Session,
    *,
    actor: str,
    action: str,
    entity_type: str,
    entity_id: Any,
    payload: dict[str, Any] | None = None,
) -> AuditEvent:
    session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": CHAIN_LOCK_KEY})
    prev = session.scalar(select(AuditEvent.hash).order_by(AuditEvent.seq.desc()).limit(1)) or GENESIS_HASH
    # Microsecond precision matches PostgreSQL, so the stored value re-hashes identically.
    at = datetime.now(UTC)
    # Hash exactly what jsonb will return on verify (it normalises numbers: -0.0, 1e16, ...).
    clean_payload = session.scalar(text("SELECT CAST(:p AS jsonb)"), {"p": canonical_json(payload or {})})
    event = AuditEvent(
        at=at,
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        payload=clean_payload,
        prev_hash=prev,
        hash=_event_hash(at, actor, action, entity_type, str(entity_id), clean_payload, prev),
    )
    session.add(event)
    session.flush()
    return event


@dataclass(frozen=True)
class ChainVerification:
    ok: bool
    checked: int
    head_seq: int | None
    head_hash: str | None
    first_bad_seq: int | None = None
    reason: str | None = None


def verify_chain(session: Session, anchor: tuple[int, str] | None = None) -> ChainVerification:
    """Recompute every hash in order. With an anchor (seq, hash) taken earlier and
    stored outside the DB, also prove the history up to that point was not rewritten."""
    prev = GENESIS_HASH
    checked = 0
    last: AuditEvent | None = None
    anchor_seen = anchor is None
    for event in session.scalars(select(AuditEvent).order_by(AuditEvent.seq)).yield_per(500):
        expected = _event_hash(
            event.at, event.actor, event.action, event.entity_type, event.entity_id, event.payload, prev
        )
        if event.prev_hash != prev or event.hash != expected:
            return ChainVerification(False, checked, event.seq, event.hash, event.seq, "hash mismatch")
        if anchor is not None and event.seq == anchor[0]:
            if event.hash != anchor[1]:
                return ChainVerification(False, checked, event.seq, event.hash, event.seq, "anchor mismatch")
            anchor_seen = True
        prev = event.hash
        checked += 1
        last = event
    if not anchor_seen:
        return ChainVerification(False, checked, None, None, anchor[0], "anchor not found")  # type: ignore[index]
    return ChainVerification(True, checked, last.seq if last else None, last.hash if last else None)


def chain_head(session: Session) -> tuple[int, str] | None:
    row = session.execute(select(AuditEvent.seq, AuditEvent.hash).order_by(AuditEvent.seq.desc()).limit(1)).first()
    return (row.seq, row.hash) if row else None
