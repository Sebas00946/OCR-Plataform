from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Application
    app_name: str = Field(default="OCR API", alias="APP_NAME")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    debug: bool = Field(default=False, alias="DEBUG")
    environment: str = Field(default="production", alias="ENVIRONMENT")
    
    # Server
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    workers: int = Field(default=4, alias="WORKERS")
    
    # Database
    database_url: str = Field(
        default="sqlite:///./ocr.db",
        alias="DATABASE_URL"
    )
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    
    # Celery
    celery_broker_url: str = Field(
        default="redis://localhost:6379/0",
        alias="CELERY_BROKER_URL"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/0",
        alias="CELERY_RESULT_BACKEND"
    )
    celery_workers: int = Field(default=4, alias="CELERY_WORKERS")
    
    # OCR Configuration
    tesseract_cmd: str = Field(
        default="/usr/bin/tesseract",
        alias="TESSERACT_CMD"
    )
    ocr_languages: str = Field(default="spa+eng", alias="OCR_LANGUAGES")
    ocr_default_quality: str = Field(default="balanced", alias="OCR_DEFAULT_QUALITY")
    
    # File Upload
    max_file_size_mb: int = Field(default=50, alias="MAX_FILE_SIZE_MB")
    allowed_image_extensions: str = Field(
        default="png,jpg,jpeg,webp",
        alias="ALLOWED_IMAGE_EXTENSIONS"
    )
    allowed_pdf_extensions: str = Field(default="pdf", alias="ALLOWED_PDF_EXTENSIONS")
    upload_dir: str = Field(default="./uploads", alias="UPLOAD_DIR")
    results_dir: str = Field(default="./results", alias="RESULTS_DIR")
    temp_dir: str = Field(default="./temp", alias="TEMP_DIR")
    
    # Processing
    max_processing_time_seconds: int = Field(
        default=300,
        alias="MAX_PROCESSING_TIME_SECONDS"
    )
    cleanup_temp_files_after_hours: int = Field(
        default=24,
        alias="CLEANUP_TEMP_FILES_AFTER_HOURS"
    )
    
    # Security
    api_key_enabled: bool = Field(default=True, alias="API_KEY_ENABLED")
    api_keys: str = Field(
        default="your-secret-api-key-here",
        alias="API_KEYS"
    )
    cors_origins: str = Field(
        default="http://localhost:3000",
        alias="CORS_ORIGINS"
    )
    
    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, alias="RATE_LIMIT_ENABLED")
    rate_limit_requests: int = Field(default=100, alias="RATE_LIMIT_REQUESTS")
    rate_limit_period_seconds: int = Field(
        default=3600,
        alias="RATE_LIMIT_PERIOD_SECONDS"
    )
    
    # Storage
    storage_type: str = Field(default="local", alias="STORAGE_TYPE")
    s3_bucket: str = Field(default="", alias="S3_BUCKET")
    s3_region: str = Field(default="", alias="S3_REGION")
    s3_access_key: str = Field(default="", alias="S3_ACCESS_KEY")
    s3_secret_key: str = Field(default="", alias="S3_SECRET_KEY")
    
    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(default="json", alias="LOG_FORMAT")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    @property
    def api_keys_list(self) -> List[str]:
        return [key.strip() for key in self.api_keys.split(",")]
    
    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    @property
    def allowed_image_extensions_list(self) -> List[str]:
        return [ext.strip() for ext in self.allowed_image_extensions.split(",")]
    
    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024


settings = Settings()
