# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Master data: kitchens, equipment (assets), customers and their delivery points."""

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Timestamps, UuidPrimaryKey
from app.models.enums import AssetType, CustomerKind, one_of


class Kitchen(UuidPrimaryKey, Timestamps, Base):
    __tablename__ = "kitchen"

    code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(200))


class Asset(UuidPrimaryKey, Timestamps, Base):
    """Fridges, freezers, trucks, thermometers. min/max are the safe temperature band."""

    __tablename__ = "asset"
    __table_args__ = (one_of("type", AssetType),)

    kitchen_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("kitchen.id"), index=True)
    code: Mapped[str] = mapped_column(String(40), unique=True)
    type: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(200))
    min_c: Mapped[Decimal | None] = mapped_column(Numeric(5, 1))
    max_c: Mapped[Decimal | None] = mapped_column(Numeric(5, 1))


class CustomerOrg(UuidPrimaryKey, Timestamps, Base):
    """A customer company/school. `kc_org_alias` ties it to the Keycloak organization."""

    __tablename__ = "customer_org"
    __table_args__ = (one_of("kind", CustomerKind),)

    kc_org_alias: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(20))
    profile: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class DeliveryPoint(UuidPrimaryKey, Timestamps, Base):
    __tablename__ = "delivery_point"

    customer_org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customer_org.id"), index=True)
    code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    address: Mapped[str] = mapped_column(String(300), default="")
