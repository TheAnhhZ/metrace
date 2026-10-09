# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""P3: a truck leaves only when every batch on it has Mẫu 1 (accepted receiving
with documents for every lot), Mẫu 2 (finished batch), Mẫu 3 (portion check
for this shipment), is on the customer's menu, has not been held too long and,
for meals of `sample_required_min_portions` or more, has a retained sample."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.core.reason_codes import ReasonCode as RC
from app.rules.rule_result import RuleResult
from app.rules.thresholds import Thresholds


@dataclass(frozen=True)
class DispatchItem:
    batch_code: str
    form1_complete: bool  # every input lot came from an accepted receiving with documents
    finished_at: datetime | None  # Mẫu 2 done when the batch is finished
    form3_done: bool  # portion check recorded for this batch on this shipment
    in_menu: bool
    batch_portions: int
    has_sample: bool


@dataclass(frozen=True)
class DispatchSnapshot:
    shipment_code: str
    status: str
    items: list[DispatchItem]


def check_dispatch(ship: DispatchSnapshot, th: Thresholds, now: datetime) -> RuleResult:
    r = RuleResult()
    if ship.status == "held":
        r.block("P3", RC.P3_SHIPMENT_HELD, shipment=ship.shipment_code)
    if not ship.items:
        r.block("P3", RC.P3_SHIPMENT_EMPTY, shipment=ship.shipment_code)
    hold_max = th.get("dispatch_hold_max_min")
    sample_from = th.get("sample_required_min_portions")
    for item in ship.items:
        if not item.form1_complete:
            r.block("P3", RC.P3_MISSING_FORM_1, batch=item.batch_code)
        if item.finished_at is None:
            r.block("P3", RC.P3_MISSING_FORM_2, batch=item.batch_code)
        elif now - item.finished_at > timedelta(minutes=float(hold_max)):
            held = int((now - item.finished_at).total_seconds() // 60)
            r.block(
                "P3",
                RC.P3_HOLD_TIME_EXCEEDED,
                batch=item.batch_code,
                held_minutes=held,
                limit=str(hold_max),
                **th.basis("dispatch_hold_max_min"),
            )
        if not item.form3_done:
            r.block("P3", RC.P3_MISSING_FORM_3, batch=item.batch_code)
        if not item.in_menu:
            r.block("P3", RC.P3_DISH_NOT_IN_MENU, batch=item.batch_code)
        if item.batch_portions >= sample_from and not item.has_sample:
            r.block(
                "P3",
                RC.P3_SAMPLE_MISSING,
                batch=item.batch_code,
                portions=item.batch_portions,
                **th.basis("sample_required_min_portions"),
            )
    return r
