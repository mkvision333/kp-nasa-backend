from reportlab.lib import colors
from reportlab.lib.units import mm

CREAM_BG = colors.HexColor("#F6EFD6")

# Dark sandal / wood tone bars
SANDAL = colors.HexColor("#5A3A21")     # dark sandal
SANDAL2 = colors.HexColor("#6B4527")    # subtle accent (optional)

GOLD = colors.HexColor("#D4AF37")
WHITE = colors.white


def on_page(canvas, doc, meta):
    canvas.saveState()
    width, height = doc.pagesize

    # ✅ Cream full-page background
    canvas.setFillColor(CREAM_BG)
    canvas.rect(0, 0, width, height, stroke=0, fill=1)

    # ✅ Decorative gold frame border
    inset = 8 * mm
    canvas.setStrokeColor(GOLD)
    canvas.setLineWidth(1.6)
    canvas.rect(inset, inset, width - 2 * inset, height - 2 * inset, stroke=1, fill=0)

    # ✅ Thick top bar (dark sandal)
    top_h = 14 * mm
    canvas.setFillColor(SANDAL)
    canvas.rect(0, height - top_h, width, top_h, stroke=0, fill=1)

    # ✅ Thin accent line under top bar
    canvas.setStrokeColor(GOLD)
    canvas.setLineWidth(1.0)
    canvas.line(0, height - top_h, width, height - top_h)

    # ✅ Thick bottom bar (dark sandal)
    bot_h = 12 * mm
    canvas.setFillColor(SANDAL)
    canvas.rect(0, 0, width, bot_h, stroke=0, fill=1)

    # ✅ Thin accent line above bottom bar
    canvas.setStrokeColor(GOLD)
    canvas.setLineWidth(1.0)
    canvas.line(0, bot_h, width, bot_h)

    # ✅ Header text INSIDE top bar
    canvas.setFont("Helvetica-Bold", 11.5)
    canvas.setFillColor(WHITE)
    canvas.drawCentredString(width / 2, height - 10.5 * mm, "🕉 PRO KP ASTROLOGY 🕉")

    # ✅ Footer text INSIDE bottom bar
    canvas.setFont("Helvetica", 9.5)
    canvas.setFillColor(WHITE)
    canvas.drawCentredString(width / 2, 4.2 * mm, f"Page {doc.page}")

    canvas.restoreState()