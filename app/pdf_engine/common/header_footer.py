from reportlab.lib.units import mm
from reportlab.lib import colors


def on_page(canvas, doc, meta):
    canvas.saveState()

    canvas.setFont("Helvetica-Bold", 9)
    canvas.setFillColor(colors.HexColor("#3E2723"))

    canvas.drawCentredString(
        doc.pagesize[0] / 2,
        doc.pagesize[1] - 12,
        "Pro KP Astrology"
    )

    canvas.drawCentredString(
        doc.pagesize[0] / 2,
        12,
        f"Page {doc.page}"
    )

    canvas.restoreState()