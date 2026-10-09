# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Poka-yoke finding as returned to clients (warnings on success, blockers on shipments)."""

from pydantic import BaseModel, ConfigDict


class Finding(BaseModel):
    """One Poka-yoke result. Extra keys carry context (measured, limit, unit, basis, basis_type, batch, ...)."""

    model_config = ConfigDict(extra="allow")

    rule: str
    code: str
    measured: str | None = None
    limit: str | None = None
    unit: str | None = None
    basis: str | None = None
    basis_type: str | None = None
