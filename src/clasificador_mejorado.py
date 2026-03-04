"""
Clasificador mejorado que usa las tablas existentes:
- ocr_proveedor_config (con unidades funcionales)
- ocr_sinonimos (con peso)
- ocr_unidad_keywords (existente)

Implementa scoring matemático para mejor precisión
Optimizado con caché y utilidades auxiliares
"""
import psycopg2.extras
from typing import Dict, Tuple, Optional, List
from .database import db
from .proveedor_matcher import ProveedorMatcher
from .utils.clasificacion_utils import (
    SucursalDetector,
    ProveedorAnalyzer,
    ScoreCalculator,
    TextNormalizer,
    UnidadFuncionalHelper
)
from .utils.cache_manager import (
    get_proveedor_cache,
    get_unidad_cache,
    cached
)
import logging

logger = logging.getLogger(__name__)


class ClasificadorMejorado:
    """
    Clasificador que usa análisis multi-paso con scoring matemático
    """
    
    def __init__(self, db_config: Optional[Dict] = None):
        """Inicializa el clasificador"""
        self.proveedor_matcher = ProveedorMatcher(db_config)
    
    def classify(self, xml_data: Dict, pdf_text: str) -> Tuple[Dict, Dict]:
        """
        Clasifica factura usando análisis multi-paso con scoring matemático
        
        PASO 1: Identificar proveedor
        PASO 2: Identificar sucursal
        PASO 3: Calcular scores para cada unidad funcional
        PASO 4: Seleccionar mejor match con validación
        
        Args:
            xml_data: Datos extraídos del XML
            pdf_text: Texto extraído del PDF (en mayúsculas)
        
        Returns:
            Tuple (sucursal_result, unidad_result)
        """
        logger.info("=== CLASIFICACIÓN MEJORADA - INICIO ===")
        
        # PASO 1: Identificar proveedor
        proveedor_info = self._identificar_proveedor(xml_data)
        logger.info(f"PASO 1 - Proveedor: {proveedor_info.get('matched', False)} - "
                   f"{proveedor_info.get('nombre', 'N/A')}")
        
        # PASO 2: Identificar sucursal
        sucursal_result = self._identificar_sucursal(xml_data, pdf_text)
        logger.info(f"PASO 2 - Sucursal: {sucursal_result.get('success', False)} - "
                   f"{sucursal_result.get('nombre', 'N/A')}")
        
        # PASO 3: Clasificar unidad funcional con scoring
        unidad_result = self._clasificar_con_scoring(
            proveedor_info,
            sucursal_result,
            pdf_text
        )
        logger.info(f"PASO 3 - Unidad: {unidad_result.get('success', False)} - "
                   f"{unidad_result.get('nombre', 'N/A')} "
                   f"(score: {unidad_result.get('score_total', 0):.1f})")
        
        logger.info("=== CLASIFICACIÓN MEJORADA - FIN ===")
        
        return sucursal_result, unidad_result
    
    def _identificar_proveedor(self, xml_data: Dict) -> Dict:
        """
        PASO 1: Identifica el proveedor usando ocr_proveedor_config
        """
        proveedor_data = xml_data.get('proveedor', {})
        
        if not proveedor_data:
            return {'matched': False, 'proveedor_id': None}
        
        # Usar el matcher existente
        match_result = self.proveedor_matcher.match_proveedor(proveedor_data)
        
        if match_result['matched']:
            # Obtener configuración del proveedor
            with db.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                
                cursor.execute("""
                    SELECT 
                        p.id,
                        p.nit,
                        p.razon_social,
                        pc.tipo_clasificacion,
                        pc.prioridad_clasificacion,
                        pc.unidades_funcionales_ids,
                        pc.alias
                    FROM proveedores p
                    JOIN ocr_proveedor_config pc ON pc.proveedor_id = p.id
                    WHERE p.id = %s AND pc.activo = TRUE
                """, (match_result['proveedor_id'],))
                
                config = cursor.fetchone()
                cursor.close()
                
                if config:
                    return {
                        'matched': True,
                        'proveedor_id': config['id'],
                        'nit': config['nit'],
                        'nombre': config['razon_social'],
                        'tipo_clasificacion': config['tipo_clasificacion'],
                        'prioridad': config['prioridad_clasificacion'],
                        'unidades_config': config['unidades_funcionales_ids'] or [],
                        'alias': config['alias'] or [],
                        'confidence': match_result['confidence']
                    }
        
        return {
            'matched': False,
            'proveedor_id': None,
            'nit': proveedor_data.get('nit'),
            'nombre': proveedor_data.get('nombre')
        }
    
    def _identificar_sucursal(self, xml_data: Dict, pdf_text: str) -> Dict:
        """
        PASO 2: Identifica la sucursal usando múltiples estrategias
        
        Estrategias (en orden de prioridad):
        1. Campo Note del XML (ej: "OC115899-TJA")
        2. Ciudad del cliente
        3. Sinónimos en la BD
        4. Búsqueda en texto PDF
        """
        sucursal_codigo = None
        confidence = 0.0
        metodo = None
        
        # Estrategia 1: Extraer del campo Note del XML
        factura = xml_data.get('factura', {})
        note = factura.get('note') or factura.get('notas')
        
        if note:
            codigo_note = SucursalDetector.extraer_de_note_xml(note)
            if codigo_note:
                sucursal_codigo = codigo_note
                confidence = 0.98
                metodo = 'note_xml'
                logger.info(f"Sucursal detectada desde Note XML: {sucursal_codigo}")
        
        # Estrategia 2: Ciudad del cliente
        if not sucursal_codigo:
            cliente = xml_data.get('cliente', {})
            ciudad = cliente.get('ciudad', '').upper().strip()
            
            if ciudad:
                codigo_ciudad = SucursalDetector.extraer_de_ciudad(ciudad)
                if codigo_ciudad:
                    sucursal_codigo = codigo_ciudad
                    confidence = 0.95
                    metodo = 'ciudad_cliente'
                    logger.info(f"Sucursal detectada desde ciudad: {ciudad} -> {sucursal_codigo}")
        
        # Estrategia 3: Buscar en texto PDF
        if not sucursal_codigo:
            codigo_texto = SucursalDetector.extraer_de_texto(pdf_text)
            if codigo_texto:
                sucursal_codigo = codigo_texto
                confidence = 0.85
                metodo = 'texto_pdf'
                logger.info(f"Sucursal detectada desde texto PDF: {sucursal_codigo}")
        
        # Estrategia 4: Sinónimos en BD (fallback)
        if not sucursal_codigo:
            with db.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                
                cursor.execute("""
                    SELECT palabra_original, peso
                    FROM ocr_sinonimos
                    WHERE tipo = 'sucursal'
                        AND activo = TRUE
                        AND (
                            UPPER(%s) LIKE '%%' || UPPER(palabra_original) || '%%'
                            OR UPPER(%s) LIKE '%%' || UPPER(sinonimo) || '%%'
                        )
                    ORDER BY peso DESC
                    LIMIT 1
                """, (pdf_text, pdf_text))
                
                sinonimo = cursor.fetchone()
                cursor.close()
                
                if sinonimo:
                    ciudad_encontrada = sinonimo['palabra_original'].upper()
                    codigo_sinonimo = SucursalDetector.extraer_de_ciudad(ciudad_encontrada)
                    if codigo_sinonimo:
                        sucursal_codigo = codigo_sinonimo
                        confidence = 0.75
                        metodo = 'sinonimo_bd'
                        logger.info(f"Sucursal detectada desde sinónimo: {sucursal_codigo}")
        
        # Obtener información completa de la sucursal
        if sucursal_codigo:
            with db.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                
                cursor.execute("""
                    SELECT id, nombre, codigo, activo
                    FROM sucursales
                    WHERE codigo = %s AND activo = TRUE
                """, (sucursal_codigo,))
                
                sucursal = cursor.fetchone()
                cursor.close()
                
                if sucursal:
                    return {
                        'success': True,
                        'id': sucursal['id'],
                        'nombre': sucursal['nombre'],
                        'codigo': sucursal['codigo'],
                        'confidence': confidence,
                        'method': metodo
                    }
        
        logger.warning("No se pudo identificar la sucursal")
        return {
            'success': False,
            'id': None,
            'nombre': None,
            'confidence': 0.0,
            'method': 'none'
        }
    
    def _clasificar_con_scoring(self, proveedor_info: Dict, 
                                sucursal_result: Dict, 
                                pdf_text: str) -> Dict:
        """
        PASO 3: Clasifica usando scoring matemático
        
        Score = Score_Keywords + Score_Sinónimos + Score_Proveedor
        
        Donde:
        - Score_Keywords: Suma de pesos de keywords que coinciden
        - Score_Sinónimos: Suma de pesos de sinónimos que coinciden
        - Score_Proveedor: Prioridad si el proveedor está configurado para esa unidad
        """
        with db.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # 1. Si hay proveedor con configuración específica, priorizar esas unidades
            if proveedor_info['matched'] and proveedor_info.get('unidades_config'):
                unidades_candidatas = self._obtener_unidades_de_proveedor(
                    proveedor_info,
                    sucursal_result.get('id')
                )
                
                if unidades_candidatas:
                    # Calcular scores para unidades del proveedor
                    mejor_unidad = self._calcular_mejor_score(
                        cursor,
                        unidades_candidatas,
                        pdf_text,
                        proveedor_info['proveedor_id']
                    )
                    
                    if mejor_unidad and mejor_unidad['score_total'] > 100:
                        cursor.close()
                        return mejor_unidad
            
            # 2. Si no hay match por proveedor, buscar por sucursal + keywords
            if sucursal_result['success']:
                cursor.execute("""
                    SELECT id, nombre, codigo, sucursal_id
                    FROM unidades_funcionales
                    WHERE sucursal_id = %s AND activo = TRUE
                """, (sucursal_result['id'],))
                
                unidades_sucursal = cursor.fetchall()
                
                if unidades_sucursal:
                    unidades_ids = [u['id'] for u in unidades_sucursal]
                    mejor_unidad = self._calcular_mejor_score(
                        cursor,
                        unidades_ids,
                        pdf_text,
                        proveedor_info.get('proveedor_id')
                    )
                    
                    if mejor_unidad:
                        cursor.close()
                        return mejor_unidad
            
            # 3. Fallback: buscar en todas las unidades
            cursor.execute("""
                SELECT id FROM unidades_funcionales WHERE activo = TRUE
            """)
            todas_unidades = [row['id'] for row in cursor.fetchall()]
            
            mejor_unidad = self._calcular_mejor_score(
                cursor,
                todas_unidades,
                pdf_text,
                proveedor_info.get('proveedor_id')
            )
            
            cursor.close()
            
            if mejor_unidad:
                mejor_unidad['method'] = 'scoring_global'
                return mejor_unidad
        
        return {
            'success': False,
            'id': None,
            'nombre': None,
            'confidence': 0.0,
            'score_total': 0
        }
    
    def _obtener_unidades_de_proveedor(self, proveedor_info: Dict, 
                                       sucursal_id: Optional[int]) -> List[int]:
        """
        Obtiene IDs de unidades funcionales configuradas para el proveedor
        Prioriza las que coinciden con la sucursal
        """
        unidades_config = proveedor_info.get('unidades_config', [])
        
        if not unidades_config:
            return []
        
        # Si es un array simple de IDs
        if isinstance(unidades_config, list) and unidades_config:
            if isinstance(unidades_config[0], int):
                return unidades_config
            
            # Si es array de objetos con configuración
            unidades_ids = []
            for config in unidades_config:
                if isinstance(config, dict):
                    unidad_id = config.get('unidad_id')
                    config_sucursal_id = config.get('sucursal_id')
                    
                    # Priorizar unidades de la sucursal correcta
                    if sucursal_id and config_sucursal_id == sucursal_id:
                        unidades_ids.insert(0, unidad_id)
                    else:
                        unidades_ids.append(unidad_id)
            
            return unidades_ids
        
        return []
    
    def _calcular_mejor_score(self, cursor, unidades_ids: List[int], 
                             texto: str, proveedor_id: Optional[int]) -> Optional[Dict]:
        """
        Calcula scores para todas las unidades y retorna la mejor
        """
        mejor_score = 0
        mejor_unidad = None
        
        for unidad_id in unidades_ids:
            # Calcular score usando la función SQL
            cursor.execute("""
                SELECT * FROM calcular_score_clasificacion(%s, %s, %s)
            """, (texto, unidad_id, proveedor_id))
            
            score_result = cursor.fetchone()
            
            if score_result and score_result['score_total'] > mejor_score:
                mejor_score = score_result['score_total']
                
                # Obtener información de la unidad
                cursor.execute("""
                    SELECT uf.id, uf.nombre, uf.codigo, uf.sucursal_id, s.nombre as sucursal_nombre
                    FROM unidades_funcionales uf
                    LEFT JOIN sucursales s ON s.id = uf.sucursal_id
                    WHERE uf.id = %s
                """, (unidad_id,))
                
                unidad_info = cursor.fetchone()
                
                if unidad_info:
                    mejor_unidad = {
                        'success': True,
                        'id': unidad_info['id'],
                        'nombre': unidad_info['nombre'],
                        'codigo': unidad_info['codigo'],
                        'sucursal_id': unidad_info['sucursal_id'],
                        'sucursal_nombre': unidad_info['sucursal_nombre'],
                        'score_total': float(score_result['score_total']),
                        'score_keywords': float(score_result['score_keywords']),
                        'score_sinonimos': float(score_result['score_sinonimos']),
                        'score_proveedor': float(score_result['score_proveedor']),
                        'keywords_matched': score_result['keywords_matched'] or [],
                        'confidence': float(score_result['confidence']),
                        'method': 'scoring_matematico'
                    }
        
        return mejor_unidad
