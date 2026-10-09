# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""OAuth 2.0 device authorization grant against Keycloak (client `metrace-cli`).

No password ever touches the CLI: the user approves the login in a browser.
Tokens are cached in ~/.config/metrace/token.json with file mode 600.
"""

import json
import os
import time
from collections.abc import Callable
from pathlib import Path

import httpx

CLIENT_ID = "metrace-cli"
SCOPE = "openid organization"


def base_url() -> str:
    return os.environ.get("METRACE_URL", "http://localhost:9080").rstrip("/")


def issuer() -> str:
    return f"{base_url()}/auth/realms/{os.environ.get('METRACE_REALM', 'metrace')}"


def token_path() -> Path:
    root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return root / "metrace" / "token.json"


def save_tokens(tokens: dict) -> None:
    path = token_path()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    tokens = {**tokens, "obtained_at": int(time.time())}
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as fh:
        json.dump(tokens, fh)
    path.chmod(0o600)


def clear_tokens() -> None:
    token_path().unlink(missing_ok=True)


def device_login(show: Callable[[str, str], None], http: httpx.Client | None = None) -> dict:
    """Start the device flow, call `show(verification_url, user_code)`, poll until approved."""
    http = http or httpx.Client(timeout=15)
    start = http.post(f"{issuer()}/protocol/openid-connect/auth/device", data={"client_id": CLIENT_ID, "scope": SCOPE})
    start.raise_for_status()
    grant = start.json()
    show(grant.get("verification_uri_complete") or grant["verification_uri"], grant["user_code"])
    interval = int(grant.get("interval", 5))
    deadline = time.monotonic() + int(grant.get("expires_in", 600))
    while time.monotonic() < deadline:
        time.sleep(interval)
        res = http.post(
            f"{issuer()}/protocol/openid-connect/token",
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "device_code": grant["device_code"],
                "client_id": CLIENT_ID,
            },
        )
        if res.status_code == 200:
            return res.json()
        error = res.json().get("error")
        if error == "slow_down":
            interval += 5
        elif error != "authorization_pending":
            raise RuntimeError(f"login failed: {error}")
    raise RuntimeError("login timed out")


def access_token(http: httpx.Client | None = None) -> str:
    """Token from METRACE_TOKEN (tests/CI) or the cache, refreshed when about to expire."""
    if env := os.environ.get("METRACE_TOKEN"):
        return env
    path = token_path()
    if not path.exists():
        raise RuntimeError("not logged in: run `metrace login`")
    tokens = json.loads(path.read_text())
    if time.time() < tokens["obtained_at"] + tokens.get("expires_in", 0) - 30:
        return tokens["access_token"]
    http = http or httpx.Client(timeout=15)
    res = http.post(
        f"{issuer()}/protocol/openid-connect/token",
        data={"grant_type": "refresh_token", "refresh_token": tokens.get("refresh_token", ""), "client_id": CLIENT_ID},
    )
    if res.status_code != 200:
        clear_tokens()
        raise RuntimeError("session expired: run `metrace login`")
    save_tokens(res.json())
    return res.json()["access_token"]
