"""
Tests for health check endpoints.
"""
import pytest
from fastapi.testclient import TestClient

def test_health_endpoint_success(client: TestClient):
    """Test that health endpoint returns healthy status."""
    response = client.get("/health/")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "version" in data
    assert "environment" in data

def test_root_endpoint(client: TestClient):
    """Test that root endpoint returns application info."""
    response = client.get("/")
    assert response.status_code == 200
    
    data = response.json()
    assert data["message"] == "Bubble Platform API"
    assert data["version"] == "1.0.0"
    assert "environment" in data

def test_features_endpoint(client: TestClient):
    """Test that features endpoint returns feature flags."""
    response = client.get("/api/v1/features/")
    assert response.status_code == 200
    
    data = response.json()
    assert "features" in data
    assert "timestamp" in data
    assert isinstance(data["features"], dict)

def test_api_docs_endpoint(client: TestClient):
    """Test that API documentation is accessible."""
    response = client.get("/docs")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]