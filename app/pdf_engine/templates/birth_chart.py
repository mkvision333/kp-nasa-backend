from __future__ import annotations

from typing import Dict, Any, List, Tuple

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Flowable,
)
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from ..common.header_footer import on_page
from app.pdf_engine.common.cover_page import build_cover_page


def _safe(v: Any, dash: str = "—") -> str:
    if v is None:
        return dash
    s = str(v).strip()
    return s if s else dash


def _kv_table(rows: List[Tuple[str, Any]]) -> Table:
    data = [[k, _safe(v)] for k, v in rows]
    t = Table(data, colWidths=[45 * mm, 140 * mm])
    t.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#333333")),
                ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor("#111111")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.whitesmoke, colors.white]),
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
        parent=styles["Heading3"],
        fontName="Helvetica-Bold",
        fontSize=11,
        textColor=colors.HexColor("#121212"),
        spaceBefore=6,
        spaceAfter=6,
    )
    return Paragraph(text, st)


def _coerce_house_map(houses: Dict[Any, Any]) -> Dict[int, str]:
    """
    JSON keys arrive as strings ("1".."12"). Convert to int.
    """
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
    Simple South Indian chart box (12 houses).
    houses: {1: "Su Mo", 2: "Ma", ...} OR {"1":"Su Mo", ...}
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

        # Outer square
        c.setStrokeColor(colors.HexColor("#222222"))
        c.setLineWidth(1)
        c.rect(x, y, self.size, self.size, stroke=1, fill=0)

        # 4x4 grid
        step = self.size / 4.0
        c.setLineWidth(0.6)
        c.setStrokeColor(colors.HexColor("#444444"))
        for i in range(1, 4):
            c.line(x + step * i, y, x + step * i, y + self.size)
            c.line(x, y + step * i, x + self.size, y + step * i)

        # Approx South Indian placement
        house_pos = {
            1: (1, 0),
            2: (2, 0),
            3: (3, 0),
            4: (3, 1),
            5: (3, 2),
            6: (3, 3),
            7: (2, 3),
            8: (1, 3),
            9: (0, 3),
            10: (0, 2),
            11: (0, 1),
            12: (0, 0),
        }

        c.setFont("Helvetica", 7.5)
        c.setFillColor(colors.HexColor("#111111"))

        for house, (cx, cy) in house_pos.items():
            txt = str(self.houses.get(house, "")).strip()
            if not txt:
                continue
            ox = x + step * cx
            oy = y + step * cy
            # House label + planets
            c.drawString(ox + 2 * mm, oy + step - 6 * mm, f"{house}: {txt}")


def build_birth_chart_pdf(file_path: str, data: Dict[str, Any], meta: Dict[str, Any]) -> None:
    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=12,
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

    # 2) Charts
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
    chart_row.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(chart_row)
    story.append(Spacer(1, 6 * mm))

    # 3) Cusps
    story.append(_section_title("3) Cusps"))
    cusps = data.get("cusps") or []
    if cusps:
        cusp_data = [["House", "Sign", "Degree", "Star Lord", "Sub Lord"]]
        for c in cusps:
            cusp_data.append(
                [
                    _safe(c.get("house")),
                    _safe(c.get("sign")),
                    _safe(c.get("deg")),
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
                    ("FONTSIZE", (0, 1), (-1, -1), 8.8),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
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
    story.append(Spacer(1, 6 * mm))

    # 4) Planets
    story.append(_section_title("4) Planets"))
    planets = data.get("planets") or []
    if planets:
        p_data = [["Planet", "Sign", "Degree", "Nakshatra", "Pada", "Star Lord", "Sub Lord"]]
        for p in planets:
            p_data.append(
                [
                    _safe(p.get("name")),
                    _safe(p.get("sign")),
                    _safe(p.get("deg")),
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
                    ("FONTSIZE", (0, 1), (-1, -1), 8.8),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
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
    story.append(Spacer(1, 6 * mm))

    # 5) Dasha (Current)
    story.append(_section_title("5) Dasha (Current)"))
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
    story.append(Spacer(1, 6 * mm))

    # 6) Mini Bhava Phalithalu
    story.append(_section_title("6) Mini Bhava Phalithalu"))
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
                    ("FONTSIZE", (0, 1), (-1, -1), 8.8),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
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