from fastapi import FastAPI, WebSocket, HTTPException, Request, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import json
import os
import jsonschema
from decoder import JsonPuml
from main import classify_and_generate_diagram, regenerate_diagram_from_data
from OperationCRUD import DiagramCRUD

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