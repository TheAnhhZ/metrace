# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Mẫu 2: open a cooking batch, add inputs (lots or intermediate batches), finish under P2."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.audit_hash_chain import append_audit
from app.core.business_time import utcnow
from app.core.database import get_or_404
from app.core.errors import AppError
from app.core.principal import Principal
from app.core.reason_codes import ReasonCode
from app.models.cooking import BatchInput, CookingBatch, Dish
from app.models.enums import BatchStatus, LotStatus
from app.models.kitchen_and_customers import Kitchen
from app.models.supplier_and_lots import IngredientLot
from app.rules.cooking_rules import FinishSnapshot, check_finish
from app.rules.thresholds import load_thresholds
from app.schemas.kitchen_operations import BatchFinishIn, BatchIn, BatchInputIn
from app.services import lock_guard
from app.services.poka_yoke_logger import enforce


def _conflict(message: str) -> AppError:
    return AppError(409, ReasonCode.CONFLICT, message)


def create_batch(session: Session, principal: Principal, req: BatchIn) -> CookingBatch:
    dish = get_or_404(session, Dish, req.dish_id, "dish")
    kitchen = session.scalar(select(Kitchen).order_by(Kitchen.code).limit(1))
    prefix = f"B-{req.service_date.strftime('%Y%m%d')}-{req.meal_slot}-{dish.code}"
    same = session.scalar(select(func.count()).where(CookingBatch.batch_code.startswith(prefix)))
    batch = CookingBatch(
        kitchen_id=kitchen.id,
        dish_id=dish.id,
        batch_code=prefix if not same else f"{prefix}-{same + 1}",
        service_date=req.service_date,
        meal_slot=req.meal_slot,
        started_at=utcnow(),
        owner=principal.username,
        portions_planned=req.portions_planned,
        status=BatchStatus.COOKING,
    )
    session.add(batch)
    session.flush()
    append_audit(
        session,
        actor=principal.username,
        action="batch.started",
        entity_type="batch",
        entity_id=batch.id,
        payload={"code": batch.batch_code},
    )
    session.commit()
    return batch


def add_input(session: Session, principal: Principal, batch_id: uuid.UUID, req: BatchInputIn) -> BatchInput:
    batch = get_or_404(session, CookingBatch, batch_id, "batch", for_update=True)
    if batch.status != BatchStatus.COOKING:
        raise _conflict("Batch is not cooking")
    if req.lot_id is not None:
        lot = get_or_404(session, IngredientLot, req.lot_id, "lot")
        if lot.status != LotStatus.IN_STOCK:
            raise _conflict("Lot is not in stock")
    else:
        source = get_or_404(session, CookingBatch, req.input_batch_id, "batch")
        if source.id == batch.id or source.status != BatchStatus.FINISHED:
            raise _conflict("Input batch must be another, finished batch")
    lock_guard.assert_input_allowed(session, principal, batch, req.lot_id, req.input_batch_id)

    row = BatchInput(
        batch_id=batch.id,
        lot_id=req.lot_id,
        input_batch_id=req.input_batch_id,
        qty_kg=req.qty_kg,
        added_by=principal.username,
        added_at=utcnow(),
    )
    session.add(row)
    session.flush()
    append_audit(
        session,
        actor=principal.username,
        action="batch.input_added",
        entity_type="batch",
        entity_id=batch.id,
        payload={"lot": req.lot_id, "input_batch": req.input_batch_id, "qty_kg": str(req.qty_kg)},
    )
    session.commit()
    return row


def finish_batch(session: Session, principal: Principal, batch_id: uuid.UUID, req: BatchFinishIn) -> CookingBatch:
    batch = get_or_404(session, CookingBatch, batch_id, "batch", for_update=True)
    if batch.status != BatchStatus.COOKING:
        raise _conflict("Batch is not cooking")
    has_inputs = session.scalar(select(BatchInput.id).where(BatchInput.batch_id == batch.id).limit(1))
    if has_inputs is None:
        raise AppError(422, ReasonCode.VALIDATION_ERROR, "Record the inputs before finishing (traceability)")
    lock_guard.assert_batch_not_locked(session, principal, batch)
    now = utcnow()
    result = check_finish(
        FinishSnapshot(batch.batch_code, batch.started_at, now, req.core_temp_c), load_thresholds(session)
    )
    enforce(session, result, principal, "batch", batch.id, {"core_temp_c": str(req.core_temp_c)})

    batch.finished_at = now
    batch.core_temp_c = req.core_temp_c
    batch.portions_produced = req.portions_produced
    batch.status = BatchStatus.FINISHED
    append_audit(
        session,
        actor=principal.username,
        action="batch.finished",
        entity_type="batch",
        entity_id=batch.id,
        payload={"core_temp_c": str(req.core_temp_c), "portions": req.portions_produced},
    )
    session.commit()
    return batch
