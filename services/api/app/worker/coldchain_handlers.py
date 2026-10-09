# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Cold-chain alerts in Flowable (`cold-chain-alert`): QA checks the fridge under a
timer that escalates to the director. Started/completed only by the worker."""

import logging
import uuid

from sqlalchemy import select

from app.core.database import new_session
from app.core.settings import get_settings
from app.models.coldchain import AlertStatus, ColdChainAlert
from app.models.kitchen_and_customers import Asset
from app.worker.handler_registry import OutboxMessage, handles, reconciler
from app.workflow.flowable_client import FlowableClient

log = logging.getLogger("metrace.worker.coldchain")
PROCESS_KEY = "cold-chain-alert"


def _flowable() -> FlowableClient:
    s = get_settings()
    return FlowableClient(s.flowable_url, s.flowable_user, s.flowable_password)


def _start(flowable: FlowableClient, alert: ColdChainAlert, asset_code: str) -> str:
    instance = flowable.start_process(
        PROCESS_KEY, f"coldchain:{alert.id}", {"assetCode": asset_code, "checkSla": get_settings().coldchain_check_sla}
    )
    return instance["id"]


@handles("coldchain.breach")
def start_alert_process(message: OutboxMessage) -> None:
    with new_session() as session, _flowable() as flowable:
        alert = session.get(ColdChainAlert, uuid.UUID(message.payload["alert_id"]))
        if alert is None or alert.process_instance_id:
            return
        alert.process_instance_id = _start(flowable, alert, message.payload["asset"])
        session.commit()
        log.warning("cold-chain alert %s for %s: process started", alert.id, message.payload["asset"])


@handles("coldchain.acknowledged")
def complete_fridge_check(message: OutboxMessage) -> None:
    with _flowable() as flowable:
        instance = flowable.find_process_instance(PROCESS_KEY, f"coldchain:{message.payload['alert_id']}")
        if instance is None:
            return
        for key in ("qa_check_fridge", "director_escalation"):  # no stale escalation task left behind
            for task in flowable.tasks(instance["id"], key):
                flowable.complete_task(task["id"])


@reconciler
def reconcile_alert_processes() -> None:
    with new_session() as session:
        rows = session.execute(
            select(ColdChainAlert, Asset.code)
            .join(Asset, Asset.id == ColdChainAlert.asset_id)
            .where(ColdChainAlert.status == AlertStatus.OPEN, ColdChainAlert.process_instance_id.is_(None))
        ).all()
        if not rows:
            return
        with _flowable() as flowable:
            for alert, code in rows:
                alert.process_instance_id = _start(flowable, alert, code)
        session.commit()
