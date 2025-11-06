import os
import json
from typing import Optional  
from decoder import JsonPuml
import jsonschema
from Clasificador_diagrama import AdvancedDiagramClassifier
from app.services.llm_client import ask_llm_for_diagram_type
import re
import asyncio

# Instancia global del clasificador avanzado (único)
diagram_classifier = AdvancedDiagramClassifier()

# umbral por debajo del cual consultamos al LLM para aclaración
LLM_FALLBACK_CONFIDENCE = 0.65

def build_json_for_decoder(text, diagram_type, classifier=None, user_id="default"):
    # Usa el contexto del clasificador si está disponible
    context = classifier.get_user_context(user_id) if classifier and hasattr(classifier, "get_user_context") else {}

    if diagram_type == "diagrama_clases":
        class_names = re.findall(r'clase\s+(\w+)', text, re.IGNORECASE)
        if context and context.get('messages'):
            for msg in context['messages']:
                class_names += re.findall(r'clase\s+(\w+)', msg, re.IGNORECASE)
        class_names = list(set(class_names))
        declaring_elements = []
        for class_name in class_names:
            attributes = []
            for attr in re.findall(r'atributo\s+(\w+)', text, re.IGNORECASE):
                attributes.append({
                    "name": attr,
                    "type": "String",
                    "visibility": "public",
                    "isStatic": False,
                    "isFinal": False
                })
            methods = []
            for method in re.findall(r'método\s+(\w+)', text, re.IGNORECASE):
                methods.append({
                    "name": method,
                    "returnType": "void",
                    "visibility": "public",
                    "isAbstract": False,
                    "params": []
                })
            declaring_elements.append({
                "type": "class",
                "name": class_name,
                "attributes": attributes,
                "methods": methods
            })
        relationShips = []
        for match in re.findall(r'(\w+)\s+hereda\s+de\s+(\w+)', text, re.IGNORECASE):
            relationShips.append({
                "type": "inheritance",
                "source": match[0],
                "target": match[1],
                "multiplicity": ["", "", "", ""]
            })
        return {
            "diagramType": "classDiagram",
            "declaringElements": declaring_elements,
            "relationShips": relationShips
        }

    elif diagram_type == "diagrama_casos_uso":
        actors = []
        for actor in re.findall(r'actor\s+(\w+)', text, re.IGNORECASE):
            actors.append({"name": actor, "alias": actor.lower(), "stereotype": "", "business": False})
        if context and context.get('messages'):
            for msg in context['messages']:
                for actor in re.findall(r'actor\s+(\w+)', msg, re.IGNORECASE):
                    actors.append({"name": actor, "alias": actor.lower(), "stereotype": "", "business": False})
        actors = [dict(t) for t in {tuple(d.items()) for d in actors}]
        useCases = []
        for usecase in re.findall(r'caso de uso\s+([\w\s]+)', text, re.IGNORECASE):
            useCases.append({"name": usecase.strip(), "alias": usecase.strip().replace(" ", "_").lower(), "stereotype": "", "business": False})
        if context and context.get('messages'):
            for msg in context['messages']:
                for usecase in re.findall(r'caso de uso\s+([\w\s]+)', msg, re.IGNORECASE):
                    useCases.append({"name": usecase.strip(), "alias": usecase.strip().replace(" ", "_").lower(), "stereotype": "", "business": False})
        useCases = [dict(t) for t in {tuple(d.items()) for d in useCases}]
        relationships = []
        for match in re.findall(r'(\w+)\s+puede\s+([\w\s]+)', text, re.IGNORECASE):
            relationships.append({
                "type": "actor_usecase",
                "principal": match[0],
                "secondary": match[1].strip().replace(" ", "_").lower(),
                "direction": "right",
                "label": ""
            })
        return {
            "diagramType": "useCaseDiagram",
            "actors": actors,
            "useCases": useCases,
            "relationships": relationships
        }
    else:
        return None

def classify_and_generate_diagram(text, uml_schema, user_id="default"):
    # 1. Clasifica el texto con el clasificador de diagramas
    # usar la interfaz del clasificador avanzado
    # AdvancedDiagramClassifier.analyze_conversation devuelve dict con 'intent' y 'confidence'
    intent_result = diagram_classifier.analyze_conversation(user_id, text) if hasattr(diagram_classifier, "analyze_conversation") else diagram_classifier.classify_intent(text)
    diagram_type = intent_result.get("intent", "unknown")
    confidence = intent_result.get("confidence", 0.0)
    method = intent_result.get("method", "")

    # Si la intención es desconocida o la confianza es baja, solicitar al LLM aclaración
    if diagram_type in ("unknown", None) or confidence < LLM_FALLBACK_CONFIDENCE:
        llm_decision = asyncio.run(ask_llm_for_diagram_type(text))
        # si LLM resolvió el tipo, usarlo
        if llm_decision.get("resolved") and llm_decision.get("diagram_type"):
            diagram_type = llm_decision["diagram_type"]
            # actualizar análisis para trazabilidad
            intent_result["method"] = f"llm_resolved ({intent_result.get('method')})"
            intent_result["confidence"] = max(confidence, 0.8)
        else:
            # devolver pregunta de aclaración al cliente para diálogo
            return {
                "text": text,
                "analysis": intent_result,
                "clarify": llm_decision.get("question") or "¿Puedes especificar si quieres un diagrama de clases o un diagrama de casos de uso?"
            }

    # 2. Construye el JSON para el decoder
    data = build_json_for_decoder(text, diagram_type, classifier=diagram_classifier, user_id=user_id)
    if not data or diagram_type == "unknown":
        return {
            "text": text,
            "analysis": intent_result,
            "error": "No se pudo construir el JSON para el diagrama."
        }
    try:
        schema = get_schema(diagram_type)
        jsonschema.validate(instance=data, schema=schema)
        config = {
            "plant_uml_path": os.path.join(os.getcwd(), "plant_uml_exc"),
            "plant_uml_version": "plantuml-1.2025.2.jar",
            "json_path": None,
            "output_path": os.path.join(os.getcwd(), "output"),
            "diagram_name": "output",
            "data": data,
        }
        json_puml = JsonPuml(config=config)
        json_puml.generate_diagram()
        svg_path = os.path.join(config["output_path"], config["diagram_name"] + ".svg")
        if not os.path.exists(svg_path):
            return {
                "text": text,
                "analysis": intent_result,
                "error": "No se pudo generar el archivo SVG."
            }
        with open(svg_path, "r", encoding="utf-8") as f:
            svg_content = f.read()
        return {
            "text": text,
            "analysis": intent_result,
            "svg": svg_content
        }
    except jsonschema.ValidationError as e:
        return {
            "text": text,
            "analysis": intent_result,
            "error": f"JSON inválido: {e.message}"
        }
    except Exception as e:
        return {
            "text": text,
            "analysis": intent_result,
            "error": f"Error al generar el diagrama: {e}"
        }

def get_schema(diagram_type):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    schema_dir = os.path.join(base_dir, "Validation Schemas")
    if diagram_type == "diagrama_clases":
        schema_path = os.path.join(schema_dir, "classDiagram_schema.json")
    elif diagram_type == "diagrama_casos_uso":
        schema_path = os.path.join(schema_dir, "useCaseDiagram_schema.json")
    else:
        raise ValueError("Tipo de diagrama no soportado")
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)

def regenerate_diagram_from_data(diagram_data: dict, user_id="default") -> str:
    """
    Recibe un JSON completo del diagrama, lo valida con el esquema apropiado,
    genera el diagrama via JsonPuml y devuelve el contenido SVG (string) o
    lanza excepción en caso de error.
    """
    diagram_type = "diagrama_clases" if diagram_data.get("diagramType") == "classDiagram" else "diagrama_casos_uso"
    schema = get_schema(diagram_type)
    jsonschema.validate(instance=diagram_data, schema=schema)
    config = {
        "plant_uml_path": os.path.join(os.getcwd(), "plant_uml_exc"),
        "plant_uml_version": "plantuml-1.2025.2.jar",
        "json_path": None,
        "output_path": os.path.join(os.getcwd(), "output"),
        "diagram_name": f"diagram_{user_id}"
    }
    config["data"] = diagram_data
    json_puml = JsonPuml(config=config)
    json_puml.generate_diagram()
    svg_path = os.path.join(config["output_path"], config["diagram_name"] + ".svg")
    with open(svg_path, "r", encoding="utf-8") as f:
        return f.read()

# uso de JsonPuml desde decoder.py no definido por el momento 

if __name__ == "__main__":
    # Pide el texto por consola
    texto = input("Introduce la descripción del diagrama: ")

    # Ejecuta el flujo principal usando el texto directamente
    result = classify_and_generate_diagram(texto, None, user_id="test_user")

    print("Resultado:")
    print(json.dumps(result, indent=2, ensure_ascii=False))

