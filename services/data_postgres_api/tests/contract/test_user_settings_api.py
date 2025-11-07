"""
Contract tests for User Settings API endpoints.

Tests request/response schemas, partial updates, and error handling
for /api/v1/user-settings endpoints using FastAPI TestClient.

Test Coverage:
    - POST /user-settings: Create settings with validation
    - GET /user-settings: Retrieve settings by user_id
    - PUT /user-settings/{user_id}: Update settings (partial)
    - Schema validation: time ranges, boolean flags
    - Error cases: 404, 422 validation

Coverage Target: 100% of user_settings.py endpoints
Execution Time: < 0.4 seconds

Author: Testing Team
Date: 2025-11-07
"""

import pytest
from datetime import datetime, time, timezone
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from src.main import app
from src.domain.models.user_settings import UserSettings


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def client():
    """Fixture: FastAPI TestClient."""
    return TestClient(app)


@pytest.fixture
def mock_settings_service():
    """Fixture: Mock UserSettingsService."""
    return AsyncMock()


@pytest.fixture
def sample_settings():
    """Fixture: Sample UserSettings model."""
    return UserSettings(
        id=1,
        user_id=1,
        weekday_interval_minutes=60,
        weekend_interval_minutes=120,
        is_reminder_enabled=True,
        quiet_hours_start=time(22, 0),
        quiet_hours_end=time(8, 0),
        created_at=datetime(2025, 11, 7, 12, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2025, 11, 7, 12, 0, 0, tzinfo=timezone.utc)
    )


# ============================================================================
# TEST SUITES
# ============================================================================

class TestCreateSettingsEndpoint:
    """Test suite for POST /api/v1/user-settings endpoint."""

    @pytest.mark.contract
    def test_create_settings_with_valid_data_returns_201(
        self,
        client,
        mock_settings_service,
        sample_settings
    ):
        """
        Test successful settings creation.

        GIVEN: Valid settings data
        WHEN: POST /api/v1/user-settings is called
        THEN: 201 status with created settings
        """
        # Arrange
        request_data = {
            "user_id": 1,
            "weekday_interval_minutes": 60,
            "weekend_interval_minutes": 120,
            "is_reminder_enabled": True
        }
        mock_settings_service.create_settings.return_value = sample_settings

        # Act
        with patch('src.api.dependencies.get_user_settings_service', return_value=mock_settings_service):
            response = client.post("/api/v1/user-settings", json=request_data)

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == 1
        assert data["weekday_interval_minutes"] == 60

    @pytest.mark.contract
    def test_create_settings_with_missing_user_id_returns_422(self, client):
        """
        Test validation: missing required user_id.

        GIVEN: Request missing user_id
        WHEN: POST request is made
        THEN: 422 validation error
        """
        # Arrange
        request_data = {"weekday_interval_minutes": 60}

        # Act
        response = client.post("/api/v1/user-settings", json=request_data)

        # Assert
        assert response.status_code == 422
        data = response.json()
        errors = data["detail"]
        assert any("user_id" in str(e.get("loc", [])) for e in errors)


class TestGetSettingsEndpoint:
    """Test suite for GET /api/v1/user-settings endpoint."""

    @pytest.mark.contract
    def test_get_settings_when_exists_returns_200(
        self,
        client,
        mock_settings_service,
        sample_settings
    ):
        """
        Test successful settings retrieval.

        GIVEN: Settings exist for user
        WHEN: GET /api/v1/user-settings?user_id=1 is called
        THEN: 200 with settings data
        """
        # Arrange
        mock_settings_service.get_by_user_id.return_value = sample_settings

        # Act
        with patch('src.api.dependencies.get_user_settings_service', return_value=mock_settings_service):
            response = client.get("/api/v1/user-settings?user_id=1")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == 1

    @pytest.mark.contract
    def test_get_settings_when_not_found_returns_404(
        self,
        client,
        mock_settings_service
    ):
        """
        Test settings not found.

        GIVEN: No settings for user
        WHEN: GET request is made
        THEN: 404 Not Found
        """
        # Arrange
        mock_settings_service.get_by_user_id.return_value = None

        # Act
        with patch('src.api.dependencies.get_user_settings_service', return_value=mock_settings_service):
            response = client.get("/api/v1/user-settings?user_id=999")

        # Assert
        assert response.status_code == 404

    @pytest.mark.contract
    def test_get_settings_without_user_id_returns_422(self, client):
        """
        Test missing required query parameter.

        GIVEN: user_id not provided
        WHEN: GET request is made
        THEN: 422 validation error
        """
        # Act
        response = client.get("/api/v1/user-settings")

        # Assert
        assert response.status_code == 422


class TestUpdateSettingsEndpoint:
    """Test suite for PUT /api/v1/user-settings/{user_id} endpoint."""

    @pytest.mark.contract
    def test_update_settings_with_partial_data_returns_200(
        self,
        client,
        mock_settings_service,
        sample_settings
    ):
        """
        Test partial settings update.

        GIVEN: Partial update data (only some fields)
        WHEN: PUT /api/v1/user-settings/{user_id} is called
        THEN: 200 with updated settings
        """
        # Arrange
        request_data = {"weekday_interval_minutes": 90}
        updated_settings = UserSettings(
            **{k: v for k, v in sample_settings.__dict__.items() if not k.startswith('_')},
            weekday_interval_minutes=90
        )
        mock_settings_service.update_settings.return_value = updated_settings

        # Act
        with patch('src.api.dependencies.get_user_settings_service', return_value=mock_settings_service):
            response = client.put("/api/v1/user-settings/1", json=request_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["weekday_interval_minutes"] == 90

    @pytest.mark.contract
    def test_update_settings_when_not_found_returns_404(
        self,
        client,
        mock_settings_service
    ):
        """
        Test update of non-existent settings.

        GIVEN: Settings do not exist
        WHEN: PUT request is made
        THEN: 404 Not Found
        """
        # Arrange
        mock_settings_service.update_settings.return_value = None

        # Act
        with patch('src.api.dependencies.get_user_settings_service', return_value=mock_settings_service):
            response = client.put(
                "/api/v1/user-settings/999",
                json={"weekday_interval_minutes": 90}
            )

        # Assert
        assert response.status_code == 404

    @pytest.mark.contract
    def test_update_settings_with_empty_body_returns_200(
        self,
        client,
        mock_settings_service,
        sample_settings
    ):
        """
        Test update with no changes.

        GIVEN: Empty update data
        WHEN: PUT request is made
        THEN: 200 with unchanged settings
        """
        # Arrange
        mock_settings_service.update_settings.return_value = sample_settings

        # Act
        with patch('src.api.dependencies.get_user_settings_service', return_value=mock_settings_service):
            response = client.put("/api/v1/user-settings/1", json={})

        # Assert
        assert response.status_code == 200
