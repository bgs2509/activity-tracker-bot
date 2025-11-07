"""
Contract tests for Users API endpoints.

Tests request/response schemas, validation rules, and error handling
for /api/v1/users endpoints using FastAPI TestClient.

Test Coverage:
    - POST /users: Create user with validation
    - GET /users/by-telegram-id/{id}: User retrieval
    - PUT /users/{id}/last-poll-time: Poll time update
    - Schema validation: Required fields, types, optional fields
    - Error cases: 404, 422 validation errors

Coverage Target: 100% of users.py endpoints
Execution Time: < 0.5 seconds

Author: Testing Team
Date: 2025-11-07
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from src.main import app
from src.domain.models.user import User


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
def mock_user_service():
    """
    Fixture: Mock UserService.

    Returns:
        AsyncMock: Mocked service for dependency injection
    """
    service = AsyncMock()
    # Default: user not found (can override in tests)
    service.get_by_telegram_id.return_value = None
    return service


@pytest.fixture
def sample_user():
    """
    Fixture: Sample User model instance.

    Returns:
        User: User object for testing
    """
    return User(
        id=1,
        telegram_id=123456789,
        username="testuser",
        first_name="Test",
        timezone="Europe/Moscow",
        created_at=datetime(2025, 11, 7, 12, 0, 0, tzinfo=timezone.utc),
        last_poll_time=None
    )


# ============================================================================
# TEST SUITES
# ============================================================================

class TestCreateUserEndpoint:
    """
    Test suite for POST /api/v1/users endpoint.

    Tests user creation with schema validation and conflict handling.
    """

    @pytest.mark.contract
    def test_create_user_with_valid_data_returns_201_with_user(
        self,
        client,
        mock_user_service,
        sample_user
    ):
        """
        Test successful user creation.

        GIVEN: Valid user creation data
        WHEN: POST /api/v1/users is called
        THEN: 201 status with created user data
              AND UserResponse schema is returned
        """
        # Arrange
        request_data = {
            "telegram_id": 123456789,
            "username": "testuser",
            "first_name": "Test"
        }
        mock_user_service.create_user.return_value = sample_user

        # Act
        with patch('src.api.dependencies.get_user_service', return_value=mock_user_service):
            response = client.post("/api/v1/users", json=request_data)

        # Assert: Status code
        assert response.status_code == 201

        # Assert: Response data
        data = response.json()
        assert data["id"] == 1
        assert data["telegram_id"] == 123456789
        assert data["username"] == "testuser"
        assert data["first_name"] == "Test"
        assert data["timezone"] == "Europe/Moscow"
        assert "created_at" in data
        assert data["last_poll_time"] is None

    @pytest.mark.contract
    def test_create_user_with_existing_telegram_id_returns_existing_user(
        self,
        client,
        mock_user_service,
        sample_user
    ):
        """
        Test idempotent user creation (existing user).

        GIVEN: User with telegram_id already exists
        WHEN: POST /api/v1/users is called with same telegram_id
        THEN: 201 status with existing user data
              (Idempotent: no duplicate created)
        """
        # Arrange: User already exists
        request_data = {"telegram_id": 123456789}
        mock_user_service.get_by_telegram_id.return_value = sample_user

        # Act
        with patch('src.api.dependencies.get_user_service', return_value=mock_user_service):
            response = client.post("/api/v1/users", json=request_data)

        # Assert: Returns existing user
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == 1
        assert data["telegram_id"] == 123456789

        # create_user should NOT be called
        mock_user_service.create_user.assert_not_called()

    @pytest.mark.contract
    def test_create_user_with_missing_telegram_id_returns_422(self, client):
        """
        Test validation: missing required field.

        GIVEN: Request missing required telegram_id field
        WHEN: POST /api/v1/users is called
        THEN: 422 Unprocessable Entity
              AND validation error details in response
        """
        # Arrange: Missing telegram_id
        request_data = {"username": "testuser"}

        # Act
        response = client.post("/api/v1/users", json=request_data)

        # Assert: Validation error
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

        # Pydantic validation error structure
        errors = data["detail"]
        assert isinstance(errors, list)
        assert any(
            "telegram_id" in str(e.get("loc", [])) and e.get("type") == "missing"
            for e in errors
        )

    @pytest.mark.contract
    def test_create_user_with_invalid_telegram_id_type_returns_422(self, client):
        """
        Test validation: wrong field type.

        GIVEN: telegram_id as string instead of integer
        WHEN: POST /api/v1/users is called
        THEN: 422 with type validation error
        """
        # Arrange: Wrong type
        request_data = {
            "telegram_id": "not_an_integer",
            "username": "testuser"
        }

        # Act
        response = client.post("/api/v1/users", json=request_data)

        # Assert: Type validation error
        assert response.status_code == 422
        data = response.json()
        errors = data["detail"]

        # Check for int validation error
        assert any(
            "telegram_id" in str(e.get("loc", []))
            for e in errors
        )

    @pytest.mark.contract
    def test_create_user_with_only_telegram_id_uses_defaults(
        self,
        client,
        mock_user_service
    ):
        """
        Test creation with minimal data (only required field).

        GIVEN: Only telegram_id provided
        WHEN: POST /api/v1/users is called
        THEN: User created with default timezone
              AND optional fields are None
        """
        # Arrange: Minimal data
        request_data = {"telegram_id": 123456789}
        created_user = User(
            id=1,
            telegram_id=123456789,
            username=None,
            first_name=None,
            timezone="Europe/Moscow",  # Default
            created_at=datetime.now(timezone.utc)
        )
        mock_user_service.create_user.return_value = created_user

        # Act
        with patch('src.api.dependencies.get_user_service', return_value=mock_user_service):
            response = client.post("/api/v1/users", json=request_data)

        # Assert: Created with defaults
        assert response.status_code == 201
        data = response.json()
        assert data["telegram_id"] == 123456789
        assert data["timezone"] == "Europe/Moscow"
        assert data["username"] is None
        assert data["first_name"] is None

    @pytest.mark.contract
    def test_create_user_response_matches_user_response_schema(
        self,
        client,
        mock_user_service,
        sample_user
    ):
        """
        Test response schema compliance.

        GIVEN: Successful user creation
        WHEN: Response is received
        THEN: Response matches UserResponse schema exactly
              (All required fields present, no extra fields)
        """
        # Arrange
        request_data = {"telegram_id": 123456789}
        mock_user_service.create_user.return_value = sample_user

        # Act
        with patch('src.api.dependencies.get_user_service', return_value=mock_user_service):
            response = client.post("/api/v1/users", json=request_data)

        # Assert: Schema compliance
        data = response.json()

        # Required fields
        required_fields = {"id", "telegram_id", "timezone", "created_at"}
        for field in required_fields:
            assert field in data, f"Required field '{field}' missing"

        # Optional fields (can be None)
        optional_fields = {"username", "first_name", "last_poll_time"}
        for field in optional_fields:
            assert field in data, f"Optional field '{field}' missing from schema"

        # No extra fields
        allowed_fields = required_fields | optional_fields
        assert set(data.keys()) == allowed_fields, \
            f"Response has unexpected fields: {set(data.keys()) - allowed_fields}"


class TestGetUserByTelegramIdEndpoint:
    """
    Test suite for GET /api/v1/users/by-telegram-id/{telegram_id} endpoint.

    Tests user retrieval by Telegram ID with error handling.
    """

    @pytest.mark.contract
    def test_get_user_by_telegram_id_when_exists_returns_200_with_user(
        self,
        client,
        mock_user_service,
        sample_user
    ):
        """
        Test successful user retrieval.

        GIVEN: User exists with telegram_id=123456789
        WHEN: GET /api/v1/users/by-telegram-id/123456789 is called
        THEN: 200 status with user data
        """
        # Arrange
        mock_user_service.get_by_telegram_id.return_value = sample_user

        # Act
        with patch('src.api.dependencies.get_user_service', return_value=mock_user_service):
            response = client.get("/api/v1/users/by-telegram-id/123456789")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["telegram_id"] == 123456789
        assert data["id"] == 1

        # Service called with correct ID
        mock_user_service.get_by_telegram_id.assert_called_once_with(123456789)

    @pytest.mark.contract
    def test_get_user_by_telegram_id_when_not_found_returns_404(
        self,
        client,
        mock_user_service
    ):
        """
        Test user not found case.

        GIVEN: User with telegram_id does not exist
        WHEN: GET /api/v1/users/by-telegram-id/{id} is called
        THEN: 404 Not Found with error detail
        """
        # Arrange: User not found
        mock_user_service.get_by_telegram_id.return_value = None

        # Act
        with patch('src.api.dependencies.get_user_service', return_value=mock_user_service):
            response = client.get("/api/v1/users/by-telegram-id/999999999")

        # Assert: 404 error
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    @pytest.mark.contract
    def test_get_user_by_telegram_id_with_invalid_id_format_returns_422(
        self,
        client
    ):
        """
        Test path parameter validation.

        GIVEN: telegram_id as non-integer in URL
        WHEN: GET /api/v1/users/by-telegram-id/invalid is called
        THEN: 422 with validation error
        """
        # Act
        response = client.get("/api/v1/users/by-telegram-id/not_a_number")

        # Assert: Path validation error
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    @pytest.mark.contract
    @pytest.mark.parametrize("telegram_id", [
        1,
        123456789,
        999999999999
    ])
    def test_get_user_by_telegram_id_handles_various_id_values(
        self,
        client,
        mock_user_service,
        telegram_id: int
    ):
        """
        Test various telegram_id values.

        GIVEN: Different valid Telegram IDs
        WHEN: GET request is made
        THEN: Request is processed correctly
        """
        # Arrange
        user = User(
            id=1,
            telegram_id=telegram_id,
            timezone="Europe/Moscow",
            created_at=datetime.now(timezone.utc)
        )
        mock_user_service.get_by_telegram_id.return_value = user

        # Act
        with patch('src.api.dependencies.get_user_service', return_value=mock_user_service):
            response = client.get(f"/api/v1/users/by-telegram-id/{telegram_id}")

        # Assert: Correct ID in response
        assert response.status_code == 200
        data = response.json()
        assert data["telegram_id"] == telegram_id


class TestUpdateLastPollTimeEndpoint:
    """
    Test suite for PUT /api/v1/users/{user_id}/last-poll-time endpoint.

    Tests poll time updates with datetime validation.
    """

    @pytest.mark.contract
    def test_update_last_poll_time_with_valid_datetime_returns_200(
        self,
        client,
        mock_user_service,
        sample_user
    ):
        """
        Test successful poll time update.

        GIVEN: Valid user_id and poll_time
        WHEN: PUT /api/v1/users/{user_id}/last-poll-time is called
        THEN: 200 status with updated user
        """
        # Arrange
        poll_time = "2025-11-07T14:30:00Z"
        updated_user = User(
            **{k: v for k, v in sample_user.__dict__.items() if not k.startswith('_')},
            last_poll_time=datetime(2025, 11, 7, 14, 30, 0, tzinfo=timezone.utc)
        )
        mock_user_service.update_last_poll_time.return_value = updated_user

        # Act
        with patch('src.api.dependencies.get_user_service', return_value=mock_user_service):
            response = client.put(
                "/api/v1/users/1/last-poll-time",
                json={"poll_time": poll_time}
            )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["last_poll_time"] is not None

    @pytest.mark.contract
    def test_update_last_poll_time_when_user_not_found_returns_404(
        self,
        client,
        mock_user_service
    ):
        """
        Test poll time update for non-existent user.

        GIVEN: user_id does not exist
        WHEN: PUT request is made
        THEN: 404 Not Found
        """
        # Arrange: Service returns None (user not found)
        mock_user_service.update_last_poll_time.return_value = None

        # Act
        with patch('src.api.dependencies.get_user_service', return_value=mock_user_service):
            response = client.put(
                "/api/v1/users/999/last-poll-time",
                json={"poll_time": "2025-11-07T14:30:00Z"}
            )

        # Assert
        assert response.status_code == 404

    @pytest.mark.contract
    def test_update_last_poll_time_with_invalid_datetime_format_returns_422(
        self,
        client
    ):
        """
        Test datetime validation.

        GIVEN: Invalid datetime format
        WHEN: PUT request is made
        THEN: 422 validation error
        """
        # Act
        response = client.put(
            "/api/v1/users/1/last-poll-time",
            json={"poll_time": "invalid-datetime"}
        )

        # Assert
        assert response.status_code == 422

    @pytest.mark.contract
    def test_update_last_poll_time_with_missing_poll_time_returns_422(
        self,
        client
    ):
        """
        Test missing required field.

        GIVEN: poll_time not provided
        WHEN: PUT request is made
        THEN: 422 validation error
        """
        # Act
        response = client.put(
            "/api/v1/users/1/last-poll-time",
            json={}
        )

        # Assert
        assert response.status_code == 422
        data = response.json()
        errors = data["detail"]
        assert any("poll_time" in str(e.get("loc", [])) for e in errors)


class TestUsersAPIErrorHandling:
    """
    Test suite for error handling across Users API.

    Tests error response formats and status codes.
    """

    @pytest.mark.contract
    def test_invalid_json_body_returns_422(self, client):
        """
        Test malformed JSON handling.

        GIVEN: Invalid JSON in request body
        WHEN: POST request is made
        THEN: 422 with JSON parse error
        """
        # Act: Send invalid JSON
        response = client.post(
            "/api/v1/users",
            data="not valid json",
            headers={"Content-Type": "application/json"}
        )

        # Assert
        assert response.status_code == 422

    @pytest.mark.contract
    def test_empty_request_body_returns_422(self, client):
        """
        Test empty body handling.

        GIVEN: Empty request body
        WHEN: POST request is made
        THEN: 422 validation error
        """
        # Act
        response = client.post(
            "/api/v1/users",
            json={}
        )

        # Assert
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    @pytest.mark.contract
    def test_service_error_propagates_correctly(
        self,
        client,
        mock_user_service
    ):
        """
        Test service layer error handling.

        GIVEN: Service raises ValueError
        WHEN: API endpoint is called
        THEN: Error is converted to appropriate HTTP status
        """
        # Arrange: Service raises ValueError
        mock_user_service.update_last_poll_time.side_effect = ValueError("User not found")

        # Act
        with patch('src.api.dependencies.get_user_service', return_value=mock_user_service):
            response = client.put(
                "/api/v1/users/1/last-poll-time",
                json={"poll_time": "2025-11-07T14:30:00Z"}
            )

        # Assert: Converted to 404
        assert response.status_code == 404
        data = response.json()
        assert "User not found" in data["detail"]
