# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""GET /api/v1/lineage/{type}/{id}: forward, backward or both. Internal staff only."""

import uuid

from fastapi import Query

from app.core.authorization import internal_router
from app.core.database import DbSession
from app.core.errors import not_found
from app.schemas.lineage import LineageDirection, LineageNodeType, LineageOut
from app.services import lineage_query
from app.services.lineage_presenter import node_exists, present
from app.services.lineage_query import DEFAULT_MAX_DEPTH, MAX_DEPTH_CAP, NodeRef

router = internal_router(prefix="/api/v1/lineage", tags=["lineage"])


@router.get("/{node_type}/{node_id}", response_model=LineageOut, response_model_by_alias=True)
def get_lineage(
    node_type: LineageNodeType,
    node_id: uuid.UUID,
    session: DbSession,
    direction: LineageDirection = LineageDirection.BOTH,
    max_depth: int = Query(DEFAULT_MAX_DEPTH, ge=1, le=MAX_DEPTH_CAP),
) -> dict:
    root = NodeRef(node_type.value, node_id)
    if not node_exists(session, root):
        raise not_found(node_type.value)
    if direction is LineageDirection.FORWARD:
        result = lineage_query.forward(session, root, max_depth=max_depth)
    elif direction is LineageDirection.BACKWARD:
        result = lineage_query.backward(session, root, max_depth=max_depth)
    else:
        result = lineage_query.both(session, root, max_depth=max_depth)
    return {"root": root.key, "direction": direction, **present(session, result)}
