"""
Script para limpiar archivos antiguos y trabajos completados
"""
import os
from datetime import datetime, timedelta
from src.infrastructure.database import SessionLocal
from src.infrastructure.repositories_impl import SQLAlchemyOCRJobRepository
from src.domain.entities import JobStatus
from src.config import settings
import structlog
import asyncio

logger = structlog.get_logger()


async def cleanup_old_jobs(days: int = 30):
    """Eliminar trabajos antiguos"""
    db = SessionLocal()
    try:
        repo = SQLAlchemyOCRJobRepository(db)
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        old_jobs = await repo.get_jobs_older_than(cutoff_date)
        
        for job in old_jobs:
            if job.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
                # Eliminar archivos asociados
                file_path = f"{settings.upload_dir}/{job.id}_{job.file_name}"
                if os.path.exists(file_path):
                    os.unlink(file_path)
                
                # Eliminar trabajo de la base de datos
                await repo.delete(job.id)
                logger.info("job_deleted", job_id=job.id, age_days=(datetime.utcnow() - job.created_at).days)
        
        logger.info("cleanup_completed", jobs_deleted=len(old_jobs))
        
    except Exception as e:
        logger.error("cleanup_failed", error=str(e))
        raise
    finally:
        db.close()


async def cleanup_temp_files(hours: int = 24):
    """Eliminar archivos temporales antiguos"""
    try:
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        for directory in [settings.upload_dir, settings.temp_dir]:
            if not os.path.exists(directory):
                continue
            
            deleted_count = 0
            for filename in os.listdir(directory):
                file_path = os.path.join(directory, filename)
                if os.path.isfile(file_path):
                    file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if file_time < cutoff_time:
                        os.unlink(file_path)
                        deleted_count += 1
            
            logger.info("temp_files_cleaned", directory=directory, count=deleted_count)
        
    except Exception as e:
        logger.error("temp_cleanup_failed", error=str(e))
        raise


async def main():
    """Ejecutar limpieza"""
    logger.info("Iniciando limpieza...")
    
    # Limpiar trabajos antiguos (más de 30 días)
    await cleanup_old_jobs(days=30)
    
    # Limpiar archivos temporales (más de 24 horas)
    await cleanup_temp_files(hours=24)
    
    logger.info("Limpieza completada")


if __name__ == "__main__":
    asyncio.run(main())
