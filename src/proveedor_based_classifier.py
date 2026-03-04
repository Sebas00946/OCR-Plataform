"""
Clasificador basado en proveedor con análisis multi-paso
Implementa toma de decisiones inteligente basada en:
1. Identificación del proveedor (NIT, nombre)
2. Relación proveedor -> unidad funcional
3. Contexto de sucursal (ciudad, dirección)
4. Keywords específicas como fallback
"""
import psycopg2.extras
from typing import Dict, Tuple, Optional, List
from .database import db
from .proveedor_matcher import ProveedorMatcher
import logging

logger = logging.getLogger(__name__)


class ProveedorBasedClassifier:
    """
    Clasificador que prioriza la relación proveedor -> unidad funcional
    con análisis multi-paso para mayor precisión
    """
    
    def __init__(self, db_config: Optional[Dict] = None):
        """Inicializa el clasificador"""
        self.proveedor_matcher = ProveedorMatcher(db_config)
    
    def classify(self, xml_data: Dict, pdf_text: str) -> Tuple[Dict, Dict]:
        """
        Clasifica factura usando análisis multi-paso:
        
        PASO 1: Identificar proveedor
        PASO 2: Identificar sucursal (por ciudad/dirección del cliente)
        PASO 3: Buscar relación proveedor -> unidad funcional
        PASO 4: Validar con keywords si es necesario
        
        Args:
            xml_data: Datos extraídos del XML
            pdf_text: Texto extraído del PDF (en mayúsculas)
        
        Returns:
            Tuple (sucursal_result, unidad_result)
        """
        logger.info("=== INICIO CLASIFICACIÓN MULTI-PASO ===")
        
        # PASO 1: Identificar proveedor
        proveedor_info = self._identificar_proveedor(xml_data)
        logger.info(f"PASO 1 - Proveedor: {proveedor_info.get('matched', False)}")
        
        # PASO 2: Identificar sucursal
        sucursal_result = self._identificar_sucursal(xml_data, pdf_text)
        logger.info(f"PASO 2 - Sucursal: {sucursal_result.get('success', False)} - {sucursal_result.get('nombre', 'N/A')}")
        
        # PASO 3: Clasificar unidad funcional
        unidad_result = self._clasificar_unidad_funcional(
            proveedor_info, 
            sucursal_result, 
            pdf_text
        )
        logger.info(f"PASO 3 - Unidad: {unidad_result.get('success', False)} - {unidad_result.get('nombre', 'N/A')}")
        
        # PASO 4: Validación cruzada
        sucursal_result, unidad_result = self._validar_coherencia(
            sucursal_result, 
            unidad_result, 
            proveedor_info
        )
        
        logger.info("=== FIN CLASIFICACIÓN MULTI-PASO ===")
        
        return sucursal_result, unidad_result
    
    def _identificar_proveedor(self, xml_data: Dict) -> Dict:
        """
        PASO 1: Identifica el proveedor de la factura
        
        Returns:
            {
                'matched': bool,
                'proveedor_id': int,
                'confidence': float,
                'nit': str,
                'nombre': str,
                'categoria': str
            }
        """
        proveedor_data = xml_data.get('proveedor', {})
        
        if not proveedor_data:
            return {'matched': False, 'proveedor_id': None, 'confidence': 0.0}
        
        # Usar el matcher existente
        match_result = self.proveedor_matcher.match_proveedor(proveedor_data)
        
        if match_result['matched']:
            proveedor_db = match_result['proveedor_db']
            
            # Obtener categoría del proveedor
            with db.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                
                cursor.execute("""
                    SELECT 
                        p.id,
                        p.nit,
                        p.razon_social,
                        p.nombre_comercial,
                        pc.nombre as categoria,
                        pc.unidad_funcional_default
                    FROM proveedores p
                    LEFT JOIN proveedor_categorias pc ON pc.id = p.categoria_id
                    WHERE p.id = %s
                """, (match_result['proveedor_id'],))
                
                proveedor_completo = cursor.fetchone()
                cursor.close()
                
                if proveedor_completo:
                    return {
                        'matched': True,
                        'proveedor_id': proveedor_completo['id'],
                        'confidence': match_result['confidence'],
                        'nit': proveedor_completo['nit'],
                        'nombre': proveedor_completo['razon_social'],
                        'categoria': proveedor_completo['categoria'],
                        'unidad_default': proveedor_completo['unidad_funcional_default'],
                        'match_method': match_result['match_method']
                    }
        
        return {
            'matched': False,
            'proveedor_id': None,
            'confidence': 0.0,
            'nit': proveedor_data.get('nit'),
            'nombre': proveedor_data.get('nombre')
        }
    
    def _identificar_sucursal(self, xml_data: Dict, pdf_text: str) -> Dict:
        """
        PASO 2: Identifica la sucursal basándose en datos del cliente
        
        Busca en:
        - Ciudad del cliente (xml_data['cliente']['ciudad'])
        - Dirección del cliente
        - Keywords de ciudad en el texto
        """
        cliente = xml_data.get('cliente', {})
        ciudad = cliente.get('ciudad', '').upper().strip()
        
        # Mapeo de ciudades a sucursales
        ciudad_sucursal_map = {
            'NEIVA': 'NVA',
            'TUNJA': 'TJA', 
            'FLORENCIA': 'FLA',
            'PITALITO': 'PTO',
            'BOGOTA': 'BOG',
            'FACATATIVA': 'FAC',
            'DUITAMA': 'DUI',
            'CARTAGENA': 'KTA',
            'PUERTO ASIS': 'PTO',
            'PUERTO ASÍS': 'PTO'
        }
        
        # Buscar ciudad en el mapeo
        sucursal_codigo = None
        confidence = 0.0
        
        if ciudad and ciudad in ciudad_sucursal_map:
            sucursal_codigo = ciudad_sucursal_map[ciudad]
            confidence = 0.95
        else:
            # Buscar en el texto si no está en XML
            for ciudad_nombre, codigo in ciudad_sucursal_map.items():
                if ciudad_nombre in pdf_text:
                    sucursal_codigo = codigo
                    confidence = 0.75
                    break
        
        if sucursal_codigo:
            # Obtener información completa de la sucursal
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
                        'ciudad': ciudad,
                        'method': 'ciudad_cliente'
                    }
        
        return {
            'success': False,
            'id': None,
            'nombre': None,
            'codigo': None,
            'confidence': 0.0,
            'ciudad': ciudad
        }
    
    def _clasificar_unidad_funcional(self, proveedor_info: Dict, 
                                     sucursal_result: Dict, 
                                     pdf_text: str) -> Dict:
        """
        PASO 3: Clasifica la unidad funcional
        
        Prioridad:
        1. Relación directa proveedor -> unidad funcional (específica por sucursal)
        2. Relación proveedor -> unidad funcional (general, todas las sucursales)
        3. Categoría del proveedor -> unidad funcional default
        4. Keywords como fallback
        """
        if not proveedor_info['matched']:
            # Si no hay proveedor, usar keywords
            return self._clasificar_por_keywords(sucursal_result, pdf_text)
        
        proveedor_id = proveedor_info['proveedor_id']
        sucursal_id = sucursal_result.get('id') if sucursal_result['success'] else None
        
        with db.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # 1. Buscar relación específica (proveedor + sucursal)
            if sucursal_id:
                cursor.execute("""
                    SELECT 
                        puf.id,
                        puf.unidad_funcional_id,
                        uf.nombre as unidad_nombre,
                        uf.codigo as unidad_codigo,
                        puf.prioridad,
                        puf.notas
                    FROM proveedor_unidad_funcional puf
                    JOIN unidades_funcionales uf ON uf.id = puf.unidad_funcional_id
                    WHERE puf.proveedor_id = %s
                        AND puf.sucursal_id = %s
                        AND puf.activo = TRUE
                        AND uf.activo = TRUE
                    ORDER BY puf.prioridad DESC
                    LIMIT 1
                """, (proveedor_id, sucursal_id))
                
                result = cursor.fetchone()
                
                if result:
                    cursor.close()
                    return {
                        'success': True,
                        'id': result['unidad_funcional_id'],
                        'nombre': result['unidad_nombre'],
                        'codigo': result['unidad_codigo'],
                        'confidence': 0.95,
                        'score': result['prioridad'],
                        'method': 'proveedor_sucursal_especifico',
                        'proveedor_id': proveedor_id,
                        'notas': result['notas']
                    }
            
            # 2. Buscar relación general (proveedor, cualquier sucursal)
            cursor.execute("""
                SELECT 
                    puf.id,
                    puf.unidad_funcional_id,
                    uf.nombre as unidad_nombre,
                    uf.codigo as unidad_codigo,
                    uf.sucursal_id,
                    puf.prioridad,
                    puf.notas
                FROM proveedor_unidad_funcional puf
                JOIN unidades_funcionales uf ON uf.id = puf.unidad_funcional_id
                WHERE puf.proveedor_id = %s
                    AND puf.activo = TRUE
                    AND uf.activo = TRUE
                ORDER BY 
                    CASE WHEN uf.sucursal_id = %s THEN 0 ELSE 1 END,
                    puf.prioridad DESC
                LIMIT 1
            """, (proveedor_id, sucursal_id))
            
            result = cursor.fetchone()
            
            if result:
                cursor.close()
                return {
                    'success': True,
                    'id': result['unidad_funcional_id'],
                    'nombre': result['unidad_nombre'],
                    'codigo': result['unidad_codigo'],
                    'confidence': 0.90,
                    'score': result['prioridad'],
                    'method': 'proveedor_general',
                    'proveedor_id': proveedor_id,
                    'notas': result['notas']
                }
            
            cursor.close()
        
        # 3. Usar categoría del proveedor
        if proveedor_info.get('unidad_default'):
            return self._buscar_unidad_por_nombre(
                proveedor_info['unidad_default'], 
                sucursal_result.get('id'),
                confidence=0.75,
                method='categoria_proveedor'
            )
        
        # 4. Fallback a keywords
        return self._clasificar_por_keywords(sucursal_result, pdf_text)
    
    def _buscar_unidad_por_nombre(self, nombre_unidad: str, sucursal_id: Optional[int],
                                   confidence: float = 0.75, method: str = 'default') -> Dict:
        """Busca unidad funcional por nombre parcial"""
        with db.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            cursor.execute("""
                SELECT id, nombre, codigo, sucursal_id
                FROM unidades_funcionales
                WHERE nombre ILIKE %s
                    AND activo = TRUE
                    AND (%s IS NULL OR sucursal_id = %s)
                ORDER BY 
                    CASE WHEN sucursal_id = %s THEN 0 ELSE 1 END
                LIMIT 1
            """, (f'%{nombre_unidad}%', sucursal_id, sucursal_id, sucursal_id))
            
            result = cursor.fetchone()
            cursor.close()
            
            if result:
                return {
                    'success': True,
                    'id': result['id'],
                    'nombre': result['nombre'],
                    'codigo': result['codigo'],
                    'confidence': confidence,
                    'score': 50,
                    'method': method
                }
        
        return {
            'success': False,
            'id': None,
            'nombre': None,
            'confidence': 0.0,
            'method': method
        }
    
    def _clasificar_por_keywords(self, sucursal_result: Dict, pdf_text: str) -> Dict:
        """
        PASO 4 (Fallback): Clasificar usando keywords tradicionales
        """
        # Importar el clasificador tradicional solo si es necesario
        from .classifier import PDFClassifier
        
        classifier = PDFClassifier()
        _, unidad_result = classifier.classify(pdf_text)
        
        # Marcar que fue clasificado por keywords (menor confianza)
        unidad_result['method'] = 'keywords_fallback'
        unidad_result['confidence'] = unidad_result.get('confidence', 0.5) * 0.8
        
        return unidad_result
    
    def _validar_coherencia(self, sucursal_result: Dict, unidad_result: Dict,
                           proveedor_info: Dict) -> Tuple[Dict, Dict]:
        """
        PASO 4: Validación cruzada de coherencia
        
        Verifica que la unidad funcional pertenezca a la sucursal identificada
        """
        if not sucursal_result['success'] or not unidad_result['success']:
            return sucursal_result, unidad_result
        
        # Verificar que la unidad pertenece a la sucursal
        with db.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            cursor.execute("""
                SELECT sucursal_id
                FROM unidades_funcionales
                WHERE id = %s
            """, (unidad_result['id'],))
            
            result = cursor.fetchone()
            cursor.close()
            
            if result and result['sucursal_id'] != sucursal_result['id']:
                # Incoherencia detectada
                logger.warning(
                    f"Incoherencia: Unidad {unidad_result['nombre']} "
                    f"no pertenece a sucursal {sucursal_result['nombre']}"
                )
                
                # Reducir confianza
                unidad_result['confidence'] *= 0.7
                unidad_result['requires_validation'] = True
        
        return sucursal_result, unidad_result
