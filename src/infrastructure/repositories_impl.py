from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
import json
from src.domain.repositories import OCRJobRepository
from src.domain.entities import OCRJob, JobStatus, FileType, ProcessingQuality
from src.infrastructure.database import OCRJobModel


class SQLAlchemyOCRJobRepository(OCRJobRepository):
    def __init__(self, db: Session):
        self.db = db
    
    def _model_to_entity(self, model: OCRJobModel) -> OCRJob:
        """Convert database model to domain entity"""
        metadata = json.loads(model.metadata) if model.metadata else {}
        return OCRJob(
            id=model.id,
            file_name=model.file_name,
            file_type=FileType(model.file_type),
            file_size=model.file_size,
            status=JobStatus(model.status),
            created_at=model.created_at,
            updated_at=model.updated_at,
            language=model.language,
            quality=ProcessingQuality(model.quality),
            result_text=model.result_text,
            confidence=model.confidence,
            processing_time=model.processing_time,
            error_message=model.error_message,
            metadata=metadata
        )
    
    def _entity_to_model(self, entity: OCRJob) -> OCRJobModel:
        """Convert domain entity to database model"""
        return OCRJobModel(
            id=entity.id,
            file_name=entity.file_name,
            file_type=entity.file_type,
            file_size=entity.file_size,
            status=entity.status,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            language=entity.language,
            quality=entity.quality,
            result_text=entity.result_text,
            confidence=entity.confidence,
            processing_time=entity.processing_time,
            error_message=entity.error_message,
            metadata=json.dumps(entity.metadata) if entity.metadata else None
        )
    
    async def create(self, job: OCRJob) -> OCRJob:
        model = self._entity_to_model(job)
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return self._model_to_entity(model)
    
    async def get_by_id(self, job_id: str) -> Optional[OCRJob]:
        model = self.db.query(OCRJobModel).filter(OCRJobModel.id == job_id).first()
        return self._model_to_entity(model) if model else None
    
    async def update(self, job: OCRJob) -> OCRJob:
        model = self.db.query(OCRJobModel).filter(OCRJobModel.id == job.id).first()
        if model:
            model.status = job.status
            model.updated_at = datetime.utcnow()
            model.result_text = job.result_text
            model.confidence = job.confidence
            model.processing_time = job.processing_time
            model.error_message = job.error_message
            model.metadata = json.dumps(job.metadata) if job.metadata else None
            self.db.commit()
            self.db.refresh(model)
            return self._model_to_entity(model)
        return job
    
    async def list_jobs(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None
    ) -> List[OCRJob]:
        query = self.db.query(OCRJobModel)
        if status:
            query = query.filter(OCRJobModel.status == status)
        models = query.order_by(OCRJobModel.created_at.desc()).offset(skip).limit(limit).all()
        return [self._model_to_entity(model) for model in models]
    
    async def delete(self, job_id: str) -> bool:
        model = self.db.query(OCRJobModel).filter(OCRJobModel.id == job_id).first()
        if model:
            self.db.delete(model)
            self.db.commit()
            return True
        return False
    
    async def get_jobs_older_than(self, date: datetime) -> List[OCRJob]:
        models = self.db.query(OCRJobModel).filter(OCRJobModel.created_at < date).all()
        return [self._model_to_entity(model) for model in models]
