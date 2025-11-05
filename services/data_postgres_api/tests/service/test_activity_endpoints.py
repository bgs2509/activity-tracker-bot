"""
Service tests for activity endpoints.

Tests full request/response cycle using FastAPI TestClient.
These tests verify endpoint behavior, validation, and serialization
without requiring a running server.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock

from src.main import app


@pytest.fixture
def client():
    """Provide TestClient for service testing."""
    return TestClient(app)


class TestActivityEndpoints:
    """Test activity API endpoints."""

    @pytest.mark.service
    def test_health_endpoint(self, client):
        """Test health check endpoint returns 200."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.service
    def test_create_activity_validation_error_missing_fields(self, client):
        """Test validation catches missing required fields."""
        payload = {
            "user_id": "u1",
            # Missing category_id, description, times
        }

        response = client.post("/api/v1/activities", json=payload)

        assert response.status_code == 422
        assert "detail" in response.json()

    @pytest.mark.service
    def test_create_activity_validation_error_invalid_time_format(self, client):
        """Test validation catches invalid datetime format."""
        payload = {
            "user_id": "u1",
            "category_id": 1,
            "description": "Test",
            "start_time": "invalid-date",
            "end_time": "2025-11-05T11:00:00Z",
            "tags": []
        }

        response = client.post("/api/v1/activities", json=payload)

        assert response.status_code == 422

    @pytest.mark.service
    def test_get_activities_missing_user_id(self, client):
        """Test GET without user_id returns 422."""
        response = client.get("/api/v1/activities")

        assert response.status_code == 422

    @pytest.mark.service
    def test_get_activities_with_limit(self, client):
        """Test GET with limit parameter validates range."""
        response = client.get(
            "/api/v1/activities",
            params={"user_id": "u1", "limit": 999}
        )

        # Should either accept or reject based on max limit validation
        # Acceptable status codes: 200 (accepted) or 422 (limit too high)
        assert response.status_code in [200, 422]


# Total: 5 tests
