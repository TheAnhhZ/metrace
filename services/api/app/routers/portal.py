# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Customer portal API (`customer_staff` only), scoped by the token's organizations."""

import uuid
from datetime import date, datetime, timedelta

from pydantic import BaseModel, Field

from app.core.authentication import CurrentPrincipal
from app.core.authorization import org_scope, portal_router
from app.core.business_time import service_date, utcnow
from app.core.database import DbSession
from app.schemas.incident import ComplaintIn, ComplaintOut
from app.services import portal_queries

router = portal_router(prefix="/api/v1/portal", tags=["portal"])


class DeliveryItem(BaseModel):
    dish: str
    batch_code: str
    portions: int
    sample_sealed: bool


class DeliveryOut(BaseModel):
    id: uuid.UUID
    code: str
    delivery_point: str
    service_date: date
    meal_slot: str
    status: str
    dispatched_at: datetime | None
    delivered_at: datetime | None
    items: list[DeliveryItem]


class PortalComplaintIn(ComplaintIn):
    file_ids: list[uuid.UUID] = Field(default_factory=list, max_length=5)


class PortalComplaintsOut(BaseModel):
    server_now: datetime
    complaints: list[ComplaintOut]


class NoticeOut(BaseModel):
    id: uuid.UUID
    incident_id: uuid.UUID
    delivery_point_id: uuid.UUID
    content: dict
    audit_seq: int
    audit_hash: str
    created_at: datetime
    acknowledged_at: datetime | None
    acknowledged_by: str | None

    model_config = {"from_attributes": True}


@router.get("/deliveries", response_model=list[DeliveryOut])
def list_deliveries(session: DbSession, principal: CurrentPrincipal, days: int = 3):
    last = service_date()
    first = last - timedelta(days=max(0, min(days, 31)) - 1)
    return portal_queries.deliveries(session, org_scope(principal), first, last)


@router.get("/complaints", response_model=PortalComplaintsOut)
def list_complaints(session: DbSession, principal: CurrentPrincipal):
    items = portal_queries.complaints(session, org_scope(principal))
    return PortalComplaintsOut(server_now=utcnow(), complaints=[ComplaintOut.model_validate(c) for c in items])


@router.post("/complaints", response_model=ComplaintOut, status_code=201)
def create_complaint(req: PortalComplaintIn, session: DbSession, principal: CurrentPrincipal):
    return portal_queries.create_complaint(session, principal, org_scope(principal), req, req.file_ids)


@router.get("/notices", response_model=list[NoticeOut])
def list_notices(session: DbSession, principal: CurrentPrincipal):
    return portal_queries.notices(session, org_scope(principal))


@router.post("/notices/{notice_id}/acknowledge", response_model=NoticeOut)
def acknowledge(notice_id: uuid.UUID, session: DbSession, principal: CurrentPrincipal):
    return portal_queries.acknowledge_notice(session, principal, org_scope(principal), notice_id)
