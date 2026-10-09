# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""What a lock holds (normal and too-deep walks) and how recall notices evolve.

Runs on a private lineage graph inside one transaction that is rolled back:
nothing reaches the demo data.
"""

import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.core.business_time import service_date, utcnow
from app.core.settings import get_settings
from app.models.cooking import BatchInput, CookingBatch
from app.models.enums import ShipmentStatus
from app.models.incident import Incident, RecallNotice
from app.models.shipment import Shipment, ShipmentItem
from app.services import lineage_query, lock_service
from app.services.lineage_query import NodeRef
from app.worker.recall_notices import upsert_notices
from tests.integration.lineage_graph_factory import build_graph

pytestmark = pytest.mark.integration


@pytest.fixture
def graph(app_session):
    g = build_graph(app_session)
    yield g
    app_session.rollback()


def _incident(session, opened_days_ago: int = 0) -> Incident:
    incident = Incident(
        code=f"T-{uuid.uuid4().hex[:10]}",
        title="lock scope probe",
        opened_by="qa-test",
        opened_at=utcnow() - timedelta(days=opened_days_ago),
    )
    session.add(incident)
    session.flush()
    return incident


def _truck(session, like: Shipment, day, status=ShipmentStatus.PLANNED, batch_id=None) -> Shipment:
    truck = Shipment(
        kitchen_id=like.kitchen_id,
        code=f"T-{uuid.uuid4().hex[:10]}",
        delivery_point_id=like.delivery_point_id,
        service_date=day,
        meal_slot="lunch",
        status=status,
    )
    session.add(truck)
    session.flush()
    if batch_id:
        session.add(ShipmentItem(shipment_id=truck.id, batch_id=batch_id, portions=5))
        session.flush()
    return truck


def _chain_beyond_depth_cap(session, start: NodeRef) -> None:
    """start -> c1 -> ... -> c12 -> truck: deeper than MAX_DEPTH_CAP from the lot above `start`."""
    base = session.get(CookingBatch, start.id)
    previous = base
    for n in range(lineage_query.MAX_DEPTH_CAP):
        nxt = CookingBatch(
            kitchen_id=base.kitchen_id,
            dish_id=base.dish_id,
            batch_code=f"C{n}-{uuid.uuid4().hex[:8]}",
            service_date=base.service_date,
            meal_slot=base.meal_slot,
            owner="t",
        )
        session.add(nxt)
        session.flush()
        session.add(BatchInput(batch_id=nxt.id, input_batch_id=previous.id, qty_kg=Decimal(1)))
        previous = nxt
    session.flush()


def test_full_walk_holds_only_trucks_on_the_lineage(app_session, graph):
    sh1 = app_session.get(Shipment, graph.sh1.id)
    bystander = _truck(app_session, sh1, service_date() + timedelta(days=1))

    result = lock_service.apply(app_session, _incident(app_session), [graph.l2], lock_lots=False, actor="qa-test")

    assert not result.truncated
    assert result.held_shipments == [graph.sh1.id]
    assert app_session.get(Shipment, bystander.id).status == ShipmentStatus.PLANNED


def test_too_deep_walk_fails_closed_only_for_food_not_yet_served(app_session, graph):
    sh1 = app_session.get(Shipment, graph.sh1.id)
    _chain_beyond_depth_cap(app_session, graph.b1)
    tomorrow, earlier = service_date() + timedelta(days=1), service_date() - timedelta(days=2)
    stale_on_walk = _truck(app_session, sh1, earlier, batch_id=graph.b1.id)  # seen by the walk: held
    stale_elsewhere = _truck(app_session, sh1, earlier, batch_id=graph.b2.id)  # old plan, not at risk
    loaded_elsewhere = _truck(app_session, sh1, tomorrow, batch_id=graph.b2.id)  # food maybe out of sight
    empty_elsewhere = _truck(app_session, sh1, tomorrow)  # no food yet: checked when food is added

    result = lock_service.apply(app_session, _incident(app_session), [graph.l2], lock_lots=False, actor="qa-test")

    held = set(result.held_shipments)
    assert result.truncated
    assert {graph.sh1.id, stale_on_walk.id, loaded_elsewhere.id} <= held
    assert not {stale_elsewhere.id, empty_elsewhere.id} & held
    assert app_session.get(Shipment, empty_elsewhere.id).status == ShipmentStatus.PLANNED


def _notice(session, incident: Incident) -> RecallNotice:
    notice = session.scalars(select(RecallNotice).where(RecallNotice.incident_id == incident.id)).one()
    session.refresh(notice)
    return notice


def test_notice_keeps_its_ack_until_what_the_customer_must_do_changes(app_session, graph):
    sh1 = app_session.get(Shipment, graph.sh1.id)
    sh1.status = ShipmentStatus.DISPATCHED
    incident = _incident(app_session)
    lock_service.apply(app_session, incident, [graph.l2], lock_lots=False, actor="qa-test")
    assert upsert_notices(app_session, incident.id) == 1
    notice = _notice(app_session, incident)
    notice.acknowledged_at, notice.acknowledged_by = utcnow(), "school-admin"
    app_session.flush()

    sh1.status = ShipmentStatus.DELIVERED  # same food, same action: nothing new to acknowledge
    app_session.flush()
    upsert_notices(app_session, incident.id, anchor=(notice.audit_seq + 1, "b" * 64))
    unchanged = _notice(app_session, incident)
    assert unchanged.acknowledged_at is not None
    assert unchanged.audit_seq == notice.audit_seq  # nothing re-issued, so the anchor stays
    assert all("status" not in s for s in unchanged.content["shipments"])
    notice = unchanged

    # Another truck with the suspect food: the customer must act again, under the new anchor.
    _truck(app_session, sh1, service_date(), status=ShipmentStatus.DISPATCHED, batch_id=graph.b1.id)
    seq = notice.audit_seq + 2
    upsert_notices(app_session, incident.id, anchor=(seq, "c" * 64))
    notice = _notice(app_session, incident)
    assert notice.acknowledged_at is None
    assert len(notice.content["shipments"]) == 2
    assert (notice.audit_seq, notice.audit_hash) == (seq, "c" * 64)


def test_recall_window_is_anchored_to_when_the_incident_opened(app_session, graph):
    sh1 = app_session.get(Shipment, graph.sh1.id)
    sh1.status = ShipmentStatus.DELIVERED
    window = get_settings().recall_window_days
    incident = _incident(app_session, opened_days_ago=10)
    in_window = _truck(
        app_session, sh1, service_date() - timedelta(days=10 + window), ShipmentStatus.DELIVERED, graph.b1.id
    )
    too_old = _truck(
        app_session, sh1, service_date() - timedelta(days=11 + window), ShipmentStatus.DELIVERED, graph.b1.id
    )

    result = lock_service.apply(app_session, incident, [graph.l2], lock_lots=False, actor="qa-test")

    assert in_window.id in result.already_dispatched  # older than today's window, still owed a recall
    assert too_old.id not in result.already_dispatched
