# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""P2: finishing a cooking batch needs start/finish times and a core temperature
at or above `core_temp_min_c`."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.core.reason_codes import ReasonCode as RC
from app.rules.rule_result import RuleResult
from app.rules.thresholds import Thresholds


@dataclass(frozen=True)
class FinishSnapshot:
    batch_code: str
    started_at: datetime | None
    finished_at: datetime | None
    core_temp_c: Decimal | None


def check_finish(batch: FinishSnapshot, th: Thresholds) -> RuleResult:
    r = RuleResult()
    if batch.started_at is None or batch.finished_at is None or batch.finished_at < batch.started_at:
        r.block("P2", RC.P2_MISSING_TIMESTAMPS, batch=batch.batch_code)
    minimum = th.get("core_temp_min_c")
    if batch.core_temp_c is None or batch.core_temp_c < minimum:
        r.block(
            "P2",
            RC.P2_CORE_TEMP_BELOW_MIN,
            batch=batch.batch_code,
            measured=str(batch.core_temp_c) if batch.core_temp_c is not None else None,
            limit=str(minimum),
            **th.basis("core_temp_min_c"),
        )
    return r
