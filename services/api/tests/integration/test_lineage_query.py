# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Recursive lineage walk on a private graph (rolled back after each test)."""

import json
from decimal import Decimal

import pytest
from sqlalchemy import text

from app.models.cooking import BatchInput
from app.services import lineage_query
from tests.integration.lineage_graph_factory import build_graph

pytestmark = pytest.mark.integration


@pytest.fixture
def graph(app_session):
    g = build_graph(app_session)
    yield g
    app_session.rollback()


def test_straight_chain_forward(app_session, graph):
    result = lineage_query.forward(app_session, graph.l2)
    assert result.nodes == {graph.l2, graph.b1, graph.sh1, graph.dp1}
    assert result.depths[graph.dp1] == 3
    assert (graph.b1, graph.sh1) in result.edges
    assert not result.truncated


def test_intermediate_batch_reaches_every_delivery_point(app_session, graph):
    result = lineage_query.forward(app_session, graph.l1)
    assert {graph.broth, graph.b1, graph.b2, graph.dp1, graph.dp2} <= result.nodes
    assert result.ids("delivery_point") == {graph.dp1.id, graph.dp2.id}


def test_backward_from_delivery_point_reaches_supplier_through_broth(app_session, graph):
    result = lineage_query.backward(app_session, graph.dp1)
    assert {graph.sh1, graph.b1, graph.broth, graph.l1, graph.l2, graph.s} <= result.nodes
    assert graph.dp2 not in result.nodes


def test_artificial_cycle_terminates(app_session, graph):
    # BROTH also consumes B2, while B2 consumes BROTH: a cycle the guard must break.
    app_session.add(BatchInput(batch_id=graph.broth.id, input_batch_id=graph.b2.id, qty_kg=Decimal(1)))
    app_session.flush()
    result = lineage_query.forward(app_session, graph.l1, max_depth=12)
    assert graph.b2 in result.nodes and graph.broth in result.nodes
    assert result.depths[graph.broth] == 1


def test_depth_limit_marks_truncated(app_session, graph):
    result = lineage_query.forward(app_session, graph.s, max_depth=2)
    assert result.truncated
    assert max(result.depths.values()) == 2
    assert graph.dp1 not in result.nodes


def test_many_roots_is_the_union(app_session, graph):
    many = lineage_query.forward_many(app_session, [graph.l1, graph.l2])
    one = lineage_query.forward(app_session, graph.l1).merge(lineage_query.forward(app_session, graph.l2))
    assert many.nodes == one.nodes


def test_node_cap_marks_truncated(app_session, graph):
    result = lineage_query.forward(app_session, graph.s, max_nodes=3)
    assert result.truncated and len(result.nodes) == 3


def test_writers_walk_without_node_cap_or_edges(app_session, graph):
    result = lineage_query.forward(app_session, graph.s, max_nodes=None, with_edges=False)
    assert not result.truncated and result.edges == set()
    assert {graph.sh1, graph.sh2, graph.dp1, graph.dp2} <= result.nodes


def test_both_directions_from_a_batch(app_session, graph):
    result = lineage_query.both(app_session, graph.b1)
    assert {graph.s, graph.l1, graph.l2, graph.broth, graph.sh1, graph.dp1} <= result.nodes
    assert graph.b2 not in result.nodes  # sibling, neither ancestor nor descendant


def test_supplier_trace_on_the_seed_stays_under_200_ms(app_session):
    """EXPLAIN ANALYZE of the heaviest realistic walk: the busiest supplier, forward, full depth."""
    supplier = app_session.execute(
        text("SELECT supplier_id FROM ingredient_lot GROUP BY supplier_id ORDER BY count(*) DESC LIMIT 1")
    ).scalar()
    if supplier is None:
        pytest.skip("no seed data")
    root = lineage_query.NodeRef("supplier", supplier)
    params = {**lineage_query._params([root]), "depth_limit": lineage_query.MAX_DEPTH_CAP + 1}
    plan = app_session.execute(
        text("EXPLAIN (ANALYZE, FORMAT JSON) " + lineage_query._walk_sql("forward")), params
    ).scalar()
    plan = plan if isinstance(plan, list) else json.loads(plan)
    elapsed_ms = plan[0]["Execution Time"]
    print(f"supplier forward walk: {elapsed_ms:.1f} ms")
    assert elapsed_ms < 200
