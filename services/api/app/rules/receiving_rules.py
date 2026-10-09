# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""P1: goods receipt. Block missing documents, blocked/locked supplier, expired
food-safety certificate (#4), out-of-range temperature. Warn when the
certificate expires within `cert_warn_days`."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.core.reason_codes import ReasonCode as RC
from app.rules.rule_result import RuleResult
from app.rules.thresholds import Thresholds


@dataclass(frozen=True)
class LineSnapshot:
    ingredient: str
    storage: str  # chilled | frozen | dry
    temp_c: Decimal | None


@dataclass(frozen=True)
class ReceivingSnapshot:
    document_count: int
    lines: list[LineSnapshot]


@dataclass(frozen=True)
class SupplierSnapshot:
    code: str
    status: str
    locked: bool
    certificate_expiries: list[date]  # every food-safety certificate on file

    def latest_valid_expiry(self, today: date) -> date | None:
        valid = [d for d in self.certificate_expiries if d >= today]
        return max(valid) if valid else None


def check_receiving(inp: ReceivingSnapshot, sup: SupplierSnapshot, th: Thresholds, today: date) -> RuleResult:
    r = RuleResult()
    if inp.document_count == 0:
        r.block("P1", RC.P1_MISSING_DOCUMENTS)
    if sup.status == "blocked" or sup.locked:
        r.block("P1", RC.P1_SUPPLIER_BLOCKED, supplier=sup.code, locked=sup.locked)

    expiry = sup.latest_valid_expiry(today)
    if expiry is None:
        last = max(sup.certificate_expiries, default=None)
        r.block("P1", RC.P1_SUPPLIER_CERT_EXPIRED, supplier=sup.code, expired_on=last.isoformat() if last else None)
    else:
        days_left = (expiry - today).days
        if days_left <= th.get("cert_warn_days"):
            r.warn("P1", RC.P1_SUPPLIER_CERT_EXPIRING, supplier=sup.code, days_left=days_left)

    for line in inp.lines:
        limit = th.max_receiving_temp(line.storage)
        if limit is None:
            continue
        code, max_c = limit
        if line.temp_c is None or line.temp_c > max_c:
            r.block(
                "P1",
                RC.P1_TEMP_OUT_OF_RANGE,
                ingredient=line.ingredient,
                measured=str(line.temp_c) if line.temp_c is not None else None,
                limit=str(max_c),
                **th.basis(code),
            )
    return r
