# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Default-deny guard, tested by behaviour (independent of FastAPI internals):
every operation in the OpenAPI schema is called with the wrong roles and must
answer 403 before touching anything else."""

import re
import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.authentication import get_principal
from app.core.principal import Principal
from app.main import create_app

OPEN_PATHS = {"/healthz", "/api/v1/whoami"}
PORTAL_PREFIX = "/api/v1/portal/"
SENSOR_PATH = re.compile(r"^/api/v1/assets/[^/]+/readings$")


def _principal(*roles: str) -> Principal:
    return Principal(sub="t", username="t", roles=frozenset(roles), org_aliases=frozenset({"truong-a"}))


def _concrete(path: str, params: list[dict]) -> str:
    """Fill path parameters with plausible values (first enum value, else a UUID)."""
    for param in params:
        if param.get("in") != "path":
            continue
        schema = param.get("schema", {})
        enum = schema.get("enum") or [None]
        value = enum[0] or str(uuid.uuid4())
        path = path.replace("{" + param["name"] + "}", str(value))
    return path


def _operations():
    app = create_app()
    schema = app.openapi()
    components = schema.get("components", {}).get("schemas", {})
    for path, item in schema["paths"].items():
        if path in OPEN_PATHS:
            continue
        for method, op in item.items():
            params = []
            for p in op.get("parameters", []):
                ref = p.get("schema", {}).get("$ref")
                if ref:  # resolve enum refs like LineageNodeType
                    p = {**p, "schema": components[ref.rsplit("/", 1)[-1]]}
                params.append(p)
            yield method.upper(), path, _concrete(path, params)


OPERATIONS = list(_operations())


def test_schema_has_gated_operations():
    assert len(OPERATIONS) >= 4


def _call(principal: Principal, method: str, url: str) -> int:
    app = create_app()
    app.dependency_overrides[get_principal] = lambda: principal
    with TestClient(app, raise_server_exceptions=True) as client:
        return client.request(method, url).status_code


@pytest.mark.parametrize(("method", "template", "url"), OPERATIONS)
def test_roleless_caller_is_forbidden_everywhere(method, template, url):
    assert _call(_principal(), method, url) == 403, f"{method} {template} is reachable without a role"


@pytest.mark.parametrize(("method", "template", "url"), OPERATIONS)
def test_each_audience_is_forbidden_on_the_others_routes(method, template, url):
    staff, customer, sensor = _principal("qa", "director"), _principal("customer_staff"), _principal("sensor")
    if template.startswith(PORTAL_PREFIX):
        intruders = [staff, sensor]
    elif SENSOR_PATH.match(template):
        intruders = [staff, customer]
    else:
        intruders = [customer, sensor]
    for intruder in intruders:
        assert _call(intruder, method, url) == 403, f"{method} {template} open to {sorted(intruder.roles)}"
