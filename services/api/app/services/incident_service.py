# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Incidents: open from complaints, confirm suspects (=> locks), four-eyes close.

`incident.status` is owned by the API. Flowable only orders human tasks and
timers; every Flowable call goes through the outbox and the worker.
"""

import uuid

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.audit_hash_chain import append_audit
from app.core.business_time import utcnow
from app.core.database import get_or_404
from app.core.errors import AppError
from app.core.outbox import emit
from app.core.principal import Principal
from app.core.reason_codes import ReasonCode
from app.models.enums import CloseRequestStatus, ComplaintStatus, IncidentStatus
from app.models.incident import Complaint, Incident, IncidentCloseRequest, IncidentComplaint
from app.schemas.incident import ConfirmSuspectsIn, IncidentIn
from app.services import lock_service
from app.services.lineage_query import NodeRef


def _require_open(incident: Incident) -> None:
    if incident.status == IncidentStatus.CLOSED:
        raise AppError(409, ReasonCode.INCIDENT_CLOSED, "Incident is closed")


def open_incident(session: Session, principal: Principal, req: IncidentIn) -> Incident:
    seq = session.scalar(text("SELECT nextval('incident_code_seq')"))  # race-free numbering
    incident = Incident(code=f"INC-{seq:03d}", title=req.title, opened_by=principal.username, suspects=[])
    session.add(incident)
    session.flush()
    for complaint in session.scalars(select(Complaint).where(Complaint.id.in_(req.complaint_ids))):
        session.add(IncidentComplaint(incident_id=incident.id, complaint_id=complaint.id))
        complaint.status = ComplaintStatus.LINKED
    append_audit(
        session,
        actor=principal.username,
        action="incident.opened",
        entity_type="incident",
        entity_id=incident.id,
        payload={"code": incident.code, "complaints": req.complaint_ids},
    )
    emit(session, "incident.opened", {"incident_id": incident.id}, aggregate_type="incident", aggregate_id=incident.id)
    session.commit()
    return incident


def confirm_suspects(session: Session, principal: Principal, incident_id: uuid.UUID, req: ConfirmSuspectsIn):
    incident = get_or_404(session, Incident, incident_id, "incident", for_update=True)
    _require_open(incident)
    suspects = [NodeRef(n.type, n.id) for n in req.nodes]
    result = lock_service.apply(session, incident, suspects, req.lock_lots, principal.username)
    known = {(s["type"], s["id"]) for s in incident.suspects}
    incident.suspects = incident.suspects + [
        {"type": s.type, "id": str(s.id)} for s in suspects if (s.type, str(s.id)) not in known
    ]
    incident.status = IncidentStatus.CONTAINED
    emit(
        session,
        "incident.suspects_confirmed",
        {"incident_id": incident.id},
        aggregate_type="incident",
        aggregate_id=incident.id,
    )
    session.commit()
    return incident, result


def request_close(session: Session, principal: Principal, incident_id: uuid.UUID, note: str) -> IncidentCloseRequest:
    incident = get_or_404(session, Incident, incident_id, "incident", for_update=True)
    _require_open(incident)
    pending = session.scalar(
        select(IncidentCloseRequest).where(
            IncidentCloseRequest.incident_id == incident.id, IncidentCloseRequest.status == CloseRequestStatus.PENDING
        )
    )
    if pending:
        raise AppError(409, ReasonCode.CLOSE_REQUEST_PENDING, "A close request is already pending")
    request = IncidentCloseRequest(incident_id=incident.id, requested_by=principal.username, note=note)
    session.add(request)
    session.flush()
    append_audit(
        session,
        actor=principal.username,
        action="incident.close_requested",
        entity_type="incident",
        entity_id=incident.id,
        payload={"request": request.id},
    )
    session.commit()
    return request


def approve_close(session: Session, principal: Principal, request_id: uuid.UUID) -> Incident:
    """Four-eyes: the approver must hold `approver` (router) and differ from the requester."""
    request = get_or_404(session, IncidentCloseRequest, request_id, "close request", for_update=True)
    if request.status != CloseRequestStatus.PENDING:
        raise AppError(409, ReasonCode.CONFLICT, f"Close request is {request.status}")
    if request.requested_by == principal.username:
        raise AppError(422, ReasonCode.P5_SAME_PERSON, "Requester and approver must be different people", rule="P5")
    incident = get_or_404(session, Incident, request.incident_id, "incident", for_update=True)
    _require_open(incident)
    released = lock_service.release_for_incident(session, incident.id, principal.username)
    now = utcnow()
    request.status, request.decided_by, request.decided_at = CloseRequestStatus.APPROVED, principal.username, now
    incident.status, incident.closed_at = IncidentStatus.CLOSED, now
    for complaint in session.scalars(
        select(Complaint).join(IncidentComplaint).where(IncidentComplaint.incident_id == incident.id)
    ):
        complaint.status, complaint.resolved_at = ComplaintStatus.RESOLVED, now
    append_audit(
        session,
        actor=principal.username,
        action="incident.closed",
        entity_type="incident",
        entity_id=incident.id,
        payload={"requested_by": request.requested_by, "approved_by": principal.username, "locks_released": released},
    )
    emit(session, "incident.closed", {"incident_id": incident.id}, aggregate_type="incident", aggregate_id=incident.id)
    session.commit()
    return incident
