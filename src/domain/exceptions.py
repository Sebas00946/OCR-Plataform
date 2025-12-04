class OCRException(Exception):
    """Base exception for OCR operations"""
    pass


class FileValidationError(OCRException):
    """Raised when file validation fails"""
    pass


class FileSizeExceededError(FileValidationError):
    """Raised when file size exceeds limit"""
    pass


class UnsupportedFileTypeError(FileValidationError):
    """Raised when file type is not supported"""
    pass


class OCRProcessingError(OCRException):
    """Raised when OCR processing fails"""
    pass


class JobNotFoundError(OCRException):
    """Raised when job is not found"""
    pass


class StorageError(OCRException):
    """Raised when storage operation fails"""
    pass


class AuthenticationError(OCRException):
    """Raised when authentication fails"""
    pass


class RateLimitExceededError(OCRException):
    """Raised when rate limit is exceeded"""
    pass
