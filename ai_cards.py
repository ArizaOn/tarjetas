"""
ai_cards.py — Genera flashcards usando Ollama (IA local)
Recibe texto extraído por OCR y devuelve lista de dicts {pregunta, respuesta}.

Requiere Ollama corriendo en el servidor:
    ollama serve
    ollama pull llama3.2:3b    # liviano (~2GB RAM)
    ollama pull llama3.1:8b    # mejor calidad (~5GB RAM)

Cambia MODEL abajo según el que hayas descargado.
"""

import json
import re
import urllib.request
import urllib.error

# ─── Configuración ───────────────────────────────────────────────
OLLAMA_URL = "http://localhost:11434/api/generate"

# Cambia a "llama3.1:8b" si tu servidor lo aguanta
MODEL = "llama3.2:latest"

SYSTEM_PROMPT = """Eres un experto en pedagogía y creación de material de estudio.
Tu tarea es analizar notas y apuntes de clase para generar flashcards de estudio.

REGLAS ESTRICTAS:
- Extrae los conceptos más importantes, definiciones, fórmulas y relaciones clave.
- Cada flashcard debe tener:
    * pregunta: breve (máximo 12 palabras), clara y directa.
    * respuesta: concisa (1-2 líneas), sin paja.
- NO generes preguntas triviales ni redundantes.
- Prioriza calidad sobre cantidad.
- Responde ÚNICAMENTE con un JSON array, sin texto adicional, sin markdown, sin backticks.
- Formato exacto: [{"pregunta": "...", "respuesta": "..."}, ...]
- Si el texto está en español, genera las tarjetas en español.
- Si el texto está en inglés, genera las tarjetas en inglés.
- Si está mezclado, usa el idioma dominante."""


def build_user_prompt(text: str, max_cards: int) -> str:
    return (
        f"Genera máximo {max_cards} flashcards de estudio a partir de los siguientes apuntes.\n\n"
        f"APUNTES:\n{text}\n\n"
        f"Responde SOLO con el JSON array. Nada más."
    )


def parse_flashcards(raw: str) -> list[dict]:
    """
    Parsea la respuesta del modelo.
    Tolerante a backticks, prefijos 'json', y espacios extra.
    """
    clean = raw.strip()
    clean = re.sub(r'^```(?:json)?\s*', '', clean)
    clean = re.sub(r'\s*```$', '', clean)
    start = clean.find('[')
    end   = clean.rfind(']')
    if start != -1 and end != -1:
        clean = clean[start:end+1]

    try:
        data = json.loads(clean)
        if isinstance(data, list):
            cards = []
            for item in data:
                if isinstance(item, dict):
                    q = str(item.get("pregunta", item.get("question", ""))).strip()
                    a = str(item.get("respuesta", item.get("answer",   ""))).strip()
                    if q and a:
                        cards.append({"pregunta": q, "respuesta": a})
            return cards
    except json.JSONDecodeError as e:
        print(f"[IA] Error parseando JSON: {e}")
        print(f"[IA] Respuesta recibida:\n{raw[:500]}")

    return []


def generate_flashcards(text: str, max_cards: int = 45) -> list[dict]:
    """
    Llama a Ollama para generar flashcards a partir del texto.

    Args:
        text:      Texto extraído por OCR.
        max_cards: Número máximo de tarjetas a generar.

    Returns:
        Lista de dicts con llaves 'pregunta' y 'respuesta'.

    Raises:
        RuntimeError: Si Ollama no está corriendo o el modelo no está descargado.
    """
    if len(text) > 12_000:
        print(f"[IA] Texto largo ({len(text)} chars), truncando a 12k...")
        text = text[:12_000]

    payload = {
        "model": MODEL,
        "stream": False,
        "options": {
            "temperature": 0.2,
            "num_predict": 1028,
        },
        "prompt": f"{SYSTEM_PROMPT}\n\n{build_user_prompt(text, max_cards)}",
    }

    body = json.dumps(payload).encode("utf-8")
    req  = urllib.request.Request(
        OLLAMA_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    print(f"[IA] Enviando a Ollama ({MODEL})...")

    try:
        with urllib.request.urlopen(req, timeout=1000) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"No se pudo conectar a Ollama en {OLLAMA_URL}.\n"
            f"Asegúrate de que esté corriendo: ollama serve\n"
            f"Error: {e}"
        )

    try:
        raw_response = result["response"]
    except (KeyError, TypeError) as e:
        raise RuntimeError(f"Respuesta inesperada de Ollama: {result}") from e

    print(f"[IA] Respuesta recibida ({len(raw_response)} chars).")

    flashcards = parse_flashcards(raw_response)
    print(f"[IA] {len(flashcards)} tarjetas válidas parseadas.")

    return flashcards
