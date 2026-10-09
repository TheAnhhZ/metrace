# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Guards that keep locked food out of kitchens and trucks.

Every guard and `lock_service.apply` take the SAME transaction-scoped advisory
lock (LOCK_NS), so reading lineage and writing locks/shipments never interleave
(no TOCTOU: a shipment created during an apply cannot slip through).
A node counts as locked while ANY incident holds an active lock on it.
Incomplete lineage (truncated walk) fails closed.
"""

import uuid
from collections.abc import Iterable

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.principal import Principal
from app.core.reason_codes import ReasonCode as RC
from app.models.cooking import CookingBatch
from app.models.incident import Complaint, Incident, IncidentComplaint, Lock
from app.models.shipment import Shipment, ShipmentItem
from app.rules.rule_result import RuleResult
from app.services import lineage_query
from app.services.lineage_query import NodeRef
from app.services.poka_yoke_logger import enforce

LOCK_NS = 42002


def serialize_lock_decisions(session: Session) -> None:
    session.execute(text("SELECT pg_advisory_xact_lock(:ns)"), {"ns": LOCK_NS})


def active_locks_on(session: Session, nodes: Iterable[NodeRef]) -> list[dict]:
    nodes = [n for n in nodes if n.type in ("batch", "lot", "supplier")]
    if not nodes:
        return []
    rows = session.execute(
        select(Lock.target_type, Lock.target_id, Incident.code)
        .join(Incident, Incident.id == Lock.incident_id)
        .where(Lock.active, Lock.target_id.in_([n.id for n in nodes]))
    ).all()
    wanted = {(n.type, n.id) for n in nodes}
    return [{"target": f"{t}:{i}", "incident": code} for t, i, code in rows if (t, i) in wanted]


def _upstream(session: Session, roots: list[NodeRef]) -> lineage_query.LineageResult:
    return lineage_query.backward_many(session, roots, max_depth=lineage_query.MAX_DEPTH_CAP)


def _check_upstream(session: Session, roots: list[NodeRef], rule: str, code: RC) -> RuleResult:
    result = RuleResult()
    walk = _upstream(session, roots)
    if walk.truncated:
        result.block(rule, RC.P3_LINEAGE_TRUNCATED if rule == "P3" else code, roots=[r.key for r in roots])
        return result
    if hits := active_locks_on(session, walk.nodes):
        result.block(rule, code, locks=hits)
    return result


def assert_input_allowed(
    session: Session, principal: Principal, batch: CookingBatch, lot_id: uuid.UUID | None, input_batch_id
) -> None:
    serialize_lock_decisions(session)
    source = NodeRef("lot", lot_id) if lot_id else NodeRef("batch", input_batch_id)
    result = _check_upstream(session, [source, NodeRef("batch", batch.id)], "P2", RC.P2_INPUT_LOCKED)
    enforce(session, result, principal, "batch", batch.id, {"input": source.key})


def assert_batch_not_locked(session: Session, principal: Principal, batch: CookingBatch) -> None:
    serialize_lock_decisions(session)
    result = _check_upstream(session, [NodeRef("batch", batch.id)], "P2", RC.P2_INPUT_LOCKED)
    enforce(session, result, principal, "batch", batch.id)


def assert_dispatchable(
    session: Session, principal: Principal, shipment: Shipment, extra_batch: uuid.UUID | None = None
):
    """Create/add-item/dispatch all go through here. Returns nothing; raises 422 when blocked."""
    serialize_lock_decisions(session)
    session.refresh(shipment, with_for_update=True)
    result = RuleResult()
    if shipment.status == "held":
        result.block("P3", RC.P3_SHIPMENT_HELD, shipment=shipment.code)
    batch_ids = set(session.scalars(select(ShipmentItem.batch_id).where(ShipmentItem.shipment_id == shipment.id)))
    if extra_batch:
        batch_ids.add(extra_batch)
    if batch_ids:
        result.extend(
            _check_upstream(session, [NodeRef("batch", b) for b in sorted(batch_ids)], "P3", RC.P3_UPSTREAM_LOCKED)
        )
    enforce(session, result, principal, "shipment", shipment.id)


def _open_incident_service_dates(session: Session) -> set:
    """Service dates of complaints attached to incidents that are not closed yet."""
    return set(
        session.scalars(
            select(Complaint.service_date)
            .join(IncidentComplaint, IncidentComplaint.complaint_id == Complaint.id)
            .join(Incident, Incident.id == IncidentComplaint.incident_id)
            .where(Incident.status != "closed")
        )
    )


def assert_sample_discard_allowed(session: Session, principal: Principal, sample_id, batch: CookingBatch) -> None:
    """Never destroy evidence while an incident could need it: the batch (or its upstream)
    is locked, an open incident names it as a suspect, or covers its service day."""
    serialize_lock_decisions(session)  # a discard must not race an incident being locked
    locked = _check_upstream(session, [NodeRef("batch", batch.id)], "P4", RC.P4_DISCARD_DURING_INCIDENT)
    suspected = session.scalars(
        select(Incident.code).where(
            Incident.status != "closed", Incident.suspects.contains([{"type": "batch", "id": str(batch.id)}])
        )
    ).all()
    same_day = batch.service_date in _open_incident_service_dates(session)
    result = RuleResult()
    if locked.violations or suspected or same_day:
        open_codes = session.scalars(select(Incident.code).where(Incident.status != "closed")).all()
        result.block("P4", RC.P4_DISCARD_DURING_INCIDENT, open_incidents=sorted(open_codes))
    enforce(session, result, principal, "sample", sample_id)
