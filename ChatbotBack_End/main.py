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
        # Primero intentar detectar bloques del tipo "Clase: atributos...; métodos..."
        pre_parsed = {}
        for m in re.finditer(r"\b([A-ZÁÉÍÓÚÑ]\w*)\s*:\s*([^\n]+)", text):
            cls = m.group(1)
            rest = m.group(2)
            attrs = []
            methods_list = []
            # Buscar secciones por palabras clave
            # ejemplo: "atributos: id, nombre; métodos: crear(), eliminar()"
            m_attrs = re.search(r"atribut(?:o|os)\s*[:\-]?\s*([^;]+)", rest, re.IGNORECASE)
            if m_attrs:
                for a in re.split(r',|\s+y\s+', m_attrs.group(1)):
                    n = a.strip()
                    # limpiar prefijos no deseados (ej. "s: id") y caracteres extra
                    n = re.sub(r'^[^\wÀ-ÿ_]+', '', n)
                    n = re.sub(r'^[A-Za-zÀ-ÿ0-9_]+:\s*', '', n)
                    n = re.sub(r'[^\wÀ-ÿ_].*$', '', n)
                    if n:
                        attrs.append(n)
            m_methods = re.search(r"métod(?:o|os)\s*[:\-]?\s*([^;]+)", rest, re.IGNORECASE)
            if m_methods:
                for mm in re.split(r',|\s+y\s+', m_methods.group(1)):
                    name = re.sub(r'\(.*\)', '', mm).strip()
                    # eliminar prefijos tipo "métodos:" o "s:" que puedan quedar
                    name = re.sub(r'^[A-Za-zÀ-ÿ0-9_]+:\s*', '', name)
                    # limpiar caracteres no alfanuméricos sobrantes
                    name = re.sub(r'[^\wÀ-ÿ_].*$', '', name)
                    if name:
                        methods_list.append(name)
            if attrs or methods_list:
                pre_parsed[cls] = {'attributes': attrs, 'methods': methods_list}

        # Buscar nombres de clase en varias formas: "clase X", o "clases A, B y C"
        class_names = re.findall(r'clase\s+(\w+)', text, re.IGNORECASE)
        if not class_names:
            m = re.search(r'clases?\s+([A-ZÁÉÍÓÚÑ][\w]*(?:\s*,\s*[A-ZÁÉÍÓÚÑ][\w]*|\s+y\s+[A-ZÁÉÍÓÚÑ][\w]*)*)', text)
            if m:
                names = re.split(r',|\s+y\s+', m.group(1))
                class_names = [n.strip() for n in names if n.strip()]

        # Añadir clases detectadas en el contexto
        if context and context.get('messages'):
            for msg in context['messages']:
                class_names += re.findall(r'clase\s+(\w+)', msg, re.IGNORECASE)
        # Añadir también clases detectadas en pre_parsed si no hay detecciones explícitas
        if not class_names and pre_parsed:
            class_names = list(pre_parsed.keys())
        else:
            for k in pre_parsed.keys():
                if k not in class_names:
                    class_names.append(k)

        class_names = list(dict.fromkeys(class_names))  # mantener orden, eliminar duplicados

        declaring_elements = []
        # Extraer atributos y métodos asociados (intento simple: si se menciona explícitamente junto a la clase)
        for class_name in class_names:
            attributes = []
            # Si habíamos preparseado un bloque para esta clase, usarlo primero
            if class_name in pre_parsed:
                for n in pre_parsed[class_name].get('attributes', []):
                    attributes.append({
                        "name": n,
                        "type": "String",
                        "visibility": "public",
                        "isStatic": False,
                        "isFinal": False
                    })
                for mname in pre_parsed[class_name].get('methods', []):
                    # dejar que el bloque sobreescriba métodos detectados posteriormente
                    pass
            # buscar "<Class> tiene atributo(s) a, b y c" o "atributo x"
            m_attr = re.search(rf'{class_name}[^\.\,\n]*atributo[s]?\s+([\w\s,]+)', text, re.IGNORECASE)
            if m_attr:
                attr_list = re.split(r',|\s+y\s+', m_attr.group(1))
                for attr in attr_list:
                    n = attr.strip()
                    if n:
                        # evitar duplicados si ya agregado por pre_parsed
                        if any(a['name'] == n for a in attributes):
                            continue
                        attributes.append({
                            "name": n,
                            "type": "String",
                            "visibility": "public",
                            "isStatic": False,
                            "isFinal": False
                        })
            else:
                # fallback global: sólo aplicarlo si hay una única clase detectada
                if len(class_names) <= 1:
                    for attr in re.findall(r'atributo[s]?\s+([\w]+)', text, re.IGNORECASE):
                        attributes.append({
                            "name": attr,
                            "type": "String",
                            "visibility": "public",
                            "isStatic": False,
                            "isFinal": False
                        })

            methods = []
            # Cargar métodos desde pre_parsed si existen
            if class_name in pre_parsed:
                for mname in pre_parsed[class_name].get('methods', []):
                    methods.append({
                        "name": mname,
                        "returnType": "void",
                        "visibility": "public",
                        "isAbstract": False,
                        "params": []
                    })
            m_methods = re.search(rf'{class_name}[^\.\,\n]*método[s]?\s+([\w\s,()]+)', text, re.IGNORECASE)
            if m_methods:
                method_list = re.split(r',|\s+y\s+', m_methods.group(1))
                for method in method_list:
                    name = re.sub(r'\(.*\)', '', method).strip()
                    if name:
                        if any(m['name'] == name for m in methods):
                            continue
                        methods.append({
                            "name": name,
                            "returnType": "void",
                            "visibility": "public",
                            "isAbstract": False,
                            "params": []
                        })
            else:
                # fallback global: sólo aplicarlo si hay una única clase detectada
                if len(class_names) <= 1:
                    for method in re.findall(r'método[s]?\s+([\w]+)', text, re.IGNORECASE):
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
        # Filtrar atributos inválidos (evitar frases completas); mantener solo nombres simples
        for el in declaring_elements:
            el['attributes'] = [a for a in el.get('attributes', []) if isinstance(a.get('name'), str) and ' ' not in a.get('name')]

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

    # Si la intención es desconocida, ambigua o la confianza es baja, solicitar al LLM aclaración
    if diagram_type in ("unknown", "ambiguous", None) or confidence < LLM_FALLBACK_CONFIDENCE:
        # pedir al LLM que resuelva o devuelva una pregunta de aclaración
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
                "clarify": llm_decision.get("question") or "¿Puedes especificar si quieres un diagrama de clases o un diagrama de casos de uso?",
                "llm_raw": llm_decision.get("raw")
            }

    # 2. Construye el JSON para el decoder
    data = build_json_for_decoder(text, diagram_type, classifier=diagram_classifier, user_id=user_id)
    if not data or diagram_type == "unknown":
        return {
            "text": text,
            "analysis": intent_result,
            "error": "No se pudo construir el JSON para el diagrama."
        }
    # Si el JSON está vacío de elementos significativos, pedir aclaración en lugar de generar un diagrama vacío
    if diagram_type == "diagrama_clases" and (not data.get("declaringElements") or len(data.get("declaringElements")) == 0):
        return {
            "text": text,
            "analysis": intent_result,
            "clarify": "No se detectaron clases ni detalles (atributos/métodos). ¿Puedes nombrar al menos una clase y, si es posible, sus atributos o métodos?"
        }
    if diagram_type == "diagrama_casos_uso" and (not data.get("actors") and not data.get("useCases")):
        return {
            "text": text,
            "analysis": intent_result,
            "clarify": "No se detectaron actores ni casos de uso. ¿Puedes indicar los actores y/o los casos de uso que quieres modelar?"
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

