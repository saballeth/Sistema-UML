import re
from typing import Dict, List, Optional

class AdvancedDiagramClassifier:
    """
    Clasificador avanzado para determinar el tipo de diagrama UML necesario
    basándose en descripciones textuales de usuarios.
    
    Características:
    - Análisis multi-nivel (términos decisivos, densidad de keywords, contexto, industria)
    - Gestión de contexto conversacional por usuario
    - Baja latencia y alta precisión para textos técnicos
    - Sin dependencias externas pesadas
    """
    
    def __init__(self):
        self.conversation_context = {}
        
        # Modelo de lenguaje mejorado con contexto
        self.domain_keywords = {
            'class_domain': [
                'clase', 'atributo', 'método', 'herencia', 'implementación', 
                'interface', 'enum', 'propiedad', 'encapsulamiento', 'polimorfismo',
                'entidad', 'objeto', 'instancia', 'constructor', 'getter', 'setter',
                'abstracto', 'static', 'final', 'paquete', 'importar', 'miembro',
                'variable', 'función', 'operación', 'signatura', 'parámetro',
                'visibilidad', 'modificador', 'sobrescritura', 'sobrecarga'
            ],
            
            'usecase_domain': [
                'actor', 'usuario', 'sistema', 'funcionalidad', 'interactúa',
                'realiza', 'ejecuta', 'escenario', 'caso de uso', 'requisito',
                'objetivo', 'proceso', 'flujo', 'paso', 'acción', 'tarea',
                'rol', 'responsabilidad', 'permiso', 'acceso', 'operación',
                'actividad', 'workflow', 'procedimiento', 'secuencia', 'interacción'
            ]
        }
        
        self.industry_context = {
            'software': [
                'código', 'programa', 'aplicación', 'software', 'desarrollo', 
                'debug', 'compilar', 'ejecutar', 'framework', 'librería',
                'api', 'sdk', 'ide', 'repositorio', 'commit', 'branch'
            ],
            'business': [
                'negocio', 'cliente', 'venta', 'marketing', 'estrategia', 
                'mercado', 'producto', 'servicio', 'empresa', 'organización',
                'departamento', 'equipo', 'proyecto', 'recurso', 'presupuesto'
            ],
            'education': [
                'curso', 'estudiante', 'profesor', 'lección', 'examen', 
                'calificación', 'universidad', 'colegio', 'clase', 'tema',
                'asignatura', 'materia', 'plan de estudios', 'currículo'
            ],
            'database': [
                'tabla', 'registro', 'campo', 'consulta', 'sql', 'entidad',
                'relación', 'clave', 'índice', 'transacción', 'esquema'
            ]
        }
        
        self.confidence_thresholds = {
            'initial': 0.6,
            'with_context': 0.75,
            'high_confidence': 0.85
        }

    def analyze_conversation(self, user_id: str, text: str, is_follow_up: bool = False) -> Dict:
        """
        Analiza el texto considerando el contexto de la conversación y determina
        el tipo de diagrama UML más apropiado.
        
        Args:
            user_id: Identificador único del usuario
            text: Descripción textual del sistema/diagrama
            is_follow_up: Indica si es un mensaje de seguimiento
            
        Returns:
            Dict con información del análisis:
            - intent: 'diagrama_clases', 'diagrama_casos_uso', o 'unknown'
            - confidence: Nivel de confianza (0.0 a 1.0)
            - method: Método utilizado para la clasificación
            - supporting_analyses: Número de análisis que apoyan la decisión
        """
        # Inicializar contexto si es nuevo usuario
        if user_id not in self.conversation_context:
            self.conversation_context[user_id] = {
                'messages': [],
                'detected_domain': None,
                'confidence_history': [],
                'last_intent': None,
                'industry_hints': set(),
                'interaction_count': 0
            }
        
        context = self.conversation_context[user_id]
        context['messages'].append(text)
        context['interaction_count'] += 1
        
        # Análisis multi-nivel
        basic_analysis = self._basic_intent_detection(text)
        contextual_analysis = self._contextual_analysis(text, context)
        industry_analysis = self._industry_analysis(text)
        semantic_analysis = self._semantic_analysis(text)
        
        # Combinar análisis
        final_result = self._combine_analyses(
            basic_analysis, contextual_analysis, industry_analysis, semantic_analysis, context, is_follow_up
        )
        
        # Actualizar contexto
        self._update_conversation_context(user_id, final_result, industry_analysis)
        
        return final_result

    def _basic_intent_detection(self, text: str) -> Dict:
        """Detección básica de intención basada en palabras clave"""
        text_lower = text.lower()
        
        # Contar ocurrencias por dominio
        class_score = sum(1 for word in self.domain_keywords['class_domain'] if word in text_lower)
        usecase_score = sum(1 for word in self.domain_keywords['usecase_domain'] if word in text_lower)
        
        # Detectar términos decisivos (alta especificidad)
        decisive_terms = {
            'diagrama_clases': [
                'clase', 'atributo', 'método', 'herencia', 'polimorfismo',
                'encapsulamiento', 'interface', 'implementación'
            ],
            'diagrama_casos_uso': [
                'actor', 'caso de uso', 'interactúa', 'funcionalidad', 'escenario',
                'requisito funcional'
            ]
        }
        
        decisive_class = any(term in text_lower for term in decisive_terms['diagrama_clases'])
        decisive_usecase = any(term in text_lower for term in decisive_terms['diagrama_casos_uso'])
        
        # Si hay términos decisivos de un tipo sin términos del otro tipo
        if decisive_class and not decisive_usecase:
            return {'intent': 'diagrama_clases', 'confidence': 0.92, 'method': 'decisive_terms'}
        elif decisive_usecase and not decisive_class:
            return {'intent': 'diagrama_casos_uso', 'confidence': 0.92, 'method': 'decisive_terms'}
        
        # Scoring basado en densidad de términos
        total_keywords = class_score + usecase_score
        if total_keywords > 0:
            class_ratio = class_score / total_keywords
            usecase_ratio = usecase_score / total_keywords
            
            # Diferencia significativa favorece un tipo
            difference = abs(class_ratio - usecase_ratio)
            if difference > 0.3:  # Diferencia del 30% o más
                intent = 'diagrama_clases' if class_ratio > usecase_ratio else 'diagrama_casos_uso'
                confidence = 0.7 + (difference * 0.3)  # Escalar confianza basada en diferencia
                return {'intent': intent, 'confidence': min(confidence, 0.9), 'method': 'keyword_density'}
            elif difference > 0.15:  # Diferencia moderada
                intent = 'diagrama_clases' if class_ratio > usecase_ratio else 'diagrama_casos_uso'
                confidence = 0.6 + (difference * 0.2)
                return {'intent': intent, 'confidence': confidence, 'method': 'keyword_density'}
        
        return {'intent': 'unknown', 'confidence': 0.4, 'method': 'basic_analysis'}

    def _contextual_analysis(self, text: str, context: Dict) -> Dict:
        """Análisis considerando el contexto de la conversación previa"""
        # Si no hay contexto previo, no podemos hacer análisis contextual
        if not context['detected_domain'] and context['interaction_count'] <= 1:
            return {'intent': 'unknown', 'confidence': 0.0, 'method': 'no_context'}
        
        previous_intent = context['last_intent']
        if previous_intent and previous_intent != 'unknown':
            # Verificar consistencia con contexto
            text_lower = text.lower()
            relevant_terms = self.domain_keywords[
                'class_domain' if previous_intent == 'diagrama_clases' else 'usecase_domain'
            ]
            
            term_matches = sum(1 for term in relevant_terms if term in text_lower)
            
            if term_matches > 0:
                # Boost basado en número de términos coincidentes e historial
                confidence_boost = min(0.4, term_matches * 0.1)
                
                # Boost adicional por historial consistente
                if len(context['confidence_history']) > 1:
                    recent_confidences = context['confidence_history'][-3:]  # Últimas 3 interacciones
                    avg_recent_confidence = sum(recent_confidences) / len(recent_confidences)
                    if avg_recent_confidence > 0.7:
                        confidence_boost += 0.1
                
                base_confidence = 0.7 if context['detected_domain'] else 0.6
                return {
                    'intent': previous_intent, 
                    'confidence': min(base_confidence + confidence_boost, 0.95),
                    'method': 'context_reinforcement'
                }
        
        return {'intent': 'unknown', 'confidence': 0.0, 'method': 'context_analysis'}

    def _industry_analysis(self, text: str) -> Dict:
        """Análisis de contexto de industria para inferir tipo de diagrama"""
        text_lower = text.lower()
        industry_scores = {}
        
        for industry, keywords in self.industry_context.items():
            industry_scores[industry] = sum(1 for keyword in keywords if keyword in text_lower)
        
        # Encontrar industria predominante
        primary_industry = max(industry_scores, key=industry_scores.get)
        max_score = industry_scores[primary_industry]
        
        if max_score > 0:
            # Mapeo industria -> preferencia de diagrama
            industry_preference = {
                'software': 'diagrama_clases',
                'business': 'diagrama_casos_uso', 
                'education': 'diagrama_clases',
                'database': 'diagrama_clases'
            }
            
            preferred_intent = industry_preference.get(primary_industry, 'unknown')
            
            # Calcular confianza basada en score y presencia de términos clave
            base_confidence = min(0.7, max_score * 0.15)
            
            # Boost si hay términos fuertes de la industria
            strong_industry_terms = {
                'software': ['código', 'programa', 'desarrollo'],
                'business': ['negocio', 'cliente', 'venta'],
                'education': ['curso', 'estudiante', 'profesor'],
                'database': ['tabla', 'registro', 'consulta']
            }
            
            strong_terms_count = sum(1 for term in strong_industry_terms.get(primary_industry, []) 
                                   if term in text_lower)
            if strong_terms_count > 0:
                base_confidence += 0.1
            
            return {
                'intent': preferred_intent,
                'confidence': base_confidence,
                'method': f'industry_{primary_industry}'
            }
        
        return {'intent': 'unknown', 'confidence': 0.0, 'method': 'industry_analysis'}

    def _semantic_analysis(self, text: str) -> Dict:
        """Análisis semántico basado en patrones y estructura del texto"""
        text_lower = text.lower()
        
        # Patrones que indican diagrama de clases
        class_patterns = [
            r'\b(clase|class)\s+\w+\s*\{',  # "clase Usuario {"
            r'\b(public|private|protected)\s+\w+',  # modificadores de acceso
            r'\w+\s+\w+\s*\([^)]*\)',  # declaraciones de métodos
            r'\b(extends|implements)\b',  # herencia/implementación
        ]
        
        # Patrones que indican diagrama de casos de uso
        usecase_patterns = [
            r'\b(actor|usuario)\s+\w+',  # "actor Cliente"
            r'\b(caso de uso|use case)\s+\w+',  # "caso de uso Login"
            r'\b(puede|pueden)\s+\w+',  # "los usuarios pueden realizar X"
            r'\b(sistema|sistem)\s+\w+',  # "el sistema debe hacer X"
        ]
        
        class_pattern_matches = sum(1 for pattern in class_patterns if re.search(pattern, text_lower))
        usecase_pattern_matches = sum(1 for pattern in usecase_patterns if re.search(pattern, text_lower))
        
        if class_pattern_matches > usecase_pattern_matches and class_pattern_matches > 0:
            confidence = min(0.8, 0.5 + (class_pattern_matches * 0.1))
            return {'intent': 'diagrama_clases', 'confidence': confidence, 'method': 'semantic_patterns'}
        elif usecase_pattern_matches > class_pattern_matches and usecase_pattern_matches > 0:
            confidence = min(0.8, 0.5 + (usecase_pattern_matches * 0.1))
            return {'intent': 'diagrama_casos_uso', 'confidence': confidence, 'method': 'semantic_patterns'}
        
        return {'intent': 'unknown', 'confidence': 0.0, 'method': 'semantic_analysis'}

    def _combine_analyses(self, basic: Dict, contextual: Dict, industry: Dict, 
                         semantic: Dict, context: Dict, is_follow_up: bool) -> Dict:
        """Combina todos los análisis para tomar una decisión final"""
        analyses = [basic, contextual, industry, semantic]
        
        # Filtrar análisis con confianza suficiente
        valid_analyses = [a for a in analyses if a['confidence'] > 0.3]
        
        if not valid_analyses:
            return {
                'intent': 'unknown', 
                'confidence': 0.3, 
                'method': 'low_confidence_combination',
                'supporting_analyses': 0
            }
        
        # Agrupar por intención
        intent_scores = {}
        for analysis in valid_analyses:
            intent = analysis['intent']
            if intent not in intent_scores:
                intent_scores[intent] = []
            intent_scores[intent].append(analysis['confidence'])
        
        # Calcular score promedio por intención
        avg_scores = {}
        for intent, scores in intent_scores.items():
            avg_scores[intent] = sum(scores) / len(scores)
        
        # Aplicar boosts estratégicos
        if is_follow_up and context['last_intent'] in avg_scores:
            # Boost por consistencia en conversación
            avg_scores[context['last_intent']] += 0.15
        
        # Boost por múltiples análisis coincidentes
        for intent, scores in intent_scores.items():
            if len(scores) >= 2:
                avg_scores[intent] += 0.1
            if len(scores) >= 3:
                avg_scores[intent] += 0.05
        
        # Seleccionar intención con mayor score
        if avg_scores:
            # Ordenar intents por score
            sorted_intents = sorted(avg_scores.items(), key=lambda x: x[1], reverse=True)
            best_intent, best_score = sorted_intents[0]
            second_score = sorted_intents[1][1] if len(sorted_intents) > 1 else 0.0

            # Detectar ambigüedad: si la diferencia entre top2 es pequeña o la mejor puntuación es baja
            score_diff = best_score - second_score
            # criterios: diferencia menor a 0.08 (8%) o mejor score < 0.55 => ambiguous
            if score_diff < 0.08 or best_score < 0.55:
                ambiguity_reason = []
                if score_diff < 0.08:
                    ambiguity_reason.append(f"small_score_diff={score_diff:.2f}")
                if best_score < 0.55:
                    ambiguity_reason.append(f"low_best_score={best_score:.2f}")

                return {
                    'intent': 'ambiguous',
                    'confidence': round(best_score, 2),
                    'method': 'ambiguous_detection',
                    'supporting_analyses': sum(len(v) for v in intent_scores.values()),
                    'ambiguity_reason': ",".join(ambiguity_reason) if ambiguity_reason else 'undetermined',
                    'analysis_breakdown': {
                        'basic': basic,
                        'contextual': contextual,
                        'industry': industry,
                        'semantic': semantic,
                        'avg_scores': avg_scores
                    }
                }

            best_confidence = min(best_score, 0.95)  # Cap at 0.95
            supporting_analyses = len(intent_scores[best_intent])

            # Ajuste final de confianza basado en número de análisis de apoyo
            if supporting_analyses >= 2:
                best_confidence = min(1.0, best_confidence + 0.05)
            if supporting_analyses >= 3:
                best_confidence = min(1.0, best_confidence + 0.03)

            return {
                'intent': best_intent,
                'confidence': best_confidence,
                'method': 'combined_analysis',
                'supporting_analyses': supporting_analyses,
                'analysis_breakdown': {
                    'basic': basic,
                    'contextual': contextual,
                    'industry': industry,
                    'semantic': semantic
                }
            }
        
        return {
            'intent': 'unknown', 
            'confidence': 0.4, 
            'method': 'fallback',
            'supporting_analyses': 0
        }

    def _update_conversation_context(self, user_id: str, result: Dict, industry_analysis: Dict):
        """Actualiza el contexto de la conversación para futuras interacciones"""
        context = self.conversation_context[user_id]
        
        # Actualizar intención detectada si hay alta confianza
        if result['confidence'] > self.confidence_thresholds['with_context']:
            context['detected_domain'] = result['intent']
        
        context['last_intent'] = result['intent']
        context['confidence_history'].append(result['confidence'])
        
        # Mantener solo las últimas 10 confianzas en el historial
        if len(context['confidence_history']) > 10:
            context['confidence_history'] = context['confidence_history'][-10:]
        
        # Actualizar pistas de industria
        if industry_analysis['method'].startswith('industry_'):
            industry = industry_analysis['method'].replace('industry_', '')
            context['industry_hints'].add(industry)

    def classify_diagram_type(self, description: str, user_id: str = "default") -> Dict:
        """
        Clasifica el tipo de diagrama basándose en una descripción.
        
        Args:
            description: Descripción textual del sistema/diagrama
            user_id: Identificador del usuario (opcional)
            
        Returns:
            Dict con el resultado de la clasificación
        """
        return self.analyze_conversation(user_id, description, is_follow_up=False)

    def get_user_context(self, user_id: str) -> Optional[Dict]:
        """Obtiene el contexto actual de un usuario específico"""
        return self.conversation_context.get(user_id)
    
    def clear_user_context(self, user_id: str):
        """Limpia el contexto de un usuario específico"""
        if user_id in self.conversation_context:
            del self.conversation_context[user_id]
    
    def get_classification_stats(self) -> Dict:
        """Obtiene estadísticas generales del clasificador"""
        total_users = len(self.conversation_context)
        active_conversations = sum(1 for ctx in self.conversation_context.values() 
                                 if ctx['interaction_count'] > 1)
        
        return {
            'total_users': total_users,
            'active_conversations': active_conversations,
            'conversation_context': self.conversation_context
        }


# Funciones de utilidad para uso rápido
def quick_classify(description: str) -> str:
    """
    Clasificación rápida sin mantener contexto de conversación.
    
    Args:
        description: Descripción textual del diagrama
        
    Returns:
        String con el tipo de diagrama detectado
    """
    classifier = AdvancedDiagramClassifier()
    result = classifier.classify_diagram_type(description)
    return result['intent']

def classify_with_details(description: str) -> Dict:
    """
    Clasificación con detalles completos del análisis.
    
    Args:
        description: Descripción textual del diagrama
        
    Returns:
        Dict con resultado completo y breakdown del análisis
    """
    classifier = AdvancedDiagramClassifier()
    return classifier.classify_diagram_type(description)


# Ejemplos de uso y pruebas
if __name__ == "__main__":
    # Ejemplos de prueba
    test_cases = [
        {
            "description": "Necesito un diagrama con las clases Usuario, Producto y Pedido. Cada clase tiene atributos y métodos específicos.",
            "expected": "diagrama_clases"
        },
        {
            "description": "Quiero mostrar cómo los actores Cliente y Administrador interactúan con el sistema mediante casos de uso como realizar pedido y gestionar inventario.",
            "expected": "diagrama_casos_uso"
        },
        {
            "description": "Sistema de gestión para una universidad con estudiantes, profesores y cursos.",
            "expected": "diagrama_clases"  # Por contexto educativo
        }
    ]
    
    classifier = AdvancedDiagramClassifier()
    
    print(" PRUEBAS DEL CLASIFICADOR AVANZADO")
    print("=" * 60)
    
    for i, test in enumerate(test_cases, 1):
        result = classifier.classify_diagram_type(test["description"], f"test_user_{i}")
        is_correct = result['intent'] == test['expected']
        
        print(f"\n📝 Test {i}:")
        print(f"   Descripción: {test['description'][:80]}...")
        print(f"   Esperado: {test['expected']}")
        print(f"   Obtenido: {result['intent']}")
        print(f"   Confianza: {result['confidence']:.2f}")
        print(f"   Método: {result['method']}")
        print(f"   Análisis de apoyo: {result.get('supporting_analyses', 'N/A')}")
        print(f"   ✅ CORRECTO" if is_correct else "   ❌ INCORRECTO")
    
    print(f"\n Estadísticas: {classifier.get_classification_stats()}")