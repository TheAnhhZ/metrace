# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Recall notices: one per (incident, delivery point), idempotent (upsert).

A notice only describes that delivery point's own shipments (a customer never
learns about other customers). It carries the audit head (seq, hash) as an
anchor outside the database.
"""

import uuid
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.audit_hash_chain import chain_head
from app.models.cooking import CookingBatch, Dish
from app.models.incident import Incident, Lock, RecallNotice
from app.models.kitchen_and_customers import DeliveryPoint
from app.models.shipment import Shipment, ShipmentItem
from app.services import lineage_query
from app.services.lineage_query import NodeRef

ACTION = {"held": "hold", "planned": "hold", "ready": "hold", "dispatched": "recall", "delivered": "recall"}


def _affected(session: Session, incident_id: uuid.UUID):
    locks = session.scalars(select(Lock).where(Lock.incident_id == incident_id, Lock.active)).all()
    if not locks:
        return {}
    down = lineage_query.forward_many(
        session,
        [NodeRef(lock.target_type, lock.target_id) for lock in locks],
        max_depth=lineage_query.MAX_DEPTH_CAP,
        max_nodes=5000,
    )
    rows = session.execute(
        select(Shipment, ShipmentItem.portions, CookingBatch.batch_code, Dish.name)
        .join(ShipmentItem, ShipmentItem.shipment_id == Shipment.id)
        .join(CookingBatch, CookingBatch.id == ShipmentItem.batch_id)
        .join(Dish, Dish.id == CookingBatch.dish_id)
        .where(Shipment.id.in_(down.ids("shipment")), ShipmentItem.batch_id.in_(down.ids("batch")))
        .order_by(Shipment.code, CookingBatch.batch_code)
    ).all()
    per_point: dict = defaultdict(dict)
    for shipment, portions, batch_code, dish in rows:
        entry = per_point[shipment.delivery_point_id].setdefault(
            shipment.code,
            {
                "shipment": shipment.code,
                "service_date": shipment.service_date.isoformat(),
                "meal_slot": shipment.meal_slot,
                "status": shipment.status,
                "action": ACTION.get(shipment.status, "hold"),
                "items": [],
            },
        )
        entry["items"].append({"batch": batch_code, "dish": dish, "portions": portions})
    return per_point


def upsert_notices(session: Session, incident_id: uuid.UUID, anchor: tuple[int, str] | None = None) -> int:
    incident = session.get(Incident, incident_id)
    per_point = _affected(session, incident_id)
    if not per_point:
        return 0
    seq, digest = anchor or chain_head(session)
    for point_id, shipments in per_point.items():
        point = session.get(DeliveryPoint, point_id)
        content = {
            "incident": incident.code,
            "title": incident.title,
            "delivery_point": point.name,
            "shipments": list(shipments.values()),
        }
        session.execute(
            insert(RecallNotice)
            .values(
                id=uuid.uuid4(),
                incident_id=incident_id,
                customer_org_id=point.customer_org_id,
                delivery_point_id=point_id,
                content=content,
                audit_seq=seq,
                audit_hash=digest,
            )
            .on_conflict_do_update(constraint="uq_recall_notice_point", set_={"content": content})
        )
    return len(per_point)


def points_missing_notice(session: Session) -> list[uuid.UUID]:
    """Incidents with active locks whose affected points lack a notice (reconciler)."""
    incident_ids = session.scalars(select(Lock.incident_id).where(Lock.active).distinct()).all()
    missing = []
    for incident_id in incident_ids:
        per_point = _affected(session, incident_id)
        have = set(
            session.scalars(select(RecallNotice.delivery_point_id).where(RecallNotice.incident_id == incident_id))
        )
        if set(per_point) - have:
            missing.append(incident_id)
    return missing
