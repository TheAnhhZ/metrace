# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Thin client for /api/v1 through the gateway: same API as the web app (headless)."""

from typing import Any

import httpx

from metrace_cli.auth_device_flow import access_token, base_url

INTERNAL_ROLES = {"qa", "procurement", "chef", "driver", "cskh", "director", "approver"}


class ApiError(Exception):
    def __init__(self, status: int, body: Any):
        self.status, self.body = status, body
        error = body.get("error", {}) if isinstance(body, dict) else {}
        super().__init__(f"HTTP {status} {error.get('code', '')}: {error.get('message', body)}")


def request(method: str, path: str, json: Any = None, **params: Any) -> Any:
    with httpx.Client(timeout=30) as http:
        res = http.request(
            method,
            f"{base_url()}/api/v1{path}",
            json=json,
            params={k: v for k, v in params.items() if v is not None},
            headers={"Authorization": f"Bearer {access_token(http)}"},
        )
    try:
        body = res.json()
    except ValueError:
        body = res.text
    if res.status_code >= 400:
        raise ApiError(res.status_code, body)
    return body


def get(path: str, **params: Any) -> Any:
    return request("GET", path, **params)


def post(path: str, json: Any) -> Any:
    return request("POST", path, json=json)


def require_internal(whoami: dict) -> None:
    """The CLI is a staff tool: customer accounts are refused even if they log in."""
    if not INTERNAL_ROLES & set(whoami.get("roles", [])):
        raise ApiError(403, {"error": {"code": "FORBIDDEN", "message": "the CLI is for internal staff only"}})
