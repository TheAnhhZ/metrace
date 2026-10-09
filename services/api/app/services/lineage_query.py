# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Walk the lineage graph (view `lineage_edge`) forward (where did it go?) or
backward (where did it come from?) with a recursive CTE.

Callers that WRITE based on a walk (locks, guards) must fail closed when
`truncated` is true: an incomplete walk may have missed affected food.
"""

import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Literal

from sqlalchemy import text
from sqlalchemy.orm import Session

Direction = Literal["forward", "backward"]
DEFAULT_MAX_DEPTH = 8
MAX_DEPTH_CAP = 12
DEFAULT_MAX_NODES = 300


@dataclass(frozen=True, order=True)
class NodeRef:
    type: str
    id: uuid.UUID

    @property
    def key(self) -> str:
        return f"{self.type}:{self.id}"


@dataclass
class LineageResult:
    depths: dict[NodeRef, int] = field(default_factory=dict)
    edges: set[tuple[NodeRef, NodeRef]] = field(default_factory=set)
    truncated: bool = False

    @property
    def nodes(self) -> set[NodeRef]:
        return set(self.depths)

    def ids(self, node_type: str) -> set[uuid.UUID]:
        return {n.id for n in self.depths if n.type == node_type}

    def merge(self, other: "LineageResult") -> "LineageResult":
        depths = dict(other.depths)
        for node, depth in self.depths.items():
            depths[node] = min(depth, depths.get(node, depth))
        return LineageResult(depths, self.edges | other.edges, self.truncated or other.truncated)


def _walk_sql(direction: Direction) -> str:
    # Only the two fixed column prefixes are interpolated; every value is a bind parameter.
    src, dst = ("from", "to") if direction == "forward" else ("to", "from")
    return f"""
    WITH RECURSIVE walk(node_type, node_id, depth, path) AS (
        SELECT r.t, r.id, 0, ARRAY[r.t || ':' || r.id::text]
          FROM unnest(CAST(:types AS text[]), CAST(:ids AS uuid[])) AS r(t, id)
        UNION ALL
        SELECT e.{dst}_type, e.{dst}_id, w.depth + 1, w.path || (e.{dst}_type || ':' || e.{dst}_id::text)
          FROM walk w
          JOIN lineage_edge e ON e.{src}_type = w.node_type AND e.{src}_id = w.node_id
         WHERE w.depth < :depth_limit
           AND NOT (e.{dst}_type || ':' || e.{dst}_id::text) = ANY (w.path)   -- cycle guard
    )
    SELECT node_type, node_id, min(depth) AS depth FROM walk GROUP BY node_type, node_id
    """  # noqa: S608


_EDGES_SQL = """
    WITH n(t, id) AS (SELECT * FROM unnest(CAST(:types AS text[]), CAST(:ids AS uuid[])))
    SELECT e.from_type, e.from_id, e.to_type, e.to_id
      FROM lineage_edge e
      JOIN n a ON a.t = e.from_type AND a.id = e.from_id
      JOIN n b ON b.t = e.to_type AND b.id = e.to_id
"""


def _params(nodes: Iterable[NodeRef]) -> dict[str, list]:
    nodes = list(nodes)
    return {"types": [n.type for n in nodes], "ids": [n.id for n in nodes]}


def walk(
    session: Session,
    roots: Iterable[NodeRef],
    direction: Direction,
    max_depth: int = DEFAULT_MAX_DEPTH,
    max_nodes: int = DEFAULT_MAX_NODES,
) -> LineageResult:
    roots = list(roots)
    if not roots:
        return LineageResult()
    max_depth = max(0, min(max_depth, MAX_DEPTH_CAP))
    # Walk one level deeper than allowed: anything found there proves truncation.
    rows = session.execute(text(_walk_sql(direction)), {**_params(roots), "depth_limit": max_depth + 1}).all()
    depths = {NodeRef(r.node_type, r.node_id): r.depth for r in rows if r.depth <= max_depth}
    truncated = any(r.depth > max_depth for r in rows)
    if len(depths) > max_nodes:
        keep = sorted(depths.items(), key=lambda item: (item[1], item[0]))[:max_nodes]
        depths, truncated = dict(keep), True
    return LineageResult(depths, _edges(session, depths), truncated)


def _edges(session: Session, nodes: Iterable[NodeRef]) -> set[tuple[NodeRef, NodeRef]]:
    rows = session.execute(text(_EDGES_SQL), _params(nodes)).all()
    return {(NodeRef(r.from_type, r.from_id), NodeRef(r.to_type, r.to_id)) for r in rows}


def forward_many(session: Session, roots: Iterable[NodeRef], **kwargs) -> LineageResult:
    return walk(session, roots, "forward", **kwargs)


def backward_many(session: Session, roots: Iterable[NodeRef], **kwargs) -> LineageResult:
    return walk(session, roots, "backward", **kwargs)


def forward(session: Session, root: NodeRef, **kwargs) -> LineageResult:
    return forward_many(session, [root], **kwargs)


def backward(session: Session, root: NodeRef, **kwargs) -> LineageResult:
    return backward_many(session, [root], **kwargs)


def both(session: Session, root: NodeRef, **kwargs) -> LineageResult:
    return forward(session, root, **kwargs).merge(backward(session, root, **kwargs))
