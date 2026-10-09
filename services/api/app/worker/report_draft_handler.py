# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Slow lane: draft an incident report with the local LLM (or the template)."""

import logging
import uuid

from app.core.database import new_session
from app.models.incident import Incident
from app.services.report_drafting import build_facts, draft_report
from app.worker.handler_registry import OutboxMessage, handles

log = logging.getLogger("metrace.worker.report")


@handles("report.draft_requested")
def draft_incident_report(message: OutboxMessage) -> None:
    incident_id = uuid.UUID(message.payload["incident_id"])
    with new_session() as session:
        incident = session.get(Incident, incident_id)
        if incident is None or incident.report_final is not None:
            return
        facts = build_facts(session, incident)
        draft_before = incident.report_draft
    text, model, prompt_sha = draft_report(facts)  # outside any transaction (may take 30 s)
    with new_session() as session:
        incident = session.get(Incident, incident_id, with_for_update=True)
        # Never overwrite QA: skip if approved meanwhile or edited while the model was writing.
        if incident.report_final is not None or incident.report_draft != draft_before:
            log.info("incident %s: draft discarded, report changed by QA meanwhile", incident_id)
            return
        incident.report_draft, incident.report_model, incident.report_prompt_sha256 = text, model, prompt_sha
        session.commit()
    log.info("incident %s: report draft ready (%s)", incident_id, model)
