# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Runtime settings, read from environment variables (see compose.yaml)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

    # OIDC: tokens carry the PUBLIC issuer (browser origin), while keys are
    # fetched over the internal docker network.
    oidc_issuer: str = "http://localhost:9080/auth/realms/metrace"
    oidc_jwks_url: str = "http://keycloak:8080/auth/realms/metrace/protocol/openid-connect/certs"
    oidc_audience: str = "metrace-api"
    oidc_leeway_seconds: int = 30

    # Business time zone: DB stores UTC, service dates are computed here.
    business_tz: str = "Asia/Ho_Chi_Minh"


@lru_cache
def get_settings() -> Settings:
    return Settings()
