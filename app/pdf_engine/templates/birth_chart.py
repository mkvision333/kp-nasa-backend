# app/pdf_engine/templates/birth_chart.py  ✅ FULL REPLACE

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


# Theme
CREAM = colors.HexColor("#FFF6E6")
CREAM2 = colors.HexColor("#FFFBF2")
GOLD = colors.HexColor("#B8860B")


def _safe(v: Any, dash: str = "—") -> str:
    if v is None:
        return dash
    s = str(v).strip()
    return s if s else dash


def _fmt_deg_short(v: Any) -> str:
    """
    Degree formatting like 12°34' (best-effort from string/number).
    Accepts: "12 34", "12°34'", "12.56", 12.56 etc.
    """
    if v is None:
        return "—"
    s = str(v).strip()
    if not s:
        return "—"

    # If it looks like float degrees (e.g., 12.56), convert to deg + minutes
    mfloat = re.findall(r"-?\d+(?:\.\d+)?", s)
    if mfloat:
        try:
            val = float(mfloat[0])
            sign = "-" if val < 0 else ""
            val = abs(val)
            d = int(val)
            mins = int(round((val - d) * 60))
            if mins >= 60:
                d += 1
                mins -= 60
            return f"{sign}{d}°{str(mins).zfill(2)}'"
        except Exception:
            pass

    # Otherwise extract first 2 integers
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


def _has_any_value(d: Dict[str, Any]) -> bool:
    if not isinstance(d, dict):
        return False
    for _, v in d.items():
        if v is None:
            continue
        if str(v).strip():
            return True
    return False


class SouthIndianChartFlowable(Flowable):
    """
    ✅ South Indian chart (12 perimeter boxes only)
    ✅ Mesham is always TOP row 2nd box, clockwise order
    ✅ NO middle grid lines / NO center boxes
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

        # Title
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(colors.HexColor("#111111"))
        c.drawString(x, y + self.size + 4 * mm, self.title)

        step = self.size / 4.0

        # Outer border
        c.setStrokeColor(GOLD)
        c.setLineWidth(1.2)
        c.rect(x, y, self.size, self.size, stroke=1, fill=0)

        # ✅ Draw ONLY 12 perimeter cells
        perimeter_cells = set()
        for cx in range(4):
            perimeter_cells.add((cx, 3))  # top
            perimeter_cells.add((cx, 0))  # bottom
        perimeter_cells.update({(0, 1), (0, 2), (3, 1), (3, 2)})  # sides

        c.setStrokeColor(GOLD)
        c.setLineWidth(1.0)
        for (cx, cy) in perimeter_cells:
            ox = x + step * cx
            oy = y + step * cy
            c.rect(ox, oy, step, step, stroke=1, fill=0)

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

        c.setFillColor(colors.HexColor("#111111"))

        for house, (cx, cy) in house_pos.items():
            ox = x + step * cx
            oy = y + step * cy
            txt = str(self.houses.get(house, "")).strip()

            # house number
            c.setFont("Helvetica-Bold", 7.2)
            c.drawString(ox + 2 * mm, oy + step - 5 * mm, str(house))

            # planets (wrap into 2 lines max)
            if txt:
                parts = txt.split()
                line1 = " ".join(parts[:6])
                line2 = " ".join(parts[6:12]) if len(parts) > 6 else ""

                c.setFont("Helvetica", 8.0)
                c.drawString(ox + 2 * mm, oy + step - 10 * mm, line1)
                if line2:
                    c.drawString(ox + 2 * mm, oy + step - 15 * mm, line2)


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

    # 1) Birth Details
    story.append(PageBreak())
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

    # 2) Charts (always start fresh page, keep together)
    story.append(PageBreak())
    story.append(_section_title("2) Charts"))
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

    # 3) Gana Kutami / Ghata Kutami / Adrushta (if provided)
    # NOTE: backend may send these under different keys; we try common ones.
    def _pick(*keys: str) -> Dict[str, Any]:
        for k in keys:
            v = data.get(k)
            if isinstance(v, dict) and _has_any_value(v):
                return v
        return {}

    gana = _pick("ganaKutami", "gana_kutami", "gana")
    ghata = _pick("ghataKutami", "ghata_kutami", "ghata")
    adrushta = _pick("adrushta", "adrushtaKutami", "adrushta_kutami")

    if gana or ghata or adrushta:
        # keep these together; if too big, it will flow but starts here under charts
        blocks: List[Any] = []
        blocks.append(_section_title("3) Gana / Ghata / Adrushta"))

        if gana:
            blocks.append(Paragraph("<b>Gana Kutami</b>", body))
            blocks.append(_kv_table([(k, v) for k, v in gana.items()]))
            blocks.append(Spacer(1, 4 * mm))

        if ghata:
            blocks.append(Paragraph("<b>Ghata Kutami</b>", body))
            blocks.append(_kv_table([(k, v) for k, v in ghata.items()]))
            blocks.append(Spacer(1, 4 * mm))

        if adrushta:
            blocks.append(Paragraph("<b>Adrushta</b>", body))
            blocks.append(_kv_table([(k, v) for k, v in adrushta.items()]))

        story.append(KeepTogether(blocks))
    else:
        # If nothing provided, show note (optional)
        story.append(Paragraph("Gana/Ghata/Adrushta details not provided.", body))

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

    # 5) Planets (degrees shown)
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

    # 6) Dasha
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

    # 7) Mini Bhava
    story.append(PageBreak())
    story.append(_section_title("7) Mini Bhava Phalithalu"))
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