import pytest
from main import build_json_for_decoder, diagram_classifier
from decoder import JsonPuml
import os


def test_build_json_for_class_diagram_simple():
    text = "Necesito un diagrama con las clases Usuario y Producto. Usuario tiene atributo id y método crear()"
    res = diagram_classifier.classify_diagram_type(text, user_id='ut_builder_1')
    assert res.get('intent') == 'diagrama_clases'
    data = build_json_for_decoder(text, res['intent'], classifier=diagram_classifier, user_id='ut_builder_1')
    assert data is not None
    assert data.get('diagramType') == 'classDiagram'
    names = [e['name'] for e in data.get('declaringElements', [])]
    assert 'Usuario' in names
    # encontrar Usuario element
    usuario = next((e for e in data['declaringElements'] if e['name'] == 'Usuario'), None)
    assert usuario is not None
    attr_names = [a['name'] for a in usuario.get('attributes', [])]
    assert 'id' in attr_names
    method_names = [m['name'] for m in usuario.get('methods', [])]
    assert 'crear' in method_names


def test_build_json_for_usecase_diagram_simple():
    text = "Actor Cliente interactúa con el sistema. Caso de uso: realizar pedido"
    res = diagram_classifier.classify_diagram_type(text, user_id='ut_builder_2')
    # classifier puede devolver diagrama_casos_uso o ambiguous; en caso de ambiguous, forzamos a usecase para la prueba
    if res.get('intent') != 'diagrama_casos_uso':
        diagram_type = 'diagrama_casos_uso'
    else:
        diagram_type = res.get('intent')
    data = build_json_for_decoder(text, diagram_type, classifier=diagram_classifier, user_id='ut_builder_2')
    assert data is not None
    assert data.get('diagramType') == 'useCaseDiagram'
    actors = [a['name'] for a in data.get('actors', [])]
    assert 'Cliente' in actors or any('cliente' in a.lower() for a in actors)


def test_jsonpuml_generates_code_for_class():
    text = "Usuario: atributos: id, nombre; métodos: crear(), eliminar()"
    res = diagram_classifier.classify_diagram_type(text, user_id='ut_builder_3')
    data = build_json_for_decoder(text, res['intent'], classifier=diagram_classifier, user_id='ut_builder_3')
    config = {
        'plant_uml_path': os.path.join(os.getcwd(), 'plant_uml_exc'),
        'plant_uml_version': 'plantuml-1.2025.2.jar',
        'output_path': os.path.join(os.getcwd(), 'output'),
        'diagram_name': 'test_output',
        'data': data
    }
    jp = JsonPuml(config=config)
    assert jp._code is not None
    assert jp._code.startswith('@startuml')
    assert 'class Usuario' in jp._code
