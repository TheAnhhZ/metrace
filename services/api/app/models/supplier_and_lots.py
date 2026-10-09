# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Suppliers, their food-safety certificates, goods receipt (Mẫu 1) and ingredient lots."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import ARRAY, Boolean, Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Timestamps, UuidPrimaryKey
from app.models.enums import LotStatus, ReceivingDecision, StorageKind, SupplierStatus, one_of


class Supplier(UuidPrimaryKey, Timestamps, Base):
    __tablename__ = "supplier"
    __table_args__ = (one_of("status", SupplierStatus),)

    code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default=SupplierStatus.ACTIVE)
    address: Mapped[str] = mapped_column(String(300), default="")


class SupplierCertificate(UuidPrimaryKey, Timestamps, Base):
    """Food-safety certificate (GCN ATTP). Expired => receiving is blocked (rule P1)."""

    __tablename__ = "supplier_certificate"

    supplier_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("supplier.id"), index=True)
    cert_type: Mapped[str] = mapped_column(String(40), default="GCN_ATTP")
    number: Mapped[str] = mapped_column(String(80))
    issued_on: Mapped[date] = mapped_column(Date)
    expires_on: Mapped[date] = mapped_column(Date)
    file_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("file_object.id"))


class Ingredient(UuidPrimaryKey, Timestamps, Base):
    __tablename__ = "ingredient"
    __table_args__ = (one_of("storage", StorageKind),)

    code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(60))
    storage: Mapped[str] = mapped_column(String(20))


class Receiving(UuidPrimaryKey, Timestamps, Base):
    """Mẫu 1: goods received from one supplier at one time."""

    __tablename__ = "receiving"
    __table_args__ = (one_of("decision", ReceivingDecision),)

    kitchen_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("kitchen.id"), index=True)
    supplier_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("supplier.id"), index=True)
    code: Mapped[str] = mapped_column(String(60), unique=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    received_by: Mapped[str] = mapped_column(String(100))
    document_file_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list)
    sensory_ok: Mapped[bool] = mapped_column(Boolean, default=True)
    quick_test: Mapped[str] = mapped_column(String(200), default="")
    decision: Mapped[str] = mapped_column(String(20), default=ReceivingDecision.ACCEPTED)
    note: Mapped[str] = mapped_column(Text, default="")
    # Fields still pending the official annex of the regulation go here.
    extra: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class IngredientLot(UuidPrimaryKey, Timestamps, Base):
    __tablename__ = "ingredient_lot"
    __table_args__ = (one_of("status", LotStatus),)

    kitchen_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("kitchen.id"), index=True)
    receiving_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("receiving.id"), index=True)
    ingredient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ingredient.id"), index=True)
    supplier_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("supplier.id"), index=True)
    lot_code: Mapped[str] = mapped_column(String(60), unique=True)
    qty_kg: Mapped[Decimal] = mapped_column(Numeric(10, 3))
    temp_c: Mapped[Decimal | None] = mapped_column(Numeric(5, 1))
    expiry: Mapped[date | None] = mapped_column(Date)
    storage_asset_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("asset.id"), index=True)
    discarded_kg: Mapped[Decimal] = mapped_column(Numeric(10, 3), default=0)
    status: Mapped[str] = mapped_column(String(20), default=LotStatus.IN_STOCK)
