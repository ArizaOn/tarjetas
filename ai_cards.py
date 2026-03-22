"""
ai_cards.py — Genera flashcards usando Groq API (llama-3.3-70b)
Rápido, gratuito, sin tarjeta de crédito.
"""

import json
import os
import re

from groq import Groq

MODEL = "llama-3.3-70b-versatile"

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
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY no está configurada.\n"
            "Ejecuta: set -x GROQ_API_KEY 'gsk_...'"
        )

    if len(text) > 12_000:
        print(f"[IA] Texto largo ({len(text)} chars), truncando a 12k...")
        text = text[:12_000]

    client = Groq(api_key=api_key)

    print(f"[IA] Enviando a Groq ({MODEL})...")

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": build_user_prompt(text, max_cards)},
        ],
        max_tokens=2048,
        temperature=0.2,
    )

    raw_response = response.choices[0].message.content.strip()
    print(f"[IA] Respuesta recibida ({len(raw_response)} chars).")

    flashcards = parse_flashcards(raw_response)
    print(f"[IA] {len(flashcards)} tarjetas válidas parseadas.")

    return flashcards
