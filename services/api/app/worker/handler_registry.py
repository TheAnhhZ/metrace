# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Outbox event handlers and periodic reconcilers, registered by domain modules.

Handlers run OUTSIDE any database transaction and must be idempotent
(e.g. start a process only if none exists for the business key).
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


class InfraError(Exception):
    """Temporary infrastructure failure: retried forever with backoff."""


@dataclass(frozen=True)
class OutboxMessage:
    id: int
    event_type: str
    aggregate_type: str | None
    aggregate_id: Any
    payload: dict[str, Any]
    attempts: int


Handler = Callable[[OutboxMessage], None]
Reconciler = Callable[[], None]

HANDLERS: dict[str, Handler] = {}
RECONCILERS: list[Reconciler] = []


def handles(event_type: str) -> Callable[[Handler], Handler]:
    def register(fn: Handler) -> Handler:
        if event_type in HANDLERS:
            raise ValueError(f"duplicate handler for {event_type}")
        HANDLERS[event_type] = fn
        return fn

    return register


def reconciler(fn: Reconciler) -> Reconciler:
    RECONCILERS.append(fn)
    return fn
