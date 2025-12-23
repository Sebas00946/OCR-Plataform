"""
Clasificador de facturas basado en keywords de PostgreSQL
Con validación de coherencia sucursal-unidad funcional
"""
import psycopg2
import psycopg2.extras
import re
from typing import Dict, Tuple, Optional, List


class PDFClassifier:
    """Clasifica facturas PDF usando keywords de la base de datos"""
    
    # Keywords que deben ignorarse (muy genéricas o numéricas)
    KEYWORDS_IGNORAR = {
        # Números de años
        '2020', '2021', '2022', '2023', '2024', '2025', '2026',
        # Números genéricos cortos
        '0001', '0002', '0003', '0004', '0005', '0006', '0007', '0008', '0009', '0010',
        # Palabras muy comunes
        'FACTURA', 'TOTAL', 'SUBTOTAL', 'IVA', 'VALOR', 'CANTIDAD',
    }
    
    def __init__(self, db_config: Dict):
        """
        Inicializa el clasificador
        
        Args:
            db_config: Configuración de conexión a PostgreSQL
        """
        self.db_config = db_config
    
    def classify(self, text: str, xml_weight: float = 1.0, pdf_weight: float = 1.0) -> Tuple[Dict, Dict]:
        """
        Clasifica un texto extraído de XML/PDF con pesos
        Valida coherencia entre sucursal y unidad funcional
        
        Args:
            text: Texto combinado en mayúsculas
            xml_weight: Peso del XML (0.0 a 1.0)
            pdf_weight: Peso del PDF (0.0 a 1.0)
            
        Returns:
            Tuple con (info_sucursal, info_unidad)
        """
        conn = psycopg2.connect(**self.db_config)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        try:
            # 1. Clasificar sucursal primero
            sucursal = self._classify_sucursal(cursor, text)
            
            # 2. Clasificar unidad funcional considerando la sucursal
            unidad = self._classify_unidad(cursor, text, sucursal.get('id') if sucursal['success'] else None)
            
            # 3. Validar coherencia y ajustar si es necesario
            sucursal, unidad = self._validar_coherencia(cursor, sucursal, unidad, text)
            
            return sucursal, unidad
            
        finally:
            cursor.close()
            conn.close()
    
    def _is_valid_keyword(self, keyword: str) -> bool:
        """
        Verifica si una keyword es válida (no es genérica o numérica)
        """
        keyword_upper = keyword.upper().strip()
        
        # Ignorar keywords en la lista negra
        if keyword_upper in self.KEYWORDS_IGNORAR:
            return False
        
        # Ignorar keywords que son solo números
        if keyword_upper.isdigit():
            return False
        
        # Ignorar keywords muy cortas (menos de 3 caracteres)
        if len(keyword_upper) < 3:
            return False
        
        # Ignorar keywords que son principalmente números (más del 70% dígitos)
        digits = sum(c.isdigit() for c in keyword_upper)
        if len(keyword_upper) > 0 and digits / len(keyword_upper) > 0.7:
            return False
        
        return True
    
    def _classify_sucursal(self, cursor, text: str) -> Dict:
        """Clasifica la sucursal"""
        cursor.execute("""
            SELECT 
                sk.sucursal_id,
                s.nombre as sucursal_nombre,
                s.codigo as sucursal_codigo,
                sk.keyword,
                sk.peso
            FROM ocr_sucursal_keywords sk
            JOIN sucursales s ON s.id = sk.sucursal_id
            WHERE sk.activo = TRUE AND s.activo = TRUE
            ORDER BY sk.peso DESC
        """)
        
        matches = {}
        for row in cursor.fetchall():
            keyword = row['keyword'].upper()
            
            # Validar que la keyword sea válida
            if not self._is_valid_keyword(keyword):
                continue
            
            # Buscar keyword en el texto
            if keyword in text:
                sucursal_id = row['sucursal_id']
                if sucursal_id not in matches:
                    matches[sucursal_id] = {
                        'id': sucursal_id,
                        'nombre': row['sucursal_nombre'],
                        'codigo': row['sucursal_codigo'],
                        'score': 0,
                        'keywords': []
                    }
                matches[sucursal_id]['score'] += row['peso']
                matches[sucursal_id]['keywords'].append(keyword)
        
        if matches:
            best = max(matches.values(), key=lambda x: x['score'])
            return {
                'success': True,
                'id': best['id'],
                'nombre': best['nombre'],
                'codigo': best['codigo'],
                'score': best['score'],
                'keywords': best['keywords']
            }
        
        return {'success': False, 'id': None, 'nombre': None, 'score': 0, 'keywords': []}
    
    def _classify_unidad(self, cursor, text: str, sucursal_id: Optional[int] = None) -> Dict:
        """
        Clasifica la unidad funcional
        Si se proporciona sucursal_id, prioriza unidades de esa sucursal
        """
        # Obtener todas las keywords de unidades funcionales
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
            WHERE uk.activo = TRUE AND uf.activo = TRUE
            ORDER BY uk.peso DESC
        """)
        
        matches = {}
        for row in cursor.fetchall():
            keyword = row['keyword'].upper()
            
            # Validar que la keyword sea válida
            if not self._is_valid_keyword(keyword):
                continue
            
            # Buscar keyword en el texto
            if keyword in text:
                unidad_id = row['unidad_funcional_id']
                if unidad_id not in matches:
                    matches[unidad_id] = {
                        'id': unidad_id,
                        'nombre': row['unidad_nombre'],
                        'codigo': row['unidad_codigo'],
                        'sucursal_id': row['sucursal_id'],
                        'score': 0,
                        'keywords': []
                    }
                matches[unidad_id]['score'] += row['peso']
                matches[unidad_id]['keywords'].append(keyword)
        
        # Si tenemos sucursal_id, priorizar unidades de esa sucursal
        if sucursal_id:
            # Filtrar solo unidades de la sucursal detectada
            matches_sucursal = {k: v for k, v in matches.items() if v['sucursal_id'] == sucursal_id}
            
            if matches_sucursal:
                # Usar la mejor unidad de la sucursal
                best = max(matches_sucursal.values(), key=lambda x: x['score'])
                return {
                    'success': True,
                    'id': best['id'],
                    'nombre': best['nombre'],
                    'codigo': best['codigo'],
                    'score': best['score'],
                    'keywords': best['keywords'],
                    'sucursal_id': best['sucursal_id']
                }
            else:
                # No hay matches de la sucursal - buscar unidad por defecto
                return self._get_unidad_por_defecto(cursor, sucursal_id, text)
        
        # Sin sucursal_id, usar el mejor match general
        if matches:
            best = max(matches.values(), key=lambda x: x['score'])
            return {
                'success': True,
                'id': best['id'],
                'nombre': best['nombre'],
                'codigo': best['codigo'],
                'score': best['score'],
                'keywords': best['keywords'],
                'sucursal_id': best['sucursal_id']
            }
        
        return {'success': False, 'id': None, 'nombre': None, 'score': 0, 'keywords': [], 'sucursal_id': None}
    
    def _get_unidad_por_defecto(self, cursor, sucursal_id: int, text: str) -> Dict:
        """
        Obtiene la unidad funcional por defecto para una sucursal
        Prioriza: Administración > Almacén > Primera disponible
        También intenta detectar el tipo de unidad por el contenido del texto
        """
        # Obtener todas las unidades de la sucursal
        cursor.execute("""
            SELECT id, nombre, codigo
            FROM unidades_funcionales
            WHERE sucursal_id = %s AND activo = TRUE
            ORDER BY nombre
        """, (sucursal_id,))
        
        unidades = cursor.fetchall()
        
        if not unidades:
            return {'success': False, 'id': None, 'nombre': None, 'score': 0, 'keywords': [], 'sucursal_id': None}
        
        # Detectar tipo de unidad por contenido del texto
        text_upper = text.upper()
        
        # Palabras clave para detectar tipo de unidad
        keywords_administracion = ['CONTRATO', 'SERVICIO', 'ADMINISTRATIVO', 'MANTENIMIENTO', 
                                   'CONSTRUCCION', 'OBRA', 'PROYECTO', 'LECTURA', 'RADIOGRAFIA',
                                   'TOMOGRAFIA', 'HONORARIOS', 'CONSULTORIA']
        keywords_almacen = ['INSUMO', 'MEDICAMENTO', 'MATERIAL', 'EQUIPO', 'DISPOSITIVO',
                           'PRODUCTO', 'SUMINISTRO', 'INVENTARIO', 'FARMACEUTICO']
        keywords_activos = ['ACTIVO FIJO', 'MAQUINARIA', 'EQUIPO MEDICO', 'MOBILIARIO']
        keywords_compras = ['CENTRAL DE COMPRAS', 'COMPRAS CENTRALIZADAS']
        
        # Contar coincidencias
        score_admin = sum(1 for kw in keywords_administracion if kw in text_upper)
        score_almacen = sum(1 for kw in keywords_almacen if kw in text_upper)
        score_activos = sum(1 for kw in keywords_activos if kw in text_upper)
        score_compras = sum(1 for kw in keywords_compras if kw in text_upper)
        
        # Determinar tipo preferido
        tipo_preferido = None
        max_score = max(score_admin, score_almacen, score_activos, score_compras)
        
        if max_score > 0:
            if score_admin == max_score:
                tipo_preferido = 'ADMINISTRACI'
            elif score_almacen == max_score:
                tipo_preferido = 'ALMAC'
            elif score_activos == max_score:
                tipo_preferido = 'ACTIVO'
            elif score_compras == max_score:
                tipo_preferido = 'COMPRAS'
        
        # Buscar unidad del tipo preferido
        unidad_seleccionada = None
        keywords_detectadas = []
        
        if tipo_preferido:
            for uf in unidades:
                if tipo_preferido in uf['nombre'].upper():
                    unidad_seleccionada = uf
                    if tipo_preferido == 'ADMINISTRACI':
                        keywords_detectadas = [kw for kw in keywords_administracion if kw in text_upper][:3]
                    elif tipo_preferido == 'ALMAC':
                        keywords_detectadas = [kw for kw in keywords_almacen if kw in text_upper][:3]
                    break
        
        # Si no encontramos el tipo preferido, usar Administración por defecto
        if not unidad_seleccionada:
            for uf in unidades:
                if 'ADMINISTRACI' in uf['nombre'].upper():
                    unidad_seleccionada = uf
                    keywords_detectadas = ['[ASIGNADO POR DEFECTO]']
                    break
        
        # Si no hay Administración, usar la primera unidad
        if not unidad_seleccionada:
            unidad_seleccionada = unidades[0]
            keywords_detectadas = ['[ASIGNADO POR DEFECTO]']
        
        return {
            'success': True,
            'id': unidad_seleccionada['id'],
            'nombre': unidad_seleccionada['nombre'],
            'codigo': unidad_seleccionada['codigo'],
            'score': max_score * 5 if max_score > 0 else 1,  # Score basado en detección
            'keywords': keywords_detectadas,
            'sucursal_id': sucursal_id
        }
    
    def _validar_coherencia(self, cursor, sucursal: Dict, unidad: Dict, text: str) -> Tuple[Dict, Dict]:
        """
        Valida que la sucursal y unidad funcional sean coherentes
        Si no lo son, intenta corregir
        """
        if not sucursal['success'] or not unidad['success']:
            return sucursal, unidad
        
        # Obtener la sucursal de la unidad funcional
        unidad_sucursal_id = unidad.get('sucursal_id')
        
        # Si la unidad pertenece a la sucursal detectada, todo bien
        if unidad_sucursal_id == sucursal['id']:
            return sucursal, unidad
        
        # HAY INCONSISTENCIA - La unidad no pertenece a la sucursal
        # Intentar encontrar una unidad funcional de la sucursal correcta
        
        # Obtener unidades funcionales de la sucursal detectada
        cursor.execute("""
            SELECT id, nombre, codigo
            FROM unidades_funcionales
            WHERE sucursal_id = %s AND activo = TRUE
        """, (sucursal['id'],))
        
        unidades_sucursal = cursor.fetchall()
        
        if not unidades_sucursal:
            # No hay unidades para esta sucursal, mantener como está
            return sucursal, unidad
        
        # Buscar la mejor unidad de la sucursal correcta basándose en el tipo
        # Por ejemplo, si la unidad detectada es "Almacén - TJA", buscar "Almacén - NVA"
        tipo_unidad = self._extraer_tipo_unidad(unidad['nombre'])
        
        mejor_unidad = None
        for uf in unidades_sucursal:
            tipo_uf = self._extraer_tipo_unidad(uf['nombre'])
            if tipo_uf == tipo_unidad:
                mejor_unidad = uf
                break
        
        # Si no encontramos el mismo tipo, usar la primera unidad (generalmente Administración)
        if not mejor_unidad:
            # Buscar Administración primero
            for uf in unidades_sucursal:
                if 'ADMINISTRACI' in uf['nombre'].upper():
                    mejor_unidad = uf
                    break
            
            # Si no hay Administración, usar la primera
            if not mejor_unidad:
                mejor_unidad = unidades_sucursal[0]
        
        # Actualizar la unidad funcional
        unidad_corregida = {
            'success': True,
            'id': mejor_unidad['id'],
            'nombre': mejor_unidad['nombre'],
            'codigo': mejor_unidad['codigo'],
            'score': unidad['score'] * 0.8,  # Reducir score por corrección
            'keywords': unidad['keywords'] + ['[CORREGIDO POR COHERENCIA]'],
            'sucursal_id': sucursal['id']
        }
        
        return sucursal, unidad_corregida
    
    def _extraer_tipo_unidad(self, nombre_unidad: str) -> str:
        """
        Extrae el tipo de unidad funcional del nombre
        Ejemplo: "Almacén - TJA" -> "Almacén"
        """
        if not nombre_unidad:
            return ""
        
        # Separar por " - " y tomar la primera parte
        partes = nombre_unidad.split(' - ')
        if partes:
            return partes[0].strip().upper()
        
        return nombre_unidad.upper()
