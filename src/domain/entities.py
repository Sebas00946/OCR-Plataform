from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass, field


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class FileType(str, Enum):
    IMAGE = "image"
    PDF = "pdf"


class ProcessingQuality(str, Enum):
    FAST = "fast"
    BALANCED = "balanced"
    ACCURATE = "accurate"


@dataclass
class OCRJob:
    id: str
    file_name: str
    file_type: FileType
    file_size: int
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    language: str = "spa+eng"
    quality: ProcessingQuality = ProcessingQuality.BALANCED
    result_text: Optional[str] = None
    confidence: Optional[float] = None
    processing_time: Optional[float] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "file_name": self.file_name,
            "file_type": self.file_type.value,
            "file_size": self.file_size,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "language": self.language,
            "quality": self.quality.value,
            "result_text": self.result_text,
            "confidence": self.confidence,
            "processing_time": self.processing_time,
            "error_message": self.error_message,
            "metadata": self.metadata
        }


@dataclass
class OCRResult:
    text: str
    confidence: float
    processing_time: float
    metadata: Dict[str, Any] = field(default_factory=dict)
