# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Sensor ingest (machine identity, asset claim, clock skew) and cold-chain alerts.

A breach opens at most one alert per asset (partial unique index) and asks the
worker, via the outbox, to start the `cold-chain-alert` process.
"""

import uuid
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.audit_hash_chain import append_audit
from app.core.business_time import utcnow
from app.core.errors import AppError, not_found
from app.core.outbox import emit
from app.core.principal import Principal
from app.core.reason_codes import ReasonCode
from app.models.coldchain import AlertStatus, ColdChainAlert, SensorReading
from app.models.cooking import RetainedSample
from app.models.enums import SampleStatus
from app.models.kitchen_and_customers import Asset
from app.rules.coldchain_rules import Band, clock_skew_ok, is_breach
from app.rules.thresholds import load_thresholds
from app.services import lineage_query
from app.services.lineage_presenter import present
from app.services.lineage_query import NodeRef


def _asset_by_code(session: Session, code: str) -> Asset:
    asset = session.scalar(select(Asset).where(Asset.code == code))
    if asset is None:
        raise not_found("asset")
    return asset


def ingest_reading(session: Session, principal: Principal, asset_code: str, ts: datetime, temp_c) -> dict:
    if asset_code not in principal.asset_codes:
        raise AppError(403, ReasonCode.FORBIDDEN, "This client may not report for that asset")
    asset = _asset_by_code(session, asset_code)
    th, now = load_thresholds(session), utcnow()
    if not clock_skew_ok(ts, now, th):
        raise AppError(
            422,
            ReasonCode.VALIDATION_ERROR,
            "Device clock is too far from server time",
            details={"max_skew_s": str(th.get("coldchain_max_skew_s"))},
        )
    session.add(
        SensorReading(asset_id=asset.id, ts=ts, received_at=now, source_client=principal.client_id or "", temp_c=temp_c)
    )
    session.flush()
    latest = session.scalars(
        select(SensorReading.temp_c)
        .where(SensorReading.asset_id == asset.id)
        .order_by(SensorReading.received_at.desc(), SensorReading.id.desc())
        .limit(10)
    ).all()
    alert_id = None
    if is_breach(latest, Band(asset.min_c, asset.max_c), th):
        alert_id = session.scalar(
            insert(ColdChainAlert)
            .values(id=uuid.uuid4(), asset_id=asset.id, max_temp_c=max(latest), status=AlertStatus.OPEN)
            .on_conflict_do_nothing(index_elements=["asset_id"], index_where=ColdChainAlert.status == "open")
            .returning(ColdChainAlert.id)
        )
        if alert_id:  # a NEW alert (an open one already exists otherwise)
            append_audit(
                session,
                actor=principal.username,
                action="coldchain.alert_opened",
                entity_type="asset",
                entity_id=asset.id,
                payload={"asset": asset.code, "readings": [str(t) for t in latest[:3]]},
            )
            emit(
                session,
                "coldchain.breach",
                {"alert_id": alert_id, "asset": asset.code},
                aggregate_type="coldchain_alert",
                aggregate_id=alert_id,
            )
    session.commit()
    return {"accepted": True, "breach": alert_id is not None, "alert_id": alert_id}


def affected(session: Session, asset: Asset) -> dict:
    """What sat in the fridge: lots (and their downstream) plus retained samples."""
    walk = lineage_query.forward(session, NodeRef("asset", asset.id), max_depth=lineage_query.MAX_DEPTH_CAP)
    nodes = [n for n in present(session, walk)["nodes"] if n["type"] in ("lot", "batch")]
    samples = session.scalars(
        select(RetainedSample.seal_code).where(
            RetainedSample.fridge_asset_id == asset.id, RetainedSample.status == SampleStatus.STORED
        )
    ).all()
    return {"nodes": nodes, "samples": list(samples)}


def open_alerts(session: Session) -> list[dict]:
    rows = session.execute(
        select(ColdChainAlert, Asset)
        .join(Asset, Asset.id == ColdChainAlert.asset_id)
        .where(ColdChainAlert.status == AlertStatus.OPEN)
        .order_by(ColdChainAlert.opened_at)
    ).all()
    return [
        {
            "id": alert.id,
            "asset_code": asset.code,
            "asset_name": asset.name,
            "opened_at": alert.opened_at,
            "max_temp_c": alert.max_temp_c,
            "min_c": asset.min_c,
            "max_c": asset.max_c,
            "process_instance_id": alert.process_instance_id,
            **affected(session, asset),
        }
        for alert, asset in rows
    ]


def acknowledge(session: Session, principal: Principal, alert_id: uuid.UUID, note: str) -> ColdChainAlert:
    alert = session.get(ColdChainAlert, alert_id, with_for_update=True)
    if alert is None:
        raise not_found("alert")
    if alert.status != AlertStatus.OPEN:
        raise AppError(409, ReasonCode.CONFLICT, "Alert already acknowledged")
    alert.status, alert.acknowledged_by, alert.acknowledged_at, alert.note = (
        AlertStatus.ACKNOWLEDGED,
        principal.username,
        utcnow(),
        note,
    )
    append_audit(
        session,
        actor=principal.username,
        action="coldchain.alert_acknowledged",
        entity_type="asset",
        entity_id=alert.asset_id,
        payload={"alert": alert.id, "note": note},
    )
    emit(
        session,
        "coldchain.acknowledged",
        {"alert_id": alert.id},
        aggregate_type="coldchain_alert",
        aggregate_id=alert.id,
    )
    session.commit()
    return alert


def recent_readings(session: Session, asset_code: str, minutes: int) -> dict:
    asset = _asset_by_code(session, asset_code)
    since = utcnow() - timedelta(minutes=minutes)
    rows = session.execute(
        select(SensorReading.received_at, SensorReading.temp_c)
        .where(SensorReading.asset_id == asset.id, SensorReading.received_at >= since)
        .order_by(SensorReading.received_at)
    ).all()
    return {
        "asset_code": asset.code,
        "min_c": asset.min_c,
        "max_c": asset.max_c,
        "server_now": utcnow(),
        "readings": [{"at": at, "temp_c": t} for at, t in rows],
    }
