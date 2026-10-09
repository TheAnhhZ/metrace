# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Outcome of a Poka-yoke check: blocking violations and non-blocking warnings.

Rules are pure functions `check_*(snapshot, thresholds, now) -> RuleResult`:
no I/O, so they are fast to test and easy for a reviewer to read.
"""

from dataclasses import dataclass, field
from typing import Any

from app.core.errors import AppError
from app.core.reason_codes import ReasonCode


@dataclass(frozen=True)
class Finding:
    rule: str  # "P1".."P6"
    code: ReasonCode
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {"rule": self.rule, "code": str(self.code), **self.details}


@dataclass
class RuleResult:
    violations: list[Finding] = field(default_factory=list)
    warnings: list[Finding] = field(default_factory=list)

    def block(self, rule: str, code: ReasonCode, **details: Any) -> None:
        self.violations.append(Finding(rule, code, details))

    def warn(self, rule: str, code: ReasonCode, **details: Any) -> None:
        self.warnings.append(Finding(rule, code, details))

    def extend(self, other: "RuleResult") -> "RuleResult":
        self.violations.extend(other.violations)
        self.warnings.extend(other.warnings)
        return self

    @property
    def ok(self) -> bool:
        return not self.violations

    def codes(self) -> list[str]:
        return [str(f.code) for f in self.violations]


class PokaYokeViolation(AppError):
    """422 with every violation (and warning) so the UI can show them all at once."""

    def __init__(self, result: RuleResult):
        first = result.violations[0]
        super().__init__(
            422,
            first.code,
            "Blocked by Poka-yoke rule " + first.rule,
            rule=first.rule,
            details={
                "violations": [f.as_dict() for f in result.violations],
                "warnings": [f.as_dict() for f in result.warnings],
            },
        )
        self.result = result
