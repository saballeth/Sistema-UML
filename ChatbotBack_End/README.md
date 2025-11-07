# ChatbotBack_End

Repositorio que contiene el backend del generador de diagramas UML (clasificador + constructor PlantUML).

## Requisitos

- Python 3.10+
- Java (si quiere generar imágenes via PlantUML)
- Opcional: `plantuml-<version>.jar` en la carpeta `plant_uml_exc/` para generar SVGs
- Variables de entorno:
  - `OPENAI_API_KEY` si usa el LLM (opcional para tests locales)

Nota: el archivo `requirements.txt` contiene muchos pins; algunos paquetes (por ejemplo `firebird-base==2.0.2`) puede que no estén disponibles en todos los entornos. Si `pip install -r requirements.txt` falla, puede instalar sólo las dependencias necesarias para desarrollo/tests (ver abajo).

## Instalación rápida (entorno de desarrollo)

Recomendado reproducible (virtualenv):

```bash
cd /path/to/ChatbotBack_End
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
# Intentar instalar todas las dependencias (puede fallar si hay pins no disponibles)
pip install -r requirements.txt || echo "requirements failed; installing minimal deps"
# Instalar deps necesarias para ejecutar tests
pip install pytest jsonschema requests
```

## Ejecutar tests

```bash
pytest -q
# o ejecutar sólo los tests del builder
pytest -k builder -q
```

## Ejecutar la API localmente (FastAPI)

La API principal está en `API_SERVICE.py`. Para arrancarla localmente:

```bash
# from repo root
uvicorn API_SERVICE:app --reload --host 0.0.0.0 --port 8000
```

Endpoints útiles:
- `POST /chat` — enviar texto y obtener análisis / diagrama (JSON o SVG si se genera)
- `POST /uml` — enviar JSON válido y generar SVG (requiere PlantUML jar si quiere generar imagen)

## Generar SVG con PlantUML (opcional)

1. Instale Java (JRE/JDK). 2. Coloque `plantuml-<version>.jar` dentro de `plant_uml_exc/`.
3. Use el endpoint `/uml` o llame `JsonPuml.generate_diagram()` desde Python.

Ejemplo rápido desde Python:

```python
from main import build_json_for_decoder, diagram_classifier
from decoder import JsonPuml
import os

text = "Usuario: atributos: id, nombre; métodos: crear()"
res = diagram_classifier.classify_diagram_type(text, user_id='local')
data = build_json_for_decoder(text, res['intent'], classifier=diagram_classifier, user_id='local')
config = {
    'plant_uml_path': os.path.join(os.getcwd(), 'plant_uml_exc'),
    'plant_uml_version': 'plantuml-1.2025.2.jar',
    'output_path': os.path.join(os.getcwd(), 'output'),
    'diagram_name': 'demo',
    'data': data
}
jp = JsonPuml(config=config)
jp.generate_diagram()  # requiere Java + plantuml JAR
```

## CI

Se añadió un workflow GitHub Actions en `.github/workflows/python-ci.yml` que ejecuta `pytest` en cada push/pull request. El flujo intenta instalar `requirements.txt` en modo best-effort (no fallará la job si un pin no está disponible) y luego ejecuta `pytest`.

## Notas y próximos pasos

- Si quieres que la CI instale exactamente todas las dependencias, reemplace/elimine los pins problemáticos en `requirements.txt`.
- Podemos añadir GitHub Actions para publicar artefactos (SVGs) o ejecutar tests de integración que incluyan PlantUML (requiere Java en runner y JAR en el repo o descarga en tiempo de ejecución).

---
Pequeñas ayudas: para problemas de instalación, copia aquí el log y te ayudo a ajustar `requirements.txt`.
JSON to PlantUML Parser

This project is a Python-based tool designed to parse a JSON file and generate a PlantUML diagram.

how to use:
you must have installed python3 or + in your pc

1) clone the repository by running:
git clone https://github.com/carlosrs14/exportation-module.git

2) open the project folder in your terminal or vscode with:
cd exportation-module

3) execute the program:
python main.py ./inpus/dir/input.json

4) output.puml is your output file

Semillero GIDSYC
