# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Default-deny guard: every route must sit behind a role check, except a short allowlist."""

from fastapi.routing import APIRoute

from app.core.principal import CUSTOMER_ROLE, INTERNAL_ROLES, SENSOR_ROLE
from app.main import create_app

OPEN_PATHS = {"/healthz", "/api/v1/whoami"}
ALLOWED_GATES = {INTERNAL_ROLES, frozenset({CUSTOMER_ROLE}), frozenset({SENSOR_ROLE})}


def _role_gates(dependant) -> list[frozenset[str]]:
    gates = []
    for dep in dependant.dependencies:
        roles = getattr(dep.call, "allowed_roles", None)
        if roles is not None:
            gates.append(roles)
        gates.extend(_role_gates(dep))
    return gates


def test_every_route_requires_role():
    offenders = []
    for route in create_app().routes:
        if not isinstance(route, APIRoute) or route.path in OPEN_PATHS:
            continue
        gates = _role_gates(route.dependant)
        if not gates or not all(gate in ALLOWED_GATES for gate in gates):
            offenders.append(f"{sorted(route.methods)} {route.path}")
    assert offenders == [], f"routes without a known role gate: {offenders}"


def test_portal_routes_are_customer_only_and_internal_routes_are_internal_only():
    for route in create_app().routes:
        if not isinstance(route, APIRoute) or route.path in OPEN_PATHS:
            continue
        gates = set(_role_gates(route.dependant))
        if route.path.startswith("/api/v1/portal/"):
            assert gates == {frozenset({CUSTOMER_ROLE})}, route.path
        elif "/readings" not in route.path:
            assert gates == {INTERNAL_ROLES}, route.path
