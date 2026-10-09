# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Lineage response: one shape for the trace table, the graph and the CLI."""

import uuid
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class LineageNodeType(StrEnum):
    SUPPLIER = "supplier"
    LOT = "lot"
    BATCH = "batch"
    SHIPMENT = "shipment"
    DELIVERY_POINT = "delivery_point"
    ASSET = "asset"


class LineageDirection(StrEnum):
    FORWARD = "forward"
    BACKWARD = "backward"
    BOTH = "both"


class LineageNode(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: LineageNodeType
    id: uuid.UUID
    label: str
    depth: int = Field(description="Hops from the root in the walked direction")
    locked: bool
    portions: int | None = Field(None, description="Affected portions delivered here (delivery points only)")
    status: str | None = None


class LineageEdge(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    from_: str = Field(alias="from")
    to: str


class LineageOut(BaseModel):
    root: str
    direction: LineageDirection
    nodes: list[LineageNode]
    edges: list[LineageEdge]
    truncated: bool = Field(description="True when depth or node caps cut the walk; writes must fail closed")
