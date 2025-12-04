from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime
from src.domain.entities import OCRJob


class OCRJobRepository(ABC):
    @abstractmethod
    async def create(self, job: OCRJob) -> OCRJob:
        """Create a new OCR job"""
        pass
    
    @abstractmethod
    async def get_by_id(self, job_id: str) -> Optional[OCRJob]:
        """Get job by ID"""
        pass
    
    @abstractmethod
    async def update(self, job: OCRJob) -> OCRJob:
        """Update existing job"""
        pass
    
    @abstractmethod
    async def list_jobs(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None
    ) -> List[OCRJob]:
        """List jobs with pagination and filtering"""
        pass
    
    @abstractmethod
    async def delete(self, job_id: str) -> bool:
        """Delete a job"""
        pass
    
    @abstractmethod
    async def get_jobs_older_than(self, date: datetime) -> List[OCRJob]:
        """Get jobs older than specified date"""
        pass
