# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Requests and responses for the kitchen flow (Mẫu 1-3, samples, shipments)."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import MealSlot


class _Read(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class WithWarnings(BaseModel):
    warnings: list[dict[str, Any]] = []


# -- receiving (Mẫu 1) ----------------------------------------------------------
class ReceivingLineIn(BaseModel):
    ingredient_id: uuid.UUID
    qty_kg: Decimal = Field(gt=0)
    temp_c: Decimal | None = None
    expiry: date | None = None
    storage_asset_id: uuid.UUID | None = None


class ReceivingIn(BaseModel):
    supplier_id: uuid.UUID
    document_file_ids: list[uuid.UUID] = []
    sensory_ok: bool = True
    quick_test: str = ""
    note: str = ""
    lines: list[ReceivingLineIn] = Field(min_length=1)


class LotOut(_Read):
    id: uuid.UUID
    lot_code: str
    ingredient_id: uuid.UUID
    qty_kg: Decimal
    temp_c: Decimal | None
    status: str


class ReceivingOut(WithWarnings):
    id: uuid.UUID
    code: str
    supplier_id: uuid.UUID
    received_at: datetime
    lots: list[LotOut]


# -- cooking (Mẫu 2) ------------------------------------------------------------
class BatchIn(BaseModel):
    dish_id: uuid.UUID
    service_date: date
    meal_slot: MealSlot
    portions_planned: int = Field(ge=0)


class BatchInputIn(BaseModel):
    lot_id: uuid.UUID | None = None
    input_batch_id: uuid.UUID | None = None
    qty_kg: Decimal = Field(gt=0)

    @model_validator(mode="after")
    def exactly_one_source(self) -> "BatchInputIn":
        if (self.lot_id is None) == (self.input_batch_id is None):
            raise ValueError("give exactly one of lot_id or input_batch_id")
        return self


class BatchFinishIn(BaseModel):
    core_temp_c: Decimal
    portions_produced: int = Field(ge=0)


class BatchOut(_Read):
    id: uuid.UUID
    batch_code: str
    dish_id: uuid.UUID
    service_date: date
    meal_slot: str
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    core_temp_c: Decimal | None
    portions_planned: int
    portions_produced: int | None
    owner: str


# -- samples --------------------------------------------------------------------
class SampleIn(BaseModel):
    batch_id: uuid.UUID
    qty_g: int | None = Field(None, gt=0)
    qty_ml: int | None = Field(None, gt=0)
    fridge_asset_id: uuid.UUID | None = None


class SampleOut(_Read):
    id: uuid.UUID
    batch_id: uuid.UUID
    seal_code: str
    qty_g: int | None
    qty_ml: int | None
    stored_at: datetime
    meal_end_at: datetime
    eligible_discard_at: datetime
    status: str
    discarded_at: datetime | None


class SampleListOut(BaseModel):
    server_now: datetime
    samples: list[SampleOut]


# -- Mẫu 3 + shipments ------------------------------------------------------------
class PortionCheckIn(BaseModel):
    batch_id: uuid.UUID
    shipment_id: uuid.UUID
    portions: int = Field(gt=0)
    menu_match: bool = True
    sensory_ok: bool = True
    note: str = ""


class ShipmentIn(BaseModel):
    delivery_point_id: uuid.UUID
    service_date: date
    meal_slot: MealSlot
    vehicle_asset_id: uuid.UUID | None = None


class ShipmentItemIn(BaseModel):
    batch_id: uuid.UUID
    portions: int = Field(gt=0)


class ShipmentItemOut(BaseModel):
    batch_id: uuid.UUID
    batch_code: str
    portions: int
    form3_done: bool


class ShipmentOut(BaseModel):
    id: uuid.UUID
    code: str
    delivery_point_id: uuid.UUID
    delivery_point: str
    service_date: date
    meal_slot: str
    status: str
    dispatched_at: datetime | None
    items: list[ShipmentItemOut]
    blockers: list[dict[str, Any]] = Field(description="What P3 would block right now (empty = ready to go)")


class MealStepOut(BaseModel):
    key: str
    done: bool
    detail: dict[str, Any]


class MealServiceStatusOut(BaseModel):
    service_date: date
    meal_slot: str
    server_now: datetime
    steps: list[MealStepOut]
