# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Shipments of cooked batches to delivery points."""

import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Timestamps, UuidPrimaryKey
from app.models.enums import MealSlot, ShipmentStatus, one_of


class Shipment(UuidPrimaryKey, Timestamps, Base):
    __tablename__ = "shipment"
    __table_args__ = (one_of("status", ShipmentStatus), one_of("meal_slot", MealSlot))

    kitchen_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("kitchen.id"), index=True)
    code: Mapped[str] = mapped_column(String(60), unique=True)
    delivery_point_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("delivery_point.id"), index=True)
    vehicle_asset_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("asset.id"))
    service_date: Mapped[date] = mapped_column(Date, index=True)
    meal_slot: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default=ShipmentStatus.PLANNED)
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dispatched_by: Mapped[str | None] = mapped_column(String(100))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ShipmentItem(UuidPrimaryKey, Base):
    __tablename__ = "shipment_item"
    __table_args__ = (
        UniqueConstraint("shipment_id", "batch_id", name="uq_shipment_item_batch"),
        CheckConstraint("portions > 0", name="portions_positive"),
    )

    shipment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shipment.id", ondelete="CASCADE"), index=True)
    batch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cooking_batch.id"), index=True)
    portions: Mapped[int] = mapped_column(Integer)
