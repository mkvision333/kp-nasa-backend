from __future__ import annotations

from typing import Dict, Any, List, Tuple
import re

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Flowable,
    KeepTogether,
    PageBreak,
)
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from ..common.header_footer import on_page
from app.pdf_engine.common.cover_page import build_cover_page


CREAM = colors.HexColor("#FFF6E6")
CREAM2 = colors.HexColor("#FFFBF2")
GOLD = colors.HexColor("#B8860B")
TXT = colors.HexColor("#111111")


def _safe(v: Any, dash: str = "—") -> str:
    if v is None:
        return dash
    s = str(v).strip()
    return s if s else dash


def _fmt_deg_short(v: Any) -> str:
    """Degree formatting like 12°34' (best-effort)."""
    s = str(v or "").strip()
    if not s:
        return "—"
    nums = re.findall(r"\d+", s)
    if len(nums) >= 2:
        d = int(nums[0])
        m = int(nums[1])
        return f"{d}°{str(m).zfill(2)}'"
    if len(nums) == 1:
        d = int(nums[0])
        return f"{d}°00'"
    return "—"


def _section_title(text: str) -> Paragraph:
    styles = getSampleStyleSheet()
    st = ParagraphStyle(
        "SecTitle",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=14,
        textColor=GOLD,
        spaceBefore=6,
        spaceAfter=8,
    )
    return Paragraph(f"🕉 {text}", st)


def _kv_table(rows: List[Tuple[str, Any]]) -> Table:
    data = [[k, _safe(v)] for k, v in rows]
    t = Table(data, colWidths=[50 * mm, 135 * mm])
    t.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 10.5),
                ("TEXTCOLOR", (0, 0), (-1, -1), TXT),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [CREAM2, CREAM]),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#DDDDDD")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return t


def _coerce_house_map(houses: Dict[Any, Any]) -> Dict[int, str]:
    out: Dict[int, str] = {}
    if not isinstance(houses, dict):
        return out
    for k, v in houses.items():
        try:
            ki = int(str(k).strip())
        except Exception:
            continue
        if 1 <= ki <= 12:
            out[ki] = str(v or "").strip()
    return out


class SouthIndianChartFlowable(Flowable):
    """
    South Indian chart:
    ✅ House 1 at TOP row 2nd box (clockwise)
    ✅ Center 2x2 EMPTY (no middle grid lines)
    """

    def __init__(self, houses: Dict[int, str], title: str = "Rasi Chart", size_mm: int = 88):
        super().__init__()
        self.houses = _coerce_house_map(houses or {})
        self.title = title
        self.size = size_mm * mm
        self.width = self.size
        self.height = self.size + 10 * mm

    def draw(self):
        c = self.canv
        x = 0
        y = 0

        # title
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(TXT)
        c.drawString(x, y + self.size + 4 * mm, self.title)

        # outer square
        c.setStrokeColor(GOLD)
        c.setLineWidth(1.2)
        c.rect(x, y, self.size, self.size, stroke=1, fill=0)

        step = self.size / 4.0

        # draw ONLY perimeter grid, keep center empty
        c.setLineWidth(0.7)
        c.setStrokeColor(colors.HexColor("#444444"))

        # full lines at 1*step and 3*step (outer ring separators)
        for i in (1, 3):
            c.line(x + step * i, y, x + step * i, y + self.size)
            c.line(x, y + step * i, x + self.size, y + step * i)

        # partial lines at 2*step (avoid the middle 2x2)
        # vertical at 2*step: bottom band + top band only
        c.line(x + step * 2, y, x + step * 2, y + step * 1)
        c.line(x + step * 2, y + step * 3, x + step * 2, y + self.size)

        # horizontal at 2*step: left band + right band only
        c.line(x, y + step * 2, x + step * 1, y + step * 2)
        c.line(x + step * 3, y + step * 2, x + self.size, y + step * 2)

        # placement (1 at top row 2nd box, clockwise)
        house_pos = {
            1: (1, 3),
            2: (2, 3),
            3: (3, 3),
            4: (3, 2),
            5: (3, 1),
            6: (3, 0),
            7: (2, 0),
            8: (1, 0),
            9: (0, 0),
            10: (0, 1),
            11: (0, 2),
            12: (0, 3),
        }

        c.setFont("Helvetica", 7.6)
        c.setFillColor(TXT)

        for house, (cx, cy) in house_pos.items():
            txt = str(self.houses.get(house, "")).strip()
            if not txt:
                continue
            ox = x + step * cx
            oy = y + step * cy
            c.drawString(ox + 2 * mm, oy + step - 6 * mm, f"{house}: {txt}")


def _table_style_header() -> List[Tuple]:
    return [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#121212")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#DDDDDD")),
        ("FONTSIZE", (0, 1), (-1, -1), 10.2),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [CREAM2, CREAM]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]


def build_birth_chart_pdf(file_path: str, data: Dict[str, Any], meta: Dict[str, Any]) -> None:
    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#222222"),
    )

    doc = SimpleDocTemplate(
        file_path,
        pagesize=A4,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=22 * mm,
        bottomMargin=16 * mm,
        title="Birth Chart Report",
        author="Pro KP Astrologer",
    )

    story: List[Any] = []

    # 0) Cover Page (this function should add its own PageBreak at end)
    build_cover_page(story, data.get("userName", ""))

    # 1) Birth Details (MUST start on next page)
    story.append(_section_title("1) Birth Details"))
    birth = data.get("birth") or {}

    # optional parent names if you pass later
    father = (birth.get("fatherName") if isinstance(birth, dict) else None) or data.get("fatherName")
    mother = (birth.get("motherName") if isinstance(birth, dict) else None) or data.get("motherName")

    story.append(
        _kv_table(
            [
                ("Name", data.get("userName") or birth.get("name")),
                ("Father Name", father),
                ("Mother Name", mother),
                ("Gender", birth.get("gender")),
                ("Date & Time", birth.get("datetime")),
                ("Place", birth.get("place")),
                ("Latitude", birth.get("lat")),
                ("Longitude", birth.get("lon")),
                ("Timezone", birth.get("tz")),
                ("Ayanamsa", data.get("ayanamsa")),
                ("Node Mode", data.get("nodeMode")),
            ]
        )
    )

    # 2) Gana / Ghata / Adrushta (separate page)
    story.append(PageBreak())
    story.append(_section_title("2) Gana Kutami • Ghata Kutami • Adrushta"))

    # Expect these keys (frontend payload should send them)
    gana = data.get("ganaKutami") or {}
    ghata = data.get("ghataKutami") or {}
    adru = data.get("adrushta") or {}

    # If nothing present, show a clear note (not empty)
    if not any([isinstance(gana, dict) and any(str(v or "").strip() for v in gana.values()),
                isinstance(ghata, dict) and any(str(v or "").strip() for v in ghata.values()),
                isinstance(adru, dict) and any(str(v or "").strip() for v in adru.values())]):
        story.append(Paragraph("Gana/Ghata/Adrushta data not provided in payload.", body))
    else:
        # Gana
        story.append(Paragraph("<b>Gana Kutami</b>", body))
        if isinstance(gana, dict) and gana:
            story.append(_kv_table([(k, v) for k, v in gana.items()]))
        else:
            story.append(Paragraph("—", body))
        story.append(Spacer(1, 4 * mm))

        # Ghata
        story.append(Paragraph("<b>Ghata Kutami</b>", body))
        if isinstance(ghata, dict) and ghata:
            story.append(_kv_table([(k, v) for k, v in ghata.items()]))
        else:
            story.append(Paragraph("—", body))
        story.append(Spacer(1, 4 * mm))

        # Adrushta
        story.append(Paragraph("<b>Adrushta</b>", body))
        if isinstance(adru, dict) and adru:
            story.append(_kv_table([(k, v) for k, v in adru.items()]))
        else:
            story.append(Paragraph("—", body))

    # 3) Charts (separate page, never half-page)
    story.append(PageBreak())
    story.append(_section_title("3) Charts"))

    charts = data.get("charts") or {}
    rasi_houses = charts.get("rasiHouses") or {}
    nav_houses = charts.get("navamsaHouses") or {}

    chart_row = Table(
        [
            [
                SouthIndianChartFlowable(rasi_houses, title="Rasi Chart", size_mm=88),
                SouthIndianChartFlowable(nav_houses, title="Navamsa Chart", size_mm=88),
            ]
        ],
        colWidths=[95 * mm, 95 * mm],
    )
    chart_row.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (-1, -1), CREAM),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(KeepTogether([chart_row, Spacer(1, 6 * mm)]))

    # 4) Cusps
    story.append(PageBreak())
    story.append(_section_title("4) Cusps"))
    cusps = data.get("cusps") or []
    if cusps:
        cusp_data = [["House", "Sign", "Degree", "Star Lord", "Sub Lord"]]
        for c in cusps:
            cusp_data.append(
                [
                    _safe(c.get("house")),
                    _safe(c.get("sign")),
                    _fmt_deg_short(c.get("deg")),
                    _safe(c.get("starLord")),
                    _safe(c.get("subLord")),
                ]
            )
        t = Table(cusp_data, repeatRows=1, colWidths=[18 * mm, 28 * mm, 28 * mm, 55 * mm, 55 * mm])
        t.setStyle(TableStyle(_table_style_header()))
        story.append(t)
    else:
        story.append(Paragraph("Cusps data not provided.", body))

    # 5) Planets
    story.append(PageBreak())
    story.append(_section_title("5) Planets"))
    planets = data.get("planets") or []
    if planets:
        p_data = [["Planet", "Sign", "Degree", "Nakshatra", "Pada", "Star Lord", "Sub Lord"]]
        for p in planets:
            p_data.append(
                [
                    _safe(p.get("name")),
                    _safe(p.get("sign")),
                    _fmt_deg_short(p.get("deg")),
                    _safe(p.get("nakshatra")),
                    _safe(p.get("pada")),
                    _safe(p.get("starLord")),
                    _safe(p.get("subLord")),
                ]
            )
        t = Table(p_data, repeatRows=1, colWidths=[18 * mm, 22 * mm, 22 * mm, 35 * mm, 12 * mm, 40 * mm, 40 * mm])
        t.setStyle(TableStyle(_table_style_header()))
        story.append(t)
    else:
        story.append(Paragraph("Planets data not provided.", body))

    # 6) Dasha (Current)
    story.append(PageBreak())
    story.append(_section_title("6) Dasha (Current)"))
    dasha = data.get("dasha") or {}
    story.append(
        _kv_table(
            [
                ("Maha Dasha", dasha.get("maha")),
                ("Bhukti", dasha.get("bhukti")),
                ("Antara", dasha.get("antara")),
                ("Start", dasha.get("start")),
                ("End", dasha.get("end")),
            ]
        )
    )

    # 7) Mini Bhava Phalithalu
    story.append(PageBreak())
    story.append(_section_title("7) Mini Bhava Phalithalu"))
    bhava = data.get("bhavaPhal") or []
    if bhava:
        b_data = [["House", "Good", "Careful", "Notes"]]
        for b in bhava:
            b_data.append([_safe(b.get("house")), _safe(b.get("good")), _safe(b.get("bad")), _safe(b.get("notes"))])
        t = Table(b_data, repeatRows=1, colWidths=[16 * mm, 55 * mm, 55 * mm, 64 * mm])
        t.setStyle(TableStyle(_table_style_header()))
        story.append(t)
    else:
        story.append(Paragraph("Bhava phalithalu data not provided.", body))

    def _on_page(canvas, doc_):
        on_page(canvas, doc_, meta)

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)