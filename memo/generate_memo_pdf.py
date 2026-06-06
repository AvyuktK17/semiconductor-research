"""Convert semiconductor_sector_memo.md to a professional PDF."""

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from pathlib import Path

MEMO_DIR = Path(__file__).parent
INPUT = MEMO_DIR / "semiconductor_sector_memo.md"
OUTPUT = MEMO_DIR / "semiconductor_sector_memo.pdf"

DARK = HexColor("#1a1a1a")
MID = HexColor("#444444")
ACCENT = HexColor("#2c5282")
LIGHT_GRAY = HexColor("#f7f7f7")
BORDER = HexColor("#cccccc")
WHITE = HexColor("#ffffff")

FONT = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
FONT_ITALIC = "Helvetica-Oblique"
FONT_BI = "Helvetica-BoldOblique"


def build_styles():
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        "MemoTitle", fontName=FONT_BOLD, fontSize=18, leading=24,
        textColor=DARK, spaceAfter=4, alignment=TA_LEFT,
    ))
    styles.add(ParagraphStyle(
        "MemoSubtitle", fontName=FONT, fontSize=9, leading=13,
        textColor=MID, spaceAfter=14, alignment=TA_LEFT,
    ))
    styles.add(ParagraphStyle(
        "H2", fontName=FONT_BOLD, fontSize=13, leading=18,
        textColor=ACCENT, spaceBefore=18, spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        "Body", fontName=FONT, fontSize=9.5, leading=14,
        textColor=DARK, spaceAfter=8, alignment=TA_JUSTIFY,
    ))
    styles.add(ParagraphStyle(
        "MemoBullet", fontName=FONT, fontSize=9.5, leading=14,
        textColor=DARK, spaceAfter=5, leftIndent=18, bulletIndent=6,
        alignment=TA_LEFT,
    ))
    styles.add(ParagraphStyle(
        "Disclaimer", fontName=FONT_ITALIC, fontSize=8, leading=11,
        textColor=MID, spaceBefore=12, spaceAfter=0, alignment=TA_LEFT,
    ))
    return styles


def md_inline(text):
    """Convert **bold** and limited markdown inline formatting to reportlab XML."""
    import re
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = text.replace("--", "—")
    return text


def parse_memo(path):
    lines = path.read_text().splitlines()
    elements = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        if stripped.startswith("# ") and not stripped.startswith("## "):
            elements.append(("title", stripped[2:].strip()))
            i += 1
            continue

        if stripped.startswith("## "):
            elements.append(("h2", stripped[3:].strip()))
            i += 1
            continue

        if stripped == "---":
            elements.append(("hr",))
            i += 1
            continue

        if stripped.startswith("| ") and "---" not in stripped:
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                if "---" not in lines[i]:
                    table_lines.append(lines[i].strip())
                i += 1
            elements.append(("table", table_lines))
            continue

        if stripped.startswith("- "):
            bullets = []
            while i < len(lines) and lines[i].strip().startswith("- "):
                bullets.append(lines[i].strip()[2:])
                i += 1
            elements.append(("bullets", bullets))
            continue

        if stripped.startswith("*") and stripped.endswith("*") and not stripped.startswith("**"):
            elements.append(("disclaimer", stripped.strip("*").strip()))
            i += 1
            continue

        para_lines = [stripped]
        i += 1
        while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith(("#", "##", "---", "| ", "- ", "*")):
            para_lines.append(lines[i].strip())
            i += 1
        elements.append(("para", " ".join(para_lines)))

    return elements


def build_table(table_lines, styles):
    rows = []
    for line in table_lines:
        cells = [c.strip() for c in line.strip("|").split("|")]
        rows.append(cells)

    header = rows[0]
    data_rows = rows[1:]

    num_cols = len(header)
    col_width = (7.0 * inch) / num_cols

    styled_rows = []
    for ri, row in enumerate([header] + data_rows):
        styled_cells = []
        for cell in row:
            if ri == 0:
                style = ParagraphStyle(
                    "TH", fontName=FONT_BOLD, fontSize=8.5, leading=11,
                    textColor=WHITE, alignment=TA_CENTER,
                )
            else:
                style = ParagraphStyle(
                    "TD", fontName=FONT, fontSize=8.5, leading=11,
                    textColor=DARK, alignment=TA_CENTER,
                )
            styled_cells.append(Paragraph(md_inline(cell), style))
        styled_rows.append(styled_cells)

    t = Table(styled_rows, colWidths=[col_width] * num_cols)

    t_style = [
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]
    for ri in range(1, len(styled_rows)):
        if ri % 2 == 0:
            t_style.append(("BACKGROUND", (0, ri), (-1, ri), LIGHT_GRAY))

    t.setStyle(TableStyle(t_style))
    return t


def build_pdf():
    styles = build_styles()
    elements = parse_memo(INPUT)

    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=letter,
        leftMargin=0.85 * inch,
        rightMargin=0.85 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        title="Semiconductor Peer Comparison",
        author="Avyukt Kochhar",
    )

    story = []
    subtitle_line = None

    for elem in elements:
        kind = elem[0]

        if kind == "title":
            story.append(Paragraph(md_inline(elem[1]), styles["MemoTitle"]))

        elif kind == "h2":
            story.append(Spacer(1, 4))
            story.append(Paragraph(md_inline(elem[1]), styles["H2"]))

        elif kind == "hr":
            if subtitle_line:
                story.append(Paragraph(md_inline(subtitle_line), styles["MemoSubtitle"]))
                subtitle_line = None
            story.append(HRFlowable(
                width="100%", thickness=0.75, color=BORDER,
                spaceBefore=4, spaceAfter=10,
            ))

        elif kind == "para":
            text = elem[1]
            if text.startswith("**Date:**"):
                subtitle_line = text
                continue
            story.append(Paragraph(md_inline(text), styles["Body"]))

        elif kind == "bullets":
            bullet_group = []
            for b in elem[1]:
                bullet_group.append(
                    Paragraph(
                        f"•  {md_inline(b)}", styles["MemoBullet"]
                    )
                )
            story.append(KeepTogether(bullet_group))

        elif kind == "table":
            story.append(Spacer(1, 4))
            story.append(build_table(elem[1], styles))
            story.append(Spacer(1, 8))

        elif kind == "disclaimer":
            story.append(Paragraph(md_inline(elem[1]), styles["Disclaimer"]))

    def add_footer(canvas_obj, doc_obj):
        canvas_obj.saveState()
        canvas_obj.setFont(FONT, 7)
        canvas_obj.setFillColor(MID)
        canvas_obj.drawCentredString(
            letter[0] / 2, 0.45 * inch,
            f"Semiconductor Peer Comparison  —  Page {doc_obj.page}"
        )
        canvas_obj.restoreState()

    doc.build(story, onFirstPage=add_footer, onLaterPages=add_footer)
    print(f"PDF written to {OUTPUT}")


if __name__ == "__main__":
    build_pdf()
