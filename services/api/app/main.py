# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""metrace API entry point."""

import logging

from fastapi import FastAPI

from app.core.errors import install_error_handlers
from app.routers import GATED_ROUTERS, PUBLIC_ROUTERS

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


def create_app() -> FastAPI:
    app = FastAPI(
        title="metrace API",
        version="0.0.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
    )
    install_error_handlers(app)
    for router in PUBLIC_ROUTERS + GATED_ROUTERS:
        app.include_router(router)
    return app


app = create_app()
