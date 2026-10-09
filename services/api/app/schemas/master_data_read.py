# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Read models for master data (there is no API to write master data)."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class _Read(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CertificateOut(_Read):
    number: str
    cert_type: str
    issued_on: date
    expires_on: date
    days_left: int
    state: str  # valid | expiring | expired


class SupplierOut(_Read):
    id: uuid.UUID
    code: str
    name: str
    status: str
    locked: bool
    certificates: list[CertificateOut]


class IngredientOut(_Read):
    id: uuid.UUID
    code: str
    name: str
    category: str
    storage: str


class LotListOut(BaseModel):
    id: uuid.UUID
    lot_code: str
    ingredient_code: str
    ingredient_name: str
    supplier_code: str
    qty_kg: Decimal
    status: str
    locked: bool
    received_at: datetime


class DishOut(_Read):
    id: uuid.UUID
    code: str
    name: str
    kind: str
    portion_size_g: int


class DeliveryPointOut(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    address: str
    customer_alias: str
    customer_name: str
    customer_kind: str


class AssetOut(_Read):
    id: uuid.UUID
    code: str
    type: str
    name: str
    min_c: Decimal | None
    max_c: Decimal | None


class MenuOut(BaseModel):
    id: uuid.UUID
    service_date: date
    meal_slot: str
    meal_end_at: datetime
    customer_alias: str | None
    dishes: list[DishOut]


class ThresholdOut(_Read):
    code: str
    value: Decimal
    unit: str
    basis: str
    basis_type: str
