"""
Sistema de matching automático de proveedores
Busca y relaciona proveedores con la base de datos
"""
import psycopg2
import psycopg2.extras
from typing import Dict, Optional, Tuple
import re
from difflib import SequenceMatcher


class ProveedorMatcher:
    """Busca y relaciona proveedores automáticamente"""
    
    def __init__(self, db_config: Dict):
        """
        Inicializa el matcher de proveedores
        
        Args:
            db_config: Configuración de conexión a PostgreSQL
        """
        self.db_config = db_config
    
    def match_proveedor(self, proveedor_data: Dict) -> Dict:
        """
        Busca y relaciona un proveedor con la base de datos
        
        Args:
            proveedor_data: Datos extraídos del XML
                {
                    'nombre': 'DISTRIBUIDORA EJEMPLO S.A.S',
                    'nit': '900123456',
                    'direccion': '...',
                    'ciudad': '...'
                }
                O formato antiguo:
                {
                    'proveedor_nombre': 'DISTRIBUIDORA EJEMPLO S.A.S',
                    'proveedor_nit': '900123456-7',
                    ...
                }
        
        Returns:
            Dict con información del proveedor y match
            {
                'matched': True/False,
                'proveedor_id': 123,
                'confidence': 0.95,
                'match_method': 'nit_exacto',
                'proveedor_info': {...},
                'datos_extraidos': {...}
            }
        """
        if not proveedor_data or not isinstance(proveedor_data, dict):
            return {
                'matched': False,
                'proveedor_id': None,
                'confidence': 0.0,
                'match_method': None,
                'proveedor_info': None,
                'datos_extraidos': {}
            }
        
        # Normalizar datos (soportar ambos formatos)
        nit = proveedor_data.get('nit') or proveedor_data.get('proveedor_nit')
        nombre = proveedor_data.get('nombre') or proveedor_data.get('proveedor_nombre')
        
        if not nit and not nombre:
            return {
                'matched': False,
                'proveedor_id': None,
                'confidence': 0.0,
                'match_method': None,
                'proveedor_info': None,
                'datos_extraidos': proveedor_data
            }
        
        conn = psycopg2.connect(**self.db_config)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        try:
            # 1. Intentar match por NIT (más confiable)
            if nit:
                result = self._match_by_nit(cursor, nit)
                if result:
                    return {
                        'matched': True,
                        'proveedor_id': result['id'],
                        'confidence': 1.0,  # 100% confianza con NIT
                        'match_method': 'nit_exacto',
                        'proveedor_info': dict(result),
                        'datos_extraidos': proveedor_data
                    }
            
            # 2. Intentar match por nombre (menos confiable)
            if nombre:
                result, confidence = self._match_by_nombre(cursor, nombre)
                if result and confidence >= 0.85:  # Mínimo 85% similitud
                    return {
                        'matched': True,
                        'proveedor_id': result['id'],
                        'confidence': confidence,
                        'match_method': 'nombre_similar',
                        'proveedor_info': dict(result),
                        'datos_extraidos': proveedor_data
                    }
            
            # 3. No se encontró match
            return {
                'matched': False,
                'proveedor_id': None,
                'confidence': 0.0,
                'match_method': None,
                'proveedor_info': None,
                'datos_extraidos': proveedor_data,
                'sugerencia': 'Crear nuevo proveedor en el sistema'
            }
            
        finally:
            cursor.close()
            conn.close()
    
    def _match_by_nit(self, cursor, nit: str) -> Optional[Dict]:
        """
        Busca proveedor por NIT
        
        Args:
            cursor: Cursor de base de datos
            nit: NIT del proveedor
        
        Returns:
            Información del proveedor o None
        """
        # Limpiar NIT (quitar guiones, puntos, espacios)
        nit_limpio = re.sub(r'[^0-9]', '', nit)
        
        # Buscar primero en tabla proveedores
        try:
            cursor.execute("""
                SELECT 
                    p.id,
                    p.nit,
                    p.razon_social,
                    p.nombre_comercial,
                    p.email,
                    p.telefono,
                    p.direccion,
                    p.activo
                FROM proveedores p
                WHERE REPLACE(REPLACE(REPLACE(p.nit, '-', ''), '.', ''), ' ', '') = %s
                    AND p.activo = TRUE
                LIMIT 1
            """, (nit_limpio,))
            
            result = cursor.fetchone()
            if result:
                return result
        except Exception as e:
            print(f"⚠️  Error al buscar en proveedores: {e}")
        
        # Si no se encuentra, buscar en ocr_proveedor_config
        try:
            cursor.execute("""
                SELECT 
                    opc.proveedor_id as id,
                    opc.nit,
                    opc.nombre_completo as razon_social,
                    opc.nombre_completo as nombre_comercial,
                    NULL as email,
                    NULL as telefono,
                    NULL as direccion,
                    opc.activo
                FROM ocr_proveedor_config opc
                WHERE REPLACE(REPLACE(REPLACE(opc.nit, '-', ''), '.', ''), ' ', '') = %s
                    AND opc.activo = TRUE
                LIMIT 1
            """, (nit_limpio,))
            
            result = cursor.fetchone()
            return result
        except Exception as e:
            print(f"⚠️  Error al buscar en ocr_proveedor_config: {e}")
            return None
    
    def _match_by_nombre(self, cursor, nombre: str) -> Tuple[Optional[Dict], float]:
        """
        Busca proveedor por nombre usando similitud de texto
        
        Args:
            cursor: Cursor de base de datos
            nombre: Nombre del proveedor
        
        Returns:
            Tuple (información_proveedor, confidence)
        """
        nombre_limpio = self._limpiar_nombre(nombre)
        
        # Obtener todos los proveedores activos de la tabla proveedores
        try:
            cursor.execute("""
                SELECT 
                    p.id,
                    p.nit,
                    p.razon_social,
                    p.nombre_comercial,
                    p.email,
                    p.telefono,
                    p.direccion,
                    p.activo
                FROM proveedores p
                WHERE p.activo = TRUE
            """)
            
            proveedores = cursor.fetchall()
        except Exception as e:
            print(f"⚠️  Error al buscar proveedores: {e}")
            return None, 0.0
        
        # Calcular similitud con cada proveedor
        mejor_match = None
        mejor_confidence = 0.0
        
        for proveedor in proveedores:
            # Comparar con razón social
            if proveedor.get('razon_social'):
                razon_limpia = self._limpiar_nombre(proveedor['razon_social'])
                confidence = self._calcular_similitud(nombre_limpio, razon_limpia)
                
                if confidence > mejor_confidence:
                    mejor_confidence = confidence
                    mejor_match = proveedor
            
            # Comparar con nombre comercial
            if proveedor.get('nombre_comercial'):
                nombre_comercial_limpio = self._limpiar_nombre(proveedor['nombre_comercial'])
                confidence_comercial = self._calcular_similitud(nombre_limpio, nombre_comercial_limpio)
                
                if confidence_comercial > mejor_confidence:
                    mejor_confidence = confidence_comercial
                    mejor_match = proveedor
        
        return mejor_match, mejor_confidence
    
    def _limpiar_nombre(self, nombre: str) -> str:
        """
        Limpia y normaliza un nombre para comparación
        
        Args:
            nombre: Nombre a limpiar
        
        Returns:
            Nombre limpio y normalizado
        """
        if not nombre:
            return ""
        
        # Convertir a mayúsculas
        nombre = nombre.upper()
        
        # Quitar sufijos comunes
        sufijos = [
            'S.A.S', 'SAS', 'S.A.', 'SA', 'S.A', 
            'LTDA', 'LTDA.', 'E.U.', 'EU',
            'CIA', 'CIA.', 'Y CIA', 'Y CIA.',
            'S.C.', 'SC'
        ]
        
        for sufijo in sufijos:
            nombre = nombre.replace(sufijo, '')
        
        # Quitar caracteres especiales
        nombre = re.sub(r'[^A-Z0-9\s]', '', nombre)
        
        # Quitar espacios múltiples
        nombre = re.sub(r'\s+', ' ', nombre)
        
        return nombre.strip()
    
    def _calcular_similitud(self, texto1: str, texto2: str) -> float:
        """
        Calcula similitud entre dos textos usando SequenceMatcher
        
        Args:
            texto1: Primer texto
            texto2: Segundo texto
        
        Returns:
            Similitud entre 0.0 y 1.0
        """
        return SequenceMatcher(None, texto1, texto2).ratio()
    
    def registrar_proveedor_nuevo(self, proveedor_data: Dict, proveedor_id: int) -> bool:
        """
        Registra un proveedor nuevo en ocr_proveedor_config
        
        Args:
            proveedor_data: Datos del proveedor extraídos
            proveedor_id: ID del proveedor en la tabla proveedores
        
        Returns:
            True si se registró exitosamente
        """
        conn = psycopg2.connect(**self.db_config)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO ocr_proveedor_config (
                    proveedor_id,
                    nit,
                    nombre_completo,
                    alias,
                    formato_preferido,
                    requiere_validacion,
                    activo
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (proveedor_id) DO NOTHING
            """, (
                proveedor_id,
                proveedor_data.get('proveedor_nit', ''),
                proveedor_data.get('proveedor_nombre', ''),
                None,  # alias
                'ambos',  # formato_preferido
                False,  # requiere_validacion
                True  # activo
            ))
            
            conn.commit()
            return True
            
        except Exception as e:
            print(f"Error al registrar proveedor: {e}")
            conn.rollback()
            return False
            
        finally:
            cursor.close()
            conn.close()