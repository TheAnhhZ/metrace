# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Customer portal read/write, always filtered by the organizations IN THE TOKEN
(never by a query parameter). Another organization's data answers 404, so a
customer cannot even learn that it exists."""

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit_hash_chain import append_audit
from app.core.authorization import OrgScope
from app.core.business_time import utcnow
from app.core.errors import not_found
from app.core.principal import Principal
from app.models.cooking import CookingBatch, Dish, RetainedSample
from app.models.enums import ComplaintChannel, SampleStatus
from app.models.incident import Complaint, RecallNotice
from app.models.kitchen_and_customers import CustomerOrg, DeliveryPoint
from app.models.platform import FileObject
from app.models.shipment import Shipment, ShipmentItem
from app.schemas.incident import ComplaintIn
from app.services import complaint_service


def _org_ids(session: Session, scope: OrgScope) -> list[uuid.UUID]:
    return list(session.scalars(select(CustomerOrg.id).where(CustomerOrg.kc_org_alias.in_(scope.aliases))))


def assert_refs_in_org(session: Session, scope: OrgScope, *, delivery_point_id=None, file_ids=()) -> None:
    """Every referenced id must belong to one of the caller's organizations, else 404."""
    org_ids = _org_ids(session, scope)
    if delivery_point_id is not None:
        point = session.get(DeliveryPoint, delivery_point_id)
        if point is None or point.customer_org_id not in org_ids:
            raise not_found("delivery point")
    if file_ids:
        files = session.scalars(select(FileObject).where(FileObject.id.in_(list(file_ids)))).all()
        if len(files) != len(set(file_ids)) or any(f.owner_org_alias not in scope.aliases for f in files):
            raise not_found("file")


def deliveries(session: Session, scope: OrgScope, first: date, last: date) -> list[dict]:
    rows = session.execute(
        select(Shipment, DeliveryPoint.name, ShipmentItem.portions, CookingBatch, Dish.name)
        .join(DeliveryPoint, DeliveryPoint.id == Shipment.delivery_point_id)
        .join(CustomerOrg, CustomerOrg.id == DeliveryPoint.customer_org_id)
        .join(ShipmentItem, ShipmentItem.shipment_id == Shipment.id)
        .join(CookingBatch, CookingBatch.id == ShipmentItem.batch_id)
        .join(Dish, Dish.id == CookingBatch.dish_id)
        .where(CustomerOrg.kc_org_alias.in_(scope.aliases), Shipment.service_date.between(first, last))
        .order_by(Shipment.service_date.desc(), Shipment.meal_slot, Shipment.code, Dish.name)
    ).all()
    sealed = set(
        session.scalars(
            select(RetainedSample.batch_id).where(
                RetainedSample.batch_id.in_([r[3].id for r in rows]), RetainedSample.status == SampleStatus.STORED
            )
        )
    )
    out: dict = {}
    for shipment, point, portions, batch, dish in rows:
        entry = out.setdefault(
            shipment.id,
            {
                "id": shipment.id,
                "code": shipment.code,
                "delivery_point": point,
                "service_date": shipment.service_date,
                "meal_slot": shipment.meal_slot,
                "status": shipment.status,
                "dispatched_at": shipment.dispatched_at,
                "delivered_at": shipment.delivered_at,
                "items": [],
            },
        )
        entry["items"].append(
            {"dish": dish, "batch_code": batch.batch_code, "portions": portions, "sample_sealed": batch.id in sealed}
        )
    return list(out.values())


def complaints(session: Session, scope: OrgScope) -> list[Complaint]:
    return session.scalars(
        select(Complaint)
        .join(CustomerOrg, CustomerOrg.id == Complaint.customer_org_id)
        .where(CustomerOrg.kc_org_alias.in_(scope.aliases))
        .order_by(Complaint.created_at.desc())
    ).all()


def create_complaint(session: Session, principal: Principal, scope: OrgScope, req: ComplaintIn, file_ids):
    assert_refs_in_org(session, scope, delivery_point_id=req.delivery_point_id, file_ids=file_ids)
    return complaint_service.create_complaint(
        session, principal, req, channel=ComplaintChannel.PORTAL, file_ids=file_ids
    )


def notices(session: Session, scope: OrgScope) -> list[RecallNotice]:
    return session.scalars(
        select(RecallNotice)
        .join(CustomerOrg, CustomerOrg.id == RecallNotice.customer_org_id)
        .where(CustomerOrg.kc_org_alias.in_(scope.aliases))
        .order_by(RecallNotice.created_at.desc())
    ).all()


def acknowledge_notice(session: Session, principal: Principal, scope: OrgScope, notice_id: uuid.UUID):
    notice = session.get(RecallNotice, notice_id, with_for_update=True)
    if notice is None or notice.customer_org_id not in _org_ids(session, scope):
        raise not_found("notice")
    if notice.acknowledged_at is None:
        notice.acknowledged_at, notice.acknowledged_by = utcnow(), principal.username
        append_audit(
            session,
            actor=principal.username,
            action="notice.acknowledged",
            entity_type="recall_notice",
            entity_id=notice.id,
            payload={"incident": notice.incident_id},
        )
        session.commit()
    return notice
