# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""P6: flag complaints whose answer deadline (`sla_due_at`) passed. No BPMN:
a 30 s sweep in the worker, every channel, each breach audited once."""

import logging

from sqlalchemy import text

from app.core.audit_hash_chain import append_audit
from app.core.database import new_session
from app.worker.handler_registry import reconciler

log = logging.getLogger("metrace.worker.sla")

SWEEP_SQL = text(
    """
    UPDATE complaint SET sla_breached = true, updated_at = now()
     WHERE sla_due_at < now() AND NOT sla_breached AND status <> 'resolved'
    RETURNING id, code
    """
)


@reconciler
def sweep_complaint_sla() -> int:
    with new_session() as session:
        breached = session.execute(SWEEP_SQL).all()
        for complaint_id, code in breached:
            append_audit(
                session,
                actor="worker",
                action="complaint.sla_breached",
                entity_type="complaint",
                entity_id=complaint_id,
                payload={"code": code},
            )
            log.warning("complaint %s missed its answer deadline", code)
        session.commit()
    return len(breached)
