from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from src.config import settings
from src.infrastructure.database import init_db
from src.presentation.routers import ocr, health
from src.presentation.middleware import (
    LoggingMiddleware,
    ErrorHandlingMiddleware,
    APIKeyMiddleware
)
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer() if settings.log_format == "json" else structlog.dev.ConsoleRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger()

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    Professional OCR API for extracting text from images and PDFs.
    
    ## Features
    
    * **Multi-language support**: Spanish, English, and more
    * **Image processing**: PNG, JPG, JPEG, WEBP
    * **PDF processing**: Both selectable text and scanned PDFs
    * **Async processing**: Queue-based processing for large files
    * **Quality options**: Fast, balanced, or accurate processing
    * **Batch processing**: Process multiple files at once
    
    ## Authentication
    
    Include your API key in the `X-API-Key` header for all requests (except /health and /docs).
    
    ## Rate Limiting
    
    API requests are rate-limited to prevent abuse. Current limit: {limit} requests per {period}.
    """.format(
        limit=settings.rate_limit_requests,
        period=f"{settings.rate_limit_period_seconds}s"
    ),
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Add custom middleware
app.add_middleware(LoggingMiddleware)
app.add_middleware(ErrorHandlingMiddleware)
if settings.api_key_enabled:
    app.add_middleware(APIKeyMiddleware)

# Include routers
app.include_router(health.router)
app.include_router(ocr.router)


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("application_starting", version=settings.app_version)
    
    # Initialize database
    init_db()
    logger.info("database_initialized")
    
    # Create necessary directories
    import os
    for directory in [settings.upload_dir, settings.results_dir, settings.temp_dir]:
        os.makedirs(directory, exist_ok=True)
    logger.info("directories_created")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("application_shutting_down")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "OCR API",
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/api/v1/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
