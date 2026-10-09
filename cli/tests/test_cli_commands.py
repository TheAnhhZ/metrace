# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""CLI tests. Unit tests run anywhere; `e2e` tests need the stack and
METRACE_TEST_PASSWORD (demo password) to mint tokens through the CI-only client."""

import json
import os
import stat

import httpx
import pytest
from typer.testing import CliRunner

from metrace_cli import auth_device_flow as auth
from metrace_cli.api_client import ApiError, require_internal
from metrace_cli.main import app

runner = CliRunner()


def test_token_cache_is_private(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    auth.save_tokens({"access_token": "a", "expires_in": 300, "refresh_token": "r"})
    mode = stat.S_IMODE(os.stat(auth.token_path()).st_mode)
    assert mode == 0o600
    assert auth.access_token() == "a"
    auth.clear_tokens()
    assert not auth.token_path().exists()


def test_customer_accounts_are_refused():
    with pytest.raises(ApiError):
        require_internal({"roles": ["customer_staff"]})
    require_internal({"roles": ["qa"]})


def test_not_logged_in_is_a_clear_error(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.delenv("METRACE_TOKEN", raising=False)
    result = runner.invoke(app, ["whoami"])
    assert result.exit_code == 1


def _token(username: str) -> str:
    password = os.environ.get("METRACE_TEST_PASSWORD") or os.environ.get("DEMO_USER_PASSWORD")
    if not password:
        pytest.skip("set DEMO_USER_PASSWORD to run CLI e2e tests")
    res = httpx.post(
        f"{auth.issuer()}/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": "metrace-test",
            "username": username,
            "password": password,
            "scope": "openid organization",
        },
    )
    if res.status_code != 200:
        pytest.skip("stack or CI-only client unavailable")
    return res.json()["access_token"]


@pytest.mark.e2e
def test_trace_by_code_matches_the_api(monkeypatch):
    token = _token("qa-lan")
    monkeypatch.setenv("METRACE_TOKEN", token)
    lots = httpx.get(f"{auth.base_url()}/api/v1/lots", headers={"Authorization": f"Bearer {token}"}).json()
    lot = next(lot for lot in lots if lot["ingredient_code"] == "XUONG-LON")
    result = runner.invoke(app, ["trace", "lot", lot["lot_code"], "--direction", "forward", "--json"])
    assert result.exit_code == 0, result.output
    cli_nodes = {(n["type"], n["id"]) for n in json.loads(result.output)["nodes"]}
    api = httpx.get(
        f"{auth.base_url()}/api/v1/lineage/lot/{lot['id']}",
        params={"direction": "forward"},
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    assert cli_nodes == {(n["type"], n["id"]) for n in api["nodes"]}


@pytest.mark.e2e
def test_shipments_filter_and_customer_token_is_forbidden(monkeypatch):
    monkeypatch.setenv("METRACE_TOKEN", _token("driver-tuan"))
    result = runner.invoke(app, ["shipments", "list", "--status", "held", "--json"])
    assert result.exit_code == 0, result.output
    assert all(s["status"] == "held" for s in json.loads(result.output))
    monkeypatch.setenv("METRACE_TOKEN", _token("truong-a"))
    result = runner.invoke(app, ["shipments", "list"])
    assert result.exit_code == 1 and "403" in result.output
