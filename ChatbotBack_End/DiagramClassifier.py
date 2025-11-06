# DiagramClassifier_light.py
import asyncio
import time
import os
import logging
import json
import uuid
import re
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict, List, Tuple

# -----------------------------
# CONFIGURACIÓN DE LOGGING
# -----------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('diagram_classifier.log')
    ]
)
logger = logging.getLogger("diagram_classifier")

# -----------------------------
# CLASIFICADOR DE DIAGRAMAS
# -----------------------------
class DiagramIntentClassifier:
    def __init__(self):
        # Patrones para falsos positivos
        self.false_positive_patterns = [
            (r'\bclase(s)? de (yoga|baile|ingles|conducción|natación)\b', 'other'),
            (r'\bsistema (solar|nervioso|operativo|digestivo|endocrino)\b', 'other'),
            (r'\bactor(es)? de (cine|teatro|televisión|doblaje)\b', 'other'),
            (r'\bmétodo(s)? (científico|estudio|enseñanza|aprendizaje)\b', 'other')
        ]
        
        self.diagram_patterns = {
            'diagrama_clases': {
                'high_priority': [
                    r'\b(clase|atributo|método|propiedad|herencia|implementación)\b',
                    r'\b(interface|interfaz|enum|abstracto|encapsulamiento|polimorfismo)\b',
                    r'\b(publico|privado|protegido|composición|agregación|asociación)\b',
                    r'\b(objeto|instancia|constructor|getter|setter|static|final)\b'
                ],
                'medium_priority': [
                    r'\b(entidad|modelo|dominio|estructura|contrato|paquete)\b',
                    r'\b(extends|implementa|relación|multiplicidad|visibilidad)\b'
                ]
            },
            'diagrama_casos_uso': {
                'high_priority': [
                    r'\b(actor|usuario|sistema|funcionalidad|caso de uso)\b',
                    r'\b(interactúa|realiza|ejecuta|escenario|requisito|requerimiento)\b',
                    r'\b(rol|objetivo|autenticación|registro|login|inicio sesión)\b'
                ],
                'medium_priority': [
                    r'\b(cliente|administrador|gestión|proceso|flujo|paso)\b',
                    r'\b(permiso|acceso|restricción|nivel|privilegio)\b'
                ]
            }
        }
        
    def classify_intent(self, text: str) -> Dict:
        """Clasifica la intención del diagrama"""
        if not text or len(text.strip()) < 10:
            return {"intent": "unknown", "confidence": 0.0, "method": "text_too_short"}
        
        text_lower = text.lower().strip()
        
        # 1. Verificar falsos positivos
        for pattern, intent in self.false_positive_patterns:
            if re.search(pattern, text_lower):
                return {"intent": intent, "confidence": 0.95, "method": "false_positive_filter"}
        
        # 2. Scoring por términos
        class_high_score = self._calculate_score(text_lower, self.diagram_patterns['diagrama_clases']['high_priority'])
        usecase_high_score = self._calculate_score(text_lower, self.diagram_patterns['diagrama_casos_uso']['high_priority'])
        
        # 3. Detección por términos exclusivos
        if class_high_score > 0 and usecase_high_score == 0:
            return {"intent": "diagrama_clases", "confidence": 0.9, "method": "high_priority_terms"}
        elif usecase_high_score > 0 and class_high_score == 0:
            return {"intent": "diagrama_casos_uso", "confidence": 0.9, "method": "high_priority_terms"}
        
        # 4. Scoring con términos de media prioridad
        class_medium_score = self._calculate_score(text_lower, self.diagram_patterns['diagrama_clases']['medium_priority'])
        usecase_medium_score = self._calculate_score(text_lower, self.diagram_patterns['diagrama_casos_uso']['medium_priority'])
        
        # 5. Cálculo de scores totales
        class_total = (class_high_score * 2) + class_medium_score
        usecase_total = (usecase_high_score * 2) + usecase_medium_score
        
        # 6. Decisión basada en diferencia significativa
        if class_total - usecase_total >= 2:
            confidence = min(0.9, 0.6 + (class_total * 0.1))
            return {"intent": "diagrama_clases", "confidence": confidence, "method": "weighted_scoring"}
        elif usecase_total - class_total >= 2:
            confidence = min(0.9, 0.6 + (usecase_total * 0.1))
            return {"intent": "diagrama_casos_uso", "confidence": confidence, "method": "weighted_scoring"}
        
        # 7. Fallback para empates
        if class_total > usecase_total:
            return {"intent": "diagrama_clases", "confidence": 0.6, "method": "tie_breaker"}
        elif usecase_total > class_total:
            return {"intent": "diagrama_casos_uso", "confidence": 0.6, "method": "tie_breaker"}
        else:
            return {"intent": "unknown", "confidence": 0.5, "method": "ambiguous"}
    
    def _calculate_score(self, text: str, patterns: List[str]) -> int:
        """Calcula score basado en patrones regex"""
        score = 0
        for pattern in patterns:
            matches = re.findall(pattern, text)
            score += len(matches)
        return score

# -----------------------------
# SISTEMA DE PRUEBAS EN CONSOLA
# -----------------------------
class TestSuite:
    """Suite de pruebas para el clasificador"""
    
    def __init__(self):
        self.classifier = DiagramIntentClassifier()
        self.test_results = {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "accuracy": 0.0
        }
    
    def run_comprehensive_tests(self):
        """Ejecuta una suite completa de pruebas"""
        print("🧪 INICIANDO PRUEBAS COMPLETAS DEL CLASIFICADOR")
        print("=" * 80)
        
        test_cases = self._get_test_cases()
        
        for i, (test_input, expected, description) in enumerate(test_cases, 1):
            self._run_single_test(i, test_input, expected, description)
        
        self._print_final_results()
    
    def _get_test_cases(self):
        """Define los casos de prueba"""
        return [
            # ✅ CASOS CLAROS DE DIAGRAMA DE CLASES
            (
                "quiero un diagrama de clases con atributos y métodos privados",
                "diagrama_clases",
                "Clases con atributos y métodos"
            ),
            (
                "necesito mostrar herencia entre las clases Usuario y Administrador",
                "diagrama_clases", 
                "Herencia entre clases"
            ),
            (
                "diagrama con interfaces y implementaciones de servicios",
                "diagrama_clases",
                "Interfaces e implementaciones"
            ),
            (
                "mostrar composición y agregación entre objetos del dominio",
                "diagrama_clases",
                "Composición y agregación"
            ),
            
            # ✅ CASOS CLAROS DE DIAGRAMA DE CASOS DE USO
            (
                "quiero ver los actores que interactúan con el sistema de ventas",
                "diagrama_casos_uso",
                "Actores del sistema"
            ),
            (
                "casos de uso para el proceso de autenticación de usuarios",
                "diagrama_casos_uso",
                "Casos de uso de autenticación"
            ),
            (
                "mostrar cómo los clientes y administradores usan la aplicación",
                "diagrama_casos_uso",
                "Interacción de usuarios"
            ),
            (
                "funcionalidades que ofrece el sistema a los diferentes roles",
                "diagrama_casos_uso", 
                "Funcionalidades por rol"
            ),
            
            # ⚠️ CASOS AMBIGUOS
            (
                "sistema con usuarios y permisos",
                "diagrama_casos_uso",  # Podría ser ambos
                "Caso ambiguo - usuarios y permisos"
            ),
            (
                "modelo del dominio con relaciones",
                "diagrama_clases",  # Podría ser ambos  
                "Caso ambiguo - modelo del dominio"
            ),
            
            # ❌ FALSOS POSITIVOS
            (
                "clase de yoga los martes y jueves",
                "other",
                "Falso positivo - clase de yoga"
            ),
            (
                "sistema solar con planetas y lunas",
                "other", 
                "Falso positivo - sistema solar"
            ),
            (
                "actor de cine famoso por sus películas",
                "other",
                "Falso positivo - actor de cine"
            ),
            
            # 📝 TEXTO INSUFICIENTE
            (
                "diagrama de clases",
                "unknown",
                "Texto muy corto"
            ),
            (
                "hola mundo",
                "unknown", 
                "Texto sin contexto"
            )
        ]
    
    def _run_single_test(self, test_num: int, test_input: str, expected: str, description: str):
        """Ejecuta una prueba individual"""
        self.test_results["total_tests"] += 1
        
        # Ejecutar clasificación
        start_time = time.time()
        result = self.classifier.classify_intent(test_input)
        processing_time = (time.time() - start_time) * 1000  # ms
        
        # Verificar resultado
        passed = result["intent"] == expected
        confidence = result["confidence"]
        method = result["method"]
        
        if passed:
            self.test_results["passed_tests"] += 1
            status = "✅ PASÓ"
            color = "\033[92m"  # Verde
        else:
            self.test_results["failed_tests"] += 1
            status = "❌ FALLÓ"
            color = "\033[91m"  # Rojo
        
        # Mostrar resultado
        print(f"\n{color}{status}\033[0m - Prueba {test_num}: {description}")
        print(f"   Entrada: '{test_input}'")
        print(f"   Esperado: {expected} | Obtenido: {result['intent']}")
        print(f"   Confianza: {confidence:.2f} | Método: {method}")
        print(f"   Tiempo: {processing_time:.2f} ms")
        
        # Mostrar detalles adicionales para fallos
        if not passed:
            print(f"   \033[93m💡 Diferencia detectada: esperabas '{expected}' pero obtuvo '{result['intent']}'\033[0m")
    
    def _print_final_results(self):
        """Imprime los resultados finales de las pruebas"""
        print("\n" + "=" * 80)
        print("📊 RESULTADOS FINALES DE LAS PRUEBAS")
        print("=" * 80)
        
        total = self.test_results["total_tests"]
        passed = self.test_results["passed_tests"]
        accuracy = (passed / total) * 100 if total > 0 else 0
        
        print(f"🔢 Total de pruebas: {total}")
        print(f"✅ Pruebas exitosas: {passed}")
        print(f"❌ Pruebas fallidas: {self.test_results['failed_tests']}")
        print(f"🎯 Precisión: {accuracy:.1f}%")
        
        if accuracy >= 90:
            print("\n🏆 \033[92mEXCELENTE - El clasificador funciona perfectamente\033[0m")
        elif accuracy >= 80:
            print("\n👍 \033[93mBUENO - El clasificador funciona bien\033[0m") 
        elif accuracy >= 70:
            print("\n⚠️  \033[93mACEPTABLE - Hay espacio para mejora\033[0m")
        else:
            print("\n🚨 \033[91mNECESITA MEJORAS - Revisar los patrones\033[0m")
        
        # Mostrar recomendaciones
        self._print_recommendations()
    
    def _print_recommendations(self):
        """Imprime recomendaciones basadas en los resultados"""
        print("\n💡 RECOMENDACIONES:")
        
        if self.test_results["failed_tests"] > 0:
            print("   • Revisar los patrones regex para los casos fallidos")
            print("   • Considerar agregar más términos específicos")
            print("   • Verificar los filtros de falsos positivos")
        else:
            print("   • ¡Excelente trabajo! El clasificador está listo para producción")
        
        print("   • Puedes agregar más casos de prueba personalizados")
        print("   • Considera ejecutar pruebas con texto real de usuarios")

    def interactive_test(self):
        """Modo interactivo para probar texto personalizado"""
        print("\n🎮 MODO INTERACTIVO - Prueba tu propio texto")
        print("Escribe 'salir' para terminar")
        print("-" * 50)
        
        while True:
            try:
                user_input = input("\n📝 Ingresa texto para clasificar: ").strip()
                
                if user_input.lower() in ['salir', 'exit', 'quit']:
                    print("👋 Saliendo del modo interactivo...")
                    break
                
                if not user_input:
                    print("⚠️  Texto vacío, intenta de nuevo")
                    continue
                
                # Clasificar
                start_time = time.time()
                result = self.classifier.classify_intent(user_input)
                processing_time = (time.time() - start_time) * 1000
                
                # Mostrar resultados
                print(f"\n🎯 RESULTADO:")
                print(f"   Tipo: {result['intent']}")
                print(f"   Confianza: {result['confidence']:.2f}")
                print(f"   Método: {result['method']}")
                print(f"   Tiempo: {processing_time:.2f} ms")
                
                # Interpretación
                if result['intent'] == 'diagrama_clases':
                    print("   💡 El usuario quiere un diagrama de CLASES")
                elif result['intent'] == 'diagrama_casos_uso':
                    print("   💡 El usuario quiere un diagrama de CASOS DE USO")
                elif result['intent'] == 'other':
                    print("   💡 Esto parece un FALSO POSITIVO (no es diagrama)")
                else:
                    print("   💡 No se pudo determinar el tipo de diagrama")
                    
            except KeyboardInterrupt:
                print("\n👋 Saliendo...")
                break
            except Exception as e:
                print(f"❌ Error: {e}")

# -----------------------------
# SERVICIO DE CLASIFICACIÓN
# -----------------------------
class DiagramClassificationService:
    def __init__(self):
        self.diagram_classifier = DiagramIntentClassifier()
        self.conversation_context = {}
        self.performance_stats = {
            "total_requests": 0,
            "successful_classifications": 0,
            "classification_accuracy": 0.0,
            "last_diagram_type": None,
            "total_processing_time": 0.0,
            "average_processing_time": 0.0
        }

    async def classify_text(self, text: str, client_id: str = "default") -> Dict:
        """Clasifica texto y devuelve tipo de diagrama"""
        start_time = time.time()
        
        # Inicializar contexto si es nuevo cliente
        if client_id not in self.conversation_context:
            self.conversation_context[client_id] = {
                'messages': [],
                'last_intent': None,
                'confidence_history': []
            }
        
        context = self.conversation_context[client_id]
        context['messages'].append(text)
        
        # Clasificación actual
        current_intent = self.diagram_classifier.classify_intent(text)
        
        # Aplicar refuerzo contextual
        if (context['last_intent'] and 
            current_intent['intent'] == context['last_intent'] and
            current_intent['confidence'] > 0.6):
            current_intent['confidence'] = min(0.95, current_intent['confidence'] + 0.1)
            current_intent['method'] = f"{current_intent['method']}_with_context"
        
        # Actualizar contexto
        context['last_intent'] = current_intent['intent']
        context['confidence_history'].append(current_intent['confidence'])
        
        # Limitar historial
        if len(context['messages']) > 10:
            context['messages'] = context['messages'][-5:]
            context['confidence_history'] = context['confidence_history'][-5:]
        
        # Actualizar métricas
        processing_time = time.time() - start_time
        self._update_metrics(current_intent, processing_time)
        
        return {
            "intent": current_intent,
            "processing_time": processing_time,
            "client_id": client_id
        }

    def _update_metrics(self, intent: Dict, processing_time: float):
        self.performance_stats["total_requests"] += 1
        self.performance_stats["total_processing_time"] += processing_time
        
        if intent["intent"] != "unknown" and intent["confidence"] > 0.6:
            self.performance_stats["successful_classifications"] += 1
            self.performance_stats["last_diagram_type"] = intent["intent"]
        
        # Calcular promedios
        total = self.performance_stats["total_requests"]
        if total > 0:
            self.performance_stats["average_processing_time"] = (
                self.performance_stats["total_processing_time"] / total
            )
            successful = self.performance_stats["successful_classifications"]
            self.performance_stats["classification_accuracy"] = successful / total

