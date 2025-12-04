from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from typing import List
import uuid
from datetime import datetime
from src.presentation.schemas import (
    OCRJobResponse,
    OCRJobCreate,
    OCRResultResponse,
    JobListResponse
)
from src.presentation.dependencies import (
    get_job_repository,
    get_storage_service,
    validate_image_file,
    validate_pdf_file
)
from src.domain.repositories import OCRJobRepository
from src.domain.services import StorageService
from src.domain.entities import OCRJob, JobStatus, FileType, ProcessingQuality
from src.domain.exceptions import JobNotFoundError
from src.infrastructure.tasks import process_ocr_job
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/ocr", tags=["OCR"])


@router.post("/image", response_model=OCRJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def process_image(
    file: UploadFile = Depends(validate_image_file),
    language: str = Form(default="spa+eng"),
    quality: str = Form(default="balanced"),
    repository: OCRJobRepository = Depends(get_job_repository),
    storage: StorageService = Depends(get_storage_service)
):
    """
    Upload an image file for OCR processing.
    
    - **file**: Image file (PNG, JPG, JPEG, WEBP)
    - **language**: OCR language codes (e.g., 'spa+eng', 'eng', 'spa')
    - **quality**: Processing quality ('fast', 'balanced', 'accurate')
    
    Returns a job ID that can be used to check status and retrieve results.
    """
    try:
        # Create job
        job_id = str(uuid.uuid4())
        job = OCRJob(
            id=job_id,
            file_name=file.filename,
            file_type=FileType.IMAGE,
            file_size=file.size,
            status=JobStatus.PENDING,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            language=language,
            quality=ProcessingQuality(quality)
        )
        
        # Save file
        file_path = await storage.save_file(file.file, f"{job_id}_{file.filename}")
        
        # Save job to database
        job = await repository.create(job)
        
        # Queue processing task
        process_ocr_job.delay(job_id)
        
        logger.info("image_job_created", job_id=job_id, file_name=file.filename)
        
        return OCRJobResponse(**job.to_dict())
        
    except Exception as e:
        logger.error("image_job_creation_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create job: {str(e)}"
        )


@router.post("/pdf", response_model=OCRJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def process_pdf(
    file: UploadFile = Depends(validate_pdf_file),
    language: str = Form(default="spa+eng"),
    quality: str = Form(default="balanced"),
    repository: OCRJobRepository = Depends(get_job_repository),
    storage: StorageService = Depends(get_storage_service)
):
    """
    Upload a PDF file for OCR processing.
    
    - **file**: PDF file
    - **language**: OCR language codes (e.g., 'spa+eng', 'eng', 'spa')
    - **quality**: Processing quality ('fast', 'balanced', 'accurate')
    
    Automatically detects if PDF has selectable text or requires OCR.
    Returns a job ID that can be used to check status and retrieve results.
    """
    try:
        # Create job
        job_id = str(uuid.uuid4())
        job = OCRJob(
            id=job_id,
            file_name=file.filename,
            file_type=FileType.PDF,
            file_size=file.size,
            status=JobStatus.PENDING,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            language=language,
            quality=ProcessingQuality(quality)
        )
        
        # Save file
        file_path = await storage.save_file(file.file, f"{job_id}_{file.filename}")
        
        # Save job to database
        job = await repository.create(job)
        
        # Queue processing task
        process_ocr_job.delay(job_id)
        
        logger.info("pdf_job_created", job_id=job_id, file_name=file.filename)
        
        return OCRJobResponse(**job.to_dict())
        
    except Exception as e:
        logger.error("pdf_job_creation_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create job: {str(e)}"
        )


@router.post("/batch", response_model=List[OCRJobResponse], status_code=status.HTTP_202_ACCEPTED)
async def process_batch(
    files: List[UploadFile] = File(...),
    language: str = Form(default="spa+eng"),
    quality: str = Form(default="balanced"),
    repository: OCRJobRepository = Depends(get_job_repository),
    storage: StorageService = Depends(get_storage_service)
):
    """
    Upload multiple files for batch OCR processing.
    
    - **files**: Multiple image or PDF files
    - **language**: OCR language codes (e.g., 'spa+eng', 'eng', 'spa')
    - **quality**: Processing quality ('fast', 'balanced', 'accurate')
    
    Returns a list of job IDs for tracking each file.
    """
    jobs = []
    
    for file in files:
        try:
            # Determine file type
            file_ext = file.filename.split('.')[-1].lower()
            if file_ext == 'pdf':
                file_type = FileType.PDF
            else:
                file_type = FileType.IMAGE
            
            # Create job
            job_id = str(uuid.uuid4())
            job = OCRJob(
                id=job_id,
                file_name=file.filename,
                file_type=file_type,
                file_size=file.size,
                status=JobStatus.PENDING,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                language=language,
                quality=ProcessingQuality(quality)
            )
            
            # Save file
            await storage.save_file(file.file, f"{job_id}_{file.filename}")
            
            # Save job to database
            job = await repository.create(job)
            
            # Queue processing task
            process_ocr_job.delay(job_id)
            
            jobs.append(OCRJobResponse(**job.to_dict()))
            
        except Exception as e:
            logger.error("batch_job_creation_failed", file_name=file.filename, error=str(e))
            # Continue with other files
    
    logger.info("batch_jobs_created", count=len(jobs))
    return jobs


@router.get("/jobs/{job_id}", response_model=OCRJobResponse)
async def get_job_status(
    job_id: str,
    repository: OCRJobRepository = Depends(get_job_repository)
):
    """
    Get the status of an OCR job.
    
    - **job_id**: The unique job identifier
    
    Returns the current status and metadata of the job.
    """
    job = await repository.get_by_id(job_id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    return OCRJobResponse(**job.to_dict())


@router.get("/jobs/{job_id}/result", response_model=OCRResultResponse)
async def get_job_result(
    job_id: str,
    repository: OCRJobRepository = Depends(get_job_repository)
):
    """
    Get the result of a completed OCR job.
    
    - **job_id**: The unique job identifier
    
    Returns the extracted text and metadata. Only available for completed jobs.
    """
    job = await repository.get_by_id(job_id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job is not completed yet. Current status: {job.status.value}"
        )
    
    return OCRResultResponse(
        job_id=job.id,
        text=job.result_text or "",
        confidence=job.confidence or 0.0,
        processing_time=job.processing_time or 0.0,
        metadata=job.metadata
    )


@router.get("/history", response_model=JobListResponse)
async def get_job_history(
    skip: int = 0,
    limit: int = 100,
    status: str = None,
    repository: OCRJobRepository = Depends(get_job_repository)
):
    """
    Get the history of OCR jobs.
    
    - **skip**: Number of records to skip (for pagination)
    - **limit**: Maximum number of records to return
    - **status**: Filter by job status (optional)
    
    Returns a paginated list of jobs.
    """
    jobs = await repository.list_jobs(skip=skip, limit=limit, status=status)
    
    return JobListResponse(
        total=len(jobs),
        jobs=[OCRJobResponse(**job.to_dict()) for job in jobs]
    )


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: str,
    repository: OCRJobRepository = Depends(get_job_repository),
    storage: StorageService = Depends(get_storage_service)
):
    """
    Delete an OCR job and its associated files.
    
    - **job_id**: The unique job identifier
    """
    job = await repository.get_by_id(job_id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    # Delete files
    try:
        from src.config import settings
        file_path = f"{settings.upload_dir}/{job_id}_{job.file_name}"
        await storage.delete_file(file_path)
    except Exception as e:
        logger.warning("file_deletion_failed", job_id=job_id, error=str(e))
    
    # Delete job from database
    await repository.delete(job_id)
    
    logger.info("job_deleted", job_id=job_id)
