# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""One error envelope for every failure:

{"error": {"code": "...", "rule": "P3"|null, "message": "...", "details": {...}, "request_id": "..."}}
"""

import logging
import uuid
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.reason_codes import ReasonCode

log = logging.getLogger("metrace.errors")

_STATUS_TO_CODE = {
    400: ReasonCode.VALIDATION_ERROR,
    401: ReasonCode.UNAUTHENTICATED,
    403: ReasonCode.FORBIDDEN,
    404: ReasonCode.NOT_FOUND,
    405: ReasonCode.METHOD_NOT_ALLOWED,
    409: ReasonCode.CONFLICT,
    413: ReasonCode.FILE_TOO_LARGE,
    415: ReasonCode.UNSUPPORTED_MEDIA_TYPE,
    429: ReasonCode.RATE_LIMITED,
    503: ReasonCode.SERVICE_UNAVAILABLE,
}


class InfraError(Exception):
    """Temporary infrastructure failure (network, 5xx, dependency down): retry with backoff."""


class AppError(Exception):
    """Raise from anywhere in the API; rendered with the common envelope."""

    def __init__(
        self,
        status: int,
        code: ReasonCode,
        message: str,
        *,
        rule: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.rule = rule
        self.details = details or {}


def not_found(entity: str) -> AppError:
    # Same answer for "does not exist" and "exists in another organization".
    return AppError(404, ReasonCode.NOT_FOUND, f"{entity} not found")


def request_id(request: Request) -> str:
    return request.headers.get("x-request-id") or str(uuid.uuid4())


def _envelope(request: Request, status: int, code: str, message: str, rule=None, details=None, headers=None):
    body = {
        "error": {
            "code": str(code),
            "rule": rule,
            "message": message,
            "details": details or {},
            "request_id": request_id(request),
        }
    }
    return JSONResponse(status_code=status, content=body, headers=headers)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError):
        return _envelope(request, exc.status, exc.code, exc.message, exc.rule, exc.details)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        details = {"errors": [{"loc": list(e["loc"]), "msg": e["msg"]} for e in exc.errors()]}
        return _envelope(request, 422, ReasonCode.VALIDATION_ERROR, "Invalid request", details=details)

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException):
        code = _STATUS_TO_CODE.get(exc.status_code, ReasonCode.INTERNAL_ERROR)
        return _envelope(request, exc.status_code, code, str(exc.detail), headers=getattr(exc, "headers", None))

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, exc: Exception):
        log.exception("unhandled error (request_id=%s)", request_id(request))
        return _envelope(request, 500, ReasonCode.INTERNAL_ERROR, "Internal error")
