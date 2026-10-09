# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Shipments: create, add batches, record Mẫu 3, dispatch under P3 + lock guard."""

import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.audit_hash_chain import append_audit
from app.core.business_time import utcnow
from app.core.database import get_or_404
from app.core.errors import AppError
from app.core.principal import Principal
from app.core.reason_codes import ReasonCode
from app.models.cooking import CookingBatch, PortionCheck
from app.models.enums import BatchStatus, ShipmentStatus
from app.models.kitchen_and_customers import DeliveryPoint, Kitchen
from app.models.shipment import Shipment, ShipmentItem
from app.rules.dispatch_rules import check_dispatch
from app.rules.thresholds import load_thresholds
from app.schemas.kitchen_operations import PortionCheckIn, ShipmentIn, ShipmentItemIn
from app.services import lock_guard
from app.services.dispatch_snapshot import build_dispatch_snapshot
from app.services.poka_yoke_logger import enforce

OPEN_STATUSES = (ShipmentStatus.PLANNED, ShipmentStatus.READY)


def _conflict(message: str) -> AppError:
    return AppError(409, ReasonCode.CONFLICT, message)


def create_shipment(session: Session, principal: Principal, req: ShipmentIn) -> Shipment:
    point = get_or_404(session, DeliveryPoint, req.delivery_point_id, "delivery point")
    kitchen = session.scalar(select(Kitchen).order_by(Kitchen.code).limit(1))
    prefix = f"SHP-{req.service_date.strftime('%Y%m%d')}-{req.meal_slot}-{point.code}"
    same = session.scalar(select(func.count()).where(Shipment.code.startswith(prefix)))
    shipment = Shipment(
        kitchen_id=kitchen.id,
        code=prefix if not same else f"{prefix}-{same + 1}",
        delivery_point_id=point.id,
        vehicle_asset_id=req.vehicle_asset_id,
        service_date=req.service_date,
        meal_slot=req.meal_slot,
    )
    session.add(shipment)
    session.flush()
    append_audit(
        session,
        actor=principal.username,
        action="shipment.created",
        entity_type="shipment",
        entity_id=shipment.id,
        payload={"code": shipment.code},
    )
    session.commit()
    return shipment


def add_item(session: Session, principal: Principal, shipment_id: uuid.UUID, req: ShipmentItemIn) -> ShipmentItem:
    shipment = get_or_404(session, Shipment, shipment_id, "shipment")
    batch = get_or_404(session, CookingBatch, req.batch_id, "batch")
    if batch.status != BatchStatus.FINISHED:
        raise _conflict("Only finished batches can be shipped")
    lock_guard.assert_dispatchable(session, principal, shipment, extra_batch=batch.id)
    if shipment.status not in OPEN_STATUSES:
        raise _conflict(f"Shipment is {shipment.status}")
    item = ShipmentItem(shipment_id=shipment.id, batch_id=batch.id, portions=req.portions)
    session.add(item)
    session.flush()
    append_audit(
        session,
        actor=principal.username,
        action="shipment.item_added",
        entity_type="shipment",
        entity_id=shipment.id,
        payload={"batch": batch.batch_code, "portions": req.portions},
    )
    session.commit()
    return item


def record_portion_check(session: Session, principal: Principal, req: PortionCheckIn) -> PortionCheck:
    item = session.scalar(
        select(ShipmentItem).where(ShipmentItem.shipment_id == req.shipment_id, ShipmentItem.batch_id == req.batch_id)
    )
    if item is None:
        raise AppError(422, ReasonCode.VALIDATION_ERROR, "Batch is not on this shipment")
    check = PortionCheck(
        batch_id=req.batch_id,
        shipment_id=req.shipment_id,
        checked_at=utcnow(),
        checked_by=principal.username,
        portions=req.portions,
        menu_match=req.menu_match,
        sensory_ok=req.sensory_ok,
        note=req.note,
    )
    session.add(check)
    session.flush()
    append_audit(
        session,
        actor=principal.username,
        action="portion_check.recorded",
        entity_type="shipment",
        entity_id=req.shipment_id,
        payload={"batch": req.batch_id, "portions": req.portions},
    )
    session.commit()
    return check


def dispatch(session: Session, principal: Principal, shipment_id: uuid.UUID) -> Shipment:
    shipment = get_or_404(session, Shipment, shipment_id, "shipment")
    lock_guard.assert_dispatchable(session, principal, shipment)
    if shipment.status not in OPEN_STATUSES:
        raise _conflict(f"Shipment is {shipment.status}")
    result = check_dispatch(build_dispatch_snapshot(session, shipment), load_thresholds(session), utcnow())
    enforce(session, result, principal, "shipment", shipment.id)
    shipment.status = ShipmentStatus.DISPATCHED
    shipment.dispatched_at = utcnow()
    shipment.dispatched_by = principal.username
    append_audit(
        session,
        actor=principal.username,
        action="shipment.dispatched",
        entity_type="shipment",
        entity_id=shipment.id,
        payload={"code": shipment.code},
    )
    session.commit()
    return shipment


def shipment_view(session: Session, shipment: Shipment) -> dict:
    """Shipment with items and what P3 would block right now (empty list = ready to go)."""
    point = session.get(DeliveryPoint, shipment.delivery_point_id)
    snapshot = build_dispatch_snapshot(session, shipment)
    blockers = []
    if shipment.status in (*OPEN_STATUSES, ShipmentStatus.HELD):
        blockers = check_dispatch(snapshot, load_thresholds(session), utcnow()).violations
    items = session.execute(
        select(ShipmentItem, CookingBatch.batch_code).join(CookingBatch).where(ShipmentItem.shipment_id == shipment.id)
    ).all()
    form3 = {i.batch_code: i.form3_done for i in snapshot.items}
    return {
        "id": shipment.id,
        "code": shipment.code,
        "delivery_point_id": shipment.delivery_point_id,
        "delivery_point": point.name,
        "service_date": shipment.service_date,
        "meal_slot": shipment.meal_slot,
        "status": shipment.status,
        "dispatched_at": shipment.dispatched_at,
        "items": [
            {"batch_id": i.batch_id, "batch_code": code, "portions": i.portions, "form3_done": form3.get(code, False)}
            for i, code in items
        ],
        "blockers": [f.as_dict() for f in blockers],
    }


def list_shipments(session: Session, day: date, meal_slot: str | None) -> list[dict]:
    query = select(Shipment).where(Shipment.service_date == day)
    if meal_slot:
        query = query.where(Shipment.meal_slot == meal_slot)
    return [shipment_view(session, s) for s in session.scalars(query.order_by(Shipment.code))]
