"""
Sistema de Clasificación Multi-Pasada con Análisis de Confiabilidad
Versión 3.0 - Enero 2026
"""
import psycopg2
import psycopg2.extras
from typing import Dict, List, Tuple, Optional
import re
from collections import defaultdict


class ContextExtractor:
    """
    PASADA 1: Extrae información estructurada de alta confiabilidad
    """
    
    # Mapeo de ciudades y sus variantes
    CIUDADES = {
        'NEIVA': ['neiva', 'nva', 'nv'],
        'TUNJA': ['tunja', 'tja', 'tj'],
        'FLORENCIA': ['florencia', 'fla', 'fl'],
        'PITALITO': ['pitalito', 'pto', 'pt'],
        'BOGOTA': ['bogota', 'bog', 'bg'],
        'FACATATIVA': ['facatativa', 'fac', 'fc'],
        'DUITAMA': ['duitama', 'dui', 'dt']
    }
    
    # Mapeo de departamentos
    DEPARTAMENTOS = {
        'HUILA': ['huila'],
        'BOYACÁ': ['boyaca', 'boyacá'],
        'CAQUETÁ': ['caqueta', 'caquetá'],
        'CUNDINAMARCA': ['cundinamarca']
    }
    
    # Tipos de proveedores
    TIPOS_PROVEEDOR = {
        'TELECOMUNICACIONES': ['movistar', 'claro', 'tigo', 'telecomunicaciones', 'colombia telecomunicaciones'],
        'MEDICAMENTOS': ['farmaquirurgicos', 'cofarma', 'drogueria', 'farmacia'],
        'SERVICIOS_MEDICOS': ['coloproctologia', 'endoscopia', 'cirugia', 'medico', 'clinica'],
        'SERVICIOS_PUBLICOS': ['energia', 'agua', 'gas', 'epm', 'acueducto'],
        'TECNOLOGIA': ['microsoft', 'google', 'aws', 'software', 'sistemas'],
        'TRANSPORTE': ['transporte', 'logistica', 'envios'],
        'ALIMENTOS': ['alimentos', 'restaurante', 'catering']
    }
    
    def extract_context(self, xml_data: Dict, pdf_text: str) -> Dict:
        """
        Extrae contexto estructurado de la factura
        
        Returns:
            Dict con contexto y niveles de confianza
        """
        context = {
            'ciudad': None,
            'departamento': None,
            'tipo_proveedor': None,
            'monto': None,
            'confidence': {}
        }
        
        # 1. Ciudad de la dirección (ALTA CONFIABILIDAD)
        direccion = xml_data.get('cliente', {}).get('direccion', '')
        ciudad = self._extract_city_from_address(direccion, pdf_text)
        if ciudad:
            context['ciudad'] = ciudad
            context['confidence']['ciudad'] = 0.95
        
        # 2. Departamento (ALTA CONFIABILIDAD)
        departamento = self._extract_department(direccion, pdf_text)
        if departamento:
            context['departamento'] = departamento
            context['confidence']['departamento'] = 0.90
        
        # 3. Tipo de proveedor (MEDIA CONFIABILIDAD)
        proveedor = xml_data.get('proveedor', {}).get('nombre', '')
        tipo = self._classify_provider_type(proveedor)
        if tipo:
            context['tipo_proveedor'] = tipo
            context['confidence']['tipo_proveedor'] = 0.75
        
        # 4. Monto (ALTA CONFIABILIDAD)
        valores = xml_data.get('factura', {}).get('valores', {})
        if valores:
            context['monto'] = valores.get('valor_neto', valores.get('total', 0))
            context['confidence']['monto'] = 0.98
        
        return context
    
    def _extract_city_from_address(self, direccion: str, pdf_text: str) -> Optional[str]:
        """Extrae ciudad de la dirección o texto del PDF"""
        # Buscar en dirección primero
        direccion_lower = direccion.lower()
        for ciudad, variantes in self.CIUDADES.items():
            for variante in variantes:
                if variante in direccion_lower:
                    return ciudad
        
        # Si no encuentra en dirección, buscar en PDF
        pdf_lower = pdf_text.lower()
        for ciudad, variantes in self.CIUDADES.items():
            for variante in variantes:
                if variante in pdf_lower:
                    return ciudad
        
        return None
    
    def _extract_department(self, direccion: str, pdf_text: str) -> Optional[str]:
        """Extrae departamento de la dirección o texto"""
        text = (direccion + ' ' + pdf_text).lower()
        
        for departamento, variantes in self.DEPARTAMENTOS.items():
            for variante in variantes:
                if variante in text:
                    return departamento
        
        return None
    
    def _classify_provider_type(self, proveedor: str) -> Optional[str]:
        """Clasifica tipo de proveedor"""
        proveedor_lower = proveedor.lower()
        
        for tipo, keywords in self.TIPOS_PROVEEDOR.items():
            for keyword in keywords:
                if keyword in proveedor_lower:
                    return tipo
        
        return None


class SpecificKeywordClassifier:
    """
    PASADA 2: Clasifica usando solo keywords específicas (únicas por unidad)
    """
    
    def __init__(self, db_config: Dict):
        self.db_config = db_config
    
    def classify(self, text: str, context: Dict) -> Dict:
        """
        Clasifica usando keywords específicas
        
        Returns:
            Dict con scores por unidad y confiabilidad
        """
        conn = psycopg2.connect(**self.db_config)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        try:
            # Obtener solo keywords únicas por unidad
            cursor.execute("""
                SELECT 
                    uk.unidad_funcional_id,
                    uf.nombre as unidad_nombre,
                    uf.codigo as unidad_codigo,
                    uf.sucursal_id,
                    uk.keyword,
                    uk.peso
                FROM ocr_unidad_keywords uk
                JOIN unidades_funcionales uf ON uf.id = uk.unidad_funcional_id
                WHERE uk.activo = TRUE
                AND uk.keyword IN (
                    SELECT keyword 
                    FROM ocr_unidad_keywords 
                    WHERE activo = TRUE
                    GROUP BY keyword 
                    HAVING COUNT(DISTINCT unidad_funcional_id) = 1
                )
                ORDER BY uk.peso DESC
            """)
            
            unique_keywords = cursor.fetchall()
            
            # Agrupar por unidad
            scores = defaultdict(lambda: {
                'score': 0,
                'matched_keywords': [],
                'unidad_nombre': '',
                'unidad_codigo': '',
                'sucursal_id': None
            })
            
            for row in unique_keywords:
                keyword = row['keyword'].upper()
                if keyword in text:
                    unidad_id = row['unidad_funcional_id']
                    
                    # Peso aumentado para keywords únicas (x10)
                    peso = row['peso'] * 10
                    
                    scores[unidad_id]['score'] += peso
                    scores[unidad_id]['matched_keywords'].append(keyword)
                    scores[unidad_id]['unidad_nombre'] = row['unidad_nombre']
                    scores[unidad_id]['unidad_codigo'] = row['unidad_codigo']
                    scores[unidad_id]['sucursal_id'] = row['sucursal_id']
            
            # Calcular confiabilidad para cada unidad
            results = {}
            for unidad_id, data in scores.items():
                confidence = self._calculate_confidence(
                    data['score'],
                    data['matched_keywords'],
                    context,
                    data['sucursal_id']
                )
                
                results[unidad_id] = {
                    'score': data['score'],
                    'confidence': confidence,
                    'matched_keywords': data['matched_keywords'],
                    'unidad_nombre': data['unidad_nombre'],
                    'unidad_codigo': data['unidad_codigo'],
                    'sucursal_id': data['sucursal_id']
                }
            
            return results
            
        finally:
            cursor.close()
            conn.close()
    
    def _calculate_confidence(self, score: int, matched_keywords: List[str], 
                            context: Dict, sucursal_id: int) -> float:
        """
        Calcula confiabilidad basada en:
        - Número de keywords coincidentes
        - Score total
        - Coherencia con contexto
        """
        confidence = 0.0
        
        # Base: número de keywords (max 0.4)
        num_keywords = len(matched_keywords)
        if num_keywords >= 5:
            confidence += 0.4
        elif num_keywords >= 3:
            confidence += 0.3
        elif num_keywords >= 1:
            confidence += 0.2
        
        # Score relativo (max 0.3)
        if score >= 100:
            confidence += 0.3
        elif score >= 50:
            confidence += 0.2
        elif score >= 20:
            confidence += 0.1
        
        # Coherencia con contexto (max 0.3)
        if self._is_coherent_with_context(sucursal_id, context):
            confidence += 0.3
        
        return min(confidence, 1.0)
    
    def _is_coherent_with_context(self, sucursal_id: int, context: Dict) -> bool:
        """Verifica si la sucursal es coherente con el contexto"""
        # Mapeo de ciudades a sucursales
        ciudad_sucursal = {
            'NEIVA': 4,
            'TUNJA': 5,
            'FLORENCIA': 6,
            'PITALITO': 7,
            'BOGOTA': 8,
            'FACATATIVA': 9,
            'DUITAMA': 10
        }
        
        ciudad = context.get('ciudad')
        if ciudad and ciudad in ciudad_sucursal:
            return ciudad_sucursal[ciudad] == sucursal_id
        
        return True  # Si no hay contexto de ciudad, asumir coherente


class SemanticAnalyzer:
    """
    PASADA 3: Analiza el contexto semántico del texto
    """
    
    # Patrones semánticos por categoría
    PATTERNS = {
        'ADMINISTRACION': [
            'servicios administrativos',
            'gestion administrativa',
            'servicios generales',
            'telecomunicaciones',
            'servicios publicos',
            'internet',
            'telefonia',
            'energia electrica',
            'agua potable',
            'aseo',
            'vigilancia',
            'mantenimiento'
        ],
        'ALMACEN': [
            'medicamentos',
            'insumos medicos',
            'material quirurgico',
            'dispositivos medicos',
            'suministros',
            'material de curacion',
            'instrumental',
            'equipos medicos'
        ],
        'CONTABILIDAD': [
            'honorarios medicos',
            'servicios profesionales medicos',
            'consultas medicas',
            'procedimientos medicos',
            'atencion medica',
            'cirugia',
            'hospitalizacion',
            'urgencias'
        ]
    }
    
    def analyze(self, text: str, context: Dict) -> Dict:
        """
        Analiza patrones semánticos en el texto
        
        Returns:
            Dict con scores por categoría
        """
        text_lower = text.lower()
        results = {}
        
        for categoria, frases in self.PATTERNS.items():
            score = 0
            matched = []
            
            for frase in frases:
                if frase in text_lower:
                    # Peso alto para frases completas
                    score += 20
                    matched.append(frase)
            
            if score > 0:
                # Confiabilidad basada en número de coincidencias
                confidence = min(len(matched) * 0.2, 0.8)  # Max 80%
                
                results[categoria] = {
                    'score': score,
                    'confidence': confidence,
                    'matched_patterns': matched
                }
        
        return results


class MultiPassClassifier:
    """
    PASADA 4: Orquesta las 3 pasadas y toma decisión final
    """
    
    def __init__(self, db_config: Dict):
        self.db_config = db_config
        self.context_extractor = ContextExtractor()
        self.keyword_classifier = SpecificKeywordClassifier(db_config)
        self.semantic_analyzer = SemanticAnalyzer()
    
    def classify(self, xml_data: Dict, pdf_text: str) -> Tuple[Dict, Dict]:
        """
        Clasifica factura usando sistema multi-pasada
        
        Returns:
            Tuple (sucursal_result, unidad_result)
        """
        # PASADA 1: Extraer contexto
        context = self.context_extractor.extract_context(xml_data, pdf_text)
        
        # PASADA 2: Clasificar con keywords específicas
        keyword_results = self.keyword_classifier.classify(pdf_text, context)
        
        # PASADA 3: Análisis semántico
        semantic_results = self.semantic_analyzer.analyze(pdf_text, context)
        
        # PASADA 4: Validación cruzada y decisión
        sucursal_result = self._classify_sucursal(context, keyword_results)
        unidad_result = self._classify_unidad(context, keyword_results, semantic_results)
        
        return sucursal_result, unidad_result
    
    def _classify_sucursal(self, context: Dict, keyword_results: Dict) -> Dict:
        """Clasifica sucursal basándose principalmente en contexto"""
        # Mapeo de ciudades a sucursales
        ciudad_sucursal = {
            'NEIVA': {'id': 4, 'nombre': 'Clinica Medilaser S.A.S - Neiva', 'codigo': '00004'},
            'TUNJA': {'id': 5, 'nombre': 'Clinica Medilaser S.A.S - Tunja', 'codigo': '00005'},
            'FLORENCIA': {'id': 6, 'nombre': 'Clinica Medilaser S.A.S - Florencia', 'codigo': '00006'},
            'PITALITO': {'id': 7, 'nombre': 'Clinica Medilaser S.A.S - Pitalito', 'codigo': '00007'},
            'BOGOTA': {'id': 8, 'nombre': 'Clinica Medilaser S.A.S - Bogota', 'codigo': '00008'},
            'FACATATIVA': {'id': 9, 'nombre': 'Clinica Medilaser S.A.S - Facatativa', 'codigo': '00009'},
            'DUITAMA': {'id': 10, 'nombre': 'Clinica Medilaser S.A.S - Duitama', 'codigo': '00010'}
        }
        
        ciudad = context.get('ciudad')
        
        if ciudad and ciudad in ciudad_sucursal:
            sucursal = ciudad_sucursal[ciudad]
            confidence = context.get('confidence', {}).get('ciudad', 0.95)
            
            return {
                'success': True,
                'id': sucursal['id'],
                'nombre': sucursal['nombre'],
                'codigo': sucursal['codigo'],
                'confidence': confidence,
                'score': 100,
                'keywords': [ciudad],
                'context': context,
                'requires_validation': confidence < 0.80
            }
        
        # Si no hay contexto de ciudad, usar keywords
        return {
            'success': False,
            'id': None,
            'nombre': 'No clasificado',
            'confidence': 0.0,
            'score': 0,
            'keywords': [],
            'context': context,
            'requires_validation': True
        }
    
    def _classify_unidad(self, context: Dict, keyword_results: Dict, 
                        semantic_results: Dict) -> Dict:
        """Clasifica unidad funcional combinando todas las pasadas"""
        candidates = []
        
        # Filtrar por sucursal si hay contexto
        ciudad = context.get('ciudad')
        if ciudad:
            ciudad_sucursal = {
                'NEIVA': 4, 'TUNJA': 5, 'FLORENCIA': 6, 'PITALITO': 7,
                'BOGOTA': 8, 'FACATATIVA': 9, 'DUITAMA': 10
            }
            sucursal_id = ciudad_sucursal.get(ciudad)
            
            if sucursal_id:
                # Filtrar solo unidades de esa sucursal
                keyword_results = {
                    k: v for k, v in keyword_results.items()
                    if v['sucursal_id'] == sucursal_id
                }
        
        # Combinar scores de keywords y semántica
        for unidad_id, kw_data in keyword_results.items():
            combined_score = kw_data['score']
            combined_confidence = kw_data['confidence']
            semantic_matches = []
            
            # Agregar score semántico si existe
            categoria = self._get_categoria_by_nombre(kw_data['unidad_nombre'])
            if categoria in semantic_results:
                sem_data = semantic_results[categoria]
                combined_score += sem_data['score']
                combined_confidence = (combined_confidence + sem_data['confidence']) / 2
                semantic_matches = sem_data['matched_patterns']
            
            # Bonus por coherencia con contexto
            if kw_data['sucursal_id'] and ciudad:
                combined_score += 50
                combined_confidence = min(combined_confidence + 0.1, 1.0)
            
            candidates.append({
                'unidad_id': unidad_id,
                'unidad_nombre': kw_data['unidad_nombre'],
                'unidad_codigo': kw_data['unidad_codigo'],
                'score': combined_score,
                'confidence': combined_confidence,
                'keyword_matches': kw_data['matched_keywords'],
                'semantic_matches': semantic_matches
            })
        
        # Ordenar por confiabilidad y score
        candidates.sort(key=lambda x: (x['confidence'], x['score']), reverse=True)
        
        if not candidates:
            return {
                'success': False,
                'id': None,
                'nombre': 'No clasificado',
                'confidence': 0.0,
                'score': 0,
                'keywords': [],
                'context': context,
                'requires_validation': True,
                'reason': 'No se encontraron coincidencias'
            }
        
        best = candidates[0]
        second_best = candidates[1] if len(candidates) > 1 else None
        
        # Verificar si hay empate o ambigüedad
        requires_validation = False
        if second_best:
            score_diff = best['score'] - second_best['score']
            conf_diff = best['confidence'] - second_best['confidence']
            
            # Si están muy cerca, requiere validación
            if score_diff < 20 or conf_diff < 0.15:
                requires_validation = True
        
        # Verificar confiabilidad mínima
        if best['confidence'] < 0.70:
            requires_validation = True
        
        return {
            'success': True,
            'id': best['unidad_id'],
            'nombre': best['unidad_nombre'],
            'codigo': best['unidad_codigo'],
            'confidence': best['confidence'],
            'score': best['score'],
            'keywords': best['keyword_matches'],
            'semantic_matches': best['semantic_matches'],
            'context': context,
            'requires_validation': requires_validation,
            'alternatives': [
                {
                    'id': c['unidad_id'],
                    'nombre': c['unidad_nombre'],
                    'score': c['score'],
                    'confidence': c['confidence']
                }
                for c in candidates[1:3]
            ] if len(candidates) > 1 else []
        }
    
    def _get_categoria_by_nombre(self, nombre: str) -> Optional[str]:
        """Obtiene categoría semántica basada en el nombre de la unidad"""
        nombre_lower = nombre.lower()
        
        if 'administracion' in nombre_lower or 'administración' in nombre_lower:
            return 'ADMINISTRACION'
        elif 'almacen' in nombre_lower or 'almacén' in nombre_lower:
            return 'ALMACEN'
        elif 'contabilidad' in nombre_lower:
            return 'CONTABILIDAD'
        
        return None
