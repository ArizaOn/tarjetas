"""
tarjetas/app.py — FlashScan montado como sub-app FastAPI
Accesible en rockola.online/tarjetas
"""

import uuid
import shutil
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from tarjetas.ocr import extract_text_from_images
from tarjetas.ai_cards import generate_flashcards
from tarjetas.pdf_generator import generate_pdf

# ─── Configuración ───────────────────────────────────────────────
BASE_DIR      = Path(__file__).resolve().parent
UPLOAD_FOLDER = BASE_DIR / "uploads"
OUTPUT_FOLDER = BASE_DIR / "outputs"
ALLOWED_EXT   = {"jpg", "jpeg", "png", "webp", "bmp", "tiff"}

UPLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER.mkdir(exist_ok=True)

# ─── App ─────────────────────────────────────────────────────────
flashscan_app = FastAPI()

# Servir archivos estáticos (html, css, js)
flashscan_app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static")),
    name="flashscan-static",
)


# ─── Rutas ───────────────────────────────────────────────────────
@flashscan_app.get("/")
async def index():
    """Sirve el frontend principal."""
    return FileResponse(str(BASE_DIR / "static" / "index.html"))


@flashscan_app.post("/generate")
async def generate(
    images: list[UploadFile] = File(...),
    cols: int = Form(3),
    rows: int = Form(5),
):
    cols = max(1, min(6, cols))
    rows = max(1, min(8, rows))

    # ── Guardar imágenes en carpeta de sesión ─────────────────────
    session_id  = uuid.uuid4().hex
    session_dir = UPLOAD_FOLDER / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    saved_paths = []
    try:
        for i, file in enumerate(images):
            ext = file.filename.rsplit(".", 1)[-1].lower()
            if ext not in ALLOWED_EXT:
                continue
            path = session_dir / f"page_{i+1:03d}.{ext}"
            content = await file.read()
            path.write_bytes(content)
            saved_paths.append(str(path))

        if not saved_paths:
            raise HTTPException(status_code=400, detail="Ninguna imagen tiene formato válido")

        # ── OCR ───────────────────────────────────────────────────
        print(f"[OCR] Procesando {len(saved_paths)} imagen(es)...")
        raw_text = extract_text_from_images(saved_paths)

        if not raw_text.strip():
            raise HTTPException(
                status_code=422,
                detail="No se pudo extraer texto. Asegúrate de que las fotos sean claras."
            )

        # ── IA → Flashcards ───────────────────────────────────────
        max_cards  = cols * rows * 4
        flashcards = generate_flashcards(raw_text, max_cards=max_cards)

        if not flashcards:
            raise HTTPException(
                status_code=422,
                detail="La IA no pudo generar tarjetas. Intenta con imágenes más nítidas."
            )

        # ── PDF ───────────────────────────────────────────────────
        pdf_path = OUTPUT_FOLDER / f"{session_id}.pdf"
        generate_pdf(
            flashcards=flashcards,
            output_path=str(pdf_path),
            cols=cols,
            rows=rows,
        )

        return FileResponse(
            path=str(pdf_path),
            media_type="application/pdf",
            filename="flashcards.pdf",
        )

    except HTTPException:
        raise
    except Exception as exc:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error interno: {str(exc)}")

    finally:
        shutil.rmtree(str(session_dir), ignore_errors=True)
