# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Outbreak scenario (on top of baseline): two schools report children with
stomach aches after yesterday's lunch. The third report is filed live during the
demo, which tips the cluster suggestion over the threshold."""

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.business_time import service_date
from app.models.incident import Complaint
from app.seed.master_data_loader import MasterData

REPORTS = [
    ("truong-a", 90, 6, "phone", "6 học sinh đau bụng, buồn nôn sau bữa trưa hôm qua; nghi do món canh."),
    ("truong-b", 60, 4, "portal", "4 học sinh đau bụng nhẹ sau bữa trưa hôm qua."),
]


def seed_outbreak(session: Session, master: MasterData, now: datetime) -> dict[str, object]:
    yesterday = service_date(now) - timedelta(days=1)
    created = 0
    for alias, minutes_ago, affected, channel, description in REPORTS:
        code = f"PA-DEMO-{yesterday:%Y%m%d}-{alias}"
        if session.scalar(select(Complaint.id).where(Complaint.code == code)):
            continue
        reported_at = now - timedelta(minutes=minutes_ago)
        session.add(
            Complaint(
                code=code,
                customer_org_id=master.customers[alias].id,
                delivery_point_id=master.points[alias].id,
                channel=channel,
                service_date=yesterday,
                meal_slot="lunch",
                affected_count=affected,
                description=description,
                reported_by="cskh-thu" if channel == "phone" else alias,
                sla_due_at=reported_at + timedelta(hours=24),
                created_at=reported_at,
            )
        )
        created += 1
    session.flush()
    return {"complaints_created": created, "service_date": yesterday.isoformat()}
