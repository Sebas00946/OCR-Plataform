"""
Sistema de auto-aprendizaje para el OCR
Aprende de las validaciones del usuario:
- Refuerza keywords correctas
- Penaliza keywords incorrectas
- EXTRAE Y AGREGA keywords nuevas desde el texto del documento cuando hay corrección
- Aprende la relación proveedor -> unidad funcional
"""
import psycopg2.extras
from typing import Dict, List, Optional, Set
import json
import re
import logging
from .database import db

logger = logging.getLogger(__name__)

# Palabras que no deben ser keywords (muy genéricas o numéricas)
STOPWORDS = {
    'DE', 'LA', 'EL', 'EN', 'Y', 'A', 'CON', 'POR', 'PARA', 'DEL', 'LOS', 'LAS',
    'UN', 'UNA', 'ES', 'SE', 'NO', 'AL', 'SU', 'QUE', 'MAS', 'O', 'E', 'NI',
    'FACTURA', 'TOTAL', 'SUBTOTAL', 'IVA', 'VALOR', 'CANTIDAD', 'PRECIO', 'UNIDAD',
    'FECHA', 'NUMERO', 'CODIGO', 'DESCRIPCION', 'ITEM', 'REFERENCIA',
    '2020', '2021', '2022', '2023', '2024', '2025', '2026',
    'SAS', 'LTDA', 'SA', 'NIT', 'COP', 'COP',
    'CLINICA', 'MEDILASER',  # Siempre presentes, no discriminan
}

# Términos que indican ALMACEN (medicamentos, insumos)
KEYWORDS_ALMACEN = [
    'MEDICAMENTO', 'INSUMO', 'FARMACO', 'FARMACEUTICO', 'DROGUERIA',
    'SUSPENSION', 'TABLETA', 'CAPSULA', 'AMPOLLA', 'JERINGA', 'CATETER',
    'SUERO', 'SOLUCION', 'INYECTABLE', 'ORAL', 'TOPICO', 'CREMA', 'GEL',
    'MATERIAL QUIRURGICO', 'MATERIAL DE CURACION', 'DISPOSITIVO MEDICO',
    'EQUIPO MEDICO', 'INSTRUMENTAL', 'GUANTE', 'GASA', 'VENDA', 'ESPARADRAPO',
    'OXCARBAZEPINA', 'IBUPROFENO', 'ACETAMINOFEN', 'AMOXICILINA',
    'SUMINISTRO', 'INVENTARIO', 'STOCK', 'ALMACEN',
]

# Términos que indican ADMINISTRACION (servicios, gastos)
KEYWORDS_ADMINISTRACION = [
    'SERVICIO', 'ADMINISTRATIVO', 'MANTENIMIENTO', 'CONTRATO', 'HONORARIO',
    'CONSULTORIA', 'ASESORIA', 'TELECOMUNICACION', 'INTERNET', 'TELEFONIA',
    'ENERGIA', 'AGUA', 'GAS', 'ACUEDUCTO', 'VIGILANCIA', 'ASEO', 'LIMPIEZA',
    'ARRENDAMIENTO', 'ALQUILER', 'PAPELERIA', 'PAPELERÍA', 'UTILES',
    'PUBLICIDAD', 'TRANSPORTE', 'MENSAJERIA', 'CORREO',
    'ADMINISTRACION', 'ADMINISTRACIÓN',
]


class LearningSystem:
    """Sistema que aprende de las clasificaciones validadas"""

    def __init__(self, db_config: Optional[Dict] = None):
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
        confianza_proveedor: Optional[float] = None,
        empresa_id: int = 1
    ) -> int:
        """Guarda una clasificación en el historial"""
        with db.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO ocr_clasificacion_historial (
                        factura_id, archivo_nombre, archivo_tipo,
                        sucursal_detectada_id, unidad_funcional_detectada_id,
                        proveedor_detectado_id, confianza_sucursal, confianza_unidad,
                        confianza_proveedor, keywords_encontradas, datos_extraidos,
                        tiempo_procesamiento_ms, empresa_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s)
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
                        'unidad': unidad.get('keywords', []),
                        # Guardar también el texto completo para aprendizaje futuro
                        'texto_completo': metadata.get('text', '')[:2000] if metadata else ''
                    }),
                    json.dumps(metadata),
                    0,
                    empresa_id
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
        auto_add_keywords: bool = True,
        empresa_id: int = 1
    ) -> Dict:
        """Valida una clasificación y aprende de ella"""
        with db.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            try:
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
                    'proveedor_aprendido': False,
                    'message': ''
                }

                if es_correcta:
                    keywords_reforzadas = self._reinforce_keywords(cursor, historial_id)
                    conn.commit()
                    learning_actions['weights_adjusted'] = len(keywords_reforzadas) > 0
                    learning_actions['message'] = f"Reforzadas {len(keywords_reforzadas)} keywords"
                    
                    # Auto-crear regla si hay consistencia
                    cursor.execute("""
                        SELECT proveedor_detectado_id, unidad_funcional_detectada_id, sucursal_detectada_id
                        FROM ocr_clasificacion_historial WHERE id = %s
                    """, (historial_id,))
                    hist = cursor.fetchone()
                    if hist and hist.get('proveedor_detectado_id') and hist.get('unidad_funcional_detectada_id'):
                        regla_creada = self._auto_crear_regla_si_consistente(
                            cursor, hist['proveedor_detectado_id'],
                            hist['unidad_funcional_detectada_id'],
                            hist['sucursal_detectada_id']
                        )
                        if regla_creada:
                            conn.commit()
                            learning_actions['regla_auto_creada'] = True
                            learning_actions['message'] += " | Regla automatica creada"
                    
                elif auto_add_keywords:
                    result = self._learn_from_correction(
                        cursor, historial_id, sucursal_correcta_id, unidad_correcta_id
                    )
                    conn.commit()
                    learning_actions['keywords_added'] = result.get('nuevas', [])
                    learning_actions['weights_adjusted'] = len(result.get('penalizadas', [])) > 0
                    learning_actions['proveedor_aprendido'] = result.get('proveedor_aprendido', False)
                    total = len(result.get('nuevas', [])) + len(result.get('penalizadas', []))
                    learning_actions['message'] = (
                        f"Aprendidas {len(result.get('nuevas', []))} keywords nuevas, "
                        f"penalizadas {len(result.get('penalizadas', []))}"
                    )
                    
                    # Auto-crear regla si hay consistencia en correcciones
                    if unidad_correcta_id:
                        cursor.execute("""
                            SELECT proveedor_detectado_id, sucursal_detectada_id
                            FROM ocr_clasificacion_historial WHERE id = %s
                        """, (historial_id,))
                        hist = cursor.fetchone()
                        if hist and hist.get('proveedor_detectado_id'):
                            regla_creada = self._auto_crear_regla_si_consistente(
                                cursor, hist['proveedor_detectado_id'],
                                unidad_correcta_id,
                                sucursal_correcta_id or hist.get('sucursal_detectada_id')
                            )
                            if regla_creada:
                                conn.commit()
                                learning_actions['regla_auto_creada'] = True
                                learning_actions['message'] += " | Regla automatica creada"
                
                # Verificar si es momento de reentrenar el clasificador bayesiano
                total_validaciones = self._contar_validaciones_totales(cursor)
                if total_validaciones > 0 and total_validaciones % 50 == 0:
                    learning_actions['reentrenamiento_sugerido'] = True
                    learning_actions['total_validaciones'] = total_validaciones

                return learning_actions
            finally:
                # Invalidar KnowledgeBase para que el próximo request use los nuevos datos
                try:
                    from .engine.knowledge_base import kb
                    kb.invalidate()
                except Exception:
                    pass
                cursor.close()

    def reinforce_correct_classification(
        self,
        texto: str,
        sucursal_id: int,
        unidad_id: int,
        peso_inicial: float = 3.0
    ) -> List[str]:
        """
        Refuerza la clasificación correcta extrayendo keywords del texto.
        Usado por el script de auto-aprendizaje masivo.
        """
        with db.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            try:
                keywords_agregadas = self._agregar_keywords_desde_texto(
                    cursor, texto, unidad_id, sucursal_id, peso_inicial
                )
                conn.commit()
                return keywords_agregadas
            finally:
                cursor.close()

    # ─────────────────────────────────────────────────────────────────────────
    # MÉTODOS PRIVADOS
    # ─────────────────────────────────────────────────────────────────────────

    def _reinforce_keywords(self, cursor, historial_id: int) -> list:
        """Aumenta el peso de las keywords que llevaron a una clasificación correcta"""
        cursor.execute("""
            SELECT keywords_encontradas, sucursal_detectada_id, unidad_funcional_detectada_id
            FROM ocr_clasificacion_historial WHERE id = %s
        """, (historial_id,))
        result = cursor.fetchone()
        if not result:
            return []

        keywords_json = result['keywords_encontradas']
        sucursal_id = result['sucursal_detectada_id']
        unidad_id = result['unidad_funcional_detectada_id']
        reinforced = []

        if sucursal_id and 'sucursal' in keywords_json:
            for keyword in keywords_json['sucursal']:
                cursor.execute("""
                    UPDATE ocr_sucursal_keywords
                    SET peso = LEAST(peso + 0.5, 10.0),
                        usos_exitosos = usos_exitosos + 1,
                        updated_at = NOW()
                    WHERE sucursal_id = %s AND keyword = %s
                """, (sucursal_id, keyword))
                if cursor.rowcount > 0:
                    reinforced.append(f"Sucursal: {keyword}")

        if unidad_id and 'unidad' in keywords_json:
            for keyword in keywords_json['unidad']:
                cursor.execute("""
                    UPDATE ocr_unidad_keywords
                    SET peso = LEAST(peso + 0.5, 10.0),
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
    ) -> Dict:
        """
        Aprende de una corrección manual:
        1. Penaliza keywords que causaron el error
        2. Extrae keywords del texto del documento y las agrega a la unidad correcta
        3. Aprende la relación proveedor -> unidad funcional
        """
        cursor.execute("""
            SELECT keywords_encontradas, datos_extraidos,
                   sucursal_detectada_id, unidad_funcional_detectada_id,
                   proveedor_detectado_id
            FROM ocr_clasificacion_historial WHERE id = %s
        """, (historial_id,))
        result = cursor.fetchone()
        if not result:
            return {'nuevas': [], 'penalizadas': [], 'proveedor_aprendido': False}

        keywords_json = result['keywords_encontradas']
        datos_extraidos = result['datos_extraidos'] or {}
        sucursal_detectada = result['sucursal_detectada_id']
        unidad_detectada = result['unidad_funcional_detectada_id']
        proveedor_id = result['proveedor_detectado_id']

        penalizadas = []
        nuevas = []

        # 1. Penalizar keywords que causaron el error
        if sucursal_correcta_id and sucursal_detectada and sucursal_detectada != sucursal_correcta_id:
            for keyword in keywords_json.get('sucursal', []):
                cursor.execute("""
                    UPDATE ocr_sucursal_keywords
                    SET peso = GREATEST(peso - 1.0, 0.1),
                        usos_fallidos = usos_fallidos + 1,
                        updated_at = NOW()
                    WHERE sucursal_id = %s AND keyword = %s
                """, (sucursal_detectada, keyword))
                penalizadas.append(f"Sucursal: {keyword}")

        if unidad_correcta_id and unidad_detectada and unidad_detectada != unidad_correcta_id:
            for keyword in keywords_json.get('unidad', []):
                cursor.execute("""
                    UPDATE ocr_unidad_keywords
                    SET peso = GREATEST(peso - 1.0, 0.1),
                        usos_fallidos = usos_fallidos + 1,
                        updated_at = NOW()
                    WHERE unidad_funcional_id = %s AND keyword = %s
                """, (unidad_detectada, keyword))
                penalizadas.append(f"Unidad: {keyword}")

        # 2. Extraer keywords del texto y agregarlas a la unidad CORRECTA
        texto = keywords_json.get('texto_completo', '')
        if not texto and isinstance(datos_extraidos, dict):
            texto = datos_extraidos.get('text', '')

        if texto and unidad_correcta_id:
            nuevas = self._agregar_keywords_desde_texto(
                cursor, texto, unidad_correcta_id,
                sucursal_correcta_id, peso_inicial=5.0  # Peso alto porque viene de corrección humana
            )

        # 3. Aprender relación proveedor -> unidad funcional
        proveedor_aprendido = False
        if proveedor_id and unidad_correcta_id:
            proveedor_aprendido = self._aprender_relacion_proveedor(
                cursor, proveedor_id, unidad_correcta_id, sucursal_correcta_id
            )

        return {
            'nuevas': nuevas,
            'penalizadas': penalizadas,
            'proveedor_aprendido': proveedor_aprendido
        }

    def _agregar_keywords_desde_texto(
        self,
        cursor,
        texto: str,
        unidad_id: int,
        sucursal_id: Optional[int],
        peso_inicial: float = 3.0
    ) -> List[str]:
        """
        Extrae términos relevantes del texto y los agrega como keywords
        para la unidad funcional indicada.

        Estrategia:
        - Detecta el tipo de unidad (ALMACEN vs ADMINISTRACION)
        - Extrae términos del texto que coincidan con ese tipo
        - Solo agrega términos que NO existan ya para esa unidad
        - Evita términos genéricos (stopwords)
        """
        if not texto or not unidad_id:
            return []

        texto_upper = texto.upper()

        # Detectar tipo de unidad
        cursor.execute("""
            SELECT nombre FROM unidades_funcionales WHERE id = %s
        """, (unidad_id,))
        row = cursor.fetchone()
        if not row:
            return []

        nombre_unidad = row['nombre'].upper()
        es_almacen = 'ALMAC' in nombre_unidad
        es_admin = 'ADMINISTR' in nombre_unidad

        # Seleccionar pool de términos según tipo de unidad
        if es_almacen:
            terminos_candidatos = KEYWORDS_ALMACEN
        elif es_admin:
            terminos_candidatos = KEYWORDS_ADMINISTRACION
        else:
            terminos_candidatos = KEYWORDS_ALMACEN + KEYWORDS_ADMINISTRACION

        # Encontrar qué términos del pool están en el texto
        terminos_en_texto = [t for t in terminos_candidatos if t in texto_upper]

        # También extraer palabras largas del texto que no sean stopwords
        palabras_texto = re.findall(r'\b[A-ZÁÉÍÓÚÑ]{5,}\b', texto_upper)
        palabras_relevantes = [
            p for p in set(palabras_texto)
            if p not in STOPWORDS and len(p) >= 5
        ]

        # Combinar: términos del pool + palabras relevantes del texto
        candidatos = list(set(terminos_en_texto + palabras_relevantes[:20]))

        if not candidatos:
            return []

        # Obtener keywords que ya existen para esta unidad
        cursor.execute("""
            SELECT keyword FROM ocr_unidad_keywords
            WHERE unidad_funcional_id = %s
        """, (unidad_id,))
        existentes = {row['keyword'].upper() for row in cursor.fetchall()}

        # Agregar solo las que no existen
        agregadas = []
        for termino in candidatos:
            if termino in existentes or termino in STOPWORDS:
                continue
            if len(termino) < 4:
                continue

            try:
                cursor.execute("""
                    INSERT INTO ocr_unidad_keywords
                        (unidad_funcional_id, keyword, peso, activo, usos_exitosos, usos_fallidos)
                    VALUES (%s, %s, %s, TRUE, 1, 0)
                    ON CONFLICT (unidad_funcional_id, keyword) DO UPDATE
                        SET peso = LEAST(ocr_unidad_keywords.peso + 0.5, 10.0),
                            usos_exitosos = ocr_unidad_keywords.usos_exitosos + 1,
                            updated_at = NOW()
                """, (unidad_id, termino, peso_inicial))
                agregadas.append(termino)
            except Exception as e:
                logger.warning(f"No se pudo agregar keyword '{termino}': {e}")

        if agregadas:
            logger.info(
                f"Agregadas {len(agregadas)} keywords a unidad {unidad_id} "
                f"({nombre_unidad}): {agregadas[:5]}..."
            )

        return agregadas

    def _aprender_relacion_proveedor(
        self,
        cursor,
        proveedor_id: int,
        unidad_id: int,
        sucursal_id: Optional[int]
    ) -> bool:
        """
        Registra/refuerza la relación proveedor -> unidad funcional en ocr_proveedor_config.
        Si el proveedor ya tiene config, actualiza las unidades_funcionales_ids.
        Si no tiene config, crea una nueva entrada.
        """
        try:
            # Verificar si ya existe config para este proveedor
            cursor.execute("""
                SELECT id, unidades_funcionales_ids
                FROM ocr_proveedor_config
                WHERE proveedor_id = %s AND activo = TRUE
                LIMIT 1
            """, (proveedor_id,))
            config = cursor.fetchone()

            if config:
                # Actualizar: agregar unidad_id al array si no está
                unidades_actuales = config['unidades_funcionales_ids'] or []
                if isinstance(unidades_actuales, list) and unidad_id not in unidades_actuales:
                    unidades_actuales.insert(0, unidad_id)  # Insertar al inicio = mayor prioridad
                    cursor.execute("""
                        UPDATE ocr_proveedor_config
                        SET unidades_funcionales_ids = %s,
                            updated_at = NOW()
                        WHERE id = %s
                    """, (json.dumps(unidades_actuales), config['id']))
                    logger.info(f"ocr_proveedor_config actualizado: proveedor {proveedor_id} -> unidad {unidad_id}")
            else:
                # Crear nueva config
                cursor.execute("""
                    INSERT INTO ocr_proveedor_config
                        (proveedor_id, tipo_clasificacion, prioridad_clasificacion,
                         unidades_funcionales_ids, activo)
                    VALUES (%s, 'APRENDIDO', 100, %s::jsonb, TRUE)
                    ON CONFLICT (proveedor_id) DO UPDATE
                        SET unidades_funcionales_ids = %s::jsonb,
                            activo = TRUE,
                            updated_at = NOW()
                """, (proveedor_id, json.dumps([unidad_id]), json.dumps([unidad_id])))
                logger.info(f"ocr_proveedor_config creado: proveedor {proveedor_id} -> unidad {unidad_id}")

            # También registrar en ocr_learning_log si la tabla existe
            try:
                cursor.execute("""
                    INSERT INTO ocr_learning_log
                        (proveedor_id, unidad_funcional_id, sucursal_id, accion, origen)
                    VALUES (%s, %s, %s, 'RELACION_APRENDIDA', 'CORRECCION_MANUAL')
                """, (proveedor_id, unidad_id, sucursal_id))
            except Exception:
                pass  # La tabla puede tener estructura diferente

            return True
        except Exception as e:
            logger.warning(f"No se pudo registrar relación proveedor-unidad: {e}")
            return False

    def _auto_crear_regla_si_consistente(self, cursor, proveedor_id: int, unidad_id: int, sucursal_id: Optional[int]) -> bool:
        """
        Si el mismo proveedor ha sido corregido/validado 3+ veces a la misma unidad,
        crea una regla automática en ocr_reglas_clasificacion.
        """
        try:
            # Buscar NIT del proveedor
            cursor.execute("SELECT nit FROM proveedores WHERE id = %s", (proveedor_id,))
            prov = cursor.fetchone()
            if not prov:
                return False
            nit = prov['nit']
            
            # Contar cuántas veces este proveedor fue clasificado/corregido a esta unidad
            cursor.execute("""
                SELECT COUNT(*) as total
                FROM ocr_clasificacion_historial
                WHERE proveedor_detectado_id = %s
                  AND clasificacion_correcta IS NOT NULL
                  AND (
                    (clasificacion_correcta = true AND unidad_funcional_detectada_id = %s)
                    OR
                    (clasificacion_correcta = false AND unidad_correcta_id = %s)
                  )
            """, (proveedor_id, unidad_id, unidad_id))
            result = cursor.fetchone()
            total = result['total'] if result else 0
            
            if total < 3:
                return False
            
            # Verificar que no exista ya una regla simple para este NIT+unidad
            cursor.execute("""
                SELECT id FROM ocr_reglas_clasificacion
                WHERE condicion->>'nit' = %s
                  AND (accion->>'unidad_funcional_id')::int = %s
                  AND activo = true
            """, (str(nit), unidad_id))
            if cursor.fetchone():
                return False  # Ya existe
            
            # Obtener nombre de la unidad
            cursor.execute("SELECT nombre FROM unidades_funcionales WHERE id = %s", (unidad_id,))
            unidad = cursor.fetchone()
            nombre_unidad = unidad['nombre'] if unidad else f'unidad_{unidad_id}'
            
            # Crear regla automática
            condicion = json.dumps({"nit": str(nit)})
            accion = json.dumps({
                "unidad_funcional_id": unidad_id,
                "sucursal_id": sucursal_id,
                "nombre": nombre_unidad
            })
            
            cursor.execute("""
                INSERT INTO ocr_reglas_clasificacion (condicion, accion, prioridad, activo)
                VALUES (%s::jsonb, %s::jsonb, 100, true)
            """, (condicion, accion))
            
            logger.info(
                f"Regla auto-creada: NIT {nit} -> {nombre_unidad} "
                f"(basado en {total} validaciones consistentes)"
            )
            return True
            
        except Exception as e:
            logger.warning(f"No se pudo auto-crear regla: {e}")
            return False

    def _contar_validaciones_totales(self, cursor) -> int:
        """Cuenta el total de validaciones para decidir si reentrenar"""
        try:
            cursor.execute("""
                SELECT COUNT(*) as total
                FROM ocr_clasificacion_historial
                WHERE clasificacion_correcta IS NOT NULL
            """)
            result = cursor.fetchone()
            return result['total'] if result else 0
        except Exception:
            return 0
