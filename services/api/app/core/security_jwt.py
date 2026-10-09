# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Verify Keycloak access tokens against the realm JWKS.

APISIX already verifies the token; the API verifies it again and never trusts
headers injected by the gateway (zero-trust, defense in depth).
"""

from functools import lru_cache
from typing import Any

import jwt
from jwt import PyJWKClient

from app.core.settings import Settings

ALLOWED_ALGORITHMS = ["RS256"]


class InvalidTokenError(Exception):
    """The bearer token is missing, malformed, expired or not for us (-> 401)."""


class KeySetUnavailableError(Exception):
    """The identity provider's key set cannot be fetched (-> 503)."""


@lru_cache
def _jwks_client(jwks_url: str) -> PyJWKClient:
    # Keys are cached in-process; a token with an unknown `kid` triggers a refetch.
    return PyJWKClient(jwks_url, cache_keys=True, lifespan=300, timeout=5)


def verify_access_token(token: str, settings: Settings) -> dict[str, Any]:
    """Return the verified claims or raise InvalidTokenError / KeySetUnavailableError."""
    try:
        signing_key = _jwks_client(settings.oidc_jwks_url).get_signing_key_from_jwt(token)
    except jwt.PyJWKClientConnectionError as exc:
        raise KeySetUnavailableError(str(exc)) from exc
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc

    try:
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=ALLOWED_ALGORITHMS,
            audience=settings.oidc_audience,
            issuer=settings.oidc_issuer,
            leeway=settings.oidc_leeway_seconds,
            options={"require": ["exp", "iat", "iss", "aud", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc
