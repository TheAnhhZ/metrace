# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""One-shot `kc-bootstrap`: make the metrace realm match the repo, idempotently.

1. Organizations + memberships from the realm file (import may skip members).
2. Overlays listed in KC_OVERLAYS (comma separated):
   - test: client `metrace-test` (direct access grants, CI/pytest only)
   - demo: longer SSO idle so demo personas stay logged in

Talks to the Keycloak admin REST API over the internal docker network only;
the admin API is never routed through the public gateway.
"""

import json
import logging
import os
import sys
from pathlib import Path

import httpx

log = logging.getLogger("kc-bootstrap")

BASE_URL = os.environ.get("KC_INTERNAL_URL", "http://keycloak:8080/auth")
REALM = os.environ.get("KC_REALM", "metrace")
REALM_FILE = Path(os.environ.get("KC_REALM_FILE", "/srv/keycloak/realm-metrace.json"))
OVERLAY_DIR = Path(os.environ.get("KC_OVERLAY_DIR", "/srv/keycloak/overlays"))
DEMO_SSO_IDLE_SECONDS = 8 * 3600


def admin_client() -> httpx.Client:
    token = httpx.post(
        f"{BASE_URL}/realms/master/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": os.environ.get("KC_ADMIN_USERNAME", "admin"),
            "password": os.environ["KC_ADMIN_PASSWORD"],
        },
        timeout=15,
    )
    token.raise_for_status()
    return httpx.Client(
        base_url=f"{BASE_URL}/admin/realms/{REALM}",
        headers={"Authorization": f"Bearer {token.json()['access_token']}"},
        timeout=15,
    )


def find_user_id(kc: httpx.Client, username: str) -> str:
    res = kc.get("/users", params={"username": username, "exact": "true"})
    res.raise_for_status()
    users = res.json()
    if not users:
        raise RuntimeError(f"user {username!r} not found in realm {REALM}")
    return users[0]["id"]


def ensure_organization(kc: httpx.Client, org: dict) -> None:
    alias = org["alias"]
    res = kc.get("/organizations", params={"search": alias, "exact": "true"})
    res.raise_for_status()
    existing = [o for o in res.json() if o.get("alias") == alias]
    if existing:
        org_id = existing[0]["id"]
    else:
        body = {k: org[k] for k in ("name", "alias", "enabled", "domains") if k in org}
        kc.post("/organizations", json=body).raise_for_status()
        org_id = kc.get("/organizations", params={"search": alias, "exact": "true"}).json()[0]["id"]
        log.info("created organization %s", alias)

    members = kc.get(f"/organizations/{org_id}/members").json()
    member_names = {m["username"] for m in members}
    for member in org.get("members", []):
        if member["username"] in member_names:
            continue
        user_id = find_user_id(kc, member["username"])
        # The endpoint takes the bare user id as a JSON string.
        kc.post(f"/organizations/{org_id}/members", json=user_id).raise_for_status()
        log.info("added %s to organization %s", member["username"], alias)


def apply_overlay(kc: httpx.Client, name: str) -> None:
    if name == "demo":
        realm = kc.get("").json()
        if realm.get("ssoSessionIdleTimeout") != DEMO_SSO_IDLE_SECONDS:
            kc.put("", json={"ssoSessionIdleTimeout": DEMO_SSO_IDLE_SECONDS}).raise_for_status()
        log.info("overlay demo: SSO idle %ss", DEMO_SSO_IDLE_SECONDS)
        return
    files = sorted(OVERLAY_DIR.glob(f"{name}-*.json"))
    if not files:
        raise RuntimeError(f"unknown overlay {name!r} (no {OVERLAY_DIR}/{name}-*.json)")
    for path in files:
        kc.post("/partialImport", json=json.loads(path.read_text())).raise_for_status()
        log.info("overlay %s: applied %s", name, path.name)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s %(message)s")
    realm = json.loads(REALM_FILE.read_text())
    overlays = [o.strip() for o in os.environ.get("KC_OVERLAYS", "").split(",") if o.strip()]
    with admin_client() as kc:
        for org in realm.get("organizations", []):
            ensure_organization(kc, org)
        for name in overlays:
            apply_overlay(kc, name)
    log.info("done (organizations=%d, overlays=%s)", len(realm.get("organizations", [])), overlays or "none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
