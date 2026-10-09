# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Obtain real tokens through the public gateway for integration tests.

Uses the CI-only client `metrace-test` (direct access grants), which exists
only when kc-bootstrap ran with KC_OVERLAYS=test.
"""

import base64
import json
import os
from functools import cache

import httpx

GATEWAY = os.environ.get("GATEWAY_URL", "http://localhost:9080")
TOKEN_URL = f"{GATEWAY}/auth/realms/metrace/protocol/openid-connect/token"


@cache
def user_token(username: str, scope: str = "openid organization") -> str:
    res = httpx.post(
        TOKEN_URL,
        data={
            "grant_type": "password",
            "client_id": "metrace-test",
            "username": username,
            "password": os.environ["DEMO_USER_PASSWORD"],
            "scope": scope,
        },
        timeout=15,
    )
    res.raise_for_status()
    return res.json()["access_token"]


def fresh_sensor_token() -> str:
    """A new token = a new rate-limit bucket at the gateway (the bucket key is the Authorization header)."""
    res = httpx.post(
        TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": "sensor-gateway",
            "client_secret": os.environ["SENSOR_GATEWAY_CLIENT_SECRET"],
        },
        timeout=15,
    )
    res.raise_for_status()
    return res.json()["access_token"]


@cache
def sensor_token() -> str:
    return fresh_sensor_token()


def claims(token: str) -> dict:
    """Decode the payload WITHOUT verification (tests inspect, the API verifies)."""
    payload = token.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
