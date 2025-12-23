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
            conn.close()
    
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
        conn = psycopg2.connect(**self.db_config)
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
                    cursor, conn, historial_id
                )
                learning_actions['weights_adjusted'] = keywords_reforzadas > 0
                learning_actions['keywords_reforzadas'] = keywords_reforzadas
                learning_actions['message'] = f'✅ {keywords_reforzadas} keywords reforzadas'
            
            else:
                # Clasificación incorrecta: aprender de la corrección
                if sucursal_correcta_id or unidad_correcta_id:
                    # Extraer keywords del texto
                    keywords_extraidas = self._extract_smart_keywords(
                        cursor, historial_id, sucursal_correcta_id, unidad_correcta_id
                    )
                    
                    if auto_add_keywords and keywords_extraidas:
                        # Agregar keywords automáticamente
                        keywords_agregadas = self._add_keywords_automatically(
                            cursor, conn, keywords_extraidas, 
                            sucursal_correcta_id, unidad_correcta_id
                        )
                        learning_actions['keywords_added'] = keywords_agregadas
                        learning_actions['message'] = f'🎓 {len(keywords_agregadas)} keywords agregadas automáticamente'
                    else:
                        # Solo sugerir keywords
                        learning_actions['keywords_suggested'] = keywords_extraidas
                        learning_actions['message'] = f'💡 {len(keywords_extraidas)} keywords sugeridas'
                    
                    # Reducir peso de keywords incorrectas
                    self._penalize_wrong_keywords(cursor, conn, historial_id)
            
            return learning_actions
            
        finally:
            cursor.close()
            conn.close()
    
    def _reinforce_keywords(self, cursor, conn, historial_id: int) -> int:
        """
        Refuerza (aumenta peso) de las keywords que funcionaron
        
        Returns:
            Número de keywords reforzadas
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
                return 0
            
            keywords_data = row['keywords_encontradas']
            sucursal_id = row['sucursal_detectada_id']
            unidad_id = row['unidad_funcional_detectada_id']
            
            count = 0
            
            # Aumentar peso de keywords de sucursal (máximo 10)
            if sucursal_id and keywords_data.get('sucursal'):
                for keyword in keywords_data['sucursal'][:5]:  # Top 5
                    cursor.execute("""
                        UPDATE ocr_sucursal_keywords
                        SET peso = LEAST(peso + 1, 10),
                            updated_at = NOW()
                        WHERE sucursal_id = %s AND keyword = %s
                    """, (sucursal_id, keyword))
                    if cursor.rowcount > 0:
                        count += 1
            
            # Aumentar peso de keywords de unidad (máximo 10)
            if unidad_id and keywords_data.get('unidad'):
                for keyword in keywords_data['unidad'][:5]:  # Top 5
                    cursor.execute("""
                        UPDATE ocr_unidad_keywords
                        SET peso = LEAST(peso + 1, 10),
                            updated_at = NOW()
                        WHERE unidad_funcional_id = %s AND keyword = %s
                    """, (unidad_id, keyword))
                    if cursor.rowcount > 0:
                        count += 1
            
            conn.commit()
            return count
            
        except Exception as e:
            print(f"Error al reforzar keywords: {e}")
            return 0
    
    def _extract_smart_keywords(
        self,
        cursor,
        historial_id: int,
        sucursal_correcta_id: Optional[int],
        unidad_correcta_id: Optional[int]
    ) -> list:
        """
        Extrae keywords inteligentes del texto de la factura
        
        Returns:
            Lista de keywords extraídas con metadatos
        """
        keywords = []
        
        try:
            # Obtener datos extraídos y nombre de la entidad correcta
            cursor.execute("""
                SELECT 
                    h.datos_extraidos,
                    s.nombre as sucursal_nombre,
                    s.codigo as sucursal_codigo,
                    uf.nombre as unidad_nombre,
                    uf.codigo as unidad_codigo
                FROM ocr_clasificacion_historial h
                LEFT JOIN sucursales s ON s.id = %s
                LEFT JOIN unidades_funcionales uf ON uf.id = %s
                WHERE h.id = %s
            """, (sucursal_correcta_id, unidad_correcta_id, historial_id))
            
            row = cursor.fetchone()
            if not row or not row['datos_extraidos']:
                return keywords
            
            text = row['datos_extraidos'].get('text', '').upper()
            
            # 1. Extraer códigos numéricos (ej: 0010, 0055)
            import re
            codigos = re.findall(r'\b\d{4}\b', text)
            for codigo in set(codigos):
                keywords.append({
                    'keyword': codigo,
                    'tipo': 'unidad' if unidad_correcta_id else 'sucursal',
                    'entity_id': unidad_correcta_id or sucursal_correcta_id,
                    'peso_sugerido': 8,
                    'razon': 'Código numérico encontrado'
                })
            
            # 2. Extraer códigos cortos (ej: TJA, FLA, NVA)
            codigos_cortos = re.findall(r'\b[A-Z]{3}\b', text)
            for codigo in set(codigos_cortos):
                # Evitar palabras comunes
                if codigo not in ['SAS', 'NIT', 'TEL', 'FAX', 'IVA']:
                    keywords.append({
                        'keyword': codigo,
                        'tipo': 'sucursal' if sucursal_correcta_id else 'unidad',
                        'entity_id': sucursal_correcta_id or unidad_correcta_id,
                        'peso_sugerido': 9,
                        'razon': 'Código corto encontrado'
                    })
            
            # 3. Buscar nombre de la entidad en el texto
            if sucursal_correcta_id and row['sucursal_nombre']:
                nombre_parts = row['sucursal_nombre'].upper().split()
                for part in nombre_parts:
                    if len(part) >= 4 and part in text:
                        # Evitar palabras muy comunes
                        if part not in ['CLINICA', 'MEDILASER', 'S.A.S']:
                            keywords.append({
                                'keyword': part,
                                'tipo': 'sucursal',
                                'entity_id': sucursal_correcta_id,
                                'peso_sugerido': 10,
                                'razon': f'Parte del nombre de sucursal'
                            })
            
            if unidad_correcta_id and row['unidad_nombre']:
                nombre_parts = row['unidad_nombre'].upper().split()
                for part in nombre_parts:
                    if len(part) >= 4 and part in text:
                        if part not in ['ALMACEN', 'ADMINISTRACION']:
                            keywords.append({
                                'keyword': part,
                                'tipo': 'unidad',
                                'entity_id': unidad_correcta_id,
                                'peso_sugerido': 9,
                                'razon': f'Parte del nombre de unidad'
                            })
            
            # 4. Buscar frases específicas (ej: "MEDILASER TUNJA", "TJA MED")
            frases_comunes = [
                r'MEDILASER\s+\w+',
                r'\w+\s+MED',
                r'SEDE\s+\w+',
                r'FACTURACION\s+\w+',
            ]
            
            for patron in frases_comunes:
                matches = re.findall(patron, text)
                for match in set(matches):
                    if len(match) <= 50:  # Evitar frases muy largas
                        keywords.append({
                            'keyword': match,
                            'tipo': 'unidad' if unidad_correcta_id else 'sucursal',
                            'entity_id': unidad_correcta_id or sucursal_correcta_id,
                            'peso_sugerido': 9,
                            'razon': 'Frase específica encontrada'
                        })
            
            # 5. Eliminar duplicados
            keywords_unicos = []
            keywords_vistos = set()
            for kw in keywords:
                if kw['keyword'] not in keywords_vistos:
                    keywords_vistos.add(kw['keyword'])
                    keywords_unicos.append(kw)
            
            return keywords_unicos[:10]  # Máximo 10 keywords
            
        except Exception as e:
            print(f"Error al extraer keywords: {e}")
            import traceback
            traceback.print_exc()
            return keywords
    
    def _add_keywords_automatically(
        self,
        cursor,
        conn,
        keywords: list,
        sucursal_correcta_id: Optional[int],
        unidad_correcta_id: Optional[int]
    ) -> list:
        """
        Agrega keywords automáticamente a la base de datos
        
        Returns:
            Lista de keywords agregadas exitosamente
        """
        keywords_agregadas = []
        
        try:
            for kw in keywords:
                keyword = kw['keyword']
                peso = kw['peso_sugerido']
                tipo = kw['tipo']
                entity_id = kw['entity_id']
                
                try:
                    if tipo == 'sucursal' and sucursal_correcta_id:
                        # Verificar si ya existe
                        cursor.execute("""
                            SELECT peso FROM ocr_sucursal_keywords
                            WHERE sucursal_id = %s AND keyword = %s
                        """, (entity_id, keyword))
                        
                        existing = cursor.fetchone()
                        
                        if existing:
                            # Ya existe, solo aumentar peso si es menor
                            if existing['peso'] < peso:
                                cursor.execute("""
                                    UPDATE ocr_sucursal_keywords
                                    SET peso = %s, updated_at = NOW()
                                    WHERE sucursal_id = %s AND keyword = %s
                                """, (peso, entity_id, keyword))
                                keywords_agregadas.append({
                                    **kw,
                                    'accion': 'actualizada',
                                    'peso_anterior': existing['peso']
                                })
                        else:
                            # No existe, agregar
                            cursor.execute("""
                                INSERT INTO ocr_sucursal_keywords 
                                (sucursal_id, keyword, peso, activo)
                                VALUES (%s, %s, %s, TRUE)
                            """, (entity_id, keyword, peso))
                            keywords_agregadas.append({
                                **kw,
                                'accion': 'agregada'
                            })
                    
                    elif tipo == 'unidad' and unidad_correcta_id:
                        # Verificar si ya existe
                        cursor.execute("""
                            SELECT peso FROM ocr_unidad_keywords
                            WHERE unidad_funcional_id = %s AND keyword = %s
                        """, (entity_id, keyword))
                        
                        existing = cursor.fetchone()
                        
                        if existing:
                            # Ya existe, solo aumentar peso si es menor
                            if existing['peso'] < peso:
                                cursor.execute("""
                                    UPDATE ocr_unidad_keywords
                                    SET peso = %s, updated_at = NOW()
                                    WHERE unidad_funcional_id = %s AND keyword = %s
                                """, (peso, entity_id, keyword))
                                keywords_agregadas.append({
                                    **kw,
                                    'accion': 'actualizada',
                                    'peso_anterior': existing['peso']
                                })
                        else:
                            # No existe, agregar
                            cursor.execute("""
                                INSERT INTO ocr_unidad_keywords 
                                (unidad_funcional_id, keyword, peso, activo)
                                VALUES (%s, %s, %s, TRUE)
                            """, (entity_id, keyword, peso))
                            keywords_agregadas.append({
                                **kw,
                                'accion': 'agregada'
                            })
                
                except Exception as e:
                    print(f"Error al agregar keyword '{keyword}': {e}")
                    continue
            
            conn.commit()
            return keywords_agregadas
            
        except Exception as e:
            print(f"Error al agregar keywords automáticamente: {e}")
            conn.rollback()
            return keywords_agregadas
    
    def _penalize_wrong_keywords(self, cursor, conn, historial_id: int):
        """
        Reduce el peso de keywords que llevaron a una clasificación incorrecta
        """
        try:
            # Obtener keywords que fallaron
            cursor.execute("""
                SELECT keywords_encontradas, sucursal_detectada_id, unidad_funcional_detectada_id
                FROM ocr_clasificacion_historial
                WHERE id = %s
            """, (historial_id,))
            
            row = cursor.fetchone()
            if not row:
                return
            
            keywords_data = row['keywords_encontradas']
            sucursal_id = row['sucursal_detectada_id']
            unidad_id = row['unidad_funcional_detectada_id']
            
            # Reducir peso de keywords de sucursal (mínimo 1)
            if sucursal_id and keywords_data.get('sucursal'):
                for keyword in keywords_data['sucursal'][:3]:  # Top 3 que fallaron
                    cursor.execute("""
                        UPDATE ocr_sucursal_keywords
                        SET peso = GREATEST(peso - 1, 1),
                            updated_at = NOW()
                        WHERE sucursal_id = %s AND keyword = %s
                    """, (sucursal_id, keyword))
            
            # Reducir peso de keywords de unidad (mínimo 1)
            if unidad_id and keywords_data.get('unidad'):
                for keyword in keywords_data['unidad'][:3]:  # Top 3 que fallaron
                    cursor.execute("""
                        UPDATE ocr_unidad_keywords
                        SET peso = GREATEST(peso - 1, 1),
                            updated_at = NOW()
                        WHERE unidad_funcional_id = %s AND keyword = %s
                    """, (unidad_id, keyword))
            
            conn.commit()
            
        except Exception as e:
            print(f"Error al penalizar keywords: {e}")
    
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
                'precision': round(float(precision), 2),
                'confianza_promedio': {
                    'sucursal': round(float(stats['avg_confianza_sucursal'] or 0), 2),
                    'unidad': round(float(stats['avg_confianza_unidad'] or 0), 2)
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

    def reinforce_correct_classification(self, text: str, sucursal_id: int, unidad_id: int):
        """
        Refuerza keywords de una clasificación correcta
        Extrae palabras clave del texto y las asocia con la sucursal y unidad correctas
        
        Args:
            text: Texto extraído del documento
            sucursal_id: ID de la sucursal correcta
            unidad_id: ID de la unidad funcional correcta
        """
        if not text or not text.strip():
            print(f"  ⚠️  Texto vacío, no se pueden extraer keywords")
            return
        
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
        except Exception as e:
            print(f"  ❌ Error conectando a BD: {e}")
            return
        
        try:
            # VALIDAR que los IDs existen en las tablas
            cursor.execute("SELECT id, nombre FROM sucursales WHERE id = %s AND activo = true", (sucursal_id,))
            sucursal = cursor.fetchone()
            
            cursor.execute("SELECT id, nombre FROM unidades_funcionales WHERE id = %s AND activo = true", (unidad_id,))
            unidad = cursor.fetchone()
            
            if not sucursal:
                print(f"  ❌ ERROR: Sucursal ID {sucursal_id} NO EXISTE en la tabla sucursales")
                cursor.close()
                conn.close()
                return
            
            if not unidad:
                print(f"  ❌ ERROR: Unidad funcional ID {unidad_id} NO EXISTE en la tabla unidades_funcionales")
                cursor.close()
                conn.close()
                return
            
            # Extraer keywords del texto (palabras de 3+ caracteres, sin números puros)
            import re
            words = re.findall(r'\b[a-záéíóúñA-ZÁÉÍÓÚÑ]{3,}\b', text.lower())
            
            if not words:
                print(f"  ⚠️  No se encontraron palabras válidas en el texto")
                cursor.close()
                conn.close()
                return
            
            # Contar frecuencia de palabras
            from collections import Counter
            word_freq = Counter(words)
            
            # Tomar las 20 palabras más frecuentes
            top_words = [word for word, count in word_freq.most_common(20) if count >= 2]
            
            # Palabras comunes a ignorar
            stopwords = {
                'para', 'con', 'por', 'sin', 'sobre', 'entre', 'hasta', 'desde',
                'del', 'los', 'las', 'una', 'uno', 'dos', 'tres', 'este', 'esta',
                'ese', 'esa', 'aquel', 'aquella', 'que', 'cual', 'quien', 'donde',
                'cuando', 'como', 'porque', 'pero', 'mas', 'menos', 'muy', 'tan',
                'total', 'subtotal', 'iva', 'valor', 'cantidad', 'precio', 'fecha'
            }
            
            keywords_added_sucursal = 0
            keywords_added_unidad = 0
            errors = []
            
            for keyword in top_words:
                if keyword in stopwords or len(keyword) < 4:
                    continue
                
                # Agregar/actualizar keyword para sucursal
                try:
                    cursor.execute("""
                        INSERT INTO ocr_sucursal_keywords (sucursal_id, keyword, peso, activo)
                        VALUES (%s, %s, 1.0, true)
                        ON CONFLICT (sucursal_id, keyword) 
                        DO UPDATE SET 
                            peso = LEAST(ocr_sucursal_keywords.peso + 0.1, 10.0),
                            activo = true,
                            updated_at = NOW()
                    """, (sucursal_id, keyword))
                    keywords_added_sucursal += 1
                except Exception as e:
                    errors.append(f"Sucursal keyword '{keyword}': {str(e)}")
                
                # Agregar/actualizar keyword para unidad funcional
                try:
                    cursor.execute("""
                        INSERT INTO ocr_unidad_keywords (unidad_funcional_id, keyword, peso, activo)
                        VALUES (%s, %s, 1.0, true)
                        ON CONFLICT (unidad_funcional_id, keyword) 
                        DO UPDATE SET 
                            peso = LEAST(ocr_unidad_keywords.peso + 0.1, 10.0),
                            activo = true,
                            updated_at = NOW()
                    """, (unidad_id, keyword))
                    keywords_added_unidad += 1
                except Exception as e:
                    errors.append(f"Unidad keyword '{keyword}': {str(e)}")
            
            conn.commit()
            
            # Log para debug
            if keywords_added_sucursal > 0 or keywords_added_unidad > 0:
                print(f"  📚 {keywords_added_sucursal} keywords → {sucursal[1]} + {keywords_added_unidad} keywords → {unidad[1]}")
                import sys
                sys.stdout.flush()
            else:
                print(f"  ⚠️  No se agregaron keywords (palabras filtradas o errores)")
                
            if errors:
                print(f"  ⚠️  {len(errors)} errores al guardar keywords:")
                for error in errors[:3]:  # Mostrar primeros 3
                    print(f"     - {error}")
                import sys
                sys.stdout.flush()
            
        except Exception as e:
            print(f"  ❌ Error en reinforce_correct_classification: {e}")
            import traceback
            traceback.print_exc()
            conn.rollback()
        finally:
            cursor.close()
            conn.close()
