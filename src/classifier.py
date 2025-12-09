"""
Clasificador de facturas basado en keywords de PostgreSQL
"""
import psycopg2
import psycopg2.extras
from typing import Dict, Tuple


class PDFClassifier:
    """Clasifica facturas PDF usando keywords de la base de datos"""
    
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
            # Clasificar sucursal
            sucursal = self._classify_sucursal(cursor, text, xml_weight, pdf_weight)
            
            # Clasificar unidad funcional
            unidad = self._classify_unidad(cursor, text, xml_weight, pdf_weight)
            
            return sucursal, unidad
            
        finally:
            cursor.close()
            conn.close()
    
    def _classify_sucursal(self, cursor, text: str, xml_weight: float = 1.0, pdf_weight: float = 1.0) -> Dict:
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
            WHERE sk.activo = TRUE
            ORDER BY sk.peso DESC
        """)
        
        matches = {}
        for row in cursor.fetchall():
            keyword = row['keyword'].upper()
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
    
    def _classify_unidad(self, cursor, text: str, xml_weight: float = 1.0, pdf_weight: float = 1.0) -> Dict:
        """Clasifica la unidad funcional"""
        cursor.execute("""
            SELECT 
                uk.unidad_funcional_id,
                uf.nombre as unidad_nombre,
                uf.codigo as unidad_codigo,
                uk.keyword,
                uk.peso
            FROM ocr_unidad_keywords uk
            JOIN unidades_funcionales uf ON uf.id = uk.unidad_funcional_id
            WHERE uk.activo = TRUE
            ORDER BY uk.peso DESC
        """)
        
        matches = {}
        for row in cursor.fetchall():
            keyword = row['keyword'].upper()
            if keyword in text:
                unidad_id = row['unidad_funcional_id']
                if unidad_id not in matches:
                    matches[unidad_id] = {
                        'id': unidad_id,
                        'nombre': row['unidad_nombre'],
                        'codigo': row['unidad_codigo'],
                        'score': 0,
                        'keywords': []
                    }
                matches[unidad_id]['score'] += row['peso']
                matches[unidad_id]['keywords'].append(keyword)
        
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
