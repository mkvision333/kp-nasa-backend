# backend/pdf_engine/common/header_footer.py
from typing import Dict, Any
from datetime import datetime

from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor

from .watermark import draw_watermark


def on_page(c: Canvas, doc, meta: Dict[str, Any]) -> None:
    """
    Header + Footer for each page.
    """
    w, h = c._pagesize

    # Watermark
    draw_watermark(c, text="Pro KP Astrologer • FREE", alpha=0.06)

    # Header bar
    c.saveState()
    c.setFillColor(HexColor("#121212"))
    c.rect(0, h - 18 * mm, w, 18 * mm, stroke=0, fill=1)

    c.setFillColor(HexColor("#F5C542"))  # gold-ish
    c.setFont("Helvetica-Bold", 12)
    c.drawString(12 * mm, h - 12.5 * mm, "Simple Birth Chart Report (FREE)")

    c.setFillColor(HexColor("#FFFFFF"))
    c.setFont("Helvetica", 9)
    c.drawRightString(w - 12 * mm, h - 12.2 * mm, f"Report ID: {meta.get('reportId','')}")
    c.restoreState()

    # Footer
    c.saveState()
    c.setFont("Helvetica", 8)
    c.setFillColor(HexColor("#666666"))

    gen = meta.get("generatedAt") or ""
    try:
        # show as local-like readable
        gen_dt = datetime.fromisoformat(gen.replace("Z", "+00:00"))
        gen_str = gen_dt.strftime("%d %b %Y, %I:%M %p")
    except Exception:
        gen_str = gen

    left = f"Generated: {gen_str}"
    mid = f"User: {meta.get('userName','')}".strip()
    right = f"Page {doc.page}"

    c.drawString(12 * mm, 10 * mm, left)
    if mid:
        c.drawCentredString(w / 2, 10 * mm, mid)
    c.drawRightString(w - 12 * mm, 10 * mm, right)
    c.restoreState()