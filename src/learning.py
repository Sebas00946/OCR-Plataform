"""
Sistema de auto-aprendizaje para el OCR
Aprende de las validaciones del usuario
"""
import psycopg2.extras
from typing import Dict, Optional
import json
from datetime import datetime
from .database import db


class LearningSystem:
    """Sistema que aprende de las clasificaciones validadas"""
    
    def __init__(self, db_config: Optional[Dict] = None):
        """
        Inicializa el sistema de aprendizaje
        
        Args:
            db_config: Configuración de conexión (obsoleto, se usa pool global)
        """
        # Se mantiene por compatibilidad
        pass
    
    def save_classification(
        self,
        factura_id: Optional[int],
        archivo_nombre: str,
        sucursal: Dict,
        unidad: Dict,
        metadata: Dict,
        proveedor_id: Optional[int] = None,
        confianza_proveedor: Optional[float] = None
    ) -> int:
        """
        Guarda una clasificación en el historial
        
        Args:
            factura_id: ID de la factura
            archivo_nombre: Nombre del archivo
            sucursal: Información de sucursal detectada
            unidad: Información de unidad detectada
            metadata: Metadatos de la extracción
            proveedor_id: ID del proveedor detectado (opcional)
            confianza_proveedor: Confianza del match de proveedor (opcional)
        
        Returns:
            ID del registro en historial
        """
        # Usar el pool de conexiones
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    INSERT INTO ocr_clasificacion_historial (
                        factura_id,
                        archivo_nombre,
                        archivo_tipo,
                        sucursal_detectada_id,
                        unidad_funcional_detectada_id,
                        proveedor_detectado_id,
                        confianza_sucursal,
                        confianza_unidad,
                        confianza_proveedor,
                        keywords_encontradas,
                        datos_extraidos,
                        tiempo_procesamiento_ms
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s)
                    RETURNING id
                """, (
                    factura_id,
                    archivo_nombre,
                    'xml' if archivo_nombre.endswith('.xml') else 'pdf',
                    sucursal.get('id'),
                    unidad.get('id'),
                    proveedor_id,
                    sucursal.get('score', 0),
                    unidad.get('score', 0),
                    confianza_proveedor,
                    json.dumps({
                        'sucursal': sucursal.get('keywords', []),
                        'unidad': unidad.get('keywords', [])
                    }),
                    json.dumps(metadata),
                    0  # Tiempo de procesamiento
                ))
                
                historial_id = cursor.fetchone()[0]
                conn.commit()
                
                return historial_id
                
            finally:
                cursor.close()
    
    def validate_and_learn(
        self,
        historial_id: int,
        es_correcta: bool,
        sucursal_correcta_id: Optional[int] = None,
        unidad_correcta_id: Optional[int] = None,
        observaciones: Optional[str] = None,
        auto_add_keywords: bool = True
    ) -> Dict:
        """
        Valida una clasificación y aprende de ella
        
        Args:
            historial_id: ID del historial de clasificación
            es_correcta: Si la clasificación fue correcta
            sucursal_correcta_id: ID de la sucursal correcta (si fue incorrecta)
            unidad_correcta_id: ID de la unidad correcta (si fue incorrecta)
            observaciones: Comentarios adicionales
            auto_add_keywords: Si debe agregar keywords automáticamente
        
        Returns:
            Dict con acciones de aprendizaje realizadas
        """
        with db.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            try:
                # Actualizar historial con la clasificación correcta
                cursor.execute("""
                    UPDATE ocr_clasificacion_historial
                    SET clasificacion_correcta = %s,
                        sucursal_correcta_id = %s,
                        unidad_correcta_id = %s,
                        observaciones = %s,
                        fecha_validacion = NOW()
                    WHERE id = %s
                """, (es_correcta, sucursal_correcta_id, unidad_correcta_id, observaciones, historial_id))
                
                conn.commit()
                
                learning_actions = {
                    'weights_adjusted': False,
                    'keywords_added': [],
                    'keywords_suggested': [],
                    'message': ''
                }
                
                if es_correcta:
                    # Clasificación correcta: reforzar keywords
                    keywords_reforzadas = self._reinforce_keywords(
                        cursor, historial_id
                    )
                    learning_actions['weights_adjusted'] = len(keywords_reforzadas) > 0
                    learning_actions['message'] = f"Reforzadas {len(keywords_reforzadas)} keywords"
                    
                elif auto_add_keywords:
                    # Clasificación incorrecta: intentar aprender nuevas keywords
                    new_keywords = self._learn_from_correction(
                        cursor, historial_id, sucursal_correcta_id, unidad_correcta_id
                    )
                    learning_actions['keywords_added'] = new_keywords
                    learning_actions['message'] = f"Aprendidas {len(new_keywords)} nuevas keywords"
                
                conn.commit()
                return learning_actions
                
            finally:
                cursor.close()
    
    def _reinforce_keywords(self, cursor, historial_id: int) -> list:
        """
        Aumenta el peso de las keywords que llevaron a una clasificación correcta
        """
        # Obtener las keywords usadas en esta clasificación
        cursor.execute("""
            SELECT keywords_encontradas, sucursal_detectada_id, unidad_funcional_detectada_id
            FROM ocr_clasificacion_historial
            WHERE id = %s
        """, (historial_id,))
        
        result = cursor.fetchone()
        if not result:
            return []
            
        keywords_json = result['keywords_encontradas']
        sucursal_id = result['sucursal_detectada_id']
        unidad_id = result['unidad_funcional_detectada_id']
        
        reinforced = []
        
        # Reforzar keywords de sucursal
        if sucursal_id and 'sucursal' in keywords_json:
            for keyword in keywords_json['sucursal']:
                cursor.execute("""
                    UPDATE ocr_sucursal_keywords
                    SET peso = LEAST(peso + 0.5, 10.0), -- Aumentar peso, máximo 10
                        usos_exitosos = usos_exitosos + 1,
                        updated_at = NOW()
                    WHERE sucursal_id = %s AND keyword = %s
                """, (sucursal_id, keyword))
                if cursor.rowcount > 0:
                    reinforced.append(f"Sucursal: {keyword}")
        
        # Reforzar keywords de unidad
        if unidad_id and 'unidad' in keywords_json:
            for keyword in keywords_json['unidad']:
                cursor.execute("""
                    UPDATE ocr_unidad_keywords
                    SET peso = LEAST(peso + 0.5, 10.0), -- Aumentar peso, máximo 10
                        usos_exitosos = usos_exitosos + 1,
                        updated_at = NOW()
                    WHERE unidad_funcional_id = %s AND keyword = %s
                """, (unidad_id, keyword))
                if cursor.rowcount > 0:
                    reinforced.append(f"Unidad: {keyword}")
                    
        return reinforced

    def _learn_from_correction(
        self, 
        cursor, 
        historial_id: int, 
        sucursal_correcta_id: Optional[int], 
        unidad_correcta_id: Optional[int]
    ) -> list:
        """
        Aprende nuevas keywords basadas en la corrección manual
        Busca texto en el documento que sea único para la sucursal/unidad correcta
        """
        # Nota: Esta es una implementación simplificada.
        # Una implementación completa requeriría re-analizar el texto del documento
        # Para este ejemplo, solo bajamos peso a las keywords que causaron el error
        
        cursor.execute("""
            SELECT keywords_encontradas, sucursal_detectada_id, unidad_funcional_detectada_id
            FROM ocr_clasificacion_historial
            WHERE id = %s
        """, (historial_id,))
        
        result = cursor.fetchone()
        if not result:
            return []
            
        keywords_json = result['keywords_encontradas']
        sucursal_detectada = result['sucursal_detectada_id']
        unidad_detectada = result['unidad_funcional_detectada_id']
        
        penalized = []
        
        # Si la sucursal estaba mal, penalizar sus keywords
        if sucursal_correcta_id and sucursal_detectada != sucursal_correcta_id:
            if 'sucursal' in keywords_json:
                for keyword in keywords_json['sucursal']:
                    cursor.execute("""
                        UPDATE ocr_sucursal_keywords
                        SET peso = GREATEST(peso - 1.0, 0.1), -- Disminuir peso, mínimo 0.1
                            usos_fallidos = usos_fallidos + 1,
                            updated_at = NOW()
                        WHERE sucursal_id = %s AND keyword = %s
                    """, (sucursal_detectada, keyword))
                    penalized.append(f"Penalizada Sucursal: {keyword}")
        
        # Si la unidad estaba mal, penalizar sus keywords
        if unidad_correcta_id and unidad_detectada != unidad_correcta_id:
            if 'unidad' in keywords_json:
                for keyword in keywords_json['unidad']:
                    cursor.execute("""
                        UPDATE ocr_unidad_keywords
                        SET peso = GREATEST(peso - 1.0, 0.1), -- Disminuir peso, mínimo 0.1
                            usos_fallidos = usos_fallidos + 1,
                            updated_at = NOW()
                        WHERE unidad_funcional_id = %s AND keyword = %s
                    """, (unidad_detectada, keyword))
                    penalized.append(f"Penalizada Unidad: {keyword}")
                    
        return penalized
