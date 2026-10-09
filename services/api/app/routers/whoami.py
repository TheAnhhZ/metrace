# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""GET /api/v1/whoami: identity as the API sees it, plus server time for UI countdowns."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.authentication import CurrentPrincipal
from app.core.settings import Settings, get_settings

router = APIRouter(tags=["identity"])


class WhoAmI(BaseModel):
    sub: str
    username: str
    roles: list[str]
    organizations: list[str]
    client_id: str | None
    server_now: datetime
    business_tz: str


@router.get("/api/v1/whoami", response_model=WhoAmI)
def whoami(principal: CurrentPrincipal, settings: Annotated[Settings, Depends(get_settings)]) -> WhoAmI:
    return WhoAmI(
        sub=principal.sub,
        username=principal.username,
        roles=sorted(principal.roles),
        organizations=sorted(principal.org_aliases),
        client_id=principal.client_id,
        server_now=datetime.now(UTC),
        business_tz=settings.business_tz,
    )
