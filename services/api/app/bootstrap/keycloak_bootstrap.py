# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""One-shot `kc-bootstrap`: make the metrace realm match the repo, idempotently.

1. Organizations + memberships from the realm file (import may skip members).
2. The `organization` claim carries the organization id next to the alias.
3. Overlays listed in KC_OVERLAYS (comma separated):
   - test: client `metrace-test` (direct access grants, CI/pytest only)
   - demo: longer SSO idle so demo personas stay logged in

Talks to the Keycloak admin REST API over the internal docker network only;
the admin API is never routed through the public gateway.
"""

import json
import logging
import os
import sys
import time
from pathlib import Path

import httpx

log = logging.getLogger("kc-bootstrap")

BASE_URL = os.environ.get("KC_INTERNAL_URL", "http://keycloak:8080/auth")
REALM = os.environ.get("KC_REALM", "metrace")
REALM_FILE = Path(os.environ.get("KC_REALM_FILE", "/srv/keycloak/realm-metrace.json"))
OVERLAY_DIR = Path(os.environ.get("KC_OVERLAY_DIR", "/srv/keycloak/overlays"))
DEMO_SSO_IDLE_SECONDS = 8 * 3600


def admin_token(attempts: int = 30, delay_seconds: float = 3.0) -> str:
    """Master-realm admin token; retries while Keycloak finishes bootstrapping (503)."""
    form = {
        "grant_type": "password",
        "client_id": "admin-cli",
        "username": os.environ.get("KC_ADMIN_USERNAME", "admin"),
        "password": os.environ["KC_ADMIN_PASSWORD"],
    }
    for attempt in range(1, attempts + 1):
        try:
            res = httpx.post(f"{BASE_URL}/realms/master/protocol/openid-connect/token", data=form, timeout=15)
            if res.status_code == 200:
                return res.json()["access_token"]
            if res.status_code < 500:
                res.raise_for_status()  # wrong credentials: retrying will not help
            log.info("keycloak not ready (HTTP %s), attempt %d/%d", res.status_code, attempt, attempts)
        except httpx.TransportError as exc:
            log.info("keycloak unreachable (%s), attempt %d/%d", exc, attempt, attempts)
        time.sleep(delay_seconds)
    raise RuntimeError("keycloak admin token unavailable")


def admin_client() -> httpx.Client:
    return httpx.Client(
        base_url=f"{BASE_URL}/admin/realms/{REALM}",
        headers={"Authorization": f"Bearer {admin_token()}"},
        timeout=15,
    )


def find_user_id(kc: httpx.Client, username: str) -> str:
    res = kc.get("/users", params={"username": username, "exact": "true"})
    res.raise_for_status()
    users = res.json()
    if not users:
        raise RuntimeError(f"user {username!r} not found in realm {REALM}")
    return users[0]["id"]


def organization_ids_by_alias(kc: httpx.Client) -> dict[str, str]:
    # `search` matches names/domains, not aliases, so list and filter here.
    res = kc.get("/organizations", params={"first": 0, "max": 1000})
    res.raise_for_status()
    return {o["alias"]: o["id"] for o in res.json()}


def ensure_organization(kc: httpx.Client, org: dict) -> None:
    alias = org["alias"]
    org_id = organization_ids_by_alias(kc).get(alias)
    if org_id is None:
        body = {k: org[k] for k in ("name", "alias", "enabled", "domains") if k in org}
        kc.post("/organizations", json=body).raise_for_status()
        org_id = organization_ids_by_alias(kc)[alias]
        log.info("created organization %s", alias)

    res = kc.get(f"/organizations/{org_id}/members")
    res.raise_for_status()
    members = res.json()
    member_names = {m["username"] for m in members}
    for member in org.get("members", []):
        if member["username"] in member_names:
            continue
        user_id = find_user_id(kc, member["username"])
        # The endpoint takes the bare user id as a JSON string.
        kc.post(f"/organizations/{org_id}/members", json=user_id).raise_for_status()
        log.info("added %s to organization %s", member["username"], alias)


def ensure_organization_claim_has_id(kc: httpx.Client) -> None:
    """Built-in `organization` scope: emit {"alias": {"id": ...}} instead of ["alias"]."""
    scopes = kc.get("/client-scopes").json()
    scope = next((s for s in scopes if s["name"] == "organization"), None)
    if scope is None:
        raise RuntimeError("client scope 'organization' missing (organizations disabled?)")
    for mapper in scope.get("protocolMappers", []):
        if mapper["protocolMapper"] != "oidc-organization-membership-mapper":
            continue
        if mapper["config"].get("addOrganizationId") == "true":
            return
        mapper["config"]["addOrganizationId"] = "true"
        kc.put(f"/client-scopes/{scope['id']}/protocol-mappers/models/{mapper['id']}", json=mapper).raise_for_status()
        log.info("organization claim now includes organization id")


def overlay_names() -> set[str]:
    return {p.name.split("-", 1)[0] for p in OVERLAY_DIR.glob("*.json")}


def remove_overlay_clients(kc: httpx.Client, name: str) -> None:
    """An overlay that is NOT requested must leave no trace (e.g. no CI client in a demo)."""
    for path in sorted(OVERLAY_DIR.glob(f"{name}-*.json")):
        for client in json.loads(path.read_text()).get("clients", []):
            res = kc.get("/clients", params={"clientId": client["clientId"]})
            res.raise_for_status()
            for found in res.json():
                kc.delete(f"/clients/{found['id']}").raise_for_status()
                log.info("overlay %s not requested: removed client %s", name, client["clientId"])


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
        ensure_organization_claim_has_id(kc)
        for name in overlays:
            apply_overlay(kc, name)
        for name in sorted(overlay_names() - set(overlays)):
            remove_overlay_clients(kc, name)
    log.info("done (organizations=%d, overlays=%s)", len(realm.get("organizations", [])), overlays or "none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
