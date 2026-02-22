# ✅ app/pdf_engine/common/header_footer.py ✅ FULL REPLACE
from reportlab.lib import colors
from reportlab.lib.units import mm

CREAM_BG = colors.HexColor("#F6EFD6")
MAROON = colors.HexColor("#7B1E1E")
GOLD = colors.HexColor("#B8860B")

def on_page(canvas, doc, meta):
    canvas.saveState()
    width, height = doc.pagesize

    # ✅ Cream Background (full page)
    canvas.setFillColor(CREAM_BG)
    canvas.rect(0, 0, width, height, stroke=0, fill=1)

    # ✅ Decorative gold frame border
    inset = 8 * mm
    canvas.setStrokeColor(GOLD)
    canvas.setLineWidth(1.6)
    canvas.rect(inset, inset, width - 2 * inset, height - 2 * inset, stroke=1, fill=0)

    # Header
    canvas.setFont("Helvetica-Bold", 11)
    canvas.setFillColor(MAROON)
    canvas.drawCentredString(width / 2, height - 14 * mm, "🕉 PRO KP ASTROLOGY 🕉")

    # Footer
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(colors.HexColor("#111111"))
    canvas.drawCentredString(width / 2, 10 * mm, f"Page {doc.page}")

    canvas.restoreState()