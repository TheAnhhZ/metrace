# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Build the P3 DispatchSnapshot of a shipment from the database (reads only)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.cooking import CookingBatch, Menu, MenuItem, PortionCheck, RetainedSample
from app.models.enums import BatchStatus, ReceivingDecision, SampleStatus
from app.models.kitchen_and_customers import DeliveryPoint
from app.models.shipment import Shipment, ShipmentItem
from app.models.supplier_and_lots import IngredientLot, Receiving
from app.rules.dispatch_rules import DispatchItem, DispatchSnapshot
from app.services import lineage_query
from app.services.lineage_query import NodeRef


def _form1_complete(session: Session, batch_id) -> bool:
    """Every lot upstream of the batch came from an accepted receiving with documents."""
    walk = lineage_query.backward(session, NodeRef("batch", batch_id), **lineage_query.WRITER_WALK)
    lot_ids = walk.ids("lot")
    if walk.truncated or not lot_ids:  # an incomplete walk cannot prove Form 1 (fail closed)
        return False
    rows = session.execute(
        select(Receiving.decision, Receiving.document_file_ids)
        .join(IngredientLot, IngredientLot.receiving_id == Receiving.id)
        .where(lineage_query.any_of(IngredientLot.id, lot_ids))
    ).all()
    return all(decision == ReceivingDecision.ACCEPTED and docs for decision, docs in rows)


def _menu_dish_ids(session: Session, shipment: Shipment) -> set:
    org_id = session.scalar(select(DeliveryPoint.customer_org_id).where(DeliveryPoint.id == shipment.delivery_point_id))
    return set(
        session.scalars(
            select(MenuItem.dish_id)
            .join(Menu, Menu.id == MenuItem.menu_id)
            .where(
                Menu.service_date == shipment.service_date,
                Menu.meal_slot == shipment.meal_slot,
                (Menu.customer_org_id.is_(None)) | (Menu.customer_org_id == org_id),
            )
        )
    )


def build_dispatch_snapshot(session: Session, shipment: Shipment) -> DispatchSnapshot:
    menu = _menu_dish_ids(session, shipment)
    rows = session.execute(
        select(ShipmentItem, CookingBatch)
        .join(CookingBatch, CookingBatch.id == ShipmentItem.batch_id)
        .where(ShipmentItem.shipment_id == shipment.id)
        .order_by(CookingBatch.batch_code)
    ).all()
    checked = set(session.scalars(select(PortionCheck.batch_id).where(PortionCheck.shipment_id == shipment.id)))
    sampled = set(
        session.scalars(
            select(RetainedSample.batch_id).where(
                RetainedSample.batch_id.in_([b.id for _, b in rows]), RetainedSample.status == SampleStatus.STORED
            )
        )
    )
    items = [
        DispatchItem(
            batch_code=batch.batch_code,
            form1_complete=_form1_complete(session, batch.id),
            finished_at=batch.finished_at if batch.status == BatchStatus.FINISHED else None,
            form3_done=batch.id in checked,
            in_menu=batch.dish_id in menu,
            batch_portions=batch.portions_produced or batch.portions_planned,
            has_sample=batch.id in sampled,
        )
        for _, batch in rows
    ]
    return DispatchSnapshot(shipment.code, shipment.status, items)
