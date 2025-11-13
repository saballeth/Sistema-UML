import json
import os
import subprocess
import sys
import shutil

class JsonPuml:
    """
    Clase para generar diagramas PlantUML a partir de un archivo JSON.
    
    Esta clase lee los datos de un archivo JSON, los convierte en código PlantUML,
    y luego ejecuta PlantUML para generar la imagen correspondiente en el formato especificado.

    Atributos:
        _plant_uml_path (str): Ruta donde se encuentra el archivo JAR de PlantUML.
        _plant_uml_version (str): Nombre del archivo JAR de PlantUML (por ejemplo, "plantuml-1.2025.2.jar").
        _json_path (str): Ruta del archivo JSON que contiene la configuración y datos del diagrama.
        _output_path (str): Ruta donde se generará el archivo de salida (diagrama generado).
        _diagram_name (str): Nombre del diagrama (se usa para el archivo .puml de entrada y el archivo de salida).
        _data (dict): Datos leídos desde el archivo JSON.
        _code (str): Código PlantUML generado a partir de los datos del JSON.
    """

    def __init__(self, config: dict):
        """
        Inicializa la clase con la configuración proporcionada en el diccionario `config`.

        Parámetros:
            config (dict): Diccionario con las rutas y configuraciones necesarias.
                           El diccionario debe contener las siguientes claves:
                           - 'plant_uml_path': Ruta al directorio donde se encuentra el archivo JAR de PlantUML.
                           - 'plant_uml_version': Nombre del archivo JAR de PlantUML (ejemplo: 'plantuml-1.2025.2.jar').
                           - 'json_path': Ruta al archivo JSON que contiene los datos del diagrama.
                           - 'output_path': Ruta donde se generará el archivo de salida.
                           - 'diagram_name': Nombre del diagrama a generar.
        """
        # Inicializa con config; si 'data' viene en config usarla (no abrir archivos).
        try:
            # claves obligatorias
            self._plant_uml_path = config['plant_uml_path']
            self._plant_uml_version = config['plant_uml_version']
            self._json_path = config.get('json_path')
            self._output_path = config.get('output_path') or os.getcwd()
            self._diagram_name = config.get('diagram_name') or "diagram"

            # Datos: preferir 'data' pasado en config, si no intentar cargar json_path si existe
            if 'data' in config and config['data'] is not None:
                self._data = config['data']
            elif self._json_path:
                self._data = self._get_data()
            else:
                self._data = None

            # Generar código inmediatamente si hay datos
            self._code = self._json_to_plantuml() if self._data is not None else None
        except KeyError as e:
            raise KeyError(f"Configuración inválida: falta la clave {e}") from e
        except Exception as e:
            raise RuntimeError(f"Error inesperado durante la inicializacion: {e}") from e

    def generate_diagram(self):
        """
        Genera el diagrama a partir del código PlantUML.

        Este método:
        1. Crea la carpeta de salida si no existe.
        2. Guarda el código PlantUML en un archivo `.puml`.
        3. Ejecuta PlantUML para generar el diagrama en el formato deseado.
        """
        # Validaciones previas
        if not self._code:
            raise RuntimeError("No hay código PlantUML para generar (self._code es None o vacío).")

        os.makedirs(self._output_path, exist_ok=True)
        out = os.path.join(self._output_path, self._diagram_name + ".puml")
        plant_uml = os.path.join(self._plant_uml_path, self._plant_uml_version)

        # Verificar entorno: java disponible y archivo jar existe
        if shutil.which("java") is None:
            raise FileNotFoundError("No se encontró 'java' en PATH. Java es requerido para ejecutar PlantUML.")
        if not os.path.isfile(plant_uml):
            raise FileNotFoundError(f"No se encontró el JAR de PlantUML en: {plant_uml}")

        # Guardar .puml
        with open(out, "w", encoding="utf-8") as output:
            output.write(self._code)

        # Ejecutar PlantUML y capturar salida para diagnóstico
        try:
            proc = subprocess.run(
                ["java", "-jar", plant_uml, "-tsvg", "-o", self._output_path, out],
                check=True, capture_output=True, text=True
            )
        except subprocess.CalledProcessError as e:
            msg = f"PlantUML falló (returncode={e.returncode}). stdout:\n{e.stdout}\nstderr:\n{e.stderr}"
            raise RuntimeError(msg) from e
        except Exception as e:
            raise RuntimeError(f"Error inesperado al ejecutar PlantUML: {e}") from e

    def _get_data(self) -> dict:
        """
        Carga los datos del archivo JSON.

        Este método abre el archivo JSON especificado en la configuración,
        lee los datos y los devuelve como un diccionario.

        Returns:
            dict: Los datos cargados del archivo JSON.
        """
        try:
            if not self._json_path:
                raise ValueError("json_path no está definido en la configuración.")
            with open(self._json_path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except FileNotFoundError as e:
            raise FileNotFoundError(f"Archivo JSON no encontrado: {self._json_path}") from e
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON mal formado en {self._json_path}: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Error inesperado al cargar el archivo JSON: {e}") from e

    def _json_to_plantuml(self) -> str:
        """
        Convierte los datos JSON a código PlantUML.

        Dependiendo del tipo de diagrama especificado en los datos JSON (como 'classDiagram' o 'useCaseDiagram'),
        este método genera el código correspondiente en el formato PlantUML.

        Returns:
            str: El código PlantUML generado a partir de los datos JSON.
        """
        try:
        # Iniciar el código PlantUML
            plantuml_str = "@startuml Diagram\n"

        # Decodificar los datos en función del tipo de diagrama
            if self._data["diagramType"] == "classDiagram":
                decode_class = DecodeClass(self._data)
                plantuml_str += decode_class.get_code()
            elif self._data["diagramType"] == "useCaseDiagram":
                decode_use_case = DecodeUseCase(self._data)
                plantuml_str += decode_use_case.get_code()
        # Finalizar el código PlantUML
            plantuml_str += "@enduml"
            return plantuml_str
        except KeyError as e:
            print(f"Error, falta la clave {e} en los datos JSON")
            sys.exit(1)
        except Exception as e:
            print(f"Error inesperado al convertir JSON a PlantUML: {e}")
            sys.exit(1)
    

class DecodeUseCase:
    """
    Esta clase se encarga de generar el código PlantUML para un diagrama de casos de uso.
    El código es generado a partir de los datos proporcionados en formato JSON, los cuales 
    contienen información sobre actores, casos de uso, paquetes y relaciones.

    Atributos:
    - _data (dict): Los datos en formato JSON que describen el diagrama de casos de uso.
    - _use_case_code (str): El código PlantUML generado para el diagrama.
    """

    def __init__(self, data: dict):
        """
        Inicializa la clase con los datos del diagrama en formato JSON.

        Parámetros:
        - data (dict): El diccionario que contiene los datos del diagrama en formato JSON.
        """
        try:
            self._data = data
            self._use_case_code = self._generate_code()
        except Exception as e:
            raise RuntimeError(f"Error inesperado en DecodeUseCase: {e}") from e

    def get_code(self) -> str:
        """
        Obtiene el código PlantUML generado para el diagrama de casos de uso.

        Retorna:
        - str: El código PlantUML para el diagrama.
        """
        return self._use_case_code

    def _generate_code(self) -> str:
        """
        Genera el código PlantUML para el diagrama de casos de uso a partir de los datos JSON.

        Este método recorre los datos JSON y genera las representaciones correspondientes para
        los actores, casos de uso, paquetes y relaciones.

        Retorna:
        - str: El código PlantUML generado para el diagrama.
        """
        try:
            plantuml_str = ""

        # Actores
            for actor in self._data.get("actors", []):
                plantuml_str = self._decodeUseCaseActor(plantuml_str, actor)
            
        # Casos de uso globales
            for use_case in self._data.get("useCases", []):
                plantuml_str = self._decodeUseCase(plantuml_str, use_case)

        # Paquetes
            plantuml_str = self._decodeUseCasePackage(plantuml_str, self._data)

        # Relaciones
            for relation in self._data.get("relationships", []):
                plantuml_str = self._decodeRelationships(plantuml_str, relation)     

            return plantuml_str
        except Exception as e: 
            print(f"Error inesperado al generar el codigo PlantUML: {e}")
            sys.exit(1)
    


    def _decodeUseCaseActor(self, current_code: str, data) -> str:
        """
        Decodifica un actor y lo convierte a código PlantUML.

        Parámetros:
        - current_code (str): El código PlantUML generado hasta el momento.
        - data (dict): Los datos del actor (nombre, alias, estereotipo, etc.).

        Retorna:
        - str: El código PlantUML actualizado con el actor.
        """
        try:     
            plantuml_str = current_code

            actor_name = data.get("name", "")
            actor_alias = data.get("alias", "") 
            actor_stereotype = f' <<{data["stereotype"]}>>' if "stereotype" in data else ""
            actor_business = "/" if data.get("business", False) else ""

            if actor_name:
                plantuml_str += f"actor{actor_business} \"{actor_name}\""
                if actor_alias:
                    plantuml_str += f" as {actor_alias}"
                plantuml_str += actor_stereotype + "\n"
        
            return plantuml_str
        except Exception as e:
            print(f"Error inesperado al decodificar actor: {e}")
            sys.exit(1)

    def _decodeUseCase(self, current_code: str, data) -> str:
        """
        Decodifica un caso de uso y lo convierte a código PlantUML.

        Parámetros:
        - current_code (str): El código PlantUML generado hasta el momento.
        - data (dict): Los datos del caso de uso (nombre, alias, estereotipo, etc.).

        Retorna:
        - str: El código PlantUML actualizado con el caso de uso.
        """
        try:
            plantuml_str = current_code

            usecase_name = data.get("name", "")
            if usecase_name:
                usecase_business = "/" if data.get("business", False) else ""
                usecase_alias = data.get("alias", "")
                usecase_stereotype = actor_stereotype = f' <<{data["stereotype"]}>>' if "stereotype" in data else ""
                if usecase_alias:
                    plantuml_str += f'usecase{usecase_business} (\"{usecase_name}\") as {usecase_alias} {usecase_stereotype}\n'
    
            return plantuml_str
        except Exception as e:
            print(f"Error inesperado al decodificar caso de uso: {e}")
            sys.exit(1)


    def _decodeUseCasePackage(self, current_code: str, data) -> str:
        """
        Decodifica los paquetes de casos de uso y actores, generando el código PlantUML correspondiente.

        Parámetros:
        - current_code (str): El código PlantUML generado hasta el momento.
        - data (dict): Los datos del paquete (que contiene casos de uso y actores).

        Retorna:
        - str: El código PlantUML actualizado con los paquetes.
        """
        try:
            plantuml_str = current_code
            packages = data.get("packages", [])
            if not packages:
                return plantuml_str
        
            for package in packages:
                plantuml_str += f'package "{package["name"]}" as {package["alias"]} {{\n'

                for use_case in package.get("useCases", []):
                    plantuml_str = self._decodeUseCase(plantuml_str, use_case) 

                for actor in package.get("actors", []):
                    plantuml_str = self._decodeUseCaseActor(plantuml_str, actor)

                plantuml_str = self._decodeUseCasePackage(plantuml_str, package)

                plantuml_str += "}\n" 

            return plantuml_str
        except Exception as e:
            print(f"Error inesperado al decodificar paquete: {e}")
            sys.exit(1)

    def _decodeRelationships(self, current_code: str, data) -> str:
        """
        Decodifica las relaciones entre actores y casos de uso y las convierte a código PlantUML.

        Parámetros:
        - current_code (str): El código PlantUML generado hasta el momento.
        - data (dict): Los datos de la relación (tipo, principal, secundario, dirección, etc.).

        Retorna:
        - str: El código PlantUML actualizado con la relación.
        """
        try:

            plantuml_str = current_code

            relation_type = data.get("type", "")
            relation_principal = data.get("principal", "")
            relation_secondary = data.get("secondary", "")
            relation_direction = data.get("direction", "")
            relation_label = f":\"{data.get('label', '')}\"" if data.get('label') else ""

            # Solo actor_actor
            relation_extend = data.get("extend", "")
        
            # Solo usecase_usecase 
            relation_stereotype = data.get("stereotype", "")

            if(relation_principal and relation_secondary):
                if relation_type == "actor_actor": 
                    if relation_extend == ">":
                        plantuml_str += f"{relation_secondary} <|-- {relation_principal}"
                    elif relation_extend == "<":
                        plantuml_str += f"{relation_principal} <|-- {relation_secondary}"
                    else:
                        plantuml_str += f"{relation_principal} -{relation_direction}-> {relation_secondary}"
                    plantuml_str += relation_label + "\n"
                    
                elif relation_type == "actor_usecase":
                    plantuml_str += f"{relation_principal} -{relation_direction}-> {relation_secondary}{relation_label}\n"

                elif relation_type == "useCase_usecase":
                    if relation_stereotype == "include" :
                        plantuml_str += f"{relation_principal} .> {relation_secondary}: include\n"
                    elif relation_stereotype == "extends":
                        plantuml_str += f"{relation_principal} .> {relation_secondary}: extends\n"

                elif relation_type == "package_package":
                    plantuml_str += f"{relation_principal} -{relation_direction}-> {relation_secondary}{relation_label}\n"

            return plantuml_str
        except Exception as e:
            print(f"Error inesperado al decodificar relaciones: {e}")
            sys.exit(1)

class DecodeClass:
    """
    Esta clase genera código PlantUML para diagramas de clases a partir de un archivo de datos JSON.
    
    Atributos:
        _data (dict): Los datos en formato JSON que describen las clases, atributos, métodos y relaciones.
        _visibilities (dict): Diccionario que mapea los niveles de visibilidad a su representación PlantUML.
        _relations_type (dict): Diccionario que mapea los tipos de relaciones a su representación PlantUML.
        _class_code (str): El código PlantUML generado a partir de los datos JSON.

    Métodos:
        __init__(self, data: dict): Inicializa la clase con los datos del diagrama de clases en formato JSON.
        get_code(self) -> str: Retorna el código PlantUML generado para el diagrama de clases.
        _generate_code(self) -> str: Genera el código PlantUML a partir de los datos del diagrama de clases.
    """
    
    def __init__(self, data: dict):
        """
        Inicializa la clase con los datos del diagrama de clases en formato JSON.

        Parámetros:
            data (dict): Los datos del diagrama de clases, incluyendo clases, atributos, métodos y relaciones.
        """
        try:
            
            self._data = data

        # Mapeo de visibilidades en PlantUML
            self._visibilities = {
                "private": "-",
                "protected": "#",
                "package private": "~",
                "public": "+"
            }

            # Mapeo de tipos de relaciones en PlantUML
            self._relations_type = {
                "inheritance": "<|--",
                "composition": "*--",
                "aggregation": "o--",
                "association": "--",
                "instantiation": "..|>",
                "realization": "<|..",
            }

            # Genera el código PlantUML
            self._class_code = self._generate_code()
        except Exception as e:
            print(f"Error inesperado en DecodeClass: {e}")
            sys.exit(1)

    def get_code(self) -> str:
        """
        Obtiene el código PlantUML generado para el diagrama de clases.

        Retorna:
            str: El código PlantUML para el diagrama de clases.
        """
        return self._class_code

    def _generate_code(self) -> str:
        """
        Genera el código PlantUML a partir de los datos del diagrama de clases en formato JSON.

        Este método recorre los datos del diagrama y construye el código PlantUML correspondiente
        a las clases, atributos, métodos y relaciones entre clases.

        Retorna:
            str: El código PlantUML generado para el diagrama de clases.
        """
        try:
            plantuml_str = ""

            # Recorre los elementos declarados (clases)
            for element in self._data.get('declaringElements', []):
                # Declara la clase
                type = element.get('type', '')
                elementName = element.get('name', '')
                plantuml_str += f"{type} {elementName}\n"

                # Añadir atributos para las clases
                for attribute in element.get('attributes', []):
                    attributeName = attribute.get('name', '')
                    attributeType = attribute.get('type', '')
                    visibility = self._visibilities.get(attribute.get('visibility', ''), '')
                    static = "{isStatic}" if attribute.get('isStatic', False) else ''
                    final = "{final}" if attribute.get('isFinal', False) else ''
                    plantuml_str += f"{elementName} : {visibility} {static} {final} {attributeType} {attributeName}\n"

                # Añadir métodos para las clases    
                for method in element.get('methods', []):
                    methodName = method.get('name', '')
                    abstract = "{abstract}" if method.get('isAbstract', False) else ''
                    visibility = self._visibilities.get(method.get('visibility', 'public'), '+')
                    returnType =  method.get('returnType', 'void')

                    # Añadir parámetros a los métodos
                    params = ""
                    for param in method.get('params', []):
                        params += f"{param.get('type', '')} {param.get('name', '')} "

                    plantuml_str += f"{elementName} : {visibility} {abstract} {returnType} {methodName}({params[:-1]})\n"  # params[:-1] elimina el último espacio

                # Añadir relaciones entre clases
                for relation in self._data.get('relationShips', []):
                    relationType = self._relations_type.get(relation.get('type', ''), '--')
                    source = relation.get('source', '') 
                    target = relation.get('target', '')
                    multiplicityEnd1 = ''
                    multiplicityEnd2 = ''
                    mult = relation.get('multiplicity')
                    if isinstance(mult, (list, tuple)):
                        if len(mult) > 0 and mult[0] is not None:
                            multiplicityEnd1 = f'"{mult[0]}"'
                        if len(mult) > 3 and mult[3] is not None:
                            multiplicityEnd2 = f'"{mult[3]}"'

                    plantuml_str += f"{source} {multiplicityEnd1} {relationType} {multiplicityEnd2} {target}\n"

            # Al final devolver el código generado (incluso si está vacío)
            return plantuml_str
        except Exception as e:
            print(f"Error inesperado al generar codigo PlantUML: {e}")
            sys.exit(1)

