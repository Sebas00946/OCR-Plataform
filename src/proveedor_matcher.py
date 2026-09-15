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
    
    def match_proveedor(self, proveedor_data: Dict, empresa_id: Optional[int] = None) -> Dict:
        """
        Busca y relaciona un proveedor con la base de datos.

        Alineado con el documento de mejoras del equipo Node.js:
        - Bug #1: filtra SIEMPRE por empresa_id (no hace fallback cross-empresa).
        - Bug #2: el match por NOMBRE solo se acepta si el NIT del candidato
          coincide con el NIT del emisor (evita GROUPJR->HYDROHER).
        - Bug #3: normaliza el NIT (solo dígitos) antes de comparar.

        Args:
            proveedor_data: Datos extraídos del XML/PDF (nombre, razon_social, nit, ...)
            empresa_id: Empresa del buzón. Si se pasa, la búsqueda se acota a ella.

        Returns:
            Dict con información del proveedor y match
        """
        if not proveedor_data or not isinstance(proveedor_data, dict):
            return self._empty_result(proveedor_data)
        
        # Obtener NIT y nombre
        nit = proveedor_data.get('nit', '')
        nombre = proveedor_data.get('nombre') or proveedor_data.get('razon_social', '')
        nit_emisor = re.sub(r'[^0-9]', '', str(nit)) if nit else ''
        
        if not nit and not nombre:
            return self._empty_result(proveedor_data)
        
        with db.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            try:
                # 1. Intentar match por NIT (más confiable)
                if nit:
                    result = self._match_by_nit(cursor, nit, empresa_id)
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
                    result, confidence = self._match_by_nombre(cursor, nombre, empresa_id)
                    if result and confidence >= 0.80:
                        # ── Bug #2: validar que el NIT del candidato coincida con el emisor ──
                        if nit_emisor:
                            nit_candidato = re.sub(r'[^0-9]', '', str(result.get('nit', '')))
                            # Comparar primeros 9 dígitos (tolerar dígito de verificación)
                            if nit_candidato[:9] != nit_emisor[:9]:
                                # El nombre coincide pero es otro proveedor: NO aceptar
                                return {
                                    'matched': False,
                                    'proveedor_id': None,
                                    'confidence': 0.0,
                                    'match_method': None,
                                    'proveedor_db': None,
                                    'datos_extraidos': proveedor_data,
                                    'sugerencia': (
                                        f'Match por nombre descartado: NIT emisor {nit_emisor} '
                                        f'no coincide con candidato {nit_candidato} '
                                        f'({result.get("razon_social")})'
                                    )
                                }
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
    
    def _match_by_nit(self, cursor, nit: str, empresa_id: Optional[int] = None) -> Optional[Dict]:
        """
        Busca proveedor por NIT en la tabla proveedores.
        
        Bug #1: si se pasa empresa_id, la búsqueda se acota a esa empresa
        (no hace fallback global cross-empresa que causaba los cruces).
        
        Args:
            cursor: Cursor de base de datos
            nit: NIT del proveedor (solo números)
            empresa_id: Empresa del buzón (filtro obligatorio si se conoce)
        
        Returns:
            Información del proveedor o None
        """
        # Limpiar NIT (quitar todo excepto números)
        nit_limpio = re.sub(r'[^0-9]', '', str(nit))
        
        if not nit_limpio or len(nit_limpio) < 6:
            return None
        
        # Filtro de empresa (evita cruces cross-empresa)
        empresa_sql = " AND empresa_id = %s" if empresa_id is not None else ""
        
        try:
            # 1. Match exacto por NIT normalizado
            params = [nit_limpio]
            if empresa_id is not None:
                params.append(empresa_id)
            cursor.execute(f"""
                SELECT id, nit, razon_social, nombre_comercial,
                       email, telefono, direccion, activo
                FROM proveedores
                WHERE REGEXP_REPLACE(nit, '[^0-9]', '', 'g') = %s
                    AND activo = TRUE{empresa_sql}
                LIMIT 1
            """, tuple(params))
            
            result = cursor.fetchone()
            if result:
                return result
            
            # 2. Match parcial (sin dígito de verificación)
            if len(nit_limpio) >= 9:
                nit_base = nit_limpio[:9]
                params = [f"{nit_base}%"]
                if empresa_id is not None:
                    params.append(empresa_id)
                cursor.execute(f"""
                    SELECT id, nit, razon_social, nombre_comercial,
                           email, telefono, direccion, activo
                    FROM proveedores
                    WHERE REGEXP_REPLACE(nit, '[^0-9]', '', 'g') LIKE %s
                        AND activo = TRUE{empresa_sql}
                    LIMIT 1
                """, tuple(params))
                return cursor.fetchone()
                
            return None
            
        except Exception:
            return None
    
    def _match_by_nombre(self, cursor, nombre: str, empresa_id: Optional[int] = None) -> Tuple[Optional[Dict], float]:
        """
        Busca proveedor por similitud de nombre.
        Bug #1: acota a la empresa del buzón si se conoce.
        
        Returns:
            Tuple[Proveedor, Confianza]
        """
        if not nombre or len(nombre) < 5:
            return None, 0.0
            
        nombre_clean = nombre.upper().strip()
        
        # Buscar candidatos (acotados a la empresa si se conoce)
        if empresa_id is not None:
            cursor.execute("""
                SELECT id, nit, razon_social, nombre_comercial,
                       email, telefono, direccion, activo
                FROM proveedores
                WHERE activo = TRUE AND empresa_id = %s
            """, (empresa_id,))
        else:
            cursor.execute("""
                SELECT id, nit, razon_social, nombre_comercial,
                       email, telefono, direccion, activo
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
