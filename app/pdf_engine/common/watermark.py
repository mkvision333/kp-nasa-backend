# backend/pdf_engine/common/watermark.py
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.colors import Color


def draw_watermark(c: Canvas, text: str = "Pro KP Astrologer • FREE", alpha: float = 0.08) -> None:
    """
    Light diagonal watermark on every page.
    """
    c.saveState()
    # ReportLab supports transparency via setFillAlpha on newer versions
    try:
        c.setFillAlpha(alpha)
    except Exception:
        pass

    c.setFont("Helvetica-Bold", 48)
    c.setFillColor(Color(0, 0, 0, alpha=alpha))
    w, h = c._pagesize
    c.translate(w * 0.15, h * 0.35)
    c.rotate(30)
    c.drawString(0, 0, text)
    c.restoreState()