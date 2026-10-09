# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Transactional outbox: record side effects in the business transaction.

The API never calls Flowable (or other slow systems) inline. It emits an
outbox row; the worker delivers it later with retries.
"""

import uuid
from typing import Any, Literal

from sqlalchemy.orm import Session

from app.core.canonical_json import normalise
from app.models.platform import OutboxEvent

Lane = Literal["fast", "slow"]


def emit(
    session: Session,
    event_type: str,
    payload: dict[str, Any],
    *,
    aggregate_type: str | None = None,
    aggregate_id: uuid.UUID | None = None,
    lane: Lane = "fast",
) -> OutboxEvent:
    event = OutboxEvent(
        event_type=event_type,
        lane=lane,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        payload=normalise(payload),
    )
    session.add(event)
    return event
