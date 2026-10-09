# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""All routers, in one list. Business routers must come from
`internal_router`, `portal_router` or `sensor_router` (default-deny)."""

from fastapi import APIRouter

from app.routers import files, health, kitchen, lineage, master_data_read, shipments, whoami

# Open to any caller (health) or to any authenticated caller (whoami).
PUBLIC_ROUTERS: list[APIRouter] = [health.router, whoami.router]

# Role-gated routers. tests/unit/test_every_route_requires_role.py enforces this.
GATED_ROUTERS: list[APIRouter] = [
    files.internal,
    files.portal,
    lineage.router,
    master_data_read.router,
    kitchen.router,
    shipments.router,
]
