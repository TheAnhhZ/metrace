# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""FastAPI dependency: bearer token -> verified Principal."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.errors import AppError
from app.core.principal import Principal, principal_from_claims
from app.core.reason_codes import ReasonCode
from app.core.security_jwt import (
    InvalidTokenError,
    KeySetUnavailableError,
    verify_access_token,
)
from app.core.settings import Settings, get_settings

_bearer = HTTPBearer(auto_error=False)


def get_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Principal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        claims = verify_access_token(credentials.credentials, settings)
    except KeySetUnavailableError as exc:
        raise AppError(503, ReasonCode.IDP_UNAVAILABLE, "Identity provider unavailable") from exc
    except InvalidTokenError as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
        ) from exc
    return principal_from_claims(claims)


CurrentPrincipal = Annotated[Principal, Depends(get_principal)]
