# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Shared PDF layout for the paper forms: Unicode font (Noto Sans, OFL-1.1) for
Vietnamese, a title block, simple tables and a footer that prints the audit
chain head (seq + hash) as an anchor outside the database."""

import io
from collections.abc import Sequence
from functools import cache
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

FONT_DIR = Path(__file__).with_name("fonts")


@cache
def _register_fonts() -> None:
    pdfmetrics.registerFont(TTFont("NotoSans", FONT_DIR / "NotoSans-Regular.ttf"))
    pdfmetrics.registerFont(TTFont("NotoSans-Bold", FONT_DIR / "NotoSans-Bold.ttf"))


def styles() -> dict[str, ParagraphStyle]:
    _register_fonts()
    return {
        "title": ParagraphStyle("title", fontName="NotoSans-Bold", fontSize=14, leading=18, spaceAfter=4),
        "note": ParagraphStyle("note", fontName="NotoSans", fontSize=8, leading=10, textColor=colors.grey),
        "h": ParagraphStyle("h", fontName="NotoSans-Bold", fontSize=10, leading=13, spaceBefore=8, spaceAfter=3),
        "body": ParagraphStyle("body", fontName="NotoSans", fontSize=9, leading=12),
    }


def table(rows: Sequence[Sequence[object]], widths: Sequence[float], header: bool = True) -> Table:
    st = styles()["body"]
    # Escape: ReportLab paragraphs parse markup, and cells carry master data typed by people.
    data = [[Paragraph(escape("" if cell is None else str(cell)), st) for cell in row] for row in rows]
    t = Table(data, colWidths=[w * mm for w in widths], repeatRows=1 if header else 0)
    commands = [
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]
    if header:
        commands.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")))
    t.setStyle(TableStyle(commands))
    return t


def render(title: str, subtitle: str, flowables: list, audit_head: tuple[int, str] | None) -> bytes:
    st = styles()
    out = io.BytesIO()
    anchor = f"Neo nhật ký kiểm toán: #{audit_head[0]} · {audit_head[1]}" if audit_head else "Chưa có nhật ký"

    def footer(canvas, doc) -> None:
        canvas.saveState()
        canvas.setFont("NotoSans", 7)
        canvas.drawString(15 * mm, 10 * mm, f"metrace · {anchor}")
        canvas.drawRightString(195 * mm, 10 * mm, f"Trang {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        out,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=18 * mm,
        title=title,
        author="metrace",
    )
    story = [
        Paragraph(title, st["title"]),
        Paragraph(subtitle, st["note"]),
        Paragraph(
            "Bố cục tham khảo theo QĐ 1246/QĐ-BYT (chờ đối chiếu phụ lục chính thức). Dữ liệu synthetic.", st["note"]
        ),
        Spacer(1, 4 * mm),
        *flowables,
    ]
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return out.getvalue()
