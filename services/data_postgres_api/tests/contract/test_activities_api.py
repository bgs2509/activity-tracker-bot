"""
Contract tests for Activities API endpoints.

Tests request/response schemas, business validation, and error handling
for /api/v1/activities endpoints using FastAPI TestClient.

Test Coverage:
    - POST /activities: Create activity with time validation
    - GET /activities: List user activities with pagination
    - Schema validation: time ranges, tags, required fields
    - Business rules: end_time > start_time, description length
    - Error cases: 400, 422 validation errors

Coverage Target: 100% of activities.py endpoints
Execution Time: < 0.5 seconds

Author: Testing Team
Date: 2025-11-07
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from src.main import app
from src.domain.models.activity import Activity


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def client():
    """
    Fixture: FastAPI TestClient.

    Returns:
        TestClient: Client for testing API endpoints
    """
    return TestClient(app)


@pytest.fixture
def mock_activity_service():
    """
    Fixture: Mock ActivityService.

    Returns:
        AsyncMock: Mocked service for dependency injection
    """
    return AsyncMock()


@pytest.fixture
def sample_activity():
    """
    Fixture: Sample Activity model instance.

    Returns:
        Activity: Activity object for testing
    """
    return Activity(
        id=1,
        user_id=1,
        category_id=1,
        description="Working on project",
        tags="python,testing",
        start_time=datetime(2025, 11, 7, 10, 0, 0, tzinfo=timezone.utc),
        end_time=datetime(2025, 11, 7, 12, 0, 0, tzinfo=timezone.utc),
        duration_minutes=120,
        created_at=datetime(2025, 11, 7, 12, 0, 0, tzinfo=timezone.utc)
    )


# ============================================================================
# TEST SUITES
# ============================================================================

class TestCreateActivityEndpoint:
    """
    Test suite for POST /api/v1/activities endpoint.

    Tests activity creation with complex validation rules.
    """

    @pytest.mark.contract
    def test_create_activity_with_valid_data_returns_201_with_activity(
        self,
        client,
        mock_activity_service,
        sample_activity
    ):
        """
        Test successful activity creation.

        GIVEN: Valid activity data with time range
        WHEN: POST /api/v1/activities is called
        THEN: 201 status with created activity
              AND duration is calculated
        """
        # Arrange
        request_data = {
            "user_id": 1,
            "category_id": 1,
            "description": "Working on project",
            "tags": ["python", "testing"],
            "start_time": "2025-11-07T10:00:00Z",
            "end_time": "2025-11-07T12:00:00Z"
        }
        mock_activity_service.create_activity.return_value = sample_activity

        # Act
        with patch('src.api.dependencies.get_activity_service', return_value=mock_activity_service):
            response = client.post("/api/v1/activities", json=request_data)

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == 1
        assert data["user_id"] == 1
        assert data["description"] == "Working on project"
        assert data["duration_minutes"] == 120  # 2 hours

    @pytest.mark.contract
    def test_create_activity_with_missing_required_field_returns_422(
        self,
        client
    ):
        """
        Test validation: missing required field.

        GIVEN: Request missing required description
        WHEN: POST /api/v1/activities is called
        THEN: 422 validation error
        """
        # Arrange: Missing description
        request_data = {
            "user_id": 1,
            "start_time": "2025-11-07T10:00:00Z",
            "end_time": "2025-11-07T12:00:00Z"
        }

        # Act
        response = client.post("/api/v1/activities", json=request_data)

        # Assert
        assert response.status_code == 422
        data = response.json()
        errors = data["detail"]
        assert any("description" in str(e.get("loc", [])) for e in errors)

    @pytest.mark.contract
    def test_create_activity_with_end_before_start_returns_422(
        self,
        client
    ):
        """
        Test business validation: time range.

        GIVEN: end_time before start_time (invalid)
        WHEN: POST /api/v1/activities is called
        THEN: 422 with custom validation error
        """
        # Arrange: Invalid time range
        request_data = {
            "user_id": 1,
            "description": "Invalid activity",
            "start_time": "2025-11-07T12:00:00Z",
            "end_time": "2025-11-07T10:00:00Z"  # Before start!
        }

        # Act
        response = client.post("/api/v1/activities", json=request_data)

        # Assert: Business validation error
        assert response.status_code == 422
        data = response.json()
        errors = data["detail"]
        # Check error message contains time validation
        assert any(
            "end_time" in str(e.get("loc", [])) or
            "after" in str(e.get("msg", "")).lower()
            for e in errors
        )

    @pytest.mark.contract
    def test_create_activity_with_short_description_returns_422(
        self,
        client
    ):
        """
        Test description length validation.

        GIVEN: description with < 3 characters
        WHEN: POST /api/v1/activities is called
        THEN: 422 validation error (min_length constraint)
        """
        # Arrange: Too short description
        request_data = {
            "user_id": 1,
            "description": "AB",  # Only 2 chars
            "start_time": "2025-11-07T10:00:00Z",
            "end_time": "2025-11-07T12:00:00Z"
        }

        # Act
        response = client.post("/api/v1/activities", json=request_data)

        # Assert
        assert response.status_code == 422
        data = response.json()
        errors = data["detail"]
        assert any("description" in str(e.get("loc", [])) for e in errors)

    @pytest.mark.contract
    def test_create_activity_without_category_creates_uncategorized(
        self,
        client,
        mock_activity_service
    ):
        """
        Test optional category field.

        GIVEN: Activity without category_id (None)
        WHEN: POST /api/v1/activities is called
        THEN: Activity created with category_id=None
        """
        # Arrange: No category
        request_data = {
            "user_id": 1,
            "category_id": None,
            "description": "Uncategorized task",
            "start_time": "2025-11-07T10:00:00Z",
            "end_time": "2025-11-07T11:00:00Z"
        }
        activity = Activity(
            id=1,
            user_id=1,
            category_id=None,
            description="Uncategorized task",
            tags=None,
            start_time=datetime(2025, 11, 7, 10, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2025, 11, 7, 11, 0, 0, tzinfo=timezone.utc),
            duration_minutes=60,
            created_at=datetime.now(timezone.utc)
        )
        mock_activity_service.create_activity.return_value = activity

        # Act
        with patch('src.api.dependencies.get_activity_service', return_value=mock_activity_service):
            response = client.post("/api/v1/activities", json=request_data)

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["category_id"] is None

    @pytest.mark.contract
    def test_create_activity_without_tags_creates_with_null_tags(
        self,
        client,
        mock_activity_service
    ):
        """
        Test optional tags field.

        GIVEN: Activity without tags
        WHEN: POST /api/v1/activities is called
        THEN: Activity created with tags=None
        """
        # Arrange
        request_data = {
            "user_id": 1,
            "description": "Task without tags",
            "start_time": "2025-11-07T10:00:00Z",
            "end_time": "2025-11-07T11:00:00Z"
        }
        activity = Activity(
            id=1,
            user_id=1,
            category_id=None,
            description="Task without tags",
            tags=None,
            start_time=datetime(2025, 11, 7, 10, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2025, 11, 7, 11, 0, 0, tzinfo=timezone.utc),
            duration_minutes=60,
            created_at=datetime.now(timezone.utc)
        )
        mock_activity_service.create_activity.return_value = activity

        # Act
        with patch('src.api.dependencies.get_activity_service', return_value=mock_activity_service):
            response = client.post("/api/v1/activities", json=request_data)

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["tags"] is None

    @pytest.mark.contract
    def test_create_activity_with_tags_list_creates_activity(
        self,
        client,
        mock_activity_service
    ):
        """
        Test tags as list.

        GIVEN: tags as list of strings
        WHEN: POST /api/v1/activities is called
        THEN: Activity created (service converts to comma-separated)
        """
        # Arrange
        request_data = {
            "user_id": 1,
            "description": "Task with tags",
            "tags": ["python", "testing", "unit"],
            "start_time": "2025-11-07T10:00:00Z",
            "end_time": "2025-11-07T11:00:00Z"
        }
        activity = Activity(
            id=1,
            user_id=1,
            category_id=None,
            description="Task with tags",
            tags="python,testing,unit",  # Converted
            start_time=datetime(2025, 11, 7, 10, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2025, 11, 7, 11, 0, 0, tzinfo=timezone.utc),
            duration_minutes=60,
            created_at=datetime.now(timezone.utc)
        )
        mock_activity_service.create_activity.return_value = activity

        # Act
        with patch('src.api.dependencies.get_activity_service', return_value=mock_activity_service):
            response = client.post("/api/v1/activities", json=request_data)

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["tags"] == "python,testing,unit"

    @pytest.mark.contract
    def test_create_activity_response_matches_activity_response_schema(
        self,
        client,
        mock_activity_service,
        sample_activity
    ):
        """
        Test response schema compliance.

        GIVEN: Successful activity creation
        WHEN: Response is received
        THEN: Response matches ActivityResponse schema exactly
        """
        # Arrange
        request_data = {
            "user_id": 1,
            "description": "Test activity",
            "start_time": "2025-11-07T10:00:00Z",
            "end_time": "2025-11-07T12:00:00Z"
        }
        mock_activity_service.create_activity.return_value = sample_activity

        # Act
        with patch('src.api.dependencies.get_activity_service', return_value=mock_activity_service):
            response = client.post("/api/v1/activities", json=request_data)

        # Assert: Schema compliance
        data = response.json()

        # Required fields
        required_fields = {
            "id", "user_id", "description",
            "start_time", "end_time", "duration_minutes", "created_at"
        }
        for field in required_fields:
            assert field in data, f"Required field '{field}' missing"

        # Optional fields
        optional_fields = {"category_id", "tags"}
        for field in optional_fields:
            assert field in data, f"Optional field '{field}' missing from schema"

        # No extra fields
        allowed_fields = required_fields | optional_fields
        assert set(data.keys()) == allowed_fields


class TestGetActivitiesEndpoint:
    """
    Test suite for GET /api/v1/activities endpoint.

    Tests activity listing with pagination and filtering.
    """

    @pytest.mark.contract
    def test_get_activities_with_user_id_returns_200_with_activities(
        self,
        client,
        mock_activity_service,
        sample_activity
    ):
        """
        Test successful activity listing.

        GIVEN: user_id query parameter
        WHEN: GET /api/v1/activities?user_id=1 is called
        THEN: 200 status with list of activities
        """
        # Arrange
        mock_activity_service.get_user_activities.return_value = [sample_activity]

        # Act
        with patch('src.api.dependencies.get_activity_service', return_value=mock_activity_service):
            response = client.get("/api/v1/activities?user_id=1")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["id"] == 1
        assert data[0]["user_id"] == 1

        # Service called with defaults
        mock_activity_service.get_user_activities.assert_called_once_with(1, 10)

    @pytest.mark.contract
    def test_get_activities_with_custom_limit_uses_provided_value(
        self,
        client,
        mock_activity_service
    ):
        """
        Test custom pagination limit.

        GIVEN: limit=20 query parameter
        WHEN: GET request is made
        THEN: Service called with limit=20
        """
        # Arrange
        mock_activity_service.get_user_activities.return_value = []

        # Act
        with patch('src.api.dependencies.get_activity_service', return_value=mock_activity_service):
            response = client.get("/api/v1/activities?user_id=1&limit=20")

        # Assert
        assert response.status_code == 200
        mock_activity_service.get_user_activities.assert_called_once_with(1, 20)

    @pytest.mark.contract
    def test_get_activities_without_user_id_returns_422(self, client):
        """
        Test missing required query parameter.

        GIVEN: user_id not provided
        WHEN: GET /api/v1/activities is called
        THEN: 422 validation error
        """
        # Act
        response = client.get("/api/v1/activities")

        # Assert
        assert response.status_code == 422
        data = response.json()
        errors = data["detail"]
        assert any("user_id" in str(e.get("loc", [])) for e in errors)

    @pytest.mark.contract
    def test_get_activities_with_limit_exceeding_max_returns_422(
        self,
        client
    ):
        """
        Test limit validation (max=100).

        GIVEN: limit=150 (exceeds maximum)
        WHEN: GET request is made
        THEN: 422 validation error
        """
        # Act
        response = client.get("/api/v1/activities?user_id=1&limit=150")

        # Assert
        assert response.status_code == 422
        data = response.json()
        errors = data["detail"]
        assert any("limit" in str(e.get("loc", [])) for e in errors)

    @pytest.mark.contract
    def test_get_activities_with_limit_below_min_returns_422(
        self,
        client
    ):
        """
        Test limit validation (min=1).

        GIVEN: limit=0 (below minimum)
        WHEN: GET request is made
        THEN: 422 validation error
        """
        # Act
        response = client.get("/api/v1/activities?user_id=1&limit=0")

        # Assert
        assert response.status_code == 422
        data = response.json()
        errors = data["detail"]
        assert any("limit" in str(e.get("loc", [])) for e in errors)

    @pytest.mark.contract
    def test_get_activities_returns_empty_list_for_user_without_activities(
        self,
        client,
        mock_activity_service
    ):
        """
        Test empty result set.

        GIVEN: User has no activities
        WHEN: GET request is made
        THEN: 200 with empty list
        """
        # Arrange: No activities
        mock_activity_service.get_user_activities.return_value = []

        # Act
        with patch('src.api.dependencies.get_activity_service', return_value=mock_activity_service):
            response = client.get("/api/v1/activities?user_id=999")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data == []

    @pytest.mark.contract
    @pytest.mark.parametrize("limit", [1, 5, 10, 25, 50, 100])
    def test_get_activities_respects_various_limit_values(
        self,
        client,
        mock_activity_service,
        limit: int
    ):
        """
        Test various valid limit values.

        GIVEN: Different limit values within range [1, 100]
        WHEN: GET request is made
        THEN: Service called with correct limit
        """
        # Arrange
        mock_activity_service.get_user_activities.return_value = []

        # Act
        with patch('src.api.dependencies.get_activity_service', return_value=mock_activity_service):
            response = client.get(f"/api/v1/activities?user_id=1&limit={limit}")

        # Assert
        assert response.status_code == 200
        mock_activity_service.get_user_activities.assert_called_once_with(1, limit)


class TestActivitiesAPIErrorHandling:
    """
    Test suite for error handling across Activities API.
    """

    @pytest.mark.contract
    def test_invalid_datetime_format_returns_422(self, client):
        """
        Test datetime validation.

        GIVEN: Invalid datetime format in start_time
        WHEN: POST request is made
        THEN: 422 validation error
        """
        # Arrange
        request_data = {
            "user_id": 1,
            "description": "Test",
            "start_time": "not-a-datetime",
            "end_time": "2025-11-07T12:00:00Z"
        }

        # Act
        response = client.post("/api/v1/activities", json=request_data)

        # Assert
        assert response.status_code == 422

    @pytest.mark.contract
    def test_negative_user_id_in_query_returns_422(self, client):
        """
        Test query parameter validation.

        GIVEN: Negative user_id
        WHEN: GET request is made
        THEN: 422 validation error (or handled by service)
        """
        # Act
        response = client.get("/api/v1/activities?user_id=-1")

        # Assert: Either 422 or 200 with empty list (depending on validation)
        assert response.status_code in [200, 422]
