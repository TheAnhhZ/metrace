# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Record every blocked action, then raise the 422.

Checks run BEFORE any business write, so committing here persists only the
poka_yoke_event rows (the data behind the "block rate" KPI and the audit view).
"""

from typing import Any

from sqlalchemy.orm import Session

from app.core.principal import Principal
from app.models.rules import PokaYokeEvent
from app.rules.rule_result import PokaYokeViolation, RuleResult


def enforce(
    session: Session,
    result: RuleResult,
    principal: Principal,
    entity_type: str,
    entity_id: Any = None,
    payload: dict[str, Any] | None = None,
) -> None:
    """No-op when the result is clean; otherwise log each violation and raise 422."""
    if result.ok:
        return
    session.rollback()  # never persist half-done business changes with the log rows
    for finding in result.violations:
        session.add(
            PokaYokeEvent(
                rule=finding.rule,
                reason_code=str(finding.code),
                entity_type=entity_type,
                entity_id=str(entity_id) if entity_id is not None else None,
                actor=principal.username,
                payload={**(payload or {}), **{k: str(v) for k, v in finding.details.items()}},
            )
        )
    session.commit()
    raise PokaYokeViolation(result)
