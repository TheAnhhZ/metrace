# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Complaints (internal channel; the portal channel reuses `create_complaint`) and
#3 cluster suggestions: plain SQL group-by, a SUGGESTION that QA confirms."""

import uuid
from datetime import timedelta

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.audit_hash_chain import append_audit
from app.core.business_time import utcnow
from app.core.database import get_or_404
from app.core.principal import Principal
from app.models.incident import Complaint
from app.models.kitchen_and_customers import DeliveryPoint
from app.schemas.incident import ComplaintIn
from app.services import lineage_query
from app.services.lineage_presenter import present
from app.services.lineage_query import NodeRef

SLA_HOURS = 24

CLUSTER_SQL = text(
    """
    SELECT si.batch_id, cb.batch_code, d.name AS dish,
           count(DISTINCT c.id) AS n_complaints, count(DISTINCT c.delivery_point_id) AS n_points,
           array_agg(DISTINCT c.id) AS complaint_ids
      FROM complaint c
      JOIN shipment sh ON sh.delivery_point_id = c.delivery_point_id
                      AND sh.service_date = c.service_date AND sh.meal_slot = c.meal_slot
      JOIN shipment_item si ON si.shipment_id = sh.id
      JOIN cooking_batch cb ON cb.id = si.batch_id
      JOIN dish d ON d.id = cb.dish_id
     WHERE c.status IN ('open', 'linked') AND c.created_at > now() - make_interval(hours => :window_h)
     GROUP BY si.batch_id, cb.batch_code, d.name
    HAVING count(DISTINCT c.delivery_point_id) >= :min_points
     ORDER BY n_points DESC, n_complaints DESC, cb.batch_code
     LIMIT 5
    """
)


def create_complaint(session: Session, principal: Principal, req: ComplaintIn) -> Complaint:
    point = get_or_404(session, DeliveryPoint, req.delivery_point_id, "delivery point")
    seq = session.scalar(select(func.count()).select_from(Complaint)) + 1
    complaint = Complaint(
        code=f"PA-{utcnow():%y%m%d}-{seq:03d}-{uuid.uuid4().hex[:3].upper()}",
        customer_org_id=point.customer_org_id,
        delivery_point_id=point.id,
        channel=req.channel,
        service_date=req.service_date,
        meal_slot=req.meal_slot,
        affected_count=req.affected_count,
        description=req.description,
        reported_by=principal.username,
        sla_due_at=utcnow() + timedelta(hours=SLA_HOURS),
    )
    session.add(complaint)
    session.flush()
    append_audit(
        session,
        actor=principal.username,
        action="complaint.created",
        entity_type="complaint",
        entity_id=complaint.id,
        payload={"code": complaint.code, "point": point.code},
    )
    session.commit()
    return complaint


def cluster_suggestions(session: Session, window_h: int, min_points: int) -> list[dict]:
    rows = session.execute(CLUSTER_SQL, {"window_h": window_h, "min_points": min_points}).all()
    suggestions = []
    for row in rows:
        upstream = lineage_query.backward(session, NodeRef("batch", row.batch_id))
        nodes = [
            n
            for n in present(session, upstream)["nodes"]
            if n["type"] in ("lot", "batch", "supplier") and n["id"] != row.batch_id
        ]
        suggestions.append(
            {
                "batch_id": row.batch_id,
                "batch_code": row.batch_code,
                "dish": row.dish,
                "n_complaints": row.n_complaints,
                "n_points": row.n_points,
                "complaint_ids": list(row.complaint_ids),
                "upstream": nodes,
            }
        )
    return suggestions
