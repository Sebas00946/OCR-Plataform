from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from src.domain.entities import JobStatus, FileType, ProcessingQuality


class OCRJobResponse(BaseModel):
    id: str
    file_name: str
    file_type: str
    file_size: int
    status: str
    created_at: datetime
    updated_at: datetime
    language: str
    quality: str
    result_text: Optional[str] = None
    confidence: Optional[float] = None
    processing_time: Optional[float] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = {}


class OCRJobCreate(BaseModel):
    language: str = Field(default="spa+eng", description="OCR language (e.g., 'spa+eng', 'eng', 'spa')")
    quality: ProcessingQuality = Field(default=ProcessingQuality.BALANCED, description="Processing quality")


class OCRResultResponse(BaseModel):
    job_id: str
    text: str
    confidence: float
    processing_time: float
    metadata: Dict[str, Any]


class JobListResponse(BaseModel):
    total: int
    jobs: list[OCRJobResponse]


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: datetime


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    timestamp: datetime
