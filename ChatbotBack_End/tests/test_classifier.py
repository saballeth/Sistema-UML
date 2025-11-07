import pytest
from Clasificador_diagrama import AdvancedDiagramClassifier


def test_classifier_detects_class_diagram():
    clf = AdvancedDiagramClassifier()
    text = "Necesito un diagrama con las clases Usuario y Producto. Usuario tiene atributos id y nombre y método crear()"
    res = clf.classify_diagram_type(text, user_id='ut_user_1')
    assert isinstance(res, dict)
    assert res.get('intent') == 'diagrama_clases'
    assert res.get('confidence', 0) >= 0.6


def test_classifier_detects_usecase_diagram():
    clf = AdvancedDiagramClassifier()
    text = "El actor Cliente interactúa con el sistema para realizar pedido como caso de uso realizar pedido"
    res = clf.classify_diagram_type(text, user_id='ut_user_2')
    assert isinstance(res, dict)
    assert res.get('intent') == 'diagrama_casos_uso'
    assert res.get('confidence', 0) >= 0.6
