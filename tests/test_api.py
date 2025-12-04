import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.config import settings

client = TestClient(app)


def get_headers():
    """Get headers with API key"""
    if settings.api_key_enabled:
        return {"X-API-Key": settings.api_keys_list[0]}
    return {}


def test_health_check():
    """Test health check endpoint"""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "timestamp" in data


def test_root_endpoint():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data


def test_upload_image_without_file():
    """Test image upload without file"""
    response = client.post(
        "/api/v1/ocr/image",
        headers=get_headers()
    )
    assert response.status_code == 422  # Validation error


def test_upload_pdf_without_file():
    """Test PDF upload without file"""
    response = client.post(
        "/api/v1/ocr/pdf",
        headers=get_headers()
    )
    assert response.status_code == 422  # Validation error


def test_get_nonexistent_job():
    """Test getting a non-existent job"""
    response = client.get(
        "/api/v1/ocr/jobs/nonexistent-id",
        headers=get_headers()
    )
    assert response.status_code == 404


def test_get_job_history():
    """Test getting job history"""
    response = client.get(
        "/api/v1/ocr/history",
        headers=get_headers()
    )
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "jobs" in data
    assert isinstance(data["jobs"], list)


def test_api_key_required():
    """Test that API key is required when enabled"""
    if not settings.api_key_enabled:
        pytest.skip("API key authentication is disabled")
    
    response = client.get("/api/v1/ocr/history")
    assert response.status_code == 401


def test_invalid_api_key():
    """Test invalid API key"""
    if not settings.api_key_enabled:
        pytest.skip("API key authentication is disabled")
    
    response = client.get(
        "/api/v1/ocr/history",
        headers={"X-API-Key": "invalid-key"}
    )
    assert response.status_code == 401
