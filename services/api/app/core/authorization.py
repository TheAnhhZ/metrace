# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Default-deny authorization.

Every business route hangs under one of three parent routers, each gated by a
role check: internal staff, customer portal, or machine (sensor). A CI test
walks `app.routes` and fails if any route escapes all three.
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from fastapi import APIRouter, Depends

from app.core.authentication import CurrentPrincipal
from app.core.errors import AppError
from app.core.principal import CUSTOMER_ROLE, INTERNAL_ROLES, SENSOR_ROLE, Principal
from app.core.reason_codes import ReasonCode


def require_any_role(roles: Iterable[str]) -> Callable[[Principal], Principal]:
    allowed = frozenset(roles)

    def dependency(principal: CurrentPrincipal) -> Principal:
        if not principal.roles & allowed:
            raise AppError(403, ReasonCode.FORBIDDEN, "Missing required role", details={"required": sorted(allowed)})
        return principal

    dependency.allowed_roles = allowed  # type: ignore[attr-defined]  # read by the route-role test
    return dependency


@dataclass(frozen=True)
class OrgScope:
    """Which customer organizations the caller may see. `all_orgs` = internal staff."""

    all_orgs: bool
    aliases: frozenset[str]

    def allows(self, org_alias: str | None) -> bool:
        if self.all_orgs:
            return True
        return org_alias is not None and org_alias in self.aliases


def org_scope(principal: Principal) -> OrgScope:
    """The single place that turns a principal into a data-visibility scope."""
    if principal.is_internal:
        return OrgScope(all_orgs=True, aliases=frozenset())
    if CUSTOMER_ROLE in principal.roles:
        return OrgScope(all_orgs=False, aliases=principal.org_aliases)
    return OrgScope(all_orgs=False, aliases=frozenset())


require_internal = require_any_role(INTERNAL_ROLES)
require_customer = require_any_role({CUSTOMER_ROLE})
require_sensor = require_any_role({SENSOR_ROLE})


def internal_router(**kwargs) -> APIRouter:
    return APIRouter(dependencies=[Depends(require_internal)], **kwargs)


def portal_router(**kwargs) -> APIRouter:
    return APIRouter(dependencies=[Depends(require_customer)], **kwargs)


def sensor_router(**kwargs) -> APIRouter:
    return APIRouter(dependencies=[Depends(require_sensor)], **kwargs)
