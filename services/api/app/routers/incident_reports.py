# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Incident report: request an AI draft (worker, slow lane), edit, approve (QA).

The draft never triggers anything. Approval freezes the text and records its
hash in the audit chain.
"""

import hashlib
import uuid

from fastapi import Depends

from app.core.audit_hash_chain import append_audit
from app.core.authentication import CurrentPrincipal
from app.core.authorization import internal_router, require_any_role
from app.core.business_time import utcnow
from app.core.database import DbSession, get_or_404
from app.core.errors import AppError
from app.core.outbox import emit
from app.core.reason_codes import ReasonCode
from app.models.incident import Incident
from app.schemas.incident import IncidentOut, ReportIn

router = internal_router(
    prefix="/api/v1/incidents", tags=["incident report"], dependencies=[Depends(require_any_role({"qa"}))]
)


@router.post("/{incident_id}/report-draft", status_code=202)
def request_draft(incident_id: uuid.UUID, session: DbSession, principal: CurrentPrincipal):
    incident = get_or_404(session, Incident, incident_id, "incident")
    emit(
        session,
        "report.draft_requested",
        {"incident_id": incident.id, "requested_by": principal.username},
        aggregate_type="incident",
        aggregate_id=incident.id,
        lane="slow",
    )
    session.commit()
    return {"status": "queued"}


@router.put("/{incident_id}/report", response_model=IncidentOut)
def edit_report(incident_id: uuid.UUID, req: ReportIn, session: DbSession, principal: CurrentPrincipal):
    incident = get_or_404(session, Incident, incident_id, "incident", for_update=True)
    if incident.report_final is not None:
        raise AppError(409, ReasonCode.CONFLICT, "Report already approved")
    incident.report_draft = req.text
    session.commit()
    return incident


@router.post("/{incident_id}/report/approve", response_model=IncidentOut)
def approve_report(incident_id: uuid.UUID, session: DbSession, principal: CurrentPrincipal):
    incident = get_or_404(session, Incident, incident_id, "incident", for_update=True)
    if not incident.report_draft:
        raise AppError(422, ReasonCode.VALIDATION_ERROR, "No draft to approve")
    if incident.report_final is not None:
        raise AppError(409, ReasonCode.CONFLICT, "Report already approved")
    incident.report_final = incident.report_draft
    incident.report_approved_by, incident.report_approved_at = principal.username, utcnow()
    append_audit(
        session,
        actor=principal.username,
        action="incident.report_approved",
        entity_type="incident",
        entity_id=incident.id,
        payload={"sha256": hashlib.sha256(incident.report_final.encode()).hexdigest(), "model": incident.report_model},
    )
    session.commit()
    return incident
