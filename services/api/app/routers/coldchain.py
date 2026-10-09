# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Cold chain: readings from the sensor gateway (machine identity) and alerts for staff."""

import uuid
from decimal import Decimal

from fastapi import Depends, Query
from pydantic import AwareDatetime, BaseModel, Field

from app.core.authentication import CurrentPrincipal
from app.core.authorization import internal_router, require_any_role, sensor_router
from app.core.database import DbSession
from app.services import coldchain_service

readings = sensor_router(prefix="/api/v1/assets", tags=["cold chain"])
alerts = internal_router(prefix="/api/v1/coldchain", tags=["cold chain"])


class ReadingIn(BaseModel):
    ts: AwareDatetime = Field(description="Device clock with offset; rejected when more than 60 s off server time")
    temp_c: Decimal = Field(ge=-60, le=120)


class ReadingAccepted(BaseModel):
    accepted: bool
    breach: bool
    alert_id: uuid.UUID | None


class AcknowledgeIn(BaseModel):
    note: str = Field("", max_length=1000)


@readings.post("/{asset_code}/readings", response_model=ReadingAccepted, status_code=201)
def post_reading(asset_code: str, req: ReadingIn, session: DbSession, principal: CurrentPrincipal):
    return coldchain_service.ingest_reading(session, principal, asset_code, req.ts, req.temp_c)


@alerts.get("/alerts")
def list_open_alerts(session: DbSession) -> list[dict]:
    return coldchain_service.open_alerts(session)


@alerts.post("/alerts/{alert_id}/acknowledge", dependencies=[Depends(require_any_role({"qa"}))])
def acknowledge_alert(alert_id: uuid.UUID, req: AcknowledgeIn, session: DbSession, principal: CurrentPrincipal):
    alert = coldchain_service.acknowledge(session, principal, alert_id, req.note)
    return {"id": alert.id, "status": alert.status, "acknowledged_by": alert.acknowledged_by}


@alerts.get("/assets/{asset_code}/readings")
def asset_readings(asset_code: str, session: DbSession, minutes: int = Query(60, ge=1, le=1440)) -> dict:
    return coldchain_service.recent_readings(session, asset_code, minutes)
