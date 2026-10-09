# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Complaints (internal channel), cluster suggestions, incidents, locks, four-eyes close."""

import uuid

from fastapi import Depends, Query
from sqlalchemy import select

from app.core.authentication import CurrentPrincipal
from app.core.authorization import internal_router, require_any_role
from app.core.database import DbSession, get_or_404
from app.models.enums import ComplaintStatus
from app.models.incident import Complaint, Incident
from app.schemas.incident import (
    CloseRequestIn,
    CloseRequestOut,
    ClusterSuggestion,
    ComplaintIn,
    ComplaintOut,
    ConfirmSuspectsIn,
    IncidentDetailOut,
    IncidentIn,
    IncidentOut,
    LockResultOut,
)
from app.services import complaint_service, incident_service
from app.services.incident_view import incident_detail

router = internal_router(prefix="/api/v1", tags=["incidents"])

INTAKE = [Depends(require_any_role({"cskh", "qa"}))]
QA = [Depends(require_any_role({"qa"}))]
APPROVER = [Depends(require_any_role({"approver"}))]


@router.post("/complaints", response_model=ComplaintOut, status_code=201, dependencies=INTAKE)
def create_complaint(req: ComplaintIn, session: DbSession, principal: CurrentPrincipal):
    return complaint_service.create_complaint(session, principal, req)


@router.get("/complaints", response_model=list[ComplaintOut])
def list_complaints(session: DbSession, status: ComplaintStatus | None = None):
    query = select(Complaint).order_by(Complaint.created_at.desc()).limit(200)
    if status:
        query = query.where(Complaint.status == status)
    return session.scalars(query).all()


@router.get("/complaints/cluster-suggestions", response_model=list[ClusterSuggestion])
def cluster_suggestions(
    session: DbSession, window_h: int = Query(48, ge=1, le=168), min_points: int = Query(2, ge=1, le=20)
):
    return complaint_service.cluster_suggestions(session, window_h, min_points)


@router.get("/incidents", response_model=list[IncidentOut])
def list_incidents(session: DbSession):
    return session.scalars(select(Incident).order_by(Incident.opened_at.desc())).all()


@router.post("/incidents", response_model=IncidentOut, status_code=201, dependencies=QA)
def open_incident(req: IncidentIn, session: DbSession, principal: CurrentPrincipal):
    return incident_service.open_incident(session, principal, req)


@router.get("/incidents/{incident_id}", response_model=IncidentDetailOut)
def get_incident(incident_id: uuid.UUID, session: DbSession):
    return incident_detail(session, get_or_404(session, Incident, incident_id, "incident"))


@router.post("/incidents/{incident_id}/confirm-suspects", response_model=LockResultOut, dependencies=QA)
def confirm_suspects(incident_id: uuid.UUID, req: ConfirmSuspectsIn, session: DbSession, principal: CurrentPrincipal):
    incident, result = incident_service.confirm_suspects(session, principal, incident_id, req)
    return LockResultOut(
        incident=IncidentOut.model_validate(incident),
        targets=result.targets,
        held_shipments=result.held_shipments,
        already_dispatched=result.already_dispatched,
        delivery_points=result.delivery_points,
        audit_head={"seq": result.audit_head[0], "hash": result.audit_head[1]},
        elapsed_ms=result.elapsed_ms,
        truncated=result.truncated,
    )


@router.post(
    "/incidents/{incident_id}/close-requests", response_model=CloseRequestOut, status_code=201, dependencies=QA
)
def request_close(incident_id: uuid.UUID, req: CloseRequestIn, session: DbSession, principal: CurrentPrincipal):
    return incident_service.request_close(session, principal, incident_id, req.note)


@router.post("/close-requests/{request_id}/approve", response_model=IncidentOut, dependencies=APPROVER)
def approve_close(request_id: uuid.UUID, session: DbSession, principal: CurrentPrincipal):
    return incident_service.approve_close(session, principal, request_id)


@router.post("/close-requests/{request_id}/reject", response_model=CloseRequestOut, dependencies=APPROVER)
def reject_close(request_id: uuid.UUID, req: CloseRequestIn, session: DbSession, principal: CurrentPrincipal):
    return incident_service.reject_close(session, principal, request_id, req.note)
