# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Decorate a LineageResult for screens and the CLI: human labels, lock state,
shipment/batch status and portions that reached each delivery point."""

import uuid
from collections import defaultdict
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.cooking import CookingBatch, Dish
from app.models.incident import Lock
from app.models.kitchen_and_customers import Asset, CustomerOrg, DeliveryPoint
from app.models.shipment import Shipment, ShipmentItem
from app.models.supplier_and_lots import Ingredient, IngredientLot, Supplier
from app.services.lineage_query import LineageResult, NodeRef

LOCKABLE_TYPES = ("batch", "lot", "supplier")
MODEL_BY_TYPE = {
    "supplier": Supplier,
    "lot": IngredientLot,
    "batch": CookingBatch,
    "shipment": Shipment,
    "delivery_point": DeliveryPoint,
    "asset": Asset,
}


CODE_COLUMN = {
    "supplier": Supplier.code,
    "lot": IngredientLot.lot_code,
    "batch": CookingBatch.batch_code,
    "shipment": Shipment.code,
    "delivery_point": DeliveryPoint.code,
    "asset": Asset.code,
}


def node_exists(session: Session, node: NodeRef) -> bool:
    model = MODEL_BY_TYPE.get(node.type)
    return model is not None and session.get(model, node.id) is not None


def resolve_node(session: Session, node_type: str, ref: str) -> NodeRef | None:
    """A node by UUID or by its business code (e.g. LOT-20261009-GA, B-20261009-lunch-COM)."""
    try:
        node = NodeRef(node_type, uuid.UUID(ref))
        return node if node_exists(session, node) else None
    except ValueError:
        model, column = MODEL_BY_TYPE.get(node_type), CODE_COLUMN.get(node_type)
        if model is None:
            return None
        found = session.scalar(select(model.id).where(column == ref))
        return NodeRef(node_type, found) if found else None


def _labels(session: Session, result: LineageResult) -> dict[NodeRef, dict[str, Any]]:
    info: dict[NodeRef, dict[str, Any]] = {}

    def put(node_type: str, node_id: uuid.UUID, label: str, **attrs: Any) -> None:
        info[NodeRef(node_type, node_id)] = {"label": label, **attrs}

    if ids := result.ids("supplier"):
        for s in session.scalars(select(Supplier).where(Supplier.id.in_(ids))):
            put("supplier", s.id, f"{s.code} · {s.name}", status=s.status)
    if ids := result.ids("lot"):
        rows = session.execute(select(IngredientLot, Ingredient.name).join(Ingredient).where(IngredientLot.id.in_(ids)))
        for lot, ingredient in rows:
            put("lot", lot.id, f"{lot.lot_code} · {ingredient}", status=lot.status)
    if ids := result.ids("batch"):
        for batch, dish in session.execute(select(CookingBatch, Dish.name).join(Dish).where(CookingBatch.id.in_(ids))):
            put("batch", batch.id, f"{batch.batch_code} · {dish}", status=batch.status)
    if ids := result.ids("shipment"):
        for s in session.scalars(select(Shipment).where(Shipment.id.in_(ids))):
            put(
                "shipment",
                s.id,
                s.code,
                status=s.status,
                service_date=s.service_date.isoformat(),
                meal_slot=s.meal_slot,
            )
    if ids := result.ids("delivery_point"):
        rows = session.execute(
            select(DeliveryPoint, CustomerOrg.kc_org_alias).join(CustomerOrg).where(DeliveryPoint.id.in_(ids))
        )
        for dp, org in rows:
            put("delivery_point", dp.id, dp.name, org=org)
    if ids := result.ids("asset"):
        for a in session.scalars(select(Asset).where(Asset.id.in_(ids))):
            put("asset", a.id, f"{a.code} · {a.name}", asset_type=a.type)
    return info


def _locked(session: Session, result: LineageResult) -> set[NodeRef]:
    candidates = [n for n in result.nodes if n.type in LOCKABLE_TYPES]
    if not candidates:
        return set()
    rows = session.execute(
        select(Lock.target_type, Lock.target_id)
        .where(Lock.active, Lock.target_id.in_([n.id for n in candidates]))
        .distinct()
    )
    return {NodeRef(t, i) for t, i in rows}


def _portions_per_point(session: Session, result: LineageResult) -> dict[uuid.UUID, int]:
    batches, shipments = result.ids("batch"), result.ids("shipment")
    if not batches or not shipments:
        return {}
    rows = session.execute(
        select(Shipment.delivery_point_id, func.sum(ShipmentItem.portions))
        .join(ShipmentItem, ShipmentItem.shipment_id == Shipment.id)
        .where(Shipment.id.in_(shipments), ShipmentItem.batch_id.in_(batches))
        .group_by(Shipment.delivery_point_id)
    )
    totals: dict[uuid.UUID, int] = defaultdict(int)
    for dp_id, portions in rows:
        totals[dp_id] += int(portions or 0)
    return totals


def present(session: Session, result: LineageResult) -> dict[str, Any]:
    info = _labels(session, result)
    locked = _locked(session, result)
    portions = _portions_per_point(session, result)
    nodes = []
    for node, depth in sorted(result.depths.items(), key=lambda item: (item[1], item[0])):
        attrs = info.get(node, {"label": node.key})
        nodes.append(
            {
                "type": node.type,
                "id": node.id,
                "depth": depth,
                "locked": node in locked,
                "portions": portions.get(node.id) if node.type == "delivery_point" else None,
                **attrs,
            }
        )
    edges = [{"from": a.key, "to": b.key} for a, b in sorted(result.edges)]
    return {"nodes": nodes, "edges": edges, "truncated": result.truncated}
