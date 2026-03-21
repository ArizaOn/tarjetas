"""
pdf_generator.py — Genera el PDF de flashcards con ReportLab
Formato: tamaño carta, cuadrícula configurable (cols x rows).

Páginas IMPARES  → Preguntas
Páginas PARES    → Respuestas (columnas espejadas para impresión doble cara)

Para imprimir: doble cara, voltear por el lado corto.
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, black, white
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit

# ─── Paleta ──────────────────────────────────────────────────────
COLOR_BG_Q     = HexColor("#0d0d0f")   # fondo pregunta (oscuro)
COLOR_BG_A     = HexColor("#1a1a2e")   # fondo respuesta (azul muy oscuro)
COLOR_ACCENT   = HexColor("#e8ff47")   # amarillo neón — número/etiqueta
COLOR_ACCENT2  = HexColor("#47c8ff")   # azul claro — número respuesta
COLOR_TEXT_Q   = HexColor("#f0efeb")   # texto pregunta
COLOR_TEXT_A   = HexColor("#d0eeff")   # texto respuesta
COLOR_BORDER   = HexColor("#2a2a35")   # borde de tarjeta
COLOR_LABEL_BG = HexColor("#1e1e24")   # fondo de la etiqueta Q / R

# ─── Tipografía ───────────────────────────────────────────────────
FONT_MAIN  = "Helvetica-Bold"
FONT_BODY  = "Helvetica"
FONT_MONO  = "Courier"

# ─── Márgenes de página ───────────────────────────────────────────
PAGE_MARGIN = 0.35 * inch
CARD_PAD    = 8     # padding interno de cada tarjeta (pt)
LABEL_H     = 14    # altura de la etiqueta "P" / "R" (pt)
GUIDE_LW    = 0.25  # grosor de líneas guía de corte
GUIDE_LEN   = 6     # longitud de marca de corte en las esquinas (pt)


def draw_cut_marks(c: canvas.Canvas, x: float, y: float, w: float, h: float):
    """Dibuja marcas de corte en las 4 esquinas de una tarjeta."""
    c.setStrokeColor(HexColor("#555566"))
    c.setLineWidth(GUIDE_LW)
    L = GUIDE_LEN
    corners = [
        (x,     y,     L,  0,  0,  L),   # top-left
        (x+w,   y,    -L,  0,  0,  L),   # top-right
        (x,     y-h,   L,  0,  0, -L),   # bottom-left
        (x+w,   y-h,  -L,  0,  0, -L),   # bottom-right
    ]
    for cx, cy, dx1, dy1, dx2, dy2 in corners:
        c.line(cx, cy, cx + dx1, cy + dy1)
        c.line(cx, cy, cx + dx2, cy + dy2)


def draw_card(
    c: canvas.Canvas,
    x: float, y: float,
    card_w: float, card_h: float,
    label: str,
    number: int,
    body_text: str,
    is_question: bool,
):
    """
    Dibuja una tarjeta individual.
    x, y = esquina superior izquierda (coordenadas ReportLab: y crece hacia arriba).
    """
    bg_color     = COLOR_BG_Q if is_question else COLOR_BG_A
    text_color   = COLOR_TEXT_Q if is_question else COLOR_TEXT_A
    accent_color = COLOR_ACCENT if is_question else COLOR_ACCENT2

    # ── Fondo ──────────────────────────────────────────────────────
    c.setFillColor(bg_color)
    c.setStrokeColor(COLOR_BORDER)
    c.setLineWidth(0.5)
    c.rect(x, y - card_h, card_w, card_h, fill=1, stroke=1)

    # ── Etiqueta superior (P / R + número) ─────────────────────────
    label_y = y - LABEL_H
    c.setFillColor(COLOR_LABEL_BG)
    c.rect(x, label_y, card_w, LABEL_H, fill=1, stroke=0)

    c.setFillColor(accent_color)
    c.setFont(FONT_MONO, 7)
    tag_text = f"{label} {number:02d}"
    c.drawString(x + CARD_PAD, label_y + 4, tag_text)

    # Línea separadora entre etiqueta y cuerpo
    c.setStrokeColor(COLOR_BORDER)
    c.setLineWidth(0.5)
    c.line(x, label_y, x + card_w, label_y)

    # ── Texto del cuerpo ───────────────────────────────────────────
    text_area_y  = label_y - CARD_PAD
    text_area_h  = card_h - LABEL_H - CARD_PAD * 2
    text_area_w  = card_w - CARD_PAD * 2

    font_size    = _fit_font_size(body_text, text_area_w, text_area_h)
    line_height  = font_size * 1.35

    c.setFillColor(text_color)
    c.setFont(FONT_BODY, font_size)

    # Dividir texto en líneas que quepan en el ancho
    lines = simpleSplit(body_text, FONT_BODY, font_size, text_area_w)
    total_text_h = len(lines) * line_height
    # Centrar verticalmente
    start_y = text_area_y - (text_area_h - total_text_h) / 2

    for i, line in enumerate(lines):
        ly = start_y - i * line_height
        c.drawString(x + CARD_PAD, ly - font_size, line)

    # ── Marcas de corte ────────────────────────────────────────────
    draw_cut_marks(c, x, y, card_w, card_h)


def _fit_font_size(text: str, max_w: float, max_h: float) -> float:
    """
    Calcula el tamaño de fuente máximo para que el texto quepa.
    Límites: 7pt mínimo, 11pt máximo (tarjetas pequeñas, texto corto).
    """
    for size in range(11, 6, -1):
        lines = simpleSplit(text, FONT_BODY, size, max_w)
        needed_h = len(lines) * size * 1.35
        if needed_h <= max_h:
            return size
    return 7


def generate_pdf(
    flashcards: list[dict],
    output_path: str,
    cols: int = 3,
    rows: int = 5,
) -> None:
    """
    Genera el PDF de flashcards.

    Args:
        flashcards:  Lista de dicts {'pregunta': str, 'respuesta': str}.
        output_path: Ruta de salida del PDF.
        cols:        Columnas de tarjetas por hoja.
        rows:        Filas de tarjetas por hoja.
    """
    PAGE_W, PAGE_H = letter  # 612 x 792 pt

    cards_per_page = cols * rows

    c = canvas.Canvas(output_path, pagesize=letter)
    c.setTitle("FlashScan — Tarjetas de estudio")
    c.setAuthor("FlashScan")

    # ── Dimensiones de tarjeta ─────────────────────────────────────
    usable_w = PAGE_W - 2 * PAGE_MARGIN
    usable_h = PAGE_H - 2 * PAGE_MARGIN
    card_w   = usable_w / cols
    card_h   = usable_h / rows

    # ── Calcular grupos de tarjetas por hoja ───────────────────────
    for page_start in range(0, len(flashcards), cards_per_page):
        group = flashcards[page_start : page_start + cards_per_page]

        # ── Página IMPAR (preguntas) ────────────────────────────────
        _draw_page(
            c=c,
            cards=group,
            field="pregunta",
            label="P",
            is_question=True,
            cols=cols,
            rows=rows,
            card_w=card_w,
            card_h=card_h,
            page_margin=PAGE_MARGIN,
            page_h=PAGE_H,
            offset=page_start,
            mirror_cols=False,
        )
        c.showPage()

        # ── Página PAR (respuestas, columnas espejadas) ─────────────
        _draw_page(
            c=c,
            cards=group,
            field="respuesta",
            label="R",
            is_question=False,
            cols=cols,
            rows=rows,
            card_w=card_w,
            card_h=card_h,
            page_margin=PAGE_MARGIN,
            page_h=PAGE_H,
            offset=page_start,
            mirror_cols=True,   # ← espejo horizontal para doble cara
        )
        c.showPage()

    c.save()
    print(f"[PDF] Guardado en {output_path}")


def _draw_page(
    c: canvas.Canvas,
    cards: list[dict],
    field: str,
    label: str,
    is_question: bool,
    cols: int,
    rows: int,
    card_w: float,
    card_h: float,
    page_margin: float,
    page_h: float,
    offset: int,
    mirror_cols: bool,
):
    """Dibuja una página completa (preguntas o respuestas)."""
    for idx, card in enumerate(cards):
        row = idx // cols
        col = idx % cols

        # Espejo horizontal: la col 0 pasa a ser la última, etc.
        if mirror_cols:
            col = (cols - 1) - col

        x = page_margin + col * card_w
        y = page_h - page_margin - row * card_h  # y es la esquina superior

        draw_card(
            c=c,
            x=x, y=y,
            card_w=card_w, card_h=card_h,
            label=label,
            number=offset + idx + 1,
            body_text=card.get(field, ""),
            is_question=is_question,
        )