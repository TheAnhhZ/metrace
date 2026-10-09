# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Dishes, menus, cooking batches (Mẫu 2, the central entity), batch inputs,
portion checks (Mẫu 3) and retained samples."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Timestamps, UuidPrimaryKey
from app.models.enums import BatchStatus, DishKind, MealSlot, SampleStatus, one_of


class Dish(UuidPrimaryKey, Timestamps, Base):
    __tablename__ = "dish"
    __table_args__ = (one_of("kind", DishKind),)

    code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(20))
    yield_factor: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=1)
    portion_size_g: Mapped[int] = mapped_column(Integer, default=0)


class Menu(UuidPrimaryKey, Timestamps, Base):
    """What a kitchen serves for one meal; customer_org_id NULL = every customer."""

    __tablename__ = "menu"
    __table_args__ = (
        one_of("meal_slot", MealSlot),
        UniqueConstraint(
            "kitchen_id",
            "service_date",
            "meal_slot",
            "customer_org_id",
            name="uq_menu_slot",
            postgresql_nulls_not_distinct=True,
        ),
    )

    kitchen_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("kitchen.id"), index=True)
    service_date: Mapped[date] = mapped_column(Date, index=True)
    meal_slot: Mapped[str] = mapped_column(String(20))
    meal_end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    customer_org_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("customer_org.id"))


class MenuItem(UuidPrimaryKey, Base):
    __tablename__ = "menu_item"
    __table_args__ = (UniqueConstraint("menu_id", "dish_id", name="uq_menu_item_dish"),)

    menu_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("menu.id", ondelete="CASCADE"), index=True)
    dish_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("dish.id"))


class CookingBatch(UuidPrimaryKey, Timestamps, Base):
    """Mẫu 2: one cooking batch. Every trace goes through here."""

    __tablename__ = "cooking_batch"
    __table_args__ = (one_of("status", BatchStatus), one_of("meal_slot", MealSlot))

    kitchen_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("kitchen.id"), index=True)
    dish_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("dish.id"), index=True)
    batch_code: Mapped[str] = mapped_column(String(60), unique=True)
    service_date: Mapped[date] = mapped_column(Date, index=True)
    meal_slot: Mapped[str] = mapped_column(String(20))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    core_temp_c: Mapped[Decimal | None] = mapped_column(Numeric(5, 1))
    owner: Mapped[str] = mapped_column(String(100))
    portions_planned: Mapped[int] = mapped_column(Integer, default=0)
    portions_produced: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default=BatchStatus.COOKING)


class BatchInput(UuidPrimaryKey, Base):
    """What went into a batch: an ingredient lot XOR another (intermediate) batch."""

    __tablename__ = "batch_input"
    __table_args__ = (
        CheckConstraint("num_nonnulls(lot_id, input_batch_id) = 1", name="lot_xor_batch"),
        CheckConstraint("input_batch_id IS NULL OR input_batch_id <> batch_id", name="not_self"),
        CheckConstraint("qty_kg > 0", name="qty_positive"),
    )

    batch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cooking_batch.id"), index=True)
    lot_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ingredient_lot.id"), index=True)
    input_batch_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("cooking_batch.id"), index=True)
    qty_kg: Mapped[Decimal] = mapped_column(Numeric(10, 3))
    added_by: Mapped[str] = mapped_column(String(100), default="")
    added_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PortionCheck(UuidPrimaryKey, Timestamps, Base):
    """Mẫu 3: check before serving (portions, matches menu, sensory)."""

    __tablename__ = "portion_check"

    batch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cooking_batch.id"), index=True)
    shipment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("shipment.id"), index=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    checked_by: Mapped[str] = mapped_column(String(100))
    portions: Mapped[int] = mapped_column(Integer)
    menu_match: Mapped[bool] = mapped_column(Boolean, default=True)
    sensory_ok: Mapped[bool] = mapped_column(Boolean, default=True)
    note: Mapped[str] = mapped_column(Text, default="")


class RetainedSample(UuidPrimaryKey, Timestamps, Base):
    """Kept 24 h from max(stored_at, meal_end_at); never discarded during an incident."""

    __tablename__ = "retained_sample"
    __table_args__ = (
        one_of("status", SampleStatus),
        CheckConstraint("num_nonnulls(qty_g, qty_ml) = 1", name="one_quantity"),
    )

    batch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cooking_batch.id"), index=True)
    qty_g: Mapped[int | None] = mapped_column(Integer)
    qty_ml: Mapped[int | None] = mapped_column(Integer)
    seal_code: Mapped[str] = mapped_column(String(40), unique=True)
    fridge_asset_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("asset.id"))
    stored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    stored_by: Mapped[str] = mapped_column(String(100), default="")
    meal_end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    eligible_discard_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    discarded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    discarded_by: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default=SampleStatus.STORED)
