import asyncio
import json
from typing import Dict
# IMPORTA la función principal desde el main del proyecto
from main import classify_and_generate_diagram

async def get_ai_response(user_message: str, user_id: str = "default") -> str:
    """
    Ejecuta la función de clasificación/generación de diagramas (sin bloquear el loop).
    Devuelve texto simple o mensaje de error. Si se genera un SVG devuelve una
    confirmación y el SVG se puede retornar si lo necesitas.
    """
    # Ejecuta la función CPU/IO-bound en thread separado
    result: Dict = await asyncio.to_thread(classify_and_generate_diagram, user_message, None, user_id)
    if "svg" in result:
        # Devuelve mensaje y opcionalmente el SVG en JSON si prefieres
        return "Diagrama generado correctamente."
    if "error" in result:
        return f"Error: {result['error']}"
    return json.dumps(result.get("analysis", result), ensure_ascii=False)