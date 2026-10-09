# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Thresholds with their basis (law | guidance | field | internal), loaded once per request."""

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.rules import RuleThreshold

# Fallbacks only matter if the seed did not run; the seed is the source of truth.
DEFAULTS: dict[str, Decimal] = {
    "receiving_chilled_max_c": Decimal("4"),
    "receiving_frozen_max_c": Decimal("-18"),
    "core_temp_min_c": Decimal("75"),
    "dispatch_hold_max_min": Decimal("120"),
    "sample_min_solid_g": Decimal("100"),
    "sample_min_liquid_ml": Decimal("150"),
    "sample_required_min_portions": Decimal("30"),
    "sample_retention_h": Decimal("24"),
    "cert_warn_days": Decimal("30"),
}


@dataclass(frozen=True)
class Basis:
    text: str
    type: str

    def as_dict(self) -> dict[str, str]:
        return {"basis": self.text, "basis_type": self.type}


@dataclass(frozen=True)
class Thresholds:
    values: dict[str, Decimal]
    bases: dict[str, Basis]

    def get(self, code: str) -> Decimal:
        return self.values.get(code, DEFAULTS[code])

    def basis(self, code: str) -> dict[str, str]:
        return self.bases.get(code, Basis("default (seed missing)", "internal")).as_dict()

    def max_receiving_temp(self, storage: str) -> tuple[str, Decimal] | None:
        code = {"chilled": "receiving_chilled_max_c", "frozen": "receiving_frozen_max_c"}.get(storage)
        return (code, self.get(code)) if code else None

    @classmethod
    def of(cls, values: dict[str, Decimal | int | float]) -> "Thresholds":
        """Build from plain values (tests)."""
        return cls({k: Decimal(str(v)) for k, v in values.items()}, {})


def load_thresholds(session: Session) -> Thresholds:
    rows = session.scalars(select(RuleThreshold).where(RuleThreshold.enabled)).all()
    return Thresholds(
        values={r.code: r.value for r in rows},
        bases={r.code: Basis(r.basis, r.basis_type) for r in rows},
    )
