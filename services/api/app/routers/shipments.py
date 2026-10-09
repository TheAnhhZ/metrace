# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Shipments, Mẫu 3 and the meal-service checklist."""

import uuid
from datetime import date

from fastapi import Depends

from app.core.authentication import CurrentPrincipal
from app.core.authorization import internal_router, require_any_role
from app.core.business_time import service_date, utcnow
from app.core.database import DbSession, get_or_404
from app.models.enums import MealSlot
from app.models.shipment import Shipment
from app.schemas.kitchen_operations import (
    MealServiceStatusOut,
    PortionCheckIn,
    ShipmentIn,
    ShipmentItemIn,
    ShipmentOut,
)
from app.services import dispatch_service
from app.services.meal_service_status import meal_status

router = internal_router(prefix="/api/v1", tags=["dispatch"])

PLANNER = [Depends(require_any_role({"chef", "driver"}))]
CHEF = [Depends(require_any_role({"chef"}))]
CHECKER = [Depends(require_any_role({"qa", "chef"}))]


def _one(session, shipment_id: uuid.UUID) -> dict:
    return dispatch_service.shipment_view(session, get_or_404(session, Shipment, shipment_id, "shipment"))


@router.get("/shipments", response_model=list[ShipmentOut])
def list_shipments(session: DbSession, day: date | None = None, meal_slot: MealSlot | None = None):
    return dispatch_service.list_shipments(session, day or service_date(), meal_slot)


@router.post("/shipments", response_model=ShipmentOut, status_code=201, dependencies=PLANNER)
def create_shipment(req: ShipmentIn, session: DbSession, principal: CurrentPrincipal):
    shipment = dispatch_service.create_shipment(session, principal, req)
    return _one(session, shipment.id)


@router.post("/shipments/{shipment_id}/items", response_model=ShipmentOut, status_code=201, dependencies=CHEF)
def add_item(shipment_id: uuid.UUID, req: ShipmentItemIn, session: DbSession, principal: CurrentPrincipal):
    dispatch_service.add_item(session, principal, shipment_id, req)
    return _one(session, shipment_id)


@router.post("/shipments/{shipment_id}/dispatch", response_model=ShipmentOut, dependencies=PLANNER)
def dispatch(shipment_id: uuid.UUID, session: DbSession, principal: CurrentPrincipal):
    dispatch_service.dispatch(session, principal, shipment_id)
    return _one(session, shipment_id)


@router.post("/portion-checks", status_code=201, dependencies=CHECKER)
def record_portion_check(req: PortionCheckIn, session: DbSession, principal: CurrentPrincipal):
    check = dispatch_service.record_portion_check(session, principal, req)
    return {"id": check.id, "batch_id": check.batch_id, "shipment_id": check.shipment_id, "portions": check.portions}


@router.get("/meal-services/{day}/{meal_slot}/status", response_model=MealServiceStatusOut)
def meal_service_status(day: date, meal_slot: MealSlot, session: DbSession):
    return MealServiceStatusOut(
        service_date=day, meal_slot=meal_slot, server_now=utcnow(), steps=meal_status(session, day, meal_slot)
    )
