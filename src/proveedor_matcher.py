"""
Sistema de matching automático de proveedores
Busca y relaciona proveedores con la base de datos PostgreSQL
"""
import psycopg2.extras
from typing import Dict, Optional, Tuple, List
import re
from difflib import SequenceMatcher
from .database import db


class ProveedorMatcher:
    """Busca y relaciona proveedores automáticamente con la tabla proveedores"""
    
    def __init__(self, db_config: Optional[Dict] = None):
        """
        Inicializa el matcher de proveedores
        
        Args:
            db_config: Configuración de conexión (obsoleto, se usa pool global)
        """
        # Se mantiene por compatibilidad
        pass
    
    def match_proveedor(self, proveedor_data: Dict) -> Dict:
        """
        Busca y relaciona un proveedor con la base de datos
        
        Args:
            proveedor_data: Datos extraídos del XML/PDF
                {
                    'nombre': 'DISTRIBUIDORA EJEMPLO S.A.S',
                    'razon_social': 'DISTRIBUIDORA EJEMPLO S.A.S',
                    'nit': '900123456',
                    'direccion': '...',
                    'ciudad': '...'
                }
        
        Returns:
            Dict con información del proveedor y match
        """
        if not proveedor_data or not isinstance(proveedor_data, dict):
            return self._empty_result(proveedor_data)
        
        # Obtener NIT y nombre
        nit = proveedor_data.get('nit', '')
        nombre = proveedor_data.get('nombre') or proveedor_data.get('razon_social', '')
        
        if not nit and not nombre:
            return self._empty_result(proveedor_data)
        
        with db.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            try:
                # 1. Intentar match por NIT (más confiable)
                if nit:
                    result = self._match_by_nit(cursor, nit)
                    if result:
                        return {
                            'matched': True,
                            'proveedor_id': result['id'],
                            'confidence': 1.0,
                            'match_method': 'nit_exacto',
                            'proveedor_db': dict(result),
                            'datos_extraidos': proveedor_data
                        }
                
                # 2. Intentar match por nombre (menos confiable)
                if nombre:
                    result, confidence = self._match_by_nombre(cursor, nombre)
                    if result and confidence >= 0.80:
                        return {
                            'matched': True,
                            'proveedor_id': result['id'],
                            'confidence': confidence,
                            'match_method': 'nombre_similar',
                            'proveedor_db': dict(result),
                            'datos_extraidos': proveedor_data
                        }
                
                # 3. No se encontró match
                return {
                    'matched': False,
                    'proveedor_id': None,
                    'confidence': 0.0,
                    'match_method': None,
                    'proveedor_db': None,
                    'datos_extraidos': proveedor_data,
                    'sugerencia': 'Proveedor no encontrado en la base de datos'
                }
                
            finally:
                cursor.close()
    
    def _empty_result(self, proveedor_data: Dict) -> Dict:
        """Retorna resultado vacío"""
        return {
            'matched': False,
            'proveedor_id': None,
            'confidence': 0.0,
            'match_method': None,
            'proveedor_db': None,
            'datos_extraidos': proveedor_data or {}
        }
    
    def _match_by_nit(self, cursor, nit: str) -> Optional[Dict]:
        """
        Busca proveedor por NIT en la tabla proveedores
        
        Args:
            cursor: Cursor de base de datos
            nit: NIT del proveedor (solo números)
        
        Returns:
            Información del proveedor o None
        """
        # Limpiar NIT (quitar todo excepto números)
        nit_limpio = re.sub(r'[^0-9]', '', str(nit))
        
        if not nit_limpio or len(nit_limpio) < 6:
            return None
        
        try:
            # Buscar en tabla proveedores
            # Comparar NIT limpio (sin guiones, puntos, espacios)
            cursor.execute("""
                SELECT 
                    id,
                    nit,
                    razon_social,
                    nombre_comercial,
                    email,
                    telefono,
                    direccion,
                    activo
                FROM proveedores
                WHERE REGEXP_REPLACE(nit, '[^0-9]', '', 'g') = %s
                    AND activo = TRUE
                LIMIT 1
            """, (nit_limpio,))
            
            result = cursor.fetchone()
            if result:
                return result
            
            # Si no encuentra exacto, buscar parcial (sin dígito de verificación)
            if len(nit_limpio) >= 9:
                nit_base = nit_limpio[:9]  # Primeros 9 dígitos
                
                cursor.execute("""
                    SELECT 
                        id,
                        nit,
                        razon_social,
                        nombre_comercial,
                        email,
                        telefono,
                        direccion,
                        activo
                    FROM proveedores
                    WHERE REGEXP_REPLACE(nit, '[^0-9]', '', 'g') LIKE %s
                        AND activo = TRUE
                    LIMIT 1
                """, (f"{nit_base}%",))
                
                return cursor.fetchone()
                
            return None
            
        except Exception:
            return None
    
    def _match_by_nombre(self, cursor, nombre: str) -> Tuple[Optional[Dict], float]:
        """
        Busca proveedor por similitud de nombre
        
        Returns:
            Tuple[Proveedor, Confianza]
        """
        if not nombre or len(nombre) < 5:
            return None, 0.0
            
        nombre_clean = nombre.upper().strip()
        
        # Buscar proveedores que podrían coincidir (búsqueda básica primero)
        # Usamos ILIKE para filtrar candidatos
        cursor.execute("""
            SELECT 
                id,
                nit,
                razon_social,
                nombre_comercial,
                email,
                telefono,
                direccion,
                activo
            FROM proveedores
            WHERE activo = TRUE
        """)
        
        proveedores = cursor.fetchall()
        
        mejor_match = None
        mejor_score = 0.0
        
        for prov in proveedores:
            # Comparar con razón social
            score_rs = self._similarity(nombre_clean, prov['razon_social'])
            
            # Comparar con nombre comercial (si existe)
            score_nc = 0.0
            if prov['nombre_comercial']:
                score_nc = self._similarity(nombre_clean, prov['nombre_comercial'])
            
            max_local = max(score_rs, score_nc)
            
            if max_local > mejor_score:
                mejor_score = max_local
                mejor_match = prov
        
        return mejor_match, mejor_score
    
    def _similarity(self, a: str, b: str) -> float:
        """Calcula similitud entre dos strings (0.0 a 1.0)"""
        if not a or not b:
            return 0.0
        return SequenceMatcher(None, a.upper(), b.upper()).ratio()
