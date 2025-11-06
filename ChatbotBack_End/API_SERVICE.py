from fastapi import FastAPI, WebSocket, HTTPException, Request, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import json
import os
import jsonschema
from decoder import JsonPuml
from main import classify_and_generate_diagram, regenerate_diagram_from_data, diagram_classifier, LLM_FALLBACK_CONFIDENCE
from OperationCRUD import DiagramCRUD
from app.services.llm_client import ask_llm_for_diagram_type

# Carga el esquema UML una sola vez
with open("uml_schema.json", encoding="utf-8") as f:
    UML_SCHEMA = json.load(f)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ejemplo: almacenamiento simple de diagramas por id en carpeta "diagrams"
DIAGRAMS_DIR = os.path.join(os.path.dirname(__file__), "diagrams")
os.makedirs(DIAGRAMS_DIR, exist_ok=True)

def _diagram_path(diagram_id: str) -> str:
    return os.path.join(DIAGRAMS_DIR, f"{diagram_id}.json")

@app.post("/diagrams")
async def create_diagram(request: Request):
    body = await request.json()
    # body must contain initial diagram structure (diagramType,...)
    diagram_id = body.get("id") or str(uuid.uuid4())
    path = _diagram_path(diagram_id)
    body["id"] = diagram_id
    with open(path, "w", encoding="utf-8") as f:
        json.dump(body, f, ensure_ascii=False, indent=2)
    return {"id": diagram_id, "diagram": body}

@app.get("/diagrams/{diagram_id}/classes")
async def list_classes(diagram_id: str = Path(...)):
    path = _diagram_path(diagram_id)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Diagrama no encontrado")
    crud = DiagramCRUD.load_from_file(path)
    return {"classes": crud.list_classes()}

@app.post("/diagrams/{diagram_id}/classes")
async def create_class(diagram_id: str, request: Request):
    path = _diagram_path(diagram_id)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Diagrama no encontrado")
    body = await request.json()
    class_name = body.get("name")
    attributes = body.get("attributes", [])
    crud = DiagramCRUD.load_from_file(path)
    new_cls = crud.create_class(class_name, attributes)
    # regenerar diagrama y devolver svg
    svg = regenerate_diagram_from_data(crud.diagram)
    return {"class": new_cls, "svg": svg}

@app.put("/diagrams/{diagram_id}/classes/{class_id}")
async def update_class(diagram_id: str, class_id: str, request: Request):
    path = _diagram_path(diagram_id)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Diagrama no encontrado")
    body = await request.json()
    crud = DiagramCRUD.load_from_file(path)
    updated = crud.update_class(class_id, body)
    if not updated:
        raise HTTPException(status_code=404, detail="Clase no encontrada")
    svg = regenerate_diagram_from_data(crud.diagram)
    return {"class": updated, "svg": svg}

@app.delete("/diagrams/{diagram_id}/classes/{class_id}")
async def delete_class(diagram_id: str, class_id: str):
    path = _diagram_path(diagram_id)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Diagrama no encontrado")
    crud = DiagramCRUD.load_from_file(path)
    ok = crud.delete_class(class_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Clase no encontrada")
    svg = regenerate_diagram_from_data(crud.diagram)
    return {"deleted": ok, "svg": svg}

# WebSocket simple para ediciones en tiempo real (envía y recibe JSON con comandos CRUD)
@app.websocket("/ws/editor/{diagram_id}")
async def ws_editor(websocket: WebSocket, diagram_id: str):
    await websocket.accept()
    path = _diagram_path(diagram_id)
    if not os.path.exists(path):
        await websocket.send_json({"error": "Diagrama no encontrado"})
        await websocket.close()
        return
    crud = DiagramCRUD.load_from_file(path)
    try:
        async for msg in websocket.iter_text():
            try:
                payload = json.loads(msg)
                cmd = payload.get("cmd")
                if cmd == "add_class":
                    new_cls = crud.create_class(payload.get("name"), payload.get("attributes", []))
                    svg = regenerate_diagram_from_data(crud.diagram)
                    await websocket.send_json({"ok": True, "class": new_cls, "svg": svg})
                elif cmd == "delete_class":
                    ok = crud.delete_class(payload.get("class_id"))
                    svg = regenerate_diagram_from_data(crud.diagram)
                    await websocket.send_json({"ok": ok, "svg": svg})
                else:
                    await websocket.send_json({"error": "Comando no soportado"})
            except Exception as e:
                await websocket.send_json({"error": str(e)})
    finally:
        await websocket.close()

@app.post("/uml")
async def process_uml(request: Request):
    try:
        data = await request.json()
        validate(instance=data, schema=UML_SCHEMA)
        config = {
            "plant_uml_path": os.path.join(os.getcwd(), "plant_uml_exc"),
            "plant_uml_version": "plantuml-1.2025.2.jar",
            "json_path": None,
            "output_path": os.path.join(os.getcwd(), "output"),
            "diagram_name": "output",
        }
        json_puml = JsonPuml(config=config)
        json_puml._data = data
        json_puml._code = json_puml._json_to_plantuml()
        json_puml.generate_diagram()
        svg_path = os.path.join(config["output_path"], config["diagram_name"] + ".svg")
        if not os.path.exists(svg_path):
            raise HTTPException(status_code=500, detail="No se pudo generar el archivo SVG.")
        with open(svg_path, "r", encoding="utf-8") as f:
            svg_content = f.read()
        return {"svg": svg_content}
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e.message))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {e}")

@app.websocket("/ws/audio")
async def websocket_audio(websocket: WebSocket):
    await websocket.accept()
    try:
        audio_bytes = await websocket.receive_bytes()
        result = classify_and_generate_diagram(audio_bytes, UML_SCHEMA)
        await websocket.send_json(result)
    except Exception as e:
        await websocket.send_json({"error": str(e)})
    finally:
        await websocket.close()

@app.websocket("/ws/generate-diagram")
async def websocket_generate_diagram(websocket: WebSocket):
    await websocket.accept()
    try:
        data = await websocket.receive_json()
        jsonschema.validate(instance=data, schema=UML_SCHEMA)
        config = {
            "plant_uml_path": os.path.join(os.getcwd(), "plant_uml_exc"),
            "plant_uml_version": "plantuml-1.2025.2.jar",
            "json_path": None,
            "output_path": os.path.join(os.getcwd(), "output"),
            "diagram_name": "output",
        }
        json_puml = JsonPuml(config=config)
        json_puml._data = data
        json_puml._code = json_puml._json_to_plantuml()
        json_puml.generate_diagram()
        svg_path = os.path.join(config["output_path"], config["diagram_name"] + ".svg")
        if not os.path.exists(svg_path):
            await websocket.send_json({"error": "No se pudo generar el archivo SVG."})
        else:
            with open(svg_path, "r", encoding="utf-8") as f:
                svg_content = f.read()
            await websocket.send_json({"svg": svg_content})
    except jsonschema.ValidationError as e:
        await websocket.send_json({"error": f" Entrada no válida: {e.message}"})
    except Exception as e:
        await websocket.send_json({"error": f"Error al generar el diagrama: {e}"})
    finally:
        await websocket.close()


@app.websocket("/ws/chat/{user_id}")
async def ws_chat(websocket: WebSocket, user_id: str):
    """
    WebSocket para diálogo en tiempo real. Mantiene contexto en `diagram_classifier` por user_id.

    Mensajes entrantes (JSON):
      {"text": "...", "follow_up": false}

    Respuestas (JSON):
      - {"analysis": {...}}  # resultado del clasificador
      - {"clarify": "..."} # si necesita aclaración
      - {"svg": "<svg>...</svg>"} # si genera diagrama
    """
    await websocket.accept()
    try:
        async for raw in websocket.iter_text():
            try:
                payload = json.loads(raw)
                text = payload.get("text", "")
                follow_up = bool(payload.get("follow_up", False))

                if not text or not text.strip():
                    await websocket.send_json({"error": "No text provided"})
                    continue

                # Analizar con el clasificador (pasar follow_up)
                intent_result = diagram_classifier.analyze_conversation(user_id, text, is_follow_up=follow_up)
                intent = intent_result.get("intent")
                confidence = intent_result.get("confidence", 0.0)

                # Si ambiguous/unknown o baja confianza -> consultar LLM
                if intent in ("ambiguous", "unknown", None) or confidence < LLM_FALLBACK_CONFIDENCE:
                    try:
                        llm_decision = await ask_llm_for_diagram_type(text)
                    except Exception as e:
                        await websocket.send_json({"analysis": intent_result, "error": f"LLM error: {e}"})
                        continue

                    if llm_decision.get("resolved") and llm_decision.get("diagram_type"):
                        # LLM resolvió: generar diagrama
                        result = classify_and_generate_diagram(text, None, user_id=user_id)
                        result.setdefault("analysis", intent_result)["llm_decision"] = llm_decision
                        await websocket.send_json(result)
                    else:
                        # Enviar pregunta de clarificación al cliente
                        await websocket.send_json({
                            "text": text,
                            "analysis": intent_result,
                            "clarify": llm_decision.get("question") or "¿Quieres un diagrama de clases o un diagrama de casos de uso?",
                            "llm_raw": llm_decision.get("raw")
                        })
                else:
                    # Intención clara: intentar generar diagrama
                    result = classify_and_generate_diagram(text, None, user_id=user_id)
                    await websocket.send_json(result)

            except json.JSONDecodeError:
                await websocket.send_json({"error": "Invalid JSON"})
            except Exception as e:
                await websocket.send_json({"error": str(e)})
    finally:
        await websocket.close()


@app.post("/chat")
async def chat_text(request: Request):
    """
    Endpoint para recibir texto plano (o JSON {"text": ...}).
    - Si el clasificador está seguro, intenta generar el diagrama.
    - Si es ambiguous/unknown o la confianza es baja, consulta al LLM y devuelve una pregunta de clarificación o genera si el LLM resuelve.
    """
    # leer body: soporta text/plain o application/json
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
        # soportar respuesta de aclaración: {"clarify_answer": "..."} o {"follow_up": true, "text": "..."}
        clarify_answer = body.get("clarify_answer")
        follow_up_flag = bool(body.get("follow_up"))
        text = clarify_answer or body.get("text")
        user_id = body.get("user_id", request.headers.get("X-User-Id", "web_user"))
    else:
        raw = await request.body()
        text = raw.decode("utf-8") if raw else ""
        user_id = request.headers.get("X-User-Id", "web_user")

    is_follow_up = False
    # Si el cliente indica que esto es una respuesta a la aclaración, marcar follow-up
    if "application/json" in content_type:
        if clarify_answer or follow_up_flag:
            is_follow_up = True

    if not text or not text.strip():
        return JSONResponse({"error": "No text provided"}, status_code=400)

    # Analizar con el clasificador en memoria
    try:
        # pasar is_follow_up para que el clasificador use refuerzo contextual
        intent_result = diagram_classifier.analyze_conversation(user_id, text, is_follow_up)
    except Exception as e:
        return JSONResponse({"error": f"Classifier error: {e}"}, status_code=500)

    intent = intent_result.get("intent")
    confidence = intent_result.get("confidence", 0.0)

    # Si es ambiguous/unknown o baja confianza -> preguntar al LLM
    if intent in ("ambiguous", "unknown", None) or confidence < LLM_FALLBACK_CONFIDENCE:
        try:
            llm_decision = await ask_llm_for_diagram_type(text)
        except Exception as e:
            return JSONResponse({"analysis": intent_result, "error": f"LLM error: {e}"}, status_code=500)

        if llm_decision.get("resolved") and llm_decision.get("diagram_type"):
            # LLM resolvió: generar diagrama usando el flujo existente
            result = classify_and_generate_diagram(text, None, user_id=user_id)
            # incluir la decisión del LLM en el análisis
            result.setdefault("analysis", intent_result)["llm_decision"] = llm_decision
            return JSONResponse(result)
        else:
            # Devolver la pregunta sugerida para que el frontend la muestre al usuario
            return JSONResponse({
                "text": text,
                "analysis": intent_result,
                "clarify": llm_decision.get("question") or "¿Quieres un diagrama de clases o un diagrama de casos de uso?",
                "llm_raw": llm_decision.get("raw")
            })

    # Si hay intención clara y confianza suficiente, intentar generar diagrama
    result = classify_and_generate_diagram(text, None, user_id=user_id)
    return JSONResponse(result)