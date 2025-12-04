import pytesseract
from PIL import Image
import cv2
import numpy as np
from typing import BinaryIO
import tempfile
import os
import time
from pdf2image import convert_from_path
import PyPDF2
import pdfplumber
from src.domain.services import OCRService, ImagePreprocessor
from src.domain.entities import OCRResult, ProcessingQuality
from src.domain.exceptions import OCRProcessingError
from src.config import settings
import structlog

logger = structlog.get_logger()


class OpenCVImagePreprocessor(ImagePreprocessor):
    def preprocess(self, image_path: str, quality: ProcessingQuality) -> str:
        """Preprocess image to improve OCR quality"""
        try:
            img = cv2.imread(image_path)
            
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            if quality == ProcessingQuality.FAST:
                # Minimal processing
                processed = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
            
            elif quality == ProcessingQuality.BALANCED:
                # Moderate processing
                # Denoise
                denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
                # Threshold
                processed = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
            
            else:  # ACCURATE
                # Aggressive processing
                # Denoise
                denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
                # Increase contrast
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                contrast = clahe.apply(denoised)
                # Threshold
                processed = cv2.threshold(contrast, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
                # Morphological operations
                kernel = np.ones((1, 1), np.uint8)
                processed = cv2.morphologyEx(processed, cv2.MORPH_CLOSE, kernel)
            
            # Save processed image
            output_path = image_path.replace('.', '_processed.')
            cv2.imwrite(output_path, processed)
            return output_path
            
        except Exception as e:
            logger.error("image_preprocessing_failed", error=str(e))
            return image_path  # Return original if preprocessing fails


class TesseractOCRService(OCRService):
    def __init__(self, preprocessor: ImagePreprocessor):
        self.preprocessor = preprocessor
        pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd
    
    async def process_image(
        self,
        image_data: BinaryIO,
        language: str = "spa+eng",
        quality: ProcessingQuality = ProcessingQuality.BALANCED
    ) -> OCRResult:
        """Process image and extract text"""
        temp_file = None
        processed_file = None
        
        try:
            start_time = time.time()
            
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
                temp_file.write(image_data.read())
                temp_path = temp_file.name
            
            # Preprocess image
            processed_path = self.preprocessor.preprocess(temp_path, quality)
            
            # Configure Tesseract
            config = self._get_tesseract_config(quality)
            
            # Perform OCR
            image = Image.open(processed_path)
            text = pytesseract.image_to_string(image, lang=language, config=config)
            
            # Get confidence
            data = pytesseract.image_to_data(image, lang=language, output_type=pytesseract.Output.DICT)
            confidences = [int(conf) for conf in data['conf'] if conf != '-1']
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            processing_time = time.time() - start_time
            
            logger.info(
                "image_ocr_completed",
                processing_time=processing_time,
                confidence=avg_confidence,
                text_length=len(text)
            )
            
            return OCRResult(
                text=text.strip(),
                confidence=avg_confidence,
                processing_time=processing_time,
                metadata={
                    "language": language,
                    "quality": quality.value,
                    "word_count": len(text.split())
                }
            )
            
        except Exception as e:
            logger.error("image_ocr_failed", error=str(e))
            raise OCRProcessingError(f"Failed to process image: {str(e)}")
        
        finally:
            # Cleanup temporary files
            if temp_file and os.path.exists(temp_path):
                os.unlink(temp_path)
            if processed_file and os.path.exists(processed_path) and processed_path != temp_path:
                os.unlink(processed_path)
    
    async def process_pdf(
        self,
        pdf_data: BinaryIO,
        language: str = "spa+eng",
        quality: ProcessingQuality = ProcessingQuality.BALANCED
    ) -> OCRResult:
        """Process PDF and extract text"""
        temp_file = None
        
        try:
            start_time = time.time()
            
            # Save PDF temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                temp_file.write(pdf_data.read())
                temp_path = temp_file.name
            
            # Try to extract text directly first
            text = self._extract_text_from_pdf(temp_path)
            
            if not text or len(text.strip()) < 50:
                # PDF is likely scanned, use OCR
                logger.info("pdf_requires_ocr", path=temp_path)
                text = await self._ocr_pdf(temp_path, language, quality)
                confidence = 85.0  # Estimated confidence for OCR
            else:
                confidence = 100.0  # High confidence for direct text extraction
            
            processing_time = time.time() - start_time
            
            logger.info(
                "pdf_ocr_completed",
                processing_time=processing_time,
                confidence=confidence,
                text_length=len(text)
            )
            
            return OCRResult(
                text=text.strip(),
                confidence=confidence,
                processing_time=processing_time,
                metadata={
                    "language": language,
                    "quality": quality.value,
                    "word_count": len(text.split())
                }
            )
            
        except Exception as e:
            logger.error("pdf_ocr_failed", error=str(e))
            raise OCRProcessingError(f"Failed to process PDF: {str(e)}")
        
        finally:
            if temp_file and os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def _extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text directly from PDF if available"""
        text = ""
        
        try:
            # Try pdfplumber first (better for complex layouts)
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception:
            # Fallback to PyPDF2
            try:
                with open(pdf_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    for page in pdf_reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
            except Exception as e:
                logger.warning("pdf_text_extraction_failed", error=str(e))
        
        return text
    
    async def _ocr_pdf(self, pdf_path: str, language: str, quality: ProcessingQuality) -> str:
        """Perform OCR on scanned PDF"""
        text = ""
        images = convert_from_path(pdf_path, dpi=300 if quality == ProcessingQuality.ACCURATE else 200)
        
        config = self._get_tesseract_config(quality)
        
        for i, image in enumerate(images):
            # Save image temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_img:
                image.save(temp_img.name, 'PNG')
                temp_img_path = temp_img.name
            
            try:
                # Preprocess
                processed_path = self.preprocessor.preprocess(temp_img_path, quality)
                
                # OCR
                page_image = Image.open(processed_path)
                page_text = pytesseract.image_to_string(page_image, lang=language, config=config)
                text += f"\n--- Page {i + 1} ---\n{page_text}\n"
                
            finally:
                if os.path.exists(temp_img_path):
                    os.unlink(temp_img_path)
                if processed_path != temp_img_path and os.path.exists(processed_path):
                    os.unlink(processed_path)
        
        return text
    
    def _get_tesseract_config(self, quality: ProcessingQuality) -> str:
        """Get Tesseract configuration based on quality"""
        if quality == ProcessingQuality.FAST:
            return '--psm 3 --oem 1'
        elif quality == ProcessingQuality.BALANCED:
            return '--psm 3 --oem 3'
        else:  # ACCURATE
            return '--psm 3 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789áéíóúñÁÉÍÓÚÑ.,;:!?()[]{}"\'-/@#$%&*+=<> '
