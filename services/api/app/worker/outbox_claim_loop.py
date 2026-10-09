# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""claim (short tx) -> handle (no tx, may call HTTP) -> mark (short tx).

Infrastructure errors retry forever with exponential backoff (max 60 s).
Logic errors retry 5 times, then the row gets `failed_at` (visible in the UI).
A crashed worker's claim simply expires after 60 s and the row is retried.
"""

import logging
import threading
from collections.abc import Mapping

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.worker import heartbeat
from app.worker.handler_registry import Handler, InfraError, OutboxMessage

log = logging.getLogger("metrace.worker")

MAX_LOGIC_ATTEMPTS = 5
CLAIM_SECONDS = 60
BATCH_SIZE = 10

CLAIM_SQL = text(
    """
    UPDATE outbox_event
       SET claimed_until = now() + make_interval(secs => :claim_seconds), attempts = attempts + 1
     WHERE id IN (
           SELECT id FROM outbox_event
            WHERE lane = :lane AND processed_at IS NULL AND failed_at IS NULL
              AND next_attempt_at <= now()
              AND (claimed_until IS NULL OR claimed_until < now())
            ORDER BY id
            LIMIT :batch
            FOR UPDATE SKIP LOCKED)
    RETURNING id, event_type, aggregate_type, aggregate_id, payload, attempts
    """
)
MARK_DONE_SQL = text(
    "UPDATE outbox_event SET processed_at = now(), claimed_until = NULL, last_error = NULL WHERE id = :id"
)
MARK_RETRY_SQL = text(
    """
    UPDATE outbox_event
       SET claimed_until = NULL, last_error = :error,
           next_attempt_at = now() + make_interval(secs => :delay),
           failed_at = CASE WHEN :fail THEN now() ELSE NULL END
     WHERE id = :id
    """
)


def claim_batch(session: Session, lane: str) -> list[OutboxMessage]:
    with session.begin():
        rows = session.execute(CLAIM_SQL, {"lane": lane, "claim_seconds": CLAIM_SECONDS, "batch": BATCH_SIZE}).all()
    return [OutboxMessage(r.id, r.event_type, r.aggregate_type, r.aggregate_id, r.payload, r.attempts) for r in rows]


def _mark(session: Session, sql, **params) -> None:
    with session.begin():
        session.execute(sql, params)


def process_message(session: Session, message: OutboxMessage, handlers: Mapping[str, Handler]) -> str:
    """Run one handler and record the outcome. Returns 'done' | 'retry' | 'failed'."""
    handler = handlers.get(message.event_type)
    try:
        if handler is None:
            raise LookupError(f"no handler for {message.event_type}")
        handler(message)
    except InfraError as exc:
        delay = min(2**message.attempts, 60)
        _mark(session, MARK_RETRY_SQL, id=message.id, error=str(exc)[:2000], delay=delay, fail=False)
        log.warning("outbox %s %s infra error, retry in %ss: %s", message.id, message.event_type, delay, exc)
        return "retry"
    except Exception as exc:
        fail = message.attempts >= MAX_LOGIC_ATTEMPTS
        _mark(session, MARK_RETRY_SQL, id=message.id, error=repr(exc)[:2000], delay=5, fail=fail)
        log.exception("outbox %s %s failed (attempt %s)", message.id, message.event_type, message.attempts)
        return "failed" if fail else "retry"
    _mark(session, MARK_DONE_SQL, id=message.id)
    return "done"


def drain_once(session: Session, lane: str, handlers: Mapping[str, Handler]) -> int:
    batch = claim_batch(session, lane)
    for message in batch:
        process_message(session, message, handlers)
    return len(batch)


def run_lane(
    session_factory, lane: str, handlers: Mapping[str, Handler], stop: threading.Event, idle_seconds: float = 1.0
) -> None:
    log.info("lane %s started (%d handlers)", lane, len(handlers))
    while not stop.is_set():
        heartbeat.touch(lane)
        try:
            with session_factory() as session:
                processed = drain_once(session, lane, handlers)
        except Exception:
            log.exception("lane %s loop error (database down?)", lane)
            processed = 0
        if not processed:
            stop.wait(idle_seconds)
