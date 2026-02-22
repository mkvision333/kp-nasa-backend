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


def _safe(v: Any, dash: str = "—") -> str:
    if v is None:
        return dash
    s = str(v).strip()
    return s if s else dash


def _fmt_deg_short(v: Any) -> str:
    """Degree formatting like 12°34' (best-effort from string/number)."""
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


def _kv_table(rows: List[Tuple[str, Any]]) -> Table:
    data = [[k, _safe(v)] for k, v in rows]
    t = Table(data, colWidths=[45 * mm, 140 * mm])
    t.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 10.5),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#333333")),
                ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor("#111111")),
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


def _section_title(text: str) -> Paragraph:
    styles = getSampleStyleSheet()
    st = ParagraphStyle(
        "SecTitle",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=14,
        textColor=GOLD,
        spaceBefore=10,
        spaceAfter=8,
    )
    return Paragraph(f"🕉 {text}", st)


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
    ✅ Mesham is always TOP-LEFT 2nd box, clockwise order.
    """

    def __init__(self, houses: Dict[int, str], title: str = "Rasi Chart", size_mm: int = 90):
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

        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(colors.HexColor("#111111"))
        c.drawString(x, y + self.size + 4 * mm, self.title)

        c.setStrokeColor(GOLD)
        c.setLineWidth(1.2)
        c.rect(x, y, self.size, self.size, stroke=1, fill=0)

        step = self.size / 4.0
        c.setLineWidth(0.6)
        c.setStrokeColor(colors.HexColor("#444444"))
        for i in range(1, 4):
            c.line(x + step * i, y, x + step * i, y + self.size)
            c.line(x, y + step * i, x + self.size, y + step * i)

        # 1 at TOP row 2nd box (clockwise)
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

        c.setFont("Helvetica", 7.5)
        c.setFillColor(colors.HexColor("#111111"))

        for house, (cx, cy) in house_pos.items():
            txt = str(self.houses.get(house, "")).strip()
            if not txt:
                continue
            ox = x + step * cx
            oy = y + step * cy
            c.drawString(ox + 2 * mm, oy + step - 6 * mm, f"{house}: {txt}")


def _has_any_value(d: Dict[str, Any]) -> bool:
    if not isinstance(d, dict):
        return False
    for _, v in d.items():
        if v is None:
            continue
        if str(v).strip():
            return True
    return False


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

    # Cover Page
    build_cover_page(story, data.get("userName", ""))

    # ✅ Page 2 starts (Birth + Gana + Ghata + Adrushta) — all on same page
    story.append(PageBreak())

    # 1) Birth Details
    story.append(_section_title("1) Birth Details"))
    birth = data.get("birth") or {}
    story.append(
        _kv_table(
            [
                ("Name", data.get("userName") or birth.get("name")),
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
    story.append(Spacer(1, 6 * mm))

    # 2) Gana Kutami
    story.append(_section_title("2) Gana Kutami"))
    gk = data.get("ganaKutami") or data.get("gana_kutami") or {}
    if _has_any_value(gk):
        story.append(
            _kv_table(
                [
                    ("Janma Nakshatram", gk.get("janmaNakshatra") or gk.get("janma_nakshatra")),
                    ("Pada", gk.get("pada")),
                    ("Ganam", gk.get("gana")),
                    ("Nadi", gk.get("nadi")),
                    ("Yoni", gk.get("yoni")),
                    ("Varna", gk.get("varna")),
                    ("Vashya", gk.get("vashya")),
                    ("Vargu", gk.get("vargu")),
                ]
            )
        )
    else:
        story.append(Paragraph("Gana Kutami data not provided.", body))
    story.append(Spacer(1, 6 * mm))

    # 3) Ghata Kutami (NEW)
    story.append(_section_title("3) Ghata Kutami"))
    gh = data.get("ghataKutami") or data.get("ghata_kutami") or {}
    if _has_any_value(gh):
        story.append(
            _kv_table(
                [
                    ("Ghata Chakram", gh.get("ghataChakram") or gh.get("ghata_chakram")),
                    ("Status", gh.get("status")),
                    ("Result", gh.get("result")),
                    ("Notes", gh.get("notes")),
                ]
            )
        )
    else:
        story.append(Paragraph("Ghata Kutami data not provided.", body))
    story.append(Spacer(1, 6 * mm))

    # 4) Adrushta (NEW)
    story.append(_section_title("4) Adrushta"))
    ad = data.get("adrushta") or {}
    if _has_any_value(ad):
        story.append(
            _kv_table(
                [
                    ("Adrushta Chakram", ad.get("chakra")),
                    ("Score", ad.get("score")),
                    ("Result", ad.get("result")),
                    ("Notes", ad.get("notes")),
                ]
            )
        )
    else:
        story.append(Paragraph("Adrushta data not provided.", body))

    # 5) Charts (fresh page)
    story.append(PageBreak())
    story.append(_section_title("5) Charts"))
    charts = data.get("charts") or {}
    rasi_houses = charts.get("rasiHouses") or {}
    nav_houses = charts.get("navamsaHouses") or {}

    chart_row = Table(
        [
            [
                SouthIndianChartFlowable(rasi_houses, title="Rasi Chart", size_mm=85),
                SouthIndianChartFlowable(nav_houses, title="Navamsa Chart", size_mm=85),
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

    # 6) Cusps
    story.append(PageBreak())
    story.append(_section_title("6) Cusps"))
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
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#121212")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 9),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#DDDDDD")),
                    ("FONTSIZE", (0, 1), (-1, -1), 10.5),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [CREAM2, CREAM]),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(t)
    else:
        story.append(Paragraph("Cusps data not provided.", body))

    # 7) Planets (degrees shown)
    story.append(PageBreak())
    story.append(_section_title("7) Planets"))
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
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#121212")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 9),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#DDDDDD")),
                    ("FONTSIZE", (0, 1), (-1, -1), 10.5),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [CREAM2, CREAM]),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(t)
    else:
        story.append(Paragraph("Planets data not provided.", body))

    # 8) Dasha
    story.append(PageBreak())
    story.append(_section_title("8) Dasha (Current)"))
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

    # 9) Mini Bhava
    story.append(PageBreak())
    story.append(_section_title("9) Mini Bhava Phalithalu"))
    bhava = data.get("bhavaPhal") or []
    if bhava:
        b_data = [["House", "Good", "Careful", "Notes"]]
        for b in bhava:
            b_data.append(
                [
                    _safe(b.get("house")),
                    _safe(b.get("good")),
                    _safe(b.get("bad")),
                    _safe(b.get("notes")),
                ]
            )
        t = Table(b_data, repeatRows=1, colWidths=[16 * mm, 55 * mm, 55 * mm, 64 * mm])
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#121212")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#DDDDDD")),
                    ("FONTSIZE", (0, 0), (-1, 0), 9),
                    ("FONTSIZE", (0, 1), (-1, -1), 10.5),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [CREAM2, CREAM]),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(t)
    else:
        story.append(Paragraph("Bhava phalithalu data not provided.", body))

    def _on_page(canvas, doc_):
        on_page(canvas, doc_, meta)

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)