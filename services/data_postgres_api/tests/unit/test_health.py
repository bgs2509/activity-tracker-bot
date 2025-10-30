"""
Unit tests for health endpoint.

Tests the /health endpoint without requiring a running server.
"""
import pytest
from fastapi.testclient import TestClient


@pytest.mark.unit
def test_health_endpoint_returns_200():
    """Verify health endpoint returns 200 status code."""
    from src.main import app

    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200


@pytest.mark.unit
def test_health_endpoint_returns_json():
    """Verify health endpoint returns valid JSON."""
    from src.main import app

    client = TestClient(app)
    response = client.get("/health")

    assert response.headers["content-type"] == "application/json"
    data = response.json()
    assert "status" in data


@pytest.mark.unit
def test_health_endpoint_status_healthy():
    """Verify health endpoint returns healthy status."""
    from src.main import app

    client = TestClient(app)
    response = client.get("/health")

    data = response.json()
    assert data["status"] == "healthy"
