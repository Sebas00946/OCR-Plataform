import pytest
from io import BytesIO
from PIL import Image
from src.infrastructure.ocr_service_impl import TesseractOCRService, OpenCVImagePreprocessor
from src.domain.entities import ProcessingQuality


@pytest.fixture
def ocr_service():
    """Create OCR service instance"""
    preprocessor = OpenCVImagePreprocessor()
    return TesseractOCRService(preprocessor)


@pytest.fixture
def sample_image():
    """Create a sample image with text"""
    img = Image.new('RGB', (200, 100), color='white')
    # In a real test, you would draw text on the image
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer


@pytest.mark.asyncio
async def test_process_image_fast(ocr_service, sample_image):
    """Test image processing with fast quality"""
    result = await ocr_service.process_image(
        sample_image,
        language="eng",
        quality=ProcessingQuality.FAST
    )
    
    assert result is not None
    assert isinstance(result.text, str)
    assert isinstance(result.confidence, float)
    assert isinstance(result.processing_time, float)
    assert result.processing_time > 0


@pytest.mark.asyncio
async def test_process_image_balanced(ocr_service, sample_image):
    """Test image processing with balanced quality"""
    result = await ocr_service.process_image(
        sample_image,
        language="eng",
        quality=ProcessingQuality.BALANCED
    )
    
    assert result is not None
    assert isinstance(result.text, str)


@pytest.mark.asyncio
async def test_process_image_accurate(ocr_service, sample_image):
    """Test image processing with accurate quality"""
    result = await ocr_service.process_image(
        sample_image,
        language="eng",
        quality=ProcessingQuality.ACCURATE
    )
    
    assert result is not None
    assert isinstance(result.text, str)
