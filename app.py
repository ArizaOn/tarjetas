"""
app.py — Servidor Flask principal de FlashScan
Recibe imágenes, coordina OCR → IA → PDF y devuelve el archivo.

Uso:
    python app.py
    Luego abre http://localhost:5000 en el navegador.
"""

import os
import uuid
import shutil
from pathlib import Path

from flask import Flask, request, send_file, jsonify, render_template_string
from werkzeug.utils import secure_filename

from ocr import extract_text_from_images
from ai_cards import generate_flashcards
from pdf_generator import generate_pdf

# ─── Configuración ───────────────────────────────────────────────
UPLOAD_FOLDER  = Path("uploads")
OUTPUT_FOLDER  = Path("outputs")
ALLOWED_EXT    = {"jpg", "jpeg", "png", "webp", "bmp", "tiff"}
MAX_CONTENT_MB = 50  # tamaño máximo de la petición en MB

UPLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER.mkdir(exist_ok=True)

app = Flask(__name__, static_folder=".", static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_MB * 1024 * 1024


# ─── Helpers ─────────────────────────────────────────────────────
def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


# ─── Rutas ───────────────────────────────────────────────────────
@app.route("/")
def index():
    """Sirve el frontend estático."""
    return app.send_static_file("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    """
    Endpoint principal.
    Recibe:
        - images: lista de archivos de imagen
        - cols: número de columnas (int, default 3)
        - rows: número de filas (int, default 5)
    Devuelve:
        - PDF como descarga directa
    """
    # ── Validar imágenes ──────────────────────────────────────────
    if "images" not in request.files:
        return jsonify({"error": "No se recibieron imágenes"}), 400

    files = request.files.getlist("images")
    if not files or all(f.filename == "" for f in files):
        return jsonify({"error": "La lista de imágenes está vacía"}), 400

    # ── Parámetros de cuadrícula ──────────────────────────────────
    try:
        cols = max(1, min(6, int(request.form.get("cols", 3))))
        rows = max(1, min(8, int(request.form.get("rows", 5))))
    except (ValueError, TypeError):
        return jsonify({"error": "Parámetros de cuadrícula inválidos"}), 400

    # ── Crear carpeta de sesión única ─────────────────────────────
    session_id  = uuid.uuid4().hex
    session_dir = UPLOAD_FOLDER / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    saved_paths = []
    try:
        # ── Guardar imágenes ──────────────────────────────────────
        for i, file in enumerate(files):
            if file and allowed_file(file.filename):
                ext      = file.filename.rsplit(".", 1)[1].lower()
                filename = f"page_{i+1:03d}.{ext}"
                path     = session_dir / filename
                file.save(str(path))
                saved_paths.append(str(path))

        if not saved_paths:
            return jsonify({"error": "Ninguna imagen tiene un formato válido"}), 400

        # ── 1. OCR ────────────────────────────────────────────────
        print(f"[OCR] Procesando {len(saved_paths)} imagen(es)...")
        raw_text = extract_text_from_images(saved_paths)

        if not raw_text.strip():
            return jsonify({"error": "No se pudo extraer texto de las imágenes. "
                                      "Asegúrate de que las fotos sean claras."}), 422

        # ── 2. IA → Flashcards ────────────────────────────────────
        max_cards = cols * rows * 4  # máximo 4 páginas de tarjetas
        print(f"[IA] Generando hasta {max_cards} flashcards...")
        flashcards = generate_flashcards(raw_text, max_cards=max_cards)

        if not flashcards:
            return jsonify({"error": "La IA no pudo generar tarjetas. "
                                      "Intenta con imágenes más nítidas."}), 422

        print(f"[IA] {len(flashcards)} tarjetas generadas.")

        # ── 3. PDF ────────────────────────────────────────────────
        pdf_path = OUTPUT_FOLDER / f"{session_id}.pdf"
        print(f"[PDF] Generando {pdf_path}...")
        generate_pdf(
            flashcards=flashcards,
            output_path=str(pdf_path),
            cols=cols,
            rows=rows,
        )

        # ── Devolver PDF ──────────────────────────────────────────
        return send_file(
            str(pdf_path),
            mimetype="application/pdf",
            as_attachment=True,
            download_name="flashcards.pdf",
        )

    except Exception as exc:
        print(f"[ERROR] {exc}")
        import traceback; traceback.print_exc()
        return jsonify({"error": f"Error interno: {str(exc)}"}), 500

    finally:
        # Limpiar imágenes de la sesión (el PDF se guarda en outputs/)
        shutil.rmtree(str(session_dir), ignore_errors=True)


@app.errorhandler(413)
def too_large(_):
    return jsonify({"error": f"Las imágenes superan el límite de {MAX_CONTENT_MB} MB"}), 413


# ─── Main ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print("  FlashScan — Servidor iniciado")
    print("  Abre http://localhost:5000")
    print("=" * 50)
    app.run(host="0.0.0.0", port=5000, debug=True)