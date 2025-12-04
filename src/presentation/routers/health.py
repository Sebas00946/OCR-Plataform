from fastapi import APIRouter
from datetime import datetime
from src.presentation.schemas import HealthResponse
from src.config import settings

router = APIRouter(tags=["Health"])


@router.get("/api/v1/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    
    Returns the current status and version of the API.
    """
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        timestamp=datetime.utcnow()
    )
