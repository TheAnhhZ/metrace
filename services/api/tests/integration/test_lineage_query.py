# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Recursive lineage walk on a private graph (rolled back after each test)."""

from decimal import Decimal

import pytest

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


def test_both_directions_from_a_batch(app_session, graph):
    result = lineage_query.both(app_session, graph.b1)
    assert {graph.s, graph.l1, graph.l2, graph.broth, graph.sh1, graph.dp1} <= result.nodes
    assert graph.b2 not in result.nodes  # sibling, neither ancestor nor descendant
