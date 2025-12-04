from celery import Celery
from src.config import settings
from src.infrastructure.database import SessionLocal
from src.infrastructure.repositories_impl import SQLAlchemyOCRJobRepository
from src.infrastructure.ocr_service_impl import TesseractOCRService, OpenCVImagePreprocessor
from src.infrastructure.storage_service_impl import LocalStorageService
from src.domain.entities import JobStatus, FileType, ProcessingQuality
import structlog
import time

logger = structlog.get_logger()

# Create Celery app
celery_app = Celery(
    "ocr_tasks",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=settings.max_processing_time_seconds,
)


@celery_app.task(name="process_ocr_job")
def process_ocr_job(job_id: str):
    """Process OCR job asynchronously"""
    db = SessionLocal()
    
    try:
        # Get repository and services
        repo = SQLAlchemyOCRJobRepository(db)
        preprocessor = OpenCVImagePreprocessor()
        ocr_service = TesseractOCRService(preprocessor)
        storage_service = LocalStorageService()
        
        # Get job
        import asyncio
        job = asyncio.run(repo.get_by_id(job_id))
        
        if not job:
            logger.error("job_not_found", job_id=job_id)
            return {"status": "error", "message": "Job not found"}
        
        # Update status to processing
        job.status = JobStatus.PROCESSING
        asyncio.run(repo.update(job))
        
        logger.info("processing_job", job_id=job_id, file_type=job.file_type)
        
        # Get file
        file_path = f"{settings.upload_dir}/{job_id}_{job.file_name}"
        file_data = asyncio.run(storage_service.get_file(file_path))
        
        # Process based on file type
        if job.file_type == FileType.IMAGE:
            result = asyncio.run(ocr_service.process_image(
                file_data,
                language=job.language,
                quality=job.quality
            ))
        else:  # PDF
            result = asyncio.run(ocr_service.process_pdf(
                file_data,
                language=job.language,
                quality=job.quality
            ))
        
        # Update job with results
        job.status = JobStatus.COMPLETED
        job.result_text = result.text
        job.confidence = result.confidence
        job.processing_time = result.processing_time
        job.metadata.update(result.metadata)
        
        asyncio.run(repo.update(job))
        
        logger.info(
            "job_completed",
            job_id=job_id,
            processing_time=result.processing_time,
            confidence=result.confidence
        )
        
        return {
            "status": "completed",
            "job_id": job_id,
            "text_length": len(result.text),
            "confidence": result.confidence
        }
        
    except Exception as e:
        logger.error("job_processing_failed", job_id=job_id, error=str(e))
        
        # Update job with error
        try:
            import asyncio
            job = asyncio.run(repo.get_by_id(job_id))
            if job:
                job.status = JobStatus.FAILED
                job.error_message = str(e)
                asyncio.run(repo.update(job))
        except Exception as update_error:
            logger.error("job_update_failed", error=str(update_error))
        
        return {"status": "error", "message": str(e)}
    
    finally:
        db.close()


@celery_app.task(name="cleanup_old_files")
def cleanup_old_files():
    """Cleanup old temporary files"""
    from datetime import datetime, timedelta
    import os
    
    try:
        cutoff_time = datetime.utcnow() - timedelta(hours=settings.cleanup_temp_files_after_hours)
        
        for directory in [settings.upload_dir, settings.temp_dir]:
            if not os.path.exists(directory):
                continue
            
            for filename in os.listdir(directory):
                file_path = os.path.join(directory, filename)
                if os.path.isfile(file_path):
                    file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if file_time < cutoff_time:
                        os.unlink(file_path)
                        logger.info("old_file_deleted", path=file_path)
        
        logger.info("cleanup_completed")
        return {"status": "completed"}
        
    except Exception as e:
        logger.error("cleanup_failed", error=str(e))
        return {"status": "error", "message": str(e)}
