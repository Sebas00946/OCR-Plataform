"""
API REST para clasificación de facturas
Compatible con Node.js backend
"""
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import psycopg2.extras
import tempfile
import os
import time
import traceback
from pathlib import Path

from .database import db
from .classifier import PDFClassifier
from .extractor import InvoiceExtractor
from .learning import LearningSystem
from .logger import ocr_logger
from .proveedor_matcher import ProveedorMatcher
from .proveedor_based_classifier import ProveedorBasedClassifier
from .comprobante_egreso_extractor import ComprobanteEgresoExtractor
from .engine.knowledge_base import kb
from .engine.fast_classifier import fast_classifier
from .qdrant_classifier import get_qdrant_classifier
from .llm_classifier import get_llm_classifier
from .probabilistic_classifier import probabilistic_classifier
from .multi_agent_classifier import multi_agent_classifier
from .config import get_cors_origins, is_production, is_debug

# Crear app
app = FastAPI(
    title="OCR Classification API",
    description="API para clasificación automática de facturas usando XML + PDF",
    version="1.0.0",
    debug=is_debug()
)

# CORS configurado por entorno
cors_origins = get_cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializar sistemas
classifier = PDFClassifier()
proveedor_classifier = ProveedorBasedClassifier()
extractor = InvoiceExtractor()
learning_system = LearningSystem()
proveedor_matcher = ProveedorMatcher()
comprobante_extractor = ComprobanteEgresoExtractor()


# ============================================
# EVENTOS DE CICLO DE VIDA
# ============================================

@app.on_event("startup")
async def startup_event():
    """Inicializar recursos al arrancar la app"""
    try:
        db.initialize()
        # Cargar toda la configuración de clasificación en RAM
        kb.initialize()
        ocr_logger.logger.info(f"KnowledgeBase cargada: {kb.get_stats()}")
        
        # Entrenar clasificador probabilístico desde historial
        try:
            probabilistic_classifier.load_from_history(limit=10000)
            ocr_logger.logger.info("Clasificador probabilístico entrenado")
        except Exception as e:
            ocr_logger.logger.warning(f"No se pudo entrenar clasificador probabilístico: {e}")
        
        ocr_logger.logger.info("Sistema inicializado correctamente")
    except Exception as e:
        ocr_logger.logger.error(f"Error en inicio de sistema: {e}")
        # No fallamos aquí para permitir que la app intente reconectar luego

@app.on_event("shutdown")
async def shutdown_event():
    """Limpiar recursos al cerrar la app"""
    try:
        db.close()
        ocr_logger.logger.info("Sistema cerrado correctamente")
    except Exception as e:
        ocr_logger.logger.error(f"Error en cierre de sistema: {e}")


# ============================================
# MIDDLEWARE PARA LOGGING
# ============================================

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware para registrar todas las peticiones"""
    start_time = time.time()
    
    # Obtener IP del cliente
    client_ip = request.client.host if request.client else "unknown"
    
    # Procesar request
    response = await call_next(request)
    
    # Calcular duración
    duration_ms = (time.time() - start_time) * 1000
    
    # Registrar petición
    ocr_logger.log_request(
        endpoint=str(request.url.path),
        method=request.method,
        status_code=response.status_code,
        duration_ms=duration_ms,
        client_ip=client_ip
    )
    
    return response


# ============================================
# MODELOS
# ============================================

class ClassificationResponse(BaseModel):
    success: bool
    sucursal: Optional[dict]
    unidad_funcional: Optional[dict]
    proveedor: Optional[dict]
    proveedor_match: Optional[dict]  # Información del match con la BD
    factura: Optional[dict]  # Datos de la factura (número, fecha, cufe)
    cliente: Optional[dict]  # Datos del cliente
    metadata: dict
    historial_id: Optional[int] = None


class ValidationRequest(BaseModel):
    historial_id: int
    es_correcta: bool
    sucursal_correcta_id: Optional[int] = None
    unidad_correcta_id: Optional[int] = None
    observaciones: Optional[str] = None


# ============================================
# ENDPOINTS
# ============================================

@app.get("/")
async def root():
    """Endpoint raíz"""
    return {
        "service": "OCR Classification API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "classify": "/api/classify",
            "validate": "/api/validate",
            "stats": "/api/stats",
            "health": "/api/health",
            "logs": "/api/logs"
        }
    }


@app.get("/api/health")
async def health_check():
    """Verificar estado del servicio"""
    try:
        # Verificar conexión a BD usando el pool
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
        
        return {
            "status": "healthy",
            "database": "connected",
            "version": "1.0.0"
        }
    except Exception as e:
        ocr_logger.log_error(
            endpoint="/api/health",
            error_message=str(e),
            error_type=type(e).__name__,
            traceback_info=traceback.format_exc()
        )
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")


@app.post("/api/classify", response_model=ClassificationResponse)
async def classify_invoice(
    background_tasks: BackgroundTasks,
    xml_file: Optional[UploadFile] = File(None),
    pdf_file: Optional[UploadFile] = File(None),
    factura_id: Optional[int] = None
):
    """
    Clasifica una factura usando XML y/o PDF
    
    Args:
        xml_file: Archivo XML (opcional)
        pdf_file: Archivo PDF (opcional)
        factura_id: ID de la factura en tu sistema (opcional)
    
    Returns:
        Clasificación con sucursal y unidad funcional
    """
    if not xml_file and not pdf_file:
        ocr_logger.log_error(
            endpoint="/api/classify",
            error_message="No se proporcionaron archivos",
            error_type="ValidationError"
        )
        raise HTTPException(
            status_code=400,
            detail="Debe proporcionar al menos un archivo (XML o PDF)"
        )
    
    xml_path = None
    pdf_path = None
    xml_filename = None
    pdf_filename = None
    
    try:
        # Guardar archivos temporalmente
        if xml_file:
            xml_filename = xml_file.filename
            # Verificar que el archivo no esté vacío
            xml_file.file.seek(0, 2)  # Ir al final
            xml_size = xml_file.file.tell()
            xml_file.file.seek(0)  # Volver al inicio
            
            if xml_size == 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"El archivo XML '{xml_filename}' está vacío (0 bytes)"
                )
            
            ocr_logger.logger.debug(f"XML recibido: {xml_filename} ({xml_size} bytes)")
            xml_path = _save_temp_file(xml_file, ".xml")
        
        if pdf_file:
            pdf_filename = pdf_file.filename
            # Verificar que el archivo no esté vacío
            pdf_file.file.seek(0, 2)  # Ir al final
            pdf_size = pdf_file.file.tell()
            pdf_file.file.seek(0)  # Volver al inicio
            
            if pdf_size == 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"El archivo PDF '{pdf_filename}' está vacío (0 bytes)"
                )
            
            ocr_logger.logger.debug(f"PDF recibido: {pdf_filename} ({pdf_size} bytes)")
            pdf_path = _save_temp_file(pdf_file, ".pdf")
        
        # Extraer texto
        try:
            data = extractor.extract_combined(xml_path, pdf_path)
            
            # Log de debugging
            ocr_logger.logger.debug(f"Extracción completada: xml_path={xml_path}, pdf_path={pdf_path}")
            ocr_logger.logger.debug(f"Texto extraído: {len(data.get('text', ''))} caracteres")
            ocr_logger.logger.debug(f"XML: {len(data.get('xml_text', ''))} chars, PDF: {len(data.get('pdf_text', ''))} chars")
            
        except Exception as e:
            import traceback
            ocr_logger.log_error(
                endpoint="/api/classify",
                error_message=f"Error al extraer texto: {str(e)}",
                error_type="ExtractionError",
                traceback_info=traceback.format_exc()
            )
            raise HTTPException(
                status_code=500,
                detail=f"Error al extraer texto: {str(e)}"
            )
        
        if not data.get('text'):
            error_detail = {
                'xml_path': xml_path,
                'pdf_path': pdf_path,
                'xml_exists': xml_path and os.path.exists(xml_path) if xml_path else False,
                'pdf_exists': pdf_path and os.path.exists(pdf_path) if pdf_path else False,
                'xml_size': os.path.getsize(xml_path) if xml_path and os.path.exists(xml_path) else 0,
                'pdf_size': os.path.getsize(pdf_path) if pdf_path and os.path.exists(pdf_path) else 0,
                'has_xml_text': bool(data.get('xml_text')),
                'has_pdf_text': bool(data.get('pdf_text'))
            }
            
            ocr_logger.log_error(
                endpoint="/api/classify",
                error_message="No se pudo extraer texto de los archivos",
                error_type="ExtractionError",
                traceback_info=str(error_detail)
            )
            raise HTTPException(
                status_code=400,
                detail=f"No se pudo extraer texto de los archivos. Detalles: {error_detail}"
            )
        
        # ── Cascada de clasificación con Multi-Agente ─────────────────────────
        # Sistema de agentes especializados que votan por la mejor clasificación:
        # 1. RuleAgent: Reglas exactas (máxima prioridad)
        # 2. ProviderAgent: Config específica del proveedor
        # 3. BayesianAgent: Inferencia probabilística con historial
        # 4. KeywordAgent: Scoring tradicional de keywords
        # 5. FallbackAgent: Heurísticas de último recurso
        # ─────────────────────────────────────────────────────────────────────
        xml_data = {
            'proveedor': data.get('proveedor', {}),
            'factura': data.get('factura', {}),
            'cliente': data.get('cliente', {}),
        }
        pdf_text = data.get('pdf_text', '') or data.get('text', '')
        proveedor_nit = xml_data['proveedor'].get('nit', '') if isinstance(xml_data['proveedor'], dict) else ''
        
        # Obtener proveedor_id
        proveedor_id = None
        if proveedor_nit:
            nit_limpio = ''.join(c for c in str(proveedor_nit) if c.isdigit())
            prov = kb.get_proveedor_by_nit(nit_limpio)
            if prov:
                proveedor_id = prov['id']
        
        # Detectar sucursal primero (necesaria para filtrar unidades)
        sucursal, _ = fast_classifier.classify(xml_data, pdf_text)
        sucursal_id = sucursal.get('id') if sucursal.get('success') else None
        
        # Clasificar con sistema multi-agente
        unidad, votos = multi_agent_classifier.classify(
            xml_data, pdf_text, sucursal_id, proveedor_id
        )
        
        clasificador_usado = unidad.get('method', 'multi_agent')
        score_actual = unidad.get('confidence', 0) * 100

        ocr_logger.logger.info(
            f"Clasificación: sucursal={sucursal.get('nombre')} "
            f"unidad={unidad.get('nombre')} confidence={unidad.get('confidence', 0):.2f} "
            f"método={clasificador_usado}"
        )
        
        # Buscar y relacionar proveedor automáticamente
        proveedor_data = data.get('proveedor', {})
        if isinstance(proveedor_data, dict) and 'proveedor' in proveedor_data:
            # Si viene anidado, extraer el diccionario interno
            proveedor_data = proveedor_data.get('proveedor', {})
        
        proveedor_match = proveedor_matcher.match_proveedor(proveedor_data)
        
        # Preparar datos de factura completos (incluyendo valores)
        factura_data = data.get('factura', {})
        
        # Log de debugging para valores
        if factura_data.get('valores'):
            ocr_logger.logger.debug(f"Valores de factura extraídos: {factura_data['valores']}")
        else:
            ocr_logger.logger.debug("No se extrajeron valores de la factura")
        
        # Guardar en historial (inmediatamente para obtener el ID)
        archivo_nombre = pdf_filename if pdf_filename else xml_filename
        historial_id = learning_system.save_classification(
            factura_id=factura_id,
            archivo_nombre=archivo_nombre,
            sucursal=sucursal,
            unidad=unidad,
            metadata=data,
            proveedor_id=proveedor_match.get('proveedor_id') if proveedor_match else None,
            confianza_proveedor=proveedor_match.get('confidence') if proveedor_match else None
        )
        
        # Registrar procesamiento de archivos
        ocr_logger.log_file_processing(
            factura_id=factura_id,
            xml_file=xml_filename,
            pdf_file=pdf_filename,
            sucursal_detectada=sucursal.get('nombre') if sucursal['success'] else None,
            unidad_detectada=unidad.get('nombre') if unidad['success'] else None,
            success=sucursal['success'] and unidad['success'],
            historial_id=historial_id
        )
        
        return ClassificationResponse(
            success=sucursal['success'] and unidad['success'],
            sucursal=sucursal if sucursal['success'] else None,
            unidad_funcional=unidad if unidad['success'] else None,
            proveedor=data.get('proveedor', {}),
            proveedor_match=proveedor_match,
            factura=data.get('factura', {}),
            cliente=data.get('cliente', {}),
            historial_id=historial_id,
            metadata={
                'xml_quality': data['xml_quality'],
                'xml_weight': data['xml_weight'],
                'pdf_weight': data['pdf_weight'],
                'has_xml': data['has_xml'],
                'has_pdf': data['has_pdf'],
                'clasificador': clasificador_usado
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        ocr_logger.log_error(
            endpoint="/api/classify",
            error_message=str(e),
            error_type=type(e).__name__,
            traceback_info=traceback.format_exc()
        )
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
    
    finally:
        # Limpiar archivos temporales
        if xml_path and os.path.exists(xml_path):
            os.unlink(xml_path)
        if pdf_path and os.path.exists(pdf_path):
            os.unlink(pdf_path)


@app.post("/api/validate")
async def validate_classification(validation: ValidationRequest):
    """
    Valida una clasificación y permite al sistema aprender
    
    Args:
        validation: Datos de validación
    
    Returns:
        Confirmación y sugerencias de mejora
    """
    try:
        # Registrar validación
        ocr_logger.log_validation(
            historial_id=validation.historial_id,
            es_correcta=validation.es_correcta,
            sucursal_correcta_id=validation.sucursal_correcta_id,
            unidad_correcta_id=validation.unidad_correcta_id,
            observaciones=validation.observaciones
        )
        
        result = learning_system.validate_and_learn(
            historial_id=validation.historial_id,
            es_correcta=validation.es_correcta,
            sucursal_correcta_id=validation.sucursal_correcta_id,
            unidad_correcta_id=validation.unidad_correcta_id,
            observaciones=validation.observaciones,
            auto_add_keywords=True  # Agregar keywords automáticamente
        )
        
        return {
            "success": True,
            "message": result.get('message', ''),
            "learning": {
                "weights_adjusted": result.get('weights_adjusted', False),
                "keywords_reforzadas": result.get('keywords_reforzadas', 0),
                "keywords_added": result.get('keywords_added', []),
                "keywords_suggested": result.get('keywords_suggested', [])
            }
        }
    
    except Exception as e:
        ocr_logger.log_error(
            endpoint="/api/validate",
            error_message=str(e),
            error_type=type(e).__name__,
            traceback_info=traceback.format_exc()
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
async def get_statistics():
    """Obtiene estadísticas del sistema"""
    try:
        # Nota: get_statistics debería implementarse en LearningSystem si no existe
        # Por ahora asumo que existe o se manejará el error
        stats = learning_system.get_statistics() if hasattr(learning_system, 'get_statistics') else {}
        
        # Registrar consulta de estadísticas
        ocr_logger.log_statistics(stats)
        
        return stats
    except Exception as e:
        ocr_logger.log_error(
            endpoint="/api/stats",
            error_message=str(e),
            error_type=type(e).__name__,
            traceback_info=traceback.format_exc()
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/keywords/sucursales/{sucursal_id}")
async def get_sucursal_keywords(sucursal_id: int):
    """Obtiene keywords de una sucursal"""
    try:
        # Nota: get_keywords debería implementarse en LearningSystem
        keywords = learning_system.get_keywords('sucursal', sucursal_id) if hasattr(learning_system, 'get_keywords') else []
        return {
            "success": True,
            "sucursal_id": sucursal_id,
            "keywords": keywords
        }
    except Exception as e:
        ocr_logger.log_error(
            endpoint=f"/api/keywords/sucursales/{sucursal_id}",
            error_message=str(e),
            error_type=type(e).__name__,
            traceback_info=traceback.format_exc()
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/keywords/unidades/{unidad_id}")
async def get_unidad_keywords(unidad_id: int):
    """Obtiene keywords de una unidad funcional"""
    try:
        keywords = learning_system.get_keywords('unidad', unidad_id) if hasattr(learning_system, 'get_keywords') else []
        return {
            "success": True,
            "unidad_id": unidad_id,
            "keywords": keywords
        }
    except Exception as e:
        ocr_logger.log_error(
            endpoint=f"/api/keywords/unidades/{unidad_id}",
            error_message=str(e),
            error_type=type(e).__name__,
            traceback_info=traceback.format_exc()
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/knowledge-base/stats")
async def knowledge_base_stats():
    """Estado de la base de conocimiento en RAM."""
    return {"success": True, "stats": kb.get_stats()}


@app.post("/api/knowledge-base/refresh")
async def knowledge_base_refresh():
    """Fuerza recarga de la KB desde BD (usar después de agregar keywords manualmente)."""
    try:
        kb.invalidate()
        return {"success": True, "stats": kb.get_stats(), "message": "KnowledgeBase recargada"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/proveedor/{nit}/historial")
async def get_proveedor_historial(nit: str, limit: int = 20):
    """
    Retorna el historial de clasificaciones de un proveedor por NIT.
    Útil para diagnosticar por qué una factura se clasificó incorrectamente.
    """
    try:
        import re as _re
        nit_limpio = _re.sub(r'[^0-9]', '', nit)
        with db.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT
                        h.id,
                        h.factura_id,
                        h.archivo_nombre,
                        s_det.nombre  AS sucursal_detectada,
                        uf_det.nombre AS unidad_detectada,
                        s_cor.nombre  AS sucursal_correcta,
                        uf_cor.nombre AS unidad_correcta,
                        h.clasificacion_correcta,
                        h.confianza_sucursal,
                        h.confianza_unidad,
                        h.fecha_validacion,
                        h.created_at
                    FROM ocr_clasificacion_historial h
                    JOIN proveedores p ON p.id = h.proveedor_detectado_id
                    LEFT JOIN sucursales s_det ON s_det.id = h.sucursal_detectada_id
                    LEFT JOIN unidades_funcionales uf_det ON uf_det.id = h.unidad_funcional_detectada_id
                    LEFT JOIN sucursales s_cor ON s_cor.id = h.sucursal_correcta_id
                    LEFT JOIN unidades_funcionales uf_cor ON uf_cor.id = h.unidad_correcta_id
                    WHERE REGEXP_REPLACE(p.nit, '[^0-9]', '', 'g') = %s
                    ORDER BY h.created_at DESC
                    LIMIT %s
                """, (nit_limpio, limit))
                rows = cursor.fetchall()

        return {
            "success": True,
            "nit": nit,
            "total": len(rows),
            "historial": [dict(r) for r in rows]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/logs")
async def get_logs_summary():
    """
    Obtiene resumen de logs del sistema
    
    Returns:
        Estadísticas de peticiones y archivos procesados
    """
    try:
        request_counts = ocr_logger.get_request_count()
        file_stats = ocr_logger.get_file_processing_count()
        
        return {
            "success": True,
            "peticiones_por_endpoint": request_counts,
            "archivos_procesados": file_stats,
            "archivos_log": {
                "api_requests": "logs/api_requests.log",
                "processed_files": "logs/processed_files.log",
                "statistics": "logs/statistics.log"
            }
        }
    except Exception as e:
        ocr_logger.log_error(
            endpoint="/api/logs",
            error_message=str(e),
            error_type=type(e).__name__,
            traceback_info=traceback.format_exc()
        )
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# COMPROBANTE DE EGRESO
# ============================================

from typing import List as TypingList

@app.post("/api/comprobante-egreso")
async def extract_comprobante_egreso(
    pdf_file: UploadFile = File(...),
):
    """
    Extrae datos de un comprobante de egreso en PDF.

    Campos extraídos:
    - consecutivo, fecha, estado, valor
    - beneficiario_nit, beneficiario_nombre
    - banco, detalle, planilla
    - facturas afectadas
    - movimientos contables

    Args:
        pdf_file: Archivo PDF del comprobante de egreso

    Returns:
        JSON con los datos extraídos
    """
    pdf_path = None

    try:
        # Validar archivo
        if not pdf_file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="El archivo debe ser un PDF")

        pdf_file.file.seek(0, 2)
        pdf_size = pdf_file.file.tell()
        pdf_file.file.seek(0)

        if pdf_size == 0:
            raise HTTPException(status_code=400, detail="El archivo PDF está vacío")

        # Guardar temporal
        pdf_path = _save_temp_file(pdf_file, ".pdf")

        # Extraer datos
        resultado = comprobante_extractor.extract(pdf_path)

        if not resultado.get('success'):
            raise HTTPException(
                status_code=422,
                detail=f"No se pudieron extraer datos del comprobante: {resultado.get('error', 'Error desconocido')}"
            )

        return resultado

    except HTTPException:
        raise
    except Exception as e:
        ocr_logger.log_error(
            endpoint="/api/comprobante-egreso",
            error_message=str(e),
            error_type=type(e).__name__,
            traceback_info=traceback.format_exc()
        )
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
    finally:
        if pdf_path and os.path.exists(pdf_path):
            os.unlink(pdf_path)


@app.post("/api/comprobantes-egreso/batch")
async def extract_comprobantes_egreso_batch(
    pdf_files: TypingList[UploadFile] = File(...),
):
    """
    Extrae datos de múltiples comprobantes de egreso en PDF.

    Args:
        pdf_files: Lista de archivos PDF

    Returns:
        JSON con resumen y lista de comprobantes extraídos
    """
    pdf_paths = []

    try:
        # Guardar todos los archivos temporalmente
        for pdf_file in pdf_files:
            if not pdf_file.filename.lower().endswith('.pdf'):
                continue
            path = _save_temp_file(pdf_file, ".pdf")
            pdf_paths.append(path)

        if not pdf_paths:
            raise HTTPException(status_code=400, detail="No se proporcionaron archivos PDF válidos")

        # Extraer datos de todos
        resultado = comprobante_extractor.extract_multiple(pdf_paths)

        return resultado

    except HTTPException:
        raise
    except Exception as e:
        ocr_logger.log_error(
            endpoint="/api/comprobantes-egreso/batch",
            error_message=str(e),
            error_type=type(e).__name__,
            traceback_info=traceback.format_exc()
        )
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
    finally:
        for path in pdf_paths:
            if os.path.exists(path):
                os.unlink(path)


# ============================================
# FUNCIONES AUXILIARES
# ============================================

def _save_temp_file(upload_file: UploadFile, suffix: str) -> str:
    """Guarda un archivo subido en temporal"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = upload_file.file.read()
        tmp.write(content)
        return tmp.name


def _get_unidades_activas(sucursal_id: Optional[int] = None) -> list:
    """Retorna unidades funcionales activas, filtradas por sucursal si se indica."""
    try:
        with db.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                if sucursal_id:
                    cursor.execute("""
                        SELECT id, nombre, codigo, sucursal_id
                        FROM unidades_funcionales
                        WHERE activo = TRUE AND sucursal_id = %s
                        ORDER BY nombre
                    """, (sucursal_id,))
                else:
                    cursor.execute("""
                        SELECT id, nombre, codigo, sucursal_id
                        FROM unidades_funcionales
                        WHERE activo = TRUE
                        ORDER BY nombre
                    """)
                return [dict(r) for r in cursor.fetchall()]
    except Exception:
        return []


# ============================================
# ENDPOINTS DE CLASIFICADOR PROBABILÍSTICO
# ============================================

@app.post("/api/probabilistic/retrain")
async def retrain_probabilistic_classifier(limit: int = 10000):
    """
    Reentrena el clasificador probabilístico desde el historial.
    
    Args:
        limit: Número máximo de registros a usar para entrenamiento
    
    Returns:
        Estadísticas del entrenamiento
    """
    try:
        probabilistic_classifier.load_from_history(limit=limit)
        
        stats = {
            'total_samples': probabilistic_classifier.total_samples,
            'unidades': len(probabilistic_classifier.priors),
            'keywords_unicas': sum(len(v) for v in probabilistic_classifier.keyword_likelihoods.values()),
            'proveedores': sum(len(v) for v in probabilistic_classifier.proveedor_likelihoods.values()),
        }
        
        return {
            "success": True,
            "message": f"Clasificador reentrenado con {limit} registros",
            "stats": stats
        }
    except Exception as e:
        ocr_logger.logger.error(f"Error reentrenando clasificador: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/probabilistic/stats")
async def get_probabilistic_stats():
    """Estadísticas del clasificador probabilístico."""
    if not probabilistic_classifier.loaded:
        return {
            "success": False,
            "message": "Clasificador no entrenado",
            "loaded": False
        }
    
    return {
        "success": True,
        "loaded": True,
        "total_samples": probabilistic_classifier.total_samples,
        "unidades": len(probabilistic_classifier.priors),
        "keywords_unicas": sum(len(v) for v in probabilistic_classifier.keyword_likelihoods.values()),
        "proveedores_conocidos": sum(len(v) for v in probabilistic_classifier.proveedor_likelihoods.values()),
        "ciudades_conocidas": sum(len(v) for v in probabilistic_classifier.ciudad_likelihoods.values()),
        "proveedor_ciudad_pairs": sum(len(v) for v in probabilistic_classifier.proveedor_ciudad_likelihoods.values()),
    }


@app.get("/api/multi-agent/explain/{historial_id}")
async def explain_classification(historial_id: int):
    """
    Explica cómo se clasificó una factura mostrando los votos de cada agente.
    
    Args:
        historial_id: ID del registro en ocr_clasificacion_historial
    
    Returns:
        Detalles de la clasificación con votos de agentes
    """
    try:
        with db.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT 
                        h.*,
                        p.nit as proveedor_nit,
                        p.razon_social as proveedor_nombre,
                        s_det.nombre as sucursal_detectada_nombre,
                        uf_det.nombre as unidad_detectada_nombre,
                        s_cor.nombre as sucursal_correcta_nombre,
                        uf_cor.nombre as unidad_correcta_nombre
                    FROM ocr_clasificacion_historial h
                    LEFT JOIN proveedores p ON p.id = h.proveedor_detectado_id
                    LEFT JOIN sucursales s_det ON s_det.id = h.sucursal_detectada_id
                    LEFT JOIN unidades_funcionales uf_det ON uf_det.id = h.unidad_funcional_detectada_id
                    LEFT JOIN sucursales s_cor ON s_cor.id = h.sucursal_correcta_id
                    LEFT JOIN unidades_funcionales uf_cor ON uf_cor.id = h.unidad_correcta_id
                    WHERE h.id = %s
                """, (historial_id,))
                
                registro = cursor.fetchone()
        
        if not registro:
            raise HTTPException(status_code=404, detail="Registro no encontrado")
        
        # Extraer datos para reclasificar
        datos_extraidos = registro.get('datos_extraidos') or {}
        xml_data = datos_extraidos.get('xml_data', {})
        pdf_text = datos_extraidos.get('text', '')
        
        # Reclasificar con multi-agente para obtener votos
        sucursal_id = registro['sucursal_detectada_id']
        proveedor_id = registro['proveedor_detectado_id']
        
        resultado, votos = multi_agent_classifier.classify(
            xml_data, pdf_text, sucursal_id, proveedor_id
        )
        
        return {
            "success": True,
            "historial": dict(registro),
            "reclasificacion": resultado,
            "votos": [
                {
                    "agente": v.agent_name,
                    "unidad_propuesta": v.unidad_nombre,
                    "confidence": v.confidence,
                    "razonamiento": v.reasoning,
                    "metadata": v.metadata
                }
                for v in votos
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        ocr_logger.logger.error(f"Error explicando clasificación: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# EJECUTAR
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
