from reportlab.lib.units import mm
from reportlab.lib import colors


def on_page(canvas, doc, meta):
    canvas.saveState()

    width, height = doc.pagesize

    # Cream Background
    canvas.setFillColor(colors.HexColor("#F6EFD6"))
    canvas.rect(0, 0, width, height, stroke=0, fill=1)

    # Header
    canvas.setFont("Helvetica-Bold", 11)
    canvas.setFillColor(colors.HexColor("#7B1E1E"))
    canvas.drawCentredString(width / 2, height - 14, "🕉 PRO KP ASTROLOGY 🕉")

    # Footer
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(colors.HexColor("#3E2723"))
    canvas.drawCentredString(width / 2, 12, f"Page {doc.page}")

    canvas.restoreState()