# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""P4: retained samples. Minimum quantity (solid g / liquid ml) and no discard
before max(stored_at, meal_end_at) + retention hours."""

from datetime import datetime, timedelta

from app.core.reason_codes import ReasonCode as RC
from app.rules.rule_result import RuleResult
from app.rules.thresholds import Thresholds


def eligible_discard_at(stored_at: datetime, meal_end_at: datetime, th: Thresholds) -> datetime:
    return max(stored_at, meal_end_at) + timedelta(hours=float(th.get("sample_retention_h")))


def check_sample_quantity(dish_kind: str, qty_g: int | None, qty_ml: int | None, th: Thresholds) -> RuleResult:
    r = RuleResult()
    if dish_kind == "liquid":
        code, measured, unit = "sample_min_liquid_ml", qty_ml, "ml"
    else:
        code, measured, unit = "sample_min_solid_g", qty_g, "g"
    minimum = th.get(code)
    if measured is None or measured < minimum:
        r.block("P4", RC.P4_SAMPLE_UNDER_MINIMUM, measured=measured, limit=str(minimum), unit=unit, **th.basis(code))
    return r


def check_sample_discard(eligible_at: datetime, now: datetime, th: Thresholds) -> RuleResult:
    r = RuleResult()
    if now < eligible_at:
        r.block(
            "P4",
            RC.P4_DISCARD_BEFORE_RETENTION,
            eligible_discard_at=eligible_at.isoformat(),
            remaining_minutes=int((eligible_at - now).total_seconds() // 60) + 1,
            **th.basis("sample_retention_h"),
        )
    return r
