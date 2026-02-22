from reportlab.platypus import Paragraph, Spacer, Image
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak
from reportlab.lib.styles import getSampleStyleSheet


def build_cover_page(story, user_name: str):
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CoverTitle",
        parent=styles["Heading1"],
        fontSize=22,
        leading=28,
        alignment=1,
        textColor=colors.HexColor("#B8860B"),
    )

    sub_style = ParagraphStyle(
        "CoverSub",
        parent=styles["Normal"],
        fontSize=14,
        alignment=1,
        textColor=colors.HexColor("#3E2723"),
    )

    story.append(Spacer(1, 30 * mm))

    story.append(Paragraph("🕉", title_style))
    story.append(Spacer(1, 10 * mm))

    story.append(Paragraph("PRO KP ASTROLOGY", title_style))
    story.append(Spacer(1, 5 * mm))
    story.append(Paragraph("Traditional Birth Chart Report", sub_style))
    story.append(Spacer(1, 5 * mm))
    story.append(Paragraph("(FREE VERSION)", sub_style))

    story.append(Spacer(1, 40 * mm))

    if user_name:
        story.append(Paragraph(f"Prepared For: <b>{user_name}</b>", sub_style))

    story.append(PageBreak())