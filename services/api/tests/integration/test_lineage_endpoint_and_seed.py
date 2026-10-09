# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Lineage endpoint on the seeded demo data + seed idempotency."""

import uuid

import httpx
import pytest
from sqlalchemy import select

from app.core.business_time import service_date
from app.models.cooking import CookingBatch
from app.services import lineage_query
from app.services.lineage_query import NodeRef
from tests.integration.gateway_tokens import GATEWAY, auth, user_token

pytestmark = pytest.mark.integration


def _batch(session, suffix: str) -> CookingBatch:
    code = f"B-{service_date().strftime('%Y%m%d')}-lunch-{suffix}"
    batch = session.scalar(select(CookingBatch).where(CookingBatch.batch_code == code))
    if batch is None:
        pytest.skip(f"seed data for today missing ({code}); run the seed one-shot")
    return batch


def _get(path: str, **params) -> httpx.Response:
    return httpx.get(f"{GATEWAY}/api/v1/lineage/{path}", params=params, headers=auth(user_token("qa-lan")))


@pytest.mark.parametrize("direction", ["forward", "backward", "both"])
def test_endpoint_returns_same_nodes_as_query(app_session, direction):
    broth = _batch(app_session, "NUOC-DUNG")
    body = _get(f"batch/{broth.id}", direction=direction).json()
    walk = {"forward": lineage_query.forward, "backward": lineage_query.backward, "both": lineage_query.both}
    expected = walk[direction](app_session, NodeRef("batch", broth.id))
    assert {(n["type"], uuid.UUID(n["id"])) for n in body["nodes"]} == {(n.type, n.id) for n in expected.nodes}
    assert body["truncated"] is False


def test_todays_broth_reaches_four_points_with_portions(app_session):
    broth = _batch(app_session, "NUOC-DUNG")
    body = _get(f"batch/{broth.id}", direction="forward").json()
    points = {n["label"]: n["portions"] for n in body["nodes"] if n["type"] == "delivery_point"}
    assert len(points) == 4
    assert all(p and p > 0 for p in points.values())
    shipments = [n for n in body["nodes"] if n["type"] == "shipment"]
    assert shipments and all(s["status"] == "ready" for s in shipments)


def test_shared_bones_lot_links_yesterday_and_today(app_session):
    broth = _batch(app_session, "NUOC-DUNG")
    lots = lineage_query.backward(app_session, NodeRef("batch", broth.id)).ids("lot")
    forward = lineage_query.forward_many(app_session, [NodeRef("lot", i) for i in lots])
    batches = app_session.scalars(select(CookingBatch).where(CookingBatch.id.in_(forward.ids("batch"))))
    dates = {b.service_date for b in batches}
    assert len(dates) == 2  # yesterday and today


def test_unknown_node_is_404_and_bad_type_is_422():
    assert _get(f"batch/{uuid.uuid4()}").status_code == 404
    assert _get(f"dish/{uuid.uuid4()}").status_code == 422


def test_seed_is_idempotent(monkeypatch, app_engine):
    from app.core import database, settings
    from app.seed.__main__ import run

    monkeypatch.setenv("DATABASE_URL", app_engine.url.render_as_string(hide_password=False))
    settings.get_settings.cache_clear()
    database.get_engine.cache_clear()
    database._session_factory.cache_clear()
    try:
        tables = ["supplier", "ingredient", "dish", "asset", "customer_org", "cooking_batch", "shipment", "menu"]

        def counts():
            with app_engine.connect() as conn:  # fixed table names above, no user input
                return {t: conn.exec_driver_sql(f"SELECT count(*) FROM {t}").scalar() for t in tables}  # noqa: S608

        run(["baseline"])
        before = counts()
        run(["baseline"])
        assert counts() == before
    finally:
        settings.get_settings.cache_clear()
        database.get_engine.cache_clear()
        database._session_factory.cache_clear()
