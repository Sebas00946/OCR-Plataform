import os
import aiofiles
from typing import BinaryIO
from src.domain.services import StorageService
from src.domain.exceptions import StorageError
from src.config import settings
import structlog

logger = structlog.get_logger()


class LocalStorageService(StorageService):
    def __init__(self):
        self.upload_dir = settings.upload_dir
        self.results_dir = settings.results_dir
        self.temp_dir = settings.temp_dir
        
        # Create directories if they don't exist
        for directory in [self.upload_dir, self.results_dir, self.temp_dir]:
            os.makedirs(directory, exist_ok=True)
    
    async def save_file(self, file_data: BinaryIO, file_name: str) -> str:
        """Save file and return path"""
        try:
            file_path = os.path.join(self.upload_dir, file_name)
            
            async with aiofiles.open(file_path, 'wb') as f:
                content = file_data.read()
                await f.write(content)
            
            logger.info("file_saved", path=file_path, size=len(content))
            return file_path
            
        except Exception as e:
            logger.error("file_save_failed", error=str(e), file_name=file_name)
            raise StorageError(f"Failed to save file: {str(e)}")
    
    async def get_file(self, file_path: str) -> BinaryIO:
        """Get file by path"""
        try:
            if not os.path.exists(file_path):
                raise StorageError(f"File not found: {file_path}")
            
            return open(file_path, 'rb')
            
        except Exception as e:
            logger.error("file_get_failed", error=str(e), path=file_path)
            raise StorageError(f"Failed to get file: {str(e)}")
    
    async def delete_file(self, file_path: str) -> bool:
        """Delete file"""
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                logger.info("file_deleted", path=file_path)
                return True
            return False
            
        except Exception as e:
            logger.error("file_delete_failed", error=str(e), path=file_path)
            raise StorageError(f"Failed to delete file: {str(e)}")
