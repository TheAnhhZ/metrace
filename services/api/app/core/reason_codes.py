# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Every machine-readable error code the API can return, in one place.

The UI maps these codes to Vietnamese messages (packages/api-client).
"""

from enum import StrEnum


class ReasonCode(StrEnum):
    # Generic
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNAUTHENTICATED = "UNAUTHENTICATED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    IDP_UNAVAILABLE = "IDP_UNAVAILABLE"
    INTERNAL_ERROR = "INTERNAL_ERROR"

    # Files
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    FILE_TYPE_NOT_ALLOWED = "FILE_TYPE_NOT_ALLOWED"
    FILE_TYPE_MISMATCH = "FILE_TYPE_MISMATCH"
    FILE_EMPTY = "FILE_EMPTY"
