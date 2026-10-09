# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Cold-chain monitoring: raw sensor readings and the alerts they raise.

Readings are NOT in the audit hash chain (high volume, simulated devices);
opening and acknowledging an alert is.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Numeric, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UuidPrimaryKey
from app.models.enums import one_of


class AlertStatus(StrEnum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"


class SensorReading(Base):
    __tablename__ = "sensor_reading"
    __table_args__ = (Index("ix_sensor_reading_asset_received", "asset_id", text("received_at DESC")),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    asset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("asset.id"))
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))  # device clock
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())  # order by this
    source_client: Mapped[str] = mapped_column(String(100))
    temp_c: Mapped[Decimal] = mapped_column(Numeric(5, 1))


class ColdChainAlert(UuidPrimaryKey, Base):
    """At most one OPEN alert per asset (partial unique index): breaches are deduplicated."""

    __tablename__ = "coldchain_alert"
    __table_args__ = (
        one_of("status", AlertStatus),
        Index("uq_coldchain_alert_open", "asset_id", unique=True, postgresql_where=text("status = 'open'")),
    )

    asset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("asset.id"), index=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    max_temp_c: Mapped[Decimal] = mapped_column(Numeric(5, 1))
    status: Mapped[str] = mapped_column(String(20), default=AlertStatus.OPEN)
    process_instance_id: Mapped[str | None] = mapped_column(String(64))
    acknowledged_by: Mapped[str | None] = mapped_column(String(100))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    note: Mapped[str] = mapped_column(String(1000), default="")
