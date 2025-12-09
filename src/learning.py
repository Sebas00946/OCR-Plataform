"""
Sistema de auto-aprendizaje para el OCR
Aprende de las validaciones del usuario
"""
import psycopg2
import psycopg2.extras
from typing import Dict, Optional
import json
from datetime import datetime


class LearningSystem:
    """Sistema que aprende de las clasificaciones validadas"""
    
    def __init__(self, db_config: Dict):
        self.db_config = db_config
    
    def save_classification(
        self,
        factura_id: Optional[int],
        archivo_nombre: str,
        sucursal: Dict,
        unidad: Dict,
        metadata: Dict
    ) -> int:
        """
        Guarda una clasificación en el historial
        
        Returns:
            ID del registro en historial
        """
        conn = psycopg2.connect(**self.db_config)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO ocr_clasificacion_historial (
                    factura_id,
                    archivo_nombre,
                    archivo_tipo,
                    sucursal_detectada_id,
                    unidad_funcional_detectada_id,
                    confianza_sucursal,
                    confianza_unidad,
                    keywords_encontradas,
                    datos_extraidos,
                    tiempo_procesamiento_ms
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s)
                RETURNING id
            """, (
                factura_id,
                archivo_nombre,
                'xml' if archivo_nombre.endswith('.xml') else 'pdf',
                sucursal.get('id'),
                unidad.get('id'),
                sucursal.get('score', 0),
                unidad.get('score', 0),
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
            conn.close()
    
    def validate_and_learn(
        self,
        historial_id: int,
        es_correcta: bool,
        sucursal_correcta_id: Optional[int] = None,
        unidad_correcta_id: Optional[int] = None,
        observaciones: Optional[str] = None
    ) -> Dict:
        """
        Valida una clasificación y aprende de ella
        
        Returns:
            Dict con acciones de aprendizaje realizadas
        """
        conn = psycopg2.connect(**self.db_config)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        try:
            # Actualizar historial
            cursor.execute("""
                UPDATE ocr_clasificacion_historial
                SET clasificacion_correcta = %s,
                    observaciones = %s
                WHERE id = %s
            """, (es_correcta, observaciones, historial_id))
            
            conn.commit()
            
            learning_actions = {
                'weights_adjusted': False,
                'keywords_suggested': [],
                'message': ''
            }
            
            if es_correcta:
                # Clasificación correcta: reforzar keywords
                learning_actions['weights_adjusted'] = self._reinforce_keywords(
                    cursor, conn, historial_id
                )
                learning_actions['message'] = 'Keywords reforzadas exitosamente'
            
            else:
                # Clasificación incorrecta: aprender de la corrección
                if sucursal_correcta_id or unidad_correcta_id:
                    learning_actions['keywords_suggested'] = self._suggest_new_keywords(
                        cursor, historial_id, sucursal_correcta_id, unidad_correcta_id
                    )
                    learning_actions['message'] = 'Se sugieren nuevas keywords para mejorar'
            
            return learning_actions
            
        finally:
            cursor.close()
            conn.close()
    
    def _reinforce_keywords(self, cursor, conn, historial_id: int) -> bool:
        """
        Refuerza (aumenta peso) de las keywords que funcionaron
        
        Returns:
            True si se ajustaron pesos
        """
        try:
            # Obtener keywords que funcionaron
            cursor.execute("""
                SELECT keywords_encontradas, sucursal_detectada_id, unidad_funcional_detectada_id
                FROM ocr_clasificacion_historial
                WHERE id = %s
            """, (historial_id,))
            
            row = cursor.fetchone()
            if not row:
                return False
            
            keywords_data = row['keywords_encontradas']
            sucursal_id = row['sucursal_detectada_id']
            unidad_id = row['unidad_funcional_detectada_id']
            
            # Aumentar peso de keywords de sucursal (máximo 10)
            if sucursal_id and keywords_data.get('sucursal'):
                for keyword in keywords_data['sucursal'][:3]:  # Top 3
                    cursor.execute("""
                        UPDATE ocr_sucursal_keywords
                        SET peso = LEAST(peso + 1, 10)
                        WHERE sucursal_id = %s AND keyword = %s
                    """, (sucursal_id, keyword))
            
            # Aumentar peso de keywords de unidad (máximo 10)
            if unidad_id and keywords_data.get('unidad'):
                for keyword in keywords_data['unidad'][:3]:  # Top 3
                    cursor.execute("""
                        UPDATE ocr_unidad_keywords
                        SET peso = LEAST(peso + 1, 10)
                        WHERE unidad_funcional_id = %s AND keyword = %s
                    """, (unidad_id, keyword))
            
            conn.commit()
            return True
            
        except Exception as e:
            print(f"Error al reforzar keywords: {e}")
            return False
    
    def _suggest_new_keywords(
        self,
        cursor,
        historial_id: int,
        sucursal_correcta_id: Optional[int],
        unidad_correcta_id: Optional[int]
    ) -> list:
        """
        Sugiere nuevas keywords basadas en clasificación incorrecta
        
        Returns:
            Lista de keywords sugeridas
        """
        suggestions = []
        
        try:
            # Obtener datos extraídos
            cursor.execute("""
                SELECT datos_extraidos
                FROM ocr_clasificacion_historial
                WHERE id = %s
            """, (historial_id,))
            
            row = cursor.fetchone()
            if not row or not row['datos_extraidos']:
                return suggestions
            
            # Analizar texto para sugerir keywords
            # (Implementación básica - puede mejorarse con NLP)
            text = row['datos_extraidos'].get('text', '')
            
            # Extraer palabras únicas de 4+ caracteres
            words = set()
            for word in text.split():
                if len(word) >= 4 and word.isalpha():
                    words.add(word)
            
            # Sugerir top 5 palabras más frecuentes
            for word in list(words)[:5]:
                suggestions.append({
                    'keyword': word,
                    'tipo': 'sucursal' if sucursal_correcta_id else 'unidad',
                    'id': sucursal_correcta_id or unidad_correcta_id,
                    'peso_sugerido': 5
                })
            
            return suggestions
            
        except Exception as e:
            print(f"Error al sugerir keywords: {e}")
            return suggestions
    
    def get_statistics(self) -> Dict:
        """Obtiene estadísticas del sistema"""
        conn = psycopg2.connect(**self.db_config)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        try:
            # Total de clasificaciones
            cursor.execute("""
                SELECT COUNT(*) as total,
                       COUNT(CASE WHEN clasificacion_correcta = true THEN 1 END) as correctas,
                       COUNT(CASE WHEN clasificacion_correcta = false THEN 1 END) as incorrectas,
                       AVG(confianza_sucursal) as avg_confianza_sucursal,
                       AVG(confianza_unidad) as avg_confianza_unidad
                FROM ocr_clasificacion_historial
                WHERE clasificacion_correcta IS NOT NULL
            """)
            
            stats = cursor.fetchone()
            
            # Precisión
            total = stats['total'] or 0
            correctas = stats['correctas'] or 0
            precision = (correctas / total * 100) if total > 0 else 0
            
            return {
                'total_clasificaciones': total,
                'correctas': correctas,
                'incorrectas': stats['incorrectas'] or 0,
                'precision': round(precision, 2),
                'confianza_promedio': {
                    'sucursal': round(stats['avg_confianza_sucursal'] or 0, 2),
                    'unidad': round(stats['avg_confianza_unidad'] or 0, 2)
                }
            }
            
        finally:
            cursor.close()
            conn.close()
    
    def get_keywords(self, tipo: str, entity_id: int) -> list:
        """Obtiene keywords de una entidad"""
        conn = psycopg2.connect(**self.db_config)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        try:
            if tipo == 'sucursal':
                cursor.execute("""
                    SELECT keyword, peso, activo
                    FROM ocr_sucursal_keywords
                    WHERE sucursal_id = %s
                    ORDER BY peso DESC
                """, (entity_id,))
            else:
                cursor.execute("""
                    SELECT keyword, peso, activo
                    FROM ocr_unidad_keywords
                    WHERE unidad_funcional_id = %s
                    ORDER BY peso DESC
                """, (entity_id,))
            
            return cursor.fetchall()
            
        finally:
            cursor.close()
            conn.close()
