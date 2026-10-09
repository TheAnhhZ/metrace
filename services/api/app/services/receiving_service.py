# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Mẫu 1: receive goods from a supplier, guarded by P1, creating ingredient lots."""

import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit_hash_chain import append_audit
from app.core.business_time import service_date, utcnow
from app.core.database import get_or_404
from app.core.errors import AppError
from app.core.principal import Principal
from app.core.reason_codes import ReasonCode
from app.models.incident import Lock
from app.models.kitchen_and_customers import Kitchen
from app.models.platform import FileObject
from app.models.supplier_and_lots import Ingredient, IngredientLot, Receiving, Supplier, SupplierCertificate
from app.rules.receiving_rules import LineSnapshot, ReceivingSnapshot, SupplierSnapshot, check_receiving
from app.rules.thresholds import load_thresholds
from app.schemas.kitchen_operations import ReceivingIn, ReceivingOut
from app.services.poka_yoke_logger import enforce


def supplier_snapshot(session: Session, supplier: Supplier) -> SupplierSnapshot:
    expiries = session.scalars(
        select(SupplierCertificate.expires_on).where(SupplierCertificate.supplier_id == supplier.id)
    ).all()
    locked = session.scalar(
        select(Lock.id).where(Lock.active, Lock.target_type == "supplier", Lock.target_id == supplier.id).limit(1)
    )
    return SupplierSnapshot(supplier.code, supplier.status, locked is not None, list(expiries))


def _company_documents(session: Session, file_ids: list) -> int:
    if not file_ids:
        return 0
    found = session.scalars(select(FileObject).where(FileObject.id.in_(file_ids))).all()
    if len(found) != len(set(file_ids)) or any(f.owner_org_alias is not None for f in found):
        raise AppError(422, ReasonCode.VALIDATION_ERROR, "Unknown document file id(s)")
    return len(found)


def create_receiving(session: Session, principal: Principal, req: ReceivingIn) -> ReceivingOut:
    supplier = get_or_404(session, Supplier, req.supplier_id, "supplier")
    ingredients = {
        i.id: i
        for i in session.scalars(
            select(Ingredient).where(Ingredient.id.in_([line.ingredient_id for line in req.lines]))
        )
    }
    if len(ingredients) != len({line.ingredient_id for line in req.lines}):
        raise AppError(422, ReasonCode.VALIDATION_ERROR, "Unknown ingredient id(s)")

    now = utcnow()
    snapshot = ReceivingSnapshot(
        document_count=_company_documents(session, req.document_file_ids),
        lines=[
            LineSnapshot(ingredients[x.ingredient_id].name, ingredients[x.ingredient_id].storage, x.temp_c)
            for x in req.lines
        ],
    )
    result = check_receiving(
        snapshot, supplier_snapshot(session, supplier), load_thresholds(session), service_date(now)
    )
    enforce(session, result, principal, "receiving", None, {"supplier": supplier.code})

    kitchen = session.scalar(select(Kitchen).order_by(Kitchen.code).limit(1))
    stamp = now.strftime("%Y%m%d%H%M%S")
    receiving = Receiving(
        kitchen_id=kitchen.id,
        supplier_id=supplier.id,
        code=f"RCV-{stamp}-{supplier.code}",
        received_at=now,
        received_by=principal.username,
        document_file_ids=list(req.document_file_ids),
        sensory_ok=req.sensory_ok,
        quick_test=req.quick_test,
        note=req.note,
    )
    session.add(receiving)
    session.flush()
    lots = []
    for line in req.lines:
        ingredient = ingredients[line.ingredient_id]
        lot = IngredientLot(
            kitchen_id=kitchen.id,
            receiving_id=receiving.id,
            ingredient_id=ingredient.id,
            supplier_id=supplier.id,
            lot_code=f"LOT-{stamp}-{ingredient.code}-{secrets.token_hex(2).upper()}",
            qty_kg=line.qty_kg,
            temp_c=line.temp_c,
            expiry=line.expiry,
            storage_asset_id=line.storage_asset_id,
        )
        session.add(lot)
        lots.append(lot)
    session.flush()
    append_audit(
        session,
        actor=principal.username,
        action="receiving.created",
        entity_type="receiving",
        entity_id=receiving.id,
        payload={"code": receiving.code, "lots": [lot.lot_code for lot in lots]},
    )
    session.commit()
    return ReceivingOut(
        id=receiving.id,
        code=receiving.code,
        supplier_id=supplier.id,
        received_at=receiving.received_at,
        lots=lots,
        warnings=[w.as_dict() for w in result.warnings],
    )
