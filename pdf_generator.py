"""
pdf_generator.py — Diseño minimalista, blanco y negro.
Genera dos PDFs separados: preguntas y respuestas.
Las columnas de respuestas van espejadas para impresión doble cara.
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import black, white
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit

FONT_BOLD  = "Helvetica-Bold"
FONT_BODY  = "Helvetica"

PAGE_MARGIN = 0.3 * inch
CARD_PAD    = 8
HEADER_H    = 16
GUIDE_LEN   = 6
GUIDE_LW    = 0.4


def draw_cut_marks(c, x, y, w, h):
    c.setStrokeColor(black)
    c.setLineWidth(GUIDE_LW)
    L = GUIDE_LEN
    for cx, cy, dx1, dy1, dx2, dy2 in [
        (x,   y,    L,  0,  0,  L),
        (x+w, y,   -L,  0,  0,  L),
        (x,   y-h,  L,  0,  0, -L),
        (x+w, y-h, -L,  0,  0, -L),
    ]:
        c.line(cx, cy, cx+dx1, cy+dy1)
        c.line(cx, cy, cx+dx2, cy+dy2)


def draw_card(c, x, y, card_w, card_h, number, body_text, is_question):
    c.setFillColor(white)
    c.rect(x, y - card_h, card_w, card_h, fill=1, stroke=0)

    header_label = f"PREGUNTA {number:02d}" if is_question else f"RESPUESTA {number:02d}"
    c.setStrokeColor(black)
    c.setLineWidth(0.8)
    c.line(x, y - HEADER_H, x + card_w, y - HEADER_H)

    c.setFillColor(black)
    c.setFont(FONT_BOLD, 7)
    c.drawString(x + CARD_PAD, y - HEADER_H + 5, header_label)

    text_area_y = y - HEADER_H - CARD_PAD
    text_area_h = card_h - HEADER_H - CARD_PAD * 2
    text_area_w = card_w - CARD_PAD * 2

    font_size   = _fit_font_size(body_text, text_area_w, text_area_h)
    line_height = font_size * 1.4

    c.setFont(FONT_BODY, font_size)
    lines        = simpleSplit(body_text, FONT_BODY, font_size, text_area_w)
    total_text_h = len(lines) * line_height
    start_y      = text_area_y - (text_area_h - total_text_h) / 2

    for i, line in enumerate(lines):
        c.drawString(x + CARD_PAD, start_y - i * line_height - font_size, line)

    draw_cut_marks(c, x, y, card_w, card_h)


def _fit_font_size(text, max_w, max_h):
    for size in range(11, 6, -1):
        if len(simpleSplit(text, FONT_BODY, size, max_w)) * size * 1.4 <= max_h:
            return size
    return 7


def _draw_single_page(c, cards, field, is_question, cols, card_w, card_h,
                      page_margin, page_h, offset, mirror_cols, page_number):
    """Dibuja una página con número de hoja en la esquina superior derecha."""
    PAGE_W = letter[0]
    # Número de hoja para instrucciones
    c.setFont(FONT_BOLD, 7)
    c.setFillColor(black)
    label = f"Hoja {page_number} — {'PREGUNTAS' if is_question else 'RESPUESTAS'}"
    c.drawRightString(PAGE_W - page_margin, page_h - page_margin + 4, label)

    for idx, card in enumerate(cards):
        row = idx // cols
        col = (cols - 1 - idx % cols) if mirror_cols else (idx % cols)
        x   = page_margin + col * card_w
        y   = page_h - page_margin - row * card_h
        draw_card(c, x, y, card_w, card_h, offset + idx + 1,
                  card.get(field, ""), is_question)


def generate_pdf(flashcards, output_path, cols=3, rows=5):
    """Genera un PDF combinado (preguntas + respuestas intercaladas)."""
    PAGE_W, PAGE_H = letter
    cards_per_page = cols * rows
    c = canvas.Canvas(output_path, pagesize=letter)
    c.setTitle("FlashScan — Tarjetas de estudio")

    usable_w = PAGE_W - 2 * PAGE_MARGIN
    usable_h = PAGE_H - 2 * PAGE_MARGIN
    card_w   = usable_w / cols
    card_h   = usable_h / rows

    sheet = 1
    for page_start in range(0, len(flashcards), cards_per_page):
        group = flashcards[page_start: page_start + cards_per_page]
        _draw_single_page(c, group, "pregunta",  True,  cols, card_w, card_h,
                          PAGE_MARGIN, PAGE_H, page_start, False, sheet)
        c.showPage()
        _draw_single_page(c, group, "respuesta", False, cols, card_w, card_h,
                          PAGE_MARGIN, PAGE_H, page_start, True, sheet)
        c.showPage()
        sheet += 1

    c.save()
    print(f"[PDF] Combinado guardado en {output_path}")


def generate_pdf_questions(flashcards, output_path, cols=3, rows=5):
    """Genera PDF solo con páginas de preguntas."""
    PAGE_W, PAGE_H = letter
    cards_per_page = cols * rows
    c = canvas.Canvas(output_path, pagesize=letter)
    c.setTitle("FlashScan — Preguntas")

    usable_w = PAGE_W - 2 * PAGE_MARGIN
    usable_h = PAGE_H - 2 * PAGE_MARGIN
    card_w   = usable_w / cols
    card_h   = usable_h / rows

    sheet = 1
    for page_start in range(0, len(flashcards), cards_per_page):
        group = flashcards[page_start: page_start + cards_per_page]
        _draw_single_page(c, group, "pregunta", True, cols, card_w, card_h,
                          PAGE_MARGIN, PAGE_H, page_start, False, sheet)
        c.showPage()
        sheet += 1

    c.save()
    print(f"[PDF] Preguntas guardado en {output_path}")


def generate_pdf_answers(flashcards, output_path, cols=3, rows=5):
    """Genera PDF solo con páginas de respuestas (columnas espejadas)."""
    PAGE_W, PAGE_H = letter
    cards_per_page = cols * rows
    c = canvas.Canvas(output_path, pagesize=letter)
    c.setTitle("FlashScan — Respuestas")

    usable_w = PAGE_W - 2 * PAGE_MARGIN
    usable_h = PAGE_H - 2 * PAGE_MARGIN
    card_w   = usable_w / cols
    card_h   = usable_h / rows

    sheet = 1
    for page_start in range(0, len(flashcards), cards_per_page):
        group = flashcards[page_start: page_start + cards_per_page]
        _draw_single_page(c, group, "respuesta", False, cols, card_w, card_h,
                          PAGE_MARGIN, PAGE_H, page_start, True, sheet)
        c.showPage()
        sheet += 1

    c.save()
    print(f"[PDF] Respuestas guardado en {output_path}")
