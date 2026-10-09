# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Gateway + identity contract: one issuer, org claim, 401s, /auth allowlist, rate limits."""

import httpx
import pytest

from tests.integration.gateway_tokens import GATEWAY, auth, claims, fresh_sensor_token, sensor_token, user_token

pytestmark = pytest.mark.integration

PUBLIC_ISSUER = f"{GATEWAY}/auth/realms/metrace"


def test_customer_token_has_org_claim_keyed_by_alias_with_id():
    token_claims = claims(user_token("truong-a"))
    assert token_claims["iss"] == PUBLIC_ISSUER
    assert token_claims["aud"] == "metrace-api" or "metrace-api" in token_claims["aud"]
    org = token_claims["organization"]
    assert isinstance(org, dict) and set(org) == {"truong-a"}
    assert org["truong-a"]["id"]


def test_whoami_returns_roles_and_org_through_gateway():
    res = httpx.get(f"{GATEWAY}/api/v1/whoami", headers=auth(user_token("truong-a")))
    assert res.status_code == 200
    body = res.json()
    assert body["username"] == "truong-a"
    assert body["roles"] == ["customer_staff"]
    assert body["organizations"] == ["truong-a"]
    assert body["business_tz"] == "Asia/Ho_Chi_Minh"
    assert res.headers.get("X-Request-Id")


def test_sensor_client_credentials_has_sensor_role_and_no_org():
    body = httpx.get(f"{GATEWAY}/api/v1/whoami", headers=auth(sensor_token())).json()
    assert body["roles"] == ["sensor"]
    assert body["organizations"] == []


@pytest.mark.parametrize(
    "headers",
    [{}, {"Authorization": "Bearer not-a-jwt"}, {"Authorization": "Basic Zm9vOmJhcg=="}],
)
def test_missing_or_garbage_token_is_401(headers):
    assert httpx.get(f"{GATEWAY}/api/v1/whoami", headers=headers).status_code == 401


def test_tampered_signature_is_401():
    head, payload, signature = user_token("qa-lan").split(".")
    forged = f"{head}.{payload}.{signature[::-1]}"
    assert httpx.get(f"{GATEWAY}/api/v1/whoami", headers=auth(forged)).status_code == 401


@pytest.mark.parametrize(
    "path",
    [
        "/auth/admin/",
        "//auth/admin/",
        "/auth/admin/realms/metrace/users",
        "/auth/admin/master/console/",
        "/auth/realms/master/.well-known/openid-configuration",
        "/auth/realms/master/protocol/openid-connect/token",
        "/auth/realms/metrace/account/",
        "/auth/%61dmin/",
        "/auth/realms/%6Daster/.well-known/openid-configuration",
        "/auth/realms/metrace/protocol/openid-connect/../../../master/.well-known/openid-configuration",
        "/auth/realms/metrace/protocol/openid-connect/..%2F..%2F..%2Fmaster%2F.well-known%2Fopenid-configuration",
    ],
)
def test_auth_paths_outside_allowlist_are_404(path):
    # Raw path on purpose: httpx must not normalise the traversal attempts.
    with httpx.Client() as client:
        req = client.build_request("GET", GATEWAY)
        req.url = req.url.copy_with(raw_path=path.encode())
        assert client.send(req).status_code == 404


def test_login_and_discovery_paths_are_allowed():
    discovery = httpx.get(f"{PUBLIC_ISSUER}/.well-known/openid-configuration")
    assert discovery.status_code == 200
    assert discovery.json()["issuer"] == PUBLIC_ISSUER
    assert httpx.get(f"{PUBLIC_ISSUER}/device").status_code == 200


def test_sensor_readings_route_has_its_own_rate_limit_bucket():
    token = fresh_sensor_token()  # its own bucket: other tests keep their readings quota
    url = f"{GATEWAY}/api/v1/assets/RL-TEST/readings"
    first = httpx.post(url, headers=auth(token))
    limit = int(first.headers["X-RateLimit-Limit"])
    if limit > 20:
        pytest.skip(f"readings limit is {limit}; start the stack with RATE_LIMIT_READINGS_PER_MIN<=20 to exercise 429")
    remaining = int(first.headers["X-RateLimit-Remaining"])
    codes = [httpx.post(url, headers=auth(token)).status_code for _ in range(remaining + 1)]
    assert codes[-1] == 429
    # The general /api bucket is untouched.
    assert httpx.get(f"{GATEWAY}/api/v1/whoami", headers=auth(token)).status_code == 200
