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

    # Runtime role (metrace_app) cannot UPDATE/DELETE the audit chain.
    database_url: str = "postgresql+psycopg://metrace_app:metrace_app@localhost:5432/metrace"

    # Object storage (SeaweedFS S3). Files are always streamed through the API.
    s3_endpoint_url: str = "http://seaweedfs:8333"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket: str = "metrace-files"
    upload_max_bytes: int = 10 * 1024 * 1024

    # Workflow engine, called by the worker only.
    flowable_url: str = "http://flowable:8080/flowable-rest"
    flowable_user: str = "rest-admin"
    flowable_password: str = ""

    # Business time zone: DB stores UTC, service dates are computed here.
    business_tz: str = "Asia/Ho_Chi_Minh"


@lru_cache
def get_settings() -> Settings:
    return Settings()
