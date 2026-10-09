# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Turn verified token claims into a Principal (who is calling, with which roles/orgs)."""

from dataclasses import dataclass
from typing import Any

INTERNAL_ROLES = frozenset({"qa", "procurement", "chef", "driver", "cskh", "director", "approver"})
CUSTOMER_ROLE = "customer_staff"
SENSOR_ROLE = "sensor"


@dataclass(frozen=True)
class Principal:
    sub: str
    username: str
    roles: frozenset[str]
    # Organizations are keyed by alias: stable across realm re-imports, unlike ids.
    org_aliases: frozenset[str]
    client_id: str | None = None

    @property
    def is_internal(self) -> bool:
        return bool(self.roles & INTERNAL_ROLES)


def parse_organization_claim(value: Any) -> frozenset[str]:
    """Accept both Keycloak shapes: {"alias": {"id": ...}} or ["alias", ...]."""
    if isinstance(value, dict):
        return frozenset(str(alias) for alias in value)
    if isinstance(value, list):
        return frozenset(str(alias) for alias in value if isinstance(alias, str))
    return frozenset()


def principal_from_claims(claims: dict[str, Any]) -> Principal:
    realm_access = claims.get("realm_access") or {}
    roles = realm_access.get("roles") or []
    return Principal(
        sub=str(claims["sub"]),
        username=str(claims.get("preferred_username") or claims["sub"]),
        roles=frozenset(str(role) for role in roles),
        org_aliases=parse_organization_claim(claims.get("organization")),
        client_id=claims.get("azp"),
    )
