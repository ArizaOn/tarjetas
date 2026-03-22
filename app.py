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
from tarjetas.pdf_generator import (
    generate_pdf,
    generate_pdf_questions,
    generate_pdf_answers,
)

BASE_DIR      = Path(__file__).resolve().parent
UPLOAD_FOLDER = BASE_DIR / "uploads"
OUTPUT_FOLDER = BASE_DIR / "outputs"
ALLOWED_EXT   = {"jpg", "jpeg", "png", "webp", "bmp", "tiff"}

UPLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER.mkdir(exist_ok=True)

flashscan_app = FastAPI()

flashscan_app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static")),
    name="flashscan-static",
)


@flashscan_app.get("/")
async def index():
    return FileResponse(str(BASE_DIR / "static" / "index.html"))


async def _save_images(images, session_dir):
    saved = []
    for i, file in enumerate(images):
        ext = file.filename.rsplit(".", 1)[-1].lower()
        if ext not in ALLOWED_EXT:
            continue
        path = session_dir / f"page_{i+1:03d}.{ext}"
        path.write_bytes(await file.read())
        saved.append(str(path))
    return saved


@flashscan_app.post("/generate")
async def generate(
    images: list[UploadFile] = File(...),
    cols: int = Form(3),
    rows: int = Form(5),
):
    """Genera PDF combinado (descarga normal)."""
    cols = max(1, min(6, cols))
    rows = max(1, min(8, rows))

    session_id  = uuid.uuid4().hex
    session_dir = UPLOAD_FOLDER / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    try:
        saved_paths = await _save_images(images, session_dir)
        if not saved_paths:
            raise HTTPException(400, "Ninguna imagen tiene formato válido")

        raw_text = extract_text_from_images(saved_paths)
        if not raw_text.strip():
            raise HTTPException(422, "No se pudo extraer texto. Asegúrate de que las fotos sean claras.")

        flashcards = generate_flashcards(raw_text, max_cards=cols * rows * 4)
        if not flashcards:
            raise HTTPException(422, "La IA no pudo generar tarjetas.")

        pdf_path = OUTPUT_FOLDER / f"{session_id}.pdf"
        generate_pdf(flashcards, str(pdf_path), cols, rows)

        return FileResponse(str(pdf_path), media_type="application/pdf", filename="flashcards.pdf")

    except HTTPException:
        raise
    except Exception as exc:
        import traceback; traceback.print_exc()
        raise HTTPException(500, f"Error interno: {str(exc)}")
    finally:
        shutil.rmtree(str(session_dir), ignore_errors=True)


@flashscan_app.post("/generate_split")
async def generate_split(
    images: list[UploadFile] = File(...),
    cols: int = Form(3),
    rows: int = Form(5),
):
    """
    Genera DOS PDFs separados para impresión controlada.
    Devuelve JSON con las URLs de descarga.
    """
    cols = max(1, min(6, cols))
    rows = max(1, min(8, rows))

    session_id  = uuid.uuid4().hex
    session_dir = UPLOAD_FOLDER / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    try:
        saved_paths = await _save_images(images, session_dir)
        if not saved_paths:
            raise HTTPException(400, "Ninguna imagen tiene formato válido")

        raw_text = extract_text_from_images(saved_paths)
        if not raw_text.strip():
            raise HTTPException(422, "No se pudo extraer texto.")

        flashcards = generate_flashcards(raw_text, max_cards=cols * rows * 4)
        if not flashcards:
            raise HTTPException(422, "La IA no pudo generar tarjetas.")

        q_path = OUTPUT_FOLDER / f"{session_id}_preguntas.pdf"
        a_path = OUTPUT_FOLDER / f"{session_id}_respuestas.pdf"

        generate_pdf_questions(flashcards, str(q_path), cols, rows)
        generate_pdf_answers(flashcards, str(a_path), cols, rows)

        total_sheets = -(-len(flashcards) // (cols * rows))  # ceil division

        return JSONResponse({
            "questions_url": f"/tarjetas/pdf/{session_id}_preguntas.pdf",
            "answers_url":   f"/tarjetas/pdf/{session_id}_respuestas.pdf",
            "total_sheets":  total_sheets,
            "total_cards":   len(flashcards),
        })

    except HTTPException:
        raise
    except Exception as exc:
        import traceback; traceback.print_exc()
        raise HTTPException(500, f"Error interno: {str(exc)}")
    finally:
        shutil.rmtree(str(session_dir), ignore_errors=True)


@flashscan_app.get("/pdf/{filename}")
async def serve_pdf(filename: str):
    """Sirve un PDF generado por nombre de archivo."""
    # Sanitizar para evitar path traversal
    filename = Path(filename).name
    pdf_path = OUTPUT_FOLDER / filename
    if not pdf_path.exists():
        raise HTTPException(404, "PDF no encontrado")
    return FileResponse(str(pdf_path), media_type="application/pdf")
