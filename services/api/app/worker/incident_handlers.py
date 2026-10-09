# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Outbox handlers + reconcilers for incidents. Only the worker talks to Flowable.

- incident.opened             -> start `incident-recall` (business key incident:<id>, idempotent)
- incident.suspects_confirmed -> complete `qa_triage` if it is still open
- incident.closed             -> complete `close_approval` if it is still open
- lock.applied                -> recall notices per affected delivery point (idempotent)
Reconcilers (30 s): start missing processes, mirror director escalation as a red
flag, create notices that a crash may have skipped.
"""

import logging
import uuid

from sqlalchemy import select

from app.core.database import new_session
from app.core.settings import get_settings
from app.models.incident import Incident
from app.worker.handler_registry import OutboxMessage, handles, reconciler
from app.worker.recall_notices import points_missing_notice, upsert_notices
from app.workflow.flowable_client import FlowableClient

log = logging.getLogger("metrace.worker.incident")
PROCESS_KEY = "incident-recall"


def _flowable() -> FlowableClient:
    s = get_settings()
    return FlowableClient(s.flowable_url, s.flowable_user, s.flowable_password)


def business_key(incident_id) -> str:
    return f"incident:{incident_id}"


def _complete_if_open(incident_id, task_key: str) -> None:
    with _flowable() as flowable:
        instance = flowable.find_process_instance(PROCESS_KEY, business_key(incident_id))
        if instance is None:
            return  # reconciler will start it; nothing to complete yet
        for task in flowable.tasks(instance["id"], task_key):
            flowable.complete_task(task["id"])
            log.info("incident %s: completed %s", incident_id, task_key)


@handles("incident.opened")
def start_incident_process(message: OutboxMessage) -> None:
    incident_id = uuid.UUID(message.payload["incident_id"])
    with _flowable() as flowable:
        instance = flowable.start_process(
            PROCESS_KEY,
            business_key(incident_id),
            {"incidentId": str(incident_id), "triageSla": get_settings().incident_triage_sla},
        )
    with new_session() as session:
        incident = session.get(Incident, incident_id)
        if incident is not None and incident.process_instance_id != instance["id"]:
            incident.process_instance_id = instance["id"]
            session.commit()


@handles("incident.suspects_confirmed")
def complete_triage(message: OutboxMessage) -> None:
    _complete_if_open(message.payload["incident_id"], "qa_triage")


@handles("incident.closed")
def complete_close(message: OutboxMessage) -> None:
    _complete_if_open(message.payload["incident_id"], "qa_triage")
    _complete_if_open(message.payload["incident_id"], "close_approval")


@handles("lock.applied")
def create_recall_notices(message: OutboxMessage) -> None:
    incident_id = uuid.UUID(message.payload["incident_id"])
    with new_session() as session:
        count = upsert_notices(session, incident_id, (message.payload["audit_seq"], message.payload["audit_hash"]))
        session.commit()
    log.info("incident %s: %d recall notice(s)", incident_id, count)


@reconciler
def reconcile_incident_processes() -> None:
    with new_session() as session:
        incidents = session.scalars(select(Incident).where(Incident.status != "closed")).all()
        if not incidents:
            return
        with _flowable() as flowable:
            for incident in incidents:
                instance = flowable.start_process(
                    PROCESS_KEY,
                    business_key(incident.id),
                    {"incidentId": str(incident.id), "triageSla": get_settings().incident_triage_sla},
                )
                incident.process_instance_id = instance["id"]
                if not incident.escalated and flowable.tasks(instance["id"], "director_escalation"):
                    incident.escalated = True
                    log.info("incident %s escalated to director (triage SLA missed)", incident.code)
        session.commit()


@reconciler
def reconcile_missing_notices() -> None:
    with new_session() as session:
        for incident_id in points_missing_notice(session):
            upsert_notices(session, incident_id)
            log.warning("incident %s: created notices missed earlier", incident_id)
        session.commit()
