# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""GET-only master data for internal screens. Changes come from seed/migrations."""

from datetime import date

from fastapi import Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.authorization import internal_router
from app.core.business_time import service_date
from app.core.database import DbSession
from app.models.cooking import Dish, Menu, MenuItem
from app.models.enums import LotStatus, MealSlot
from app.models.incident import Lock
from app.models.kitchen_and_customers import Asset, CustomerOrg, DeliveryPoint
from app.models.rules import RuleThreshold
from app.models.supplier_and_lots import Ingredient, IngredientLot, Receiving, Supplier, SupplierCertificate
from app.schemas.master_data_read import (
    AssetOut,
    CertificateOut,
    DeliveryPointOut,
    DishOut,
    IngredientOut,
    LotListOut,
    MenuOut,
    SupplierOut,
    ThresholdOut,
)

router = internal_router(prefix="/api/v1", tags=["master data"])


def _cert_warn_days(session: Session) -> int:
    value = session.scalar(select(RuleThreshold.value).where(RuleThreshold.code == "cert_warn_days"))
    return int(value) if value is not None else 30


@router.get("/suppliers", response_model=list[SupplierOut])
def list_suppliers(session: DbSession):
    today, warn = service_date(), _cert_warn_days(session)
    certs: dict = {}
    for cert in session.scalars(select(SupplierCertificate).order_by(SupplierCertificate.expires_on.desc())):
        days_left = (cert.expires_on - today).days
        state = "expired" if days_left < 0 else "expiring" if days_left <= warn else "valid"
        certs.setdefault(cert.supplier_id, []).append(
            CertificateOut(
                number=cert.number,
                cert_type=cert.cert_type,
                issued_on=cert.issued_on,
                expires_on=cert.expires_on,
                days_left=days_left,
                state=state,
            )
        )
    locked = set(session.scalars(select(Lock.target_id).where(Lock.active, Lock.target_type == "supplier")))
    return [
        SupplierOut(
            id=s.id, code=s.code, name=s.name, status=s.status, locked=s.id in locked, certificates=certs.get(s.id, [])
        )
        for s in session.scalars(select(Supplier).order_by(Supplier.code))
    ]


@router.get("/ingredients", response_model=list[IngredientOut])
def list_ingredients(session: DbSession):
    return session.scalars(select(Ingredient).order_by(Ingredient.code)).all()


@router.get("/lots", response_model=list[LotListOut])
def list_lots(session: DbSession, status: LotStatus | None = LotStatus.IN_STOCK):
    query = (
        select(IngredientLot, Ingredient, Supplier.code, Receiving.received_at)
        .join(Ingredient, Ingredient.id == IngredientLot.ingredient_id)
        .join(Supplier, Supplier.id == IngredientLot.supplier_id)
        .join(Receiving, Receiving.id == IngredientLot.receiving_id)
        .order_by(Receiving.received_at.desc(), IngredientLot.lot_code)
    )
    if status is not None:
        query = query.where(IngredientLot.status == status)
    rows = session.execute(query).all()
    locked = set(
        session.scalars(
            select(Lock.target_id).where(
                Lock.active, Lock.target_type == "lot", Lock.target_id.in_([r[0].id for r in rows])
            )
        )
    )
    return [
        LotListOut(
            id=lot.id,
            lot_code=lot.lot_code,
            ingredient_code=ingredient.code,
            ingredient_name=ingredient.name,
            supplier_code=supplier_code,
            qty_kg=lot.qty_kg,
            status=lot.status,
            locked=lot.id in locked,
            received_at=received_at,
        )
        for lot, ingredient, supplier_code, received_at in rows
    ]


@router.get("/dishes", response_model=list[DishOut])
def list_dishes(session: DbSession):
    return session.scalars(select(Dish).order_by(Dish.code)).all()


@router.get("/delivery-points", response_model=list[DeliveryPointOut])
def list_delivery_points(session: DbSession):
    rows = session.execute(select(DeliveryPoint, CustomerOrg).join(CustomerOrg).order_by(DeliveryPoint.code))
    return [
        DeliveryPointOut(
            id=dp.id,
            code=dp.code,
            name=dp.name,
            address=dp.address,
            customer_alias=org.kc_org_alias,
            customer_name=org.name,
            customer_kind=org.kind,
        )
        for dp, org in rows
    ]


@router.get("/assets", response_model=list[AssetOut])
def list_assets(session: DbSession):
    return session.scalars(select(Asset).order_by(Asset.code)).all()


@router.get("/rule-thresholds", response_model=list[ThresholdOut])
def list_thresholds(session: DbSession):
    return session.scalars(select(RuleThreshold).where(RuleThreshold.enabled).order_by(RuleThreshold.code)).all()


@router.get("/menus", response_model=list[MenuOut])
def list_menus(
    session: DbSession,
    service_day: date | None = Query(None, alias="service_date"),
    meal_slot: MealSlot | None = None,
):
    query = (
        select(Menu, CustomerOrg.kc_org_alias)
        .outerjoin(CustomerOrg, CustomerOrg.id == Menu.customer_org_id)
        .where(Menu.service_date == (service_day or service_date()))
        .order_by(Menu.meal_slot)
    )
    if meal_slot is not None:
        query = query.where(Menu.meal_slot == meal_slot)
    menus = session.execute(query).all()
    dishes: dict = {}
    if menus:
        rows = session.execute(
            select(MenuItem.menu_id, Dish).join(Dish).where(MenuItem.menu_id.in_([m.id for m, _ in menus]))
        )
        for menu_id, dish in rows:
            dishes.setdefault(menu_id, []).append(DishOut.model_validate(dish))
    return [
        MenuOut(
            id=m.id,
            service_date=m.service_date,
            meal_slot=m.meal_slot,
            meal_end_at=m.meal_end_at,
            customer_alias=alias,
            dishes=sorted(dishes.get(m.id, []), key=lambda d: d.code),
        )
        for m, alias in menus
    ]
