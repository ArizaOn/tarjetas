"""
ocr.py — Extracción de texto con Groq Vision API (usando SDK oficial)
Usa llama-3.2-11b-vision, excelente para letra manuscrita.
Gratis, sin tarjeta de crédito.
"""

import base64
import os
from pathlib import Path

from groq import Groq

MODEL  = "meta-llama/llama-4-scout-17b-16e-instruct"
PROMPT = """Please transcribe ALL the text you can see in this image, exactly as written.
Include every word, title, definition, and note.
Return only the transcribed text, nothing else. No explanations, no comments."""


def extract_text_from_image(image_path: str) -> str:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY no está configurada.")

    ext = Path(image_path).suffix.lower()
    mime_types = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".webp": "image/webp",
    }
    mime_type = mime_types.get(ext, "image/jpeg")

    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    client = Groq(api_key=api_key)

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{image_data}"
                        }
                    },
                    {
                        "type": "text",
                        "text": PROMPT
                    }
                ]
            }
        ],
        max_tokens=2048,
        temperature=0.1,
    )

    return response.choices[0].message.content.strip()


def clean_text(text: str) -> str:
    import re
    lines = text.splitlines()
    cleaned = [line.strip() for line in lines if len(line.strip()) >= 2]
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(cleaned)).strip()


def extract_text_from_images(image_paths: list[str]) -> str:
    parts = []
    for i, path in enumerate(image_paths, start=1):
        print(f"[OCR] Procesando imagen {i}/{len(image_paths)}: {Path(path).name}")
        try:
            raw   = extract_text_from_image(path)
            clean = clean_text(raw)
            if clean:
                parts.append(f"--- Página {i} ---\n{clean}")
                print(f"[OCR] ✓ {len(clean)} caracteres extraídos")
            else:
                print(f"[OCR] Advertencia: no se extrajo texto de {Path(path).name}")
        except Exception as e:
            print(f"[OCR] Error en {Path(path).name}: {e}")

    return "\n\n".join(parts)
