# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Poka-yoke thresholds (with their legal/field basis) and the log of every block."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import BasisType, one_of


class RuleThreshold(Base):
    """No API writes these: changing a threshold is a migration or a seed change."""

    __tablename__ = "rule_threshold"
    __table_args__ = (one_of("basis_type", BasisType),)

    code: Mapped[str] = mapped_column(String(60), primary_key=True)
    value: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    unit: Mapped[str] = mapped_column(String(20))
    basis: Mapped[str] = mapped_column(Text)
    basis_type: Mapped[str] = mapped_column(String(20))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class PokaYokeEvent(Base):
    """Every blocked action, for audit and the 'block rate' KPI."""

    __tablename__ = "poka_yoke_event"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    rule: Mapped[str] = mapped_column(String(10))
    reason_code: Mapped[str] = mapped_column(String(60), index=True)
    entity_type: Mapped[str] = mapped_column(String(60))
    entity_id: Mapped[str | None] = mapped_column(String(100))
    actor: Mapped[str] = mapped_column(String(100))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
