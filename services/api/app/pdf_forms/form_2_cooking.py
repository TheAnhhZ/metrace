# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Mẫu 2 (kiểm tra khi chế biến) for one cooking batch, from recorded data only."""

import uuid

from reportlab.platypus import Paragraph
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit_hash_chain import chain_head
from app.core.business_time import business_tz
from app.core.database import get_or_404
from app.models.cooking import CookingBatch, Dish, PortionCheck, RetainedSample
from app.models.shipment import Shipment
from app.pdf_forms.pdf_base_layout import render, styles, table
from app.services.cooking_service import list_inputs


def _local(at) -> str:
    return at.astimezone(business_tz()).strftime("%d/%m/%Y %H:%M") if at else "—"


def form_2_pdf(session: Session, batch_id: uuid.UUID) -> bytes:
    batch = get_or_404(session, CookingBatch, batch_id, "batch")
    dish = session.get(Dish, batch.dish_id)
    st = styles()
    general = table(
        [
            ["Mã mẻ", batch.batch_code, "Món", dish.name],
            ["Ngày phục vụ", batch.service_date.strftime("%d/%m/%Y"), "Bữa", batch.meal_slot],
            ["Bắt đầu nấu", _local(batch.started_at), "Kết thúc", _local(batch.finished_at)],
            ["Nhiệt độ tâm (°C)", batch.core_temp_c or "—", "Người phụ trách", batch.owner],
            ["Suất dự kiến", batch.portions_planned, "Suất thực tế", batch.portions_produced or "—"],
        ],
        [32, 58, 32, 58],
        header=False,
    )
    inputs = table(
        [["Nguyên liệu / bán thành phẩm", "Khối lượng (kg)", "Người ghi", "Thời điểm"]]
        + [[i["label"], i["qty_kg"], i["added_by"], _local(i["added_at"])] for i in list_inputs(session, batch.id)],
        [80, 30, 35, 35],
    )
    samples = session.scalars(select(RetainedSample).where(RetainedSample.batch_id == batch.id)).all()
    sample_rows = [["Mã niêm phong", "Khối lượng", "Lưu lúc", "Được hủy sau"]] + [
        [
            s.seal_code,
            f"{s.qty_g} g" if s.qty_g else f"{s.qty_ml} ml",
            _local(s.stored_at),
            _local(s.eligible_discard_at),
        ]
        for s in samples
    ]
    checks = session.execute(
        select(PortionCheck, Shipment.code)
        .join(Shipment, Shipment.id == PortionCheck.shipment_id)
        .where(PortionCheck.batch_id == batch.id)
        .order_by(PortionCheck.checked_at)
    ).all()
    check_rows = [["Chuyến", "Số suất", "Đúng thực đơn", "Cảm quan", "Người kiểm"]] + [
        [code, c.portions, "Đạt" if c.menu_match else "Không", "Đạt" if c.sensory_ok else "Không", c.checked_by]
        for c, code in checks
    ]
    flowables = [
        Paragraph("Thông tin mẻ", st["h"]),
        general,
        Paragraph("Nguyên liệu đưa vào (truy xuất được tới lô và nhà cung cấp)", st["h"]),
        inputs,
        Paragraph("Mẫu lưu", st["h"]),
        table(sample_rows, [45, 30, 50, 55]),
        Paragraph("Kiểm tra trước khi chia/giao (Mẫu 3)", st["h"]),
        table(check_rows, [55, 25, 35, 30, 35]),
    ]
    return render(
        "MẪU 2 — KIỂM TRA KHI CHẾ BIẾN THỨC ĂN", f"Bếp trung tâm · {batch.batch_code}", flowables, chain_head(session)
    )
