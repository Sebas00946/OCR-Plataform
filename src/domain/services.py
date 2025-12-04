from abc import ABC, abstractmethod
from typing import BinaryIO
from src.domain.entities import OCRResult, ProcessingQuality


class OCRService(ABC):
    @abstractmethod
    async def process_image(
        self,
        image_data: BinaryIO,
        language: str = "spa+eng",
        quality: ProcessingQuality = ProcessingQuality.BALANCED
    ) -> OCRResult:
        """Process image and extract text"""
        pass
    
    @abstractmethod
    async def process_pdf(
        self,
        pdf_data: BinaryIO,
        language: str = "spa+eng",
        quality: ProcessingQuality = ProcessingQuality.BALANCED
    ) -> OCRResult:
        """Process PDF and extract text"""
        pass


class ImagePreprocessor(ABC):
    @abstractmethod
    def preprocess(self, image_path: str, quality: ProcessingQuality) -> str:
        """Preprocess image to improve OCR quality"""
        pass


class StorageService(ABC):
    @abstractmethod
    async def save_file(self, file_data: BinaryIO, file_name: str) -> str:
        """Save file and return path"""
        pass
    
    @abstractmethod
    async def get_file(self, file_path: str) -> BinaryIO:
        """Get file by path"""
        pass
    
    @abstractmethod
    async def delete_file(self, file_path: str) -> bool:
        """Delete file"""
        pass
