# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Read side of an incident: complaints, locks, notices and affected shipments."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.business_time import utcnow
from app.models.incident import Complaint, Incident, IncidentCloseRequest, IncidentComplaint, Lock, RecallNotice
from app.models.kitchen_and_customers import CustomerOrg, DeliveryPoint
from app.models.shipment import Shipment
from app.schemas.incident import CloseRequestOut, ComplaintOut, IncidentDetailOut, IncidentOut, LockOut
from app.services import lineage_query
from app.services.lineage_query import NodeRef
from app.services.lock_service import WRITER_WALK, recall_since


def affected_shipments(session: Session, incident: Incident, locks: list[Lock]) -> list[dict]:
    targets = [NodeRef(lock.target_type, lock.target_id) for lock in locks]
    if not targets:
        return []
    # Same walk and window as the lock and the notices, so the three never disagree.
    down = lineage_query.forward_many(session, targets, **WRITER_WALK)
    rows = session.execute(
        select(Shipment, DeliveryPoint.name, CustomerOrg.kc_org_alias)
        .join(DeliveryPoint, DeliveryPoint.id == Shipment.delivery_point_id)
        .join(CustomerOrg, CustomerOrg.id == DeliveryPoint.customer_org_id)
        .where(
            Shipment.id.in_(down.ids("shipment")),
            Shipment.status.in_(["planned", "ready", "held"])
            | (Shipment.service_date >= recall_since(incident.opened_at)),
        )
        .order_by(Shipment.service_date, Shipment.code)
    ).all()
    return [
        {
            "id": s.id,
            "code": s.code,
            "status": s.status,
            "service_date": s.service_date.isoformat(),
            "meal_slot": s.meal_slot,
            "delivery_point": point,
            "org": org,
        }
        for s, point, org in rows
    ]


def incident_detail(session: Session, incident: Incident) -> IncidentDetailOut:
    complaints = session.scalars(
        select(Complaint)
        .join(IncidentComplaint)
        .where(IncidentComplaint.incident_id == incident.id)
        .order_by(Complaint.created_at)
    ).all()
    locks = session.scalars(select(Lock).where(Lock.incident_id == incident.id).order_by(Lock.created_at)).all()
    requests = session.scalars(
        select(IncidentCloseRequest)
        .where(IncidentCloseRequest.incident_id == incident.id)
        .order_by(IncidentCloseRequest.requested_at)
    ).all()
    notices = session.execute(
        select(RecallNotice, DeliveryPoint.name)
        .join(DeliveryPoint, DeliveryPoint.id == RecallNotice.delivery_point_id)
        .where(RecallNotice.incident_id == incident.id)
        .order_by(DeliveryPoint.code)
    ).all()
    return IncidentDetailOut(
        **IncidentOut.model_validate(incident).model_dump(),
        server_now=utcnow(),
        complaints=[ComplaintOut.model_validate(c) for c in complaints],
        locks=[LockOut.model_validate(lock) for lock in locks],
        close_requests=[CloseRequestOut.model_validate(r) for r in requests],
        notices=[
            {
                "id": n.id,
                "delivery_point": point,
                "created_at": n.created_at.isoformat(),
                "acknowledged_at": n.acknowledged_at.isoformat() if n.acknowledged_at else None,
                "audit_seq": n.audit_seq,
            }
            for n, point in notices
        ],
        shipments=affected_shipments(session, incident, locks),
    )
