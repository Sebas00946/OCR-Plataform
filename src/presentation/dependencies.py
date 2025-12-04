from fastapi import Depends, UploadFile, HTTPException, status
from sqlalchemy.orm import Session
from src.infrastructure.database import get_db
from src.infrastructure.repositories_impl import SQLAlchemyOCRJobRepository
from src.infrastructure.ocr_service_impl import TesseractOCRService, OpenCVImagePreprocessor
from src.infrastructure.storage_service_impl import LocalStorageService
from src.domain.exceptions import FileSizeExceededError, UnsupportedFileTypeError
from src.config import settings
import magic


def get_job_repository(db: Session = Depends(get_db)) -> SQLAlchemyOCRJobRepository:
    return SQLAlchemyOCRJobRepository(db)


def get_ocr_service() -> TesseractOCRService:
    preprocessor = OpenCVImagePreprocessor()
    return TesseractOCRService(preprocessor)


def get_storage_service() -> LocalStorageService:
    return LocalStorageService()


async def validate_file(file: UploadFile, allowed_extensions: list[str]) -> UploadFile:
    """Validate uploaded file"""
    # Check file size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning
    
    if file_size > settings.max_file_size_bytes:
        raise FileSizeExceededError(
            f"File size {file_size} bytes exceeds maximum allowed size of {settings.max_file_size_bytes} bytes"
        )
    
    # Check file extension
    file_ext = file.filename.split('.')[-1].lower() if '.' in file.filename else ''
    if file_ext not in allowed_extensions:
        raise UnsupportedFileTypeError(
            f"File type '.{file_ext}' is not supported. Allowed types: {', '.join(allowed_extensions)}"
        )
    
    # Verify MIME type
    file_content = await file.read(2048)
    await file.seek(0)
    
    try:
        mime = magic.from_buffer(file_content, mime=True)
        
        # Validate MIME type matches extension
        valid_mimes = {
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'webp': 'image/webp',
            'pdf': 'application/pdf'
        }
        
        expected_mime = valid_mimes.get(file_ext)
        if expected_mime and mime != expected_mime:
            raise UnsupportedFileTypeError(
                f"File MIME type '{mime}' does not match extension '.{file_ext}'"
            )
    except Exception as e:
        # If magic fails, continue with extension validation only
        pass
    
    return file


async def validate_image_file(file: UploadFile = None) -> UploadFile:
    """Validate image file"""
    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided"
        )
    return await validate_file(file, settings.allowed_image_extensions_list)


async def validate_pdf_file(file: UploadFile = None) -> UploadFile:
    """Validate PDF file"""
    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided"
        )
    return await validate_file(file, ['pdf'])
