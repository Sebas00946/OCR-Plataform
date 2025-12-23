"""
Sistema de matching automático de proveedores
Busca y relaciona proveedores con la base de datos PostgreSQL
"""
import psycopg2
import psycopg2.extras
from typing import Dict, Optional, Tuple, List
import re
from difflib import SequenceMatcher


class ProveedorMatcher:
    """Busca y relaciona proveedores automáticamente con la tabla proveedores"""
    
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
            conn.close()
    
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
                """, (nit_base + '%',))
                
                result = cursor.fetchone()
                return result
                
        except Exception as e:
            print(f"⚠️  Error al buscar por NIT: {e}")
        
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
        
        if not nombre_limpio or len(nombre_limpio) < 3:
            return None, 0.0
        
        try:
            # Obtener proveedores activos
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
        except Exception as e:
            print(f"⚠️  Error al buscar proveedores: {e}")
            return None, 0.0
        
        # Calcular similitud con cada proveedor
        mejor_match = None
        mejor_confidence = 0.0
        
        for proveedor in proveedores:
            max_similarity = 0.0
            
            # Comparar con razón social
            if proveedor.get('razon_social'):
                razon_limpia = self._limpiar_nombre(proveedor['razon_social'])
                similarity = self._calcular_similitud(nombre_limpio, razon_limpia)
                max_similarity = max(max_similarity, similarity)
            
            # Comparar con nombre comercial
            if proveedor.get('nombre_comercial'):
                nombre_comercial_limpio = self._limpiar_nombre(proveedor['nombre_comercial'])
                similarity = self._calcular_similitud(nombre_limpio, nombre_comercial_limpio)
                max_similarity = max(max_similarity, similarity)
            
            if max_similarity > mejor_confidence:
                mejor_confidence = max_similarity
                mejor_match = proveedor
        
        return mejor_match, mejor_confidence
    
    def _limpiar_nombre(self, nombre: str) -> str:
        """
        Limpia y normaliza un nombre para comparación
        """
        if not nombre:
            return ""
        
        # Convertir a mayúsculas
        nombre = nombre.upper()
        
        # Quitar sufijos comunes de empresas
        sufijos = [
            r'\bS\.?A\.?S\.?\b',
            r'\bLTDA\.?\b',
            r'\bS\.?A\.?\b',
            r'\bE\.?U\.?\b',
            r'\bCIA\.?\b',
            r'\bY\s+CIA\.?\b',
            r'\bS\.?C\.?\b',
            r'\bS\.?EN\s*C\.?\b',
        ]
        
        for sufijo in sufijos:
            nombre = re.sub(sufijo, '', nombre, flags=re.IGNORECASE)
        
        # Quitar caracteres especiales
        nombre = re.sub(r'[^A-ZÁÉÍÓÚÑ0-9\s]', '', nombre)
        
        # Quitar espacios múltiples
        nombre = re.sub(r'\s+', ' ', nombre)
        
        return nombre.strip()
    
    def _calcular_similitud(self, texto1: str, texto2: str) -> float:
        """
        Calcula similitud entre dos textos
        """
        if not texto1 or not texto2:
            return 0.0
        return SequenceMatcher(None, texto1, texto2).ratio()
    
    def buscar_proveedores_similares(self, nombre: str, limite: int = 5) -> List[Dict]:
        """
        Busca proveedores similares por nombre
        Útil para sugerir proveedores cuando no hay match exacto
        
        Args:
            nombre: Nombre a buscar
            limite: Número máximo de resultados
        
        Returns:
            Lista de proveedores similares con su score
        """
        conn = psycopg2.connect(**self.db_config)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        try:
            nombre_limpio = self._limpiar_nombre(nombre)
            
            cursor.execute("""
                SELECT id, nit, razon_social, nombre_comercial
                FROM proveedores
                WHERE activo = TRUE
            """)
            
            proveedores = cursor.fetchall()
            
            # Calcular similitud
            resultados = []
            for prov in proveedores:
                max_sim = 0.0
                
                if prov.get('razon_social'):
                    sim = self._calcular_similitud(nombre_limpio, self._limpiar_nombre(prov['razon_social']))
                    max_sim = max(max_sim, sim)
                
                if prov.get('nombre_comercial'):
                    sim = self._calcular_similitud(nombre_limpio, self._limpiar_nombre(prov['nombre_comercial']))
                    max_sim = max(max_sim, sim)
                
                if max_sim > 0.5:  # Solo incluir si hay algo de similitud
                    resultados.append({
                        'id': prov['id'],
                        'nit': prov['nit'],
                        'razon_social': prov['razon_social'],
                        'nombre_comercial': prov['nombre_comercial'],
                        'similitud': round(max_sim, 2)
                    })
            
            # Ordenar por similitud descendente
            resultados.sort(key=lambda x: x['similitud'], reverse=True)
            
            return resultados[:limite]
            
        finally:
            cursor.close()
            conn.close()
