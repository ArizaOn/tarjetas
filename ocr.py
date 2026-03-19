"""
ocr.py — Extracción de texto con Tesseract OCR
Soporta español e inglés. Aplica preprocesamiento con OpenCV para mejorar calidad.
"""

import re
from pathlib import Path

import cv2
import numpy as np
import pytesseract
from PIL import Image

# Idiomas para Tesseract (español + inglés)
TESSERACT_LANG = "spa+eng"

# Configuración de Tesseract: modo de segmentación automático + engine LSTM
TESSERACT_CONFIG = "--psm 1 --oem 3"


def preprocess_image(image_path: str) -> np.ndarray:
    """
    Preprocesa la imagen para mejorar el reconocimiento OCR:
    - Convierte a escala de grises
    - Aumenta contraste (CLAHE)
    - Binariza con umbral adaptativo
    - Elimina ruido
    """
    img = cv2.imread(image_path)

    if img is None:
        # Intentar con PIL como fallback (para formatos como HEIC parcialmente)
        pil_img = Image.open(image_path).convert("RGB")
        img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    # Redimensionar si es muy pequeña (mínimo 1500px de ancho para buena lectura)
    h, w = img.shape[:2]
    if w < 1500:
        scale = 1500 / w
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)

    # Escala de grises
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # CLAHE — mejora contraste de forma adaptativa (útil para fotos con luz irregular)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)

    # Umbral adaptativo para binarización robusta ante sombras y gradientes de luz
    binary = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=31,
        C=10,
    )

    # Reducción de ruido morfológico
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
    clean  = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    return clean


def extract_text_from_image(image_path: str) -> str:
    """
    Extrae texto de una sola imagen.
    Devuelve el texto como string.
    """
    try:
        processed = preprocess_image(image_path)
        pil_image = Image.fromarray(processed)

        text = pytesseract.image_to_string(
            pil_image,
            lang=TESSERACT_LANG,
            config=TESSERACT_CONFIG,
        )
        return text

    except pytesseract.TesseractNotFoundError:
        raise RuntimeError(
            "Tesseract no está instalado o no se encontró en el PATH. "
            "Instala con: sudo apt install tesseract-ocr tesseract-ocr-spa"
        )
    except Exception as exc:
        print(f"[OCR] Error procesando {image_path}: {exc}")
        return ""


def clean_text(text: str) -> str:
    """
    Limpia el texto extraído por Tesseract:
    - Elimina líneas con solo caracteres raros (artefactos OCR)
    - Colapsa múltiples líneas vacías
    - Elimina caracteres de control
    """
    lines = text.splitlines()
    cleaned = []
    for line in lines:
        stripped = line.strip()
        # Descartar líneas que son básicamente ruido (menos de 3 chars reales)
        real_chars = re.sub(r'[^a-zA-Z0-9áéíóúÁÉÍÓÚñÑüÜ]', '', stripped)
        if len(real_chars) >= 2:
            cleaned.append(stripped)

    # Colapsar líneas vacías múltiples en una sola
    result = re.sub(r'\n{3,}', '\n\n', '\n'.join(cleaned))
    return result.strip()


def extract_text_from_images(image_paths: list[str]) -> str:
    """
    Extrae y concatena el texto de una lista de imágenes.
    Separa cada página con un marcador para que la IA entienda la estructura.

    Args:
        image_paths: lista de rutas a las imágenes, en orden.

    Returns:
        Texto combinado de todas las páginas.
    """
    parts = []
    for i, path in enumerate(image_paths, start=1):
        print(f"[OCR] Procesando imagen {i}/{len(image_paths)}: {Path(path).name}")
        raw   = extract_text_from_image(path)
        clean = clean_text(raw)
        if clean:
            parts.append(f"--- Página {i} ---\n{clean}")
        else:
            print(f"[OCR] Advertencia: no se extrajo texto de {Path(path).name}")

    return "\n\n".join(parts)