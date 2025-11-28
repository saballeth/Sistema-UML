Instrucciones para probar el proyecto (desarrollo y tests)

Requisitos recomendados
- Python 3.11+ (recomendado para instalar el `requirements.txt` completo)

Dependencias mínimas para ejecutar tests (proporcionadas en `requirements-dev.txt`).

Pasos rápidos (desde la carpeta raíz del repo):

1) Crear un entorno virtual y activarlo

```bash
cd ChatbotBack_End
python3 -m venv .venv
source .venv/bin/activate
```

2) Instalar dependencias de desarrollo

```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements-dev.txt
```

3) Ejecutar la suite de tests

```bash
python3 -m pytest -q
```

4) Ejecutar `main.py` con una entrada de ejemplo

```bash
# desde la carpeta ChatbotBack_End
python3 main.py
# introduce una descripción cuando se pida, por ejemplo:
# Usuario: atributos: id, nombre; métodos: crear(), eliminar()
```

Notas importantes
- El archivo `requirements.txt` original contiene paquetes (numpy 2.3.x, ipython 9.x, etc.) que pueden requerir Python 3.11+. Si usas Python 3.10 puedes optar por instalar sólo `requirements-dev.txt` para ejecutar tests.
- Si necesitas el conjunto completo de dependencias en `requirements.txt`, crea un entorno con Python 3.11+ y luego:

```bash
pip install -r requirements.txt
```

- Si alguna instalación falla por paquetes nativos (scipy, numpy, etc.), instala las dependencias del sistema (p. ej. `libblas-dev`, `liblapack-dev` o usa ruedas precompiladas).

Siguientes pasos sugeridos
- Añadir un workflow de CI (GitHub Actions) que ejecute `pytest` en cada PR.
- Crear `requirements-prod.txt` y `requirements-dev.txt` separados si quieres aislar dependencias pesadas.
