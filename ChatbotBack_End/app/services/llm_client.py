import os
import json
import asyncio
import requests
from typing import Optional

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

DEFAULT_MODEL = os.environ.get("LLM_MODEL", "gpt-4o-mini")

def _sync_query_openai(prompt: str, model: str = None) -> dict:
    """
    Síncrono: llama a la API de OpenAI ChatCompletion y devuelve la respuesta.
    Ejecutar en hilo con asyncio.to_thread desde código async.
    """
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY no definido en variables de entorno")

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model or DEFAULT_MODEL,
        "messages": [
            {"role": "system", "content": "Eres un asistente que decide si un texto describe un diagrama de clases o un diagrama de casos de uso o necesita preguntar más al usuario."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.0,
        "max_tokens": 300
    }
    r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=15)
    r.raise_for_status()
    return r.json()

async def ask_llm_for_diagram_type(text: str) -> dict:
    """
    Pregunta al LLM si el texto corresponde a 'diagrama_clases', 'diagrama_casos_uso'
    o si se necesita una pregunta de aclaración. Devuelve dict:
      { "resolved": bool, "diagram_type": Optional[str], "question": Optional[str], "raw": {...} }
    """
    prompt = (
        f"Analiza este texto y responde sólo en JSON con las claves:\n"
        f" - resolved: true|false (si puedes decidir el tipo de diagrama ahora)\n"
        f" - diagram_type: 'diagrama_clases'|'diagrama_casos_uso'|null\n"
        f" - question: Si resolved es false, propone una única pregunta clara para pedir más información al usuario.\n\n"
        f"Texto:\n\"\"\"\n{text}\n\"\"\"\n\n"
        f"Ejemplo de salida válida:\n{{\"resolved\": false, \"diagram_type\": null, \"question\": \"¿Quieres modelar entidades y relaciones (clases) o actores y funcionalidades (casos de uso)?\"}}\n"
    )
    try:
        resp = await asyncio.to_thread(_sync_query_openai, prompt)
        content = resp["choices"][0]["message"]["content"]
        # intentar parsear JSON de la respuesta
        try:
            j = json.loads(content)
        except Exception:
            # si no es JSON, devolver raw y fallback a pregunta genérica
            return {"resolved": False, "diagram_type": None, "question": "¿Puedes especificar si quieres un diagrama de clases o de casos de uso?", "raw": {"content": content, "api": resp}}
        # Normalizar
        return {"resolved": bool(j.get("resolved")), "diagram_type": j.get("diagram_type"), "question": j.get("question"), "raw": j}
    except Exception as e:
        return {"resolved": False, "diagram_type": None, "question": "¿Puedes especificar si quieres un diagrama de clases o de casos de uso?", "error": str(e)}