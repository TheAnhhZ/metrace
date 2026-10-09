# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""metrace API entry point."""

from fastapi import FastAPI

from app.routers import health, whoami

app = FastAPI(
    title="metrace API",
    version="0.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
)
app.include_router(health.router)
app.include_router(whoami.router)
