"""
API REST para clasificación de facturas
Compatible con Node.js backend
"""
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import tempfile
import os
from pathlib import Path

from .config import get_db_config
from .classifier import PDFClassifier
from .extractor import InvoiceExtractor
from .learning import LearningSystem

# Crear app
app = FastAPI(
    title="OCR Classification API",
    description="API para clasificación automática de facturas usando XML + PDF",
    version="1.0.0"
)

# CORS para Node.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializar sistemas
db_config = get_db_config()
classifier = PDFClassifier(db_config)
extractor = InvoiceExtractor()
learning_system = LearningSystem(db_config)


# ============================================
# MODELOS
# ============================================

class ClassificationResponse(BaseModel):
    success: bool
    sucursal: Optional[dict]
    unidad_funcional: Optional[dict]
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
            "health": "/api/health"
        }
    }


@app.get("/api/health")
async def health_check():
    """Verificar estado del servicio"""
    try:
        # Verificar conexión a BD
        import psycopg2
        conn = psycopg2.connect(**db_config)
        conn.close()
        
        return {
            "status": "healthy",
            "database": "connected",
            "version": "1.0.0"
        }
    except Exception as e:
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
        raise HTTPException(
            status_code=400,
            detail="Debe proporcionar al menos un archivo (XML o PDF)"
        )
    
    xml_path = None
    pdf_path = None
    
    try:
        # Guardar archivos temporalmente
        if xml_file:
            xml_path = _save_temp_file(xml_file, ".xml")
        
        if pdf_file:
            pdf_path = _save_temp_file(pdf_file, ".pdf")
        
        # Extraer texto
        data = extractor.extract_combined(xml_path, pdf_path)
        
        if not data['text']:
            raise HTTPException(
                status_code=400,
                detail="No se pudo extraer texto de los archivos"
            )
        
        # Clasificar
        sucursal, unidad = classifier.classify(
            data['text'],
            xml_weight=data['xml_weight'],
            pdf_weight=data['pdf_weight']
        )
        
        # Guardar en historial (inmediatamente para obtener el ID)
        archivo_nombre = pdf_file.filename if pdf_file else xml_file.filename
        historial_id = learning_system.save_classification(
            factura_id=factura_id,
            archivo_nombre=archivo_nombre,
            sucursal=sucursal,
            unidad=unidad,
            metadata=data
        )
        
        return ClassificationResponse(
            success=sucursal['success'] and unidad['success'],
            sucursal=sucursal if sucursal['success'] else None,
            unidad_funcional=unidad if unidad['success'] else None,
            historial_id=historial_id,
            metadata={
                'xml_quality': data['xml_quality'],
                'xml_weight': data['xml_weight'],
                'pdf_weight': data['pdf_weight'],
                'has_xml': data['has_xml'],
                'has_pdf': data['has_pdf']
            }
        )
    
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
        result = learning_system.validate_and_learn(
            historial_id=validation.historial_id,
            es_correcta=validation.es_correcta,
            sucursal_correcta_id=validation.sucursal_correcta_id,
            unidad_correcta_id=validation.unidad_correcta_id,
            observaciones=validation.observaciones
        )
        
        message = "Clasificación correcta - Keywords reforzadas" if validation.es_correcta else "Clasificación incorrecta - Sugerencias generadas"
        
        return {
            "success": True,
            "message": message,
            "keywords_reforzadas": result.get('keywords_reforzadas', 0),
            "sugerencias": result.get('sugerencias', [])
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
async def get_statistics():
    """Obtiene estadísticas del sistema"""
    try:
        stats = learning_system.get_statistics()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/keywords/sucursales/{sucursal_id}")
async def get_sucursal_keywords(sucursal_id: int):
    """Obtiene keywords de una sucursal"""
    try:
        keywords = learning_system.get_keywords('sucursal', sucursal_id)
        return {
            "success": True,
            "sucursal_id": sucursal_id,
            "keywords": keywords
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/keywords/unidades/{unidad_id}")
async def get_unidad_keywords(unidad_id: int):
    """Obtiene keywords de una unidad funcional"""
    try:
        keywords = learning_system.get_keywords('unidad', unidad_id)
        return {
            "success": True,
            "unidad_id": unidad_id,
            "keywords": keywords
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# FUNCIONES AUXILIARES
# ============================================

def _save_temp_file(upload_file: UploadFile, suffix: str) -> str:
    """Guarda un archivo subido en temporal"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = upload_file.file.read()
        tmp.write(content)
        return tmp.name


# ============================================
# EJECUTAR
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
