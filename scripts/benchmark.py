"""
Script para hacer benchmark del servicio OCR
"""
import time
import asyncio
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from src.infrastructure.ocr_service_impl import TesseractOCRService, OpenCVImagePreprocessor
from src.domain.entities import ProcessingQuality
import statistics


def create_test_image(width: int = 800, height: int = 600) -> BytesIO:
    """Crear imagen de prueba"""
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    
    # Agregar texto de prueba
    text = """
    Lorem ipsum dolor sit amet, consectetur adipiscing elit.
    Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
    Ut enim ad minim veniam, quis nostrud exercitation ullamco.
    Duis aute irure dolor in reprehenderit in voluptate velit.
    """
    
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
    except:
        font = ImageFont.load_default()
    
    draw.text((50, 50), text, fill='black', font=font)
    
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer


async def benchmark_quality(ocr_service, quality: ProcessingQuality, iterations: int = 5):
    """Benchmark para una calidad específica"""
    times = []
    confidences = []
    
    print(f"\nBenchmark para calidad: {quality.value}")
    print("-" * 50)
    
    for i in range(iterations):
        image = create_test_image()
        
        start = time.time()
        result = await ocr_service.process_image(
            image,
            language="eng",
            quality=quality
        )
        elapsed = time.time() - start
        
        times.append(elapsed)
        confidences.append(result.confidence)
        
        print(f"Iteración {i+1}: {elapsed:.2f}s - Confianza: {result.confidence:.2f}%")
    
    # Estadísticas
    print("\nEstadísticas:")
    print(f"  Tiempo promedio: {statistics.mean(times):.2f}s")
    print(f"  Tiempo mínimo: {min(times):.2f}s")
    print(f"  Tiempo máximo: {max(times):.2f}s")
    print(f"  Desviación estándar: {statistics.stdev(times):.2f}s")
    print(f"  Confianza promedio: {statistics.mean(confidences):.2f}%")
    
    return {
        "quality": quality.value,
        "avg_time": statistics.mean(times),
        "min_time": min(times),
        "max_time": max(times),
        "std_dev": statistics.stdev(times),
        "avg_confidence": statistics.mean(confidences)
    }


async def main():
    """Ejecutar benchmark completo"""
    print("=" * 50)
    print("OCR Service Benchmark")
    print("=" * 50)
    
    preprocessor = OpenCVImagePreprocessor()
    ocr_service = TesseractOCRService(preprocessor)
    
    iterations = 5
    results = []
    
    for quality in [ProcessingQuality.FAST, ProcessingQuality.BALANCED, ProcessingQuality.ACCURATE]:
        result = await benchmark_quality(ocr_service, quality, iterations)
        results.append(result)
    
    # Resumen
    print("\n" + "=" * 50)
    print("RESUMEN")
    print("=" * 50)
    print(f"{'Calidad':<15} {'Tiempo Avg':<15} {'Confianza Avg':<15}")
    print("-" * 50)
    
    for result in results:
        print(f"{result['quality']:<15} {result['avg_time']:<15.2f} {result['avg_confidence']:<15.2f}")
    
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
