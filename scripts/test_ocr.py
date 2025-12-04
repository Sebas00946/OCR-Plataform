"""
Script para probar el servicio OCR localmente
"""
from PIL import Image, ImageDraw, ImageFont
import io
from src.infrastructure.ocr_service_impl import TesseractOCRService, OpenCVImagePreprocessor
from src.domain.entities import ProcessingQuality
import asyncio
import structlog

logger = structlog.get_logger()


def create_test_image(text: str = "Hola Mundo\nOCR Test 123") -> io.BytesIO:
    """Crear una imagen de prueba con texto"""
    # Crear imagen blanca
    img = Image.new('RGB', (400, 200), color='white')
    draw = ImageDraw.Draw(img)
    
    # Dibujar texto
    try:
        # Intentar usar una fuente del sistema
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 40)
    except:
        # Usar fuente por defecto si no está disponible
        font = ImageFont.load_default()
    
    draw.text((20, 50), text, fill='black', font=font)
    
    # Guardar en buffer
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    return buffer


async def test_ocr():
    """Probar el servicio OCR"""
    logger.info("Iniciando prueba de OCR...")
    
    # Crear servicio
    preprocessor = OpenCVImagePreprocessor()
    ocr_service = TesseractOCRService(preprocessor)
    
    # Crear imagen de prueba
    test_text = "Hola Mundo\nOCR Test 123\nEspañol e Inglés"
    image_buffer = create_test_image(test_text)
    
    # Probar con diferentes calidades
    for quality in [ProcessingQuality.FAST, ProcessingQuality.BALANCED, ProcessingQuality.ACCURATE]:
        logger.info(f"Probando con calidad: {quality.value}")
        
        # Resetear buffer
        image_buffer.seek(0)
        
        # Procesar
        result = await ocr_service.process_image(
            image_buffer,
            language="spa+eng",
            quality=quality
        )
        
        logger.info(
            "ocr_result",
            quality=quality.value,
            text=result.text,
            confidence=result.confidence,
            processing_time=result.processing_time
        )
        
        print(f"\n{'='*50}")
        print(f"Calidad: {quality.value}")
        print(f"Texto extraído: {result.text}")
        print(f"Confianza: {result.confidence:.2f}%")
        print(f"Tiempo: {result.processing_time:.2f}s")
        print(f"{'='*50}\n")


if __name__ == "__main__":
    asyncio.run(test_ocr())
