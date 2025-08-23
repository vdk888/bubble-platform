"""
Tests for health check endpoints.
"""
import pytest
from fastapi.testclient import TestClient

def test_health_endpoint_success(client: TestClient):
    """Test that health endpoint returns healthy status with standardized format."""
    response = client.get("/health/")
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] == True
    assert data["data"]["status"] == "healthy"
    assert "timestamp" in data["data"]
    assert "version" in data["data"]
    assert "environment" in data["data"]
    assert "message" in data
    assert "next_actions" in data
    assert isinstance(data["next_actions"], list)

def test_root_endpoint(client: TestClient):
    """Test that root endpoint returns application info with standardized format."""
    response = client.get("/")
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] == True
    assert data["data"]["name"] == "Bubble Platform API"
    assert data["data"]["version"] == "1.0.0"
    assert "environment" in data["data"]
    assert "message" in data
    assert "next_actions" in data
    assert isinstance(data["next_actions"], list)

def test_features_endpoint(client: TestClient):
    """Test that features endpoint returns feature flags with standardized format."""
    response = client.get("/api/v1/features/")
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] == True
    assert "features" in data["data"]
    assert "timestamp" in data["data"]
    assert isinstance(data["data"]["features"], dict)
    assert "message" in data
    assert "next_actions" in data
    assert isinstance(data["next_actions"], list)

def test_api_docs_endpoint(client: TestClient):
    """Test that API documentation is accessible."""
    response = client.get("/docs")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]