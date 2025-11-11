"""
Unit tests for UserService.

Tests user service that provides business logic for user operations.
Verifies API client integration, error handling, and data transformation.

Test Coverage:
    - get_by_telegram_id(): User retrieval, 404 handling
    - create_user(): User creation with default timezone
    - update_last_poll_time(): Poll time updates with ISO format
    - Error handling: HTTP errors, network failures

Coverage Target: 100% of user_service.py
Execution Time: < 0.3 seconds

Author: Testing Team
Date: 2025-11-07
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import httpx

from src.infrastructure.http_clients.user_service import UserService
from src.infrastructure.http_clients.http_client import DataAPIClient


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def mock_client():
    """
    Fixture: Mock DataAPIClient.

    Returns:
        MagicMock: Mocked HTTP client for testing without network calls
    """
    client = MagicMock(spec=DataAPIClient)
    client.get = AsyncMock()
    client.post = AsyncMock()
    client.patch = AsyncMock()
    return client


@pytest.fixture
def user_service(mock_client):
    """
    Fixture: UserService instance with mocked client.

    Args:
        mock_client: Mocked DataAPIClient from fixture

    Returns:
        UserService: Service instance for testing
    """
    return UserService(mock_client)


@pytest.fixture
def sample_user_data():
    """
    Fixture: Sample user data returned from API.

    Returns:
        dict: User data with typical fields
    """
    return {
        "id": 1,
        "telegram_id": 123456789,
        "username": "testuser",
        "first_name": "Test",
        "timezone": "Europe/Moscow",
        "last_poll_time": None
    }


# ============================================================================
# TEST SUITES
# ============================================================================

class TestUserServiceGetByTelegramId:
    """
    Test suite for get_by_telegram_id() method.

    This is the most frequently used method - called on every bot interaction
    to identify the user. Must handle both existing and new users gracefully.
    """

    @pytest.mark.unit
    async def test_get_by_telegram_id_when_user_exists_returns_user_data(
        self,
        user_service: UserService,
        mock_client,
        sample_user_data
    ):
        """
        Test successful user retrieval.

        GIVEN: User exists with telegram_id=123456789
        WHEN: get_by_telegram_id(123456789) is called
        THEN: GET request is made to /api/v1/users/by-telegram/{telegram_id}
              AND user data is returned
        """
        # Arrange
        mock_client.get.return_value = sample_user_data

        # Act
        result = await user_service.get_by_telegram_id(123456789)

        # Assert: Correct API call
        mock_client.get.assert_called_once_with(
            "/api/v1/users/by-telegram/123456789"
        )

        # User data returned
        assert result == sample_user_data
        assert result["telegram_id"] == 123456789
        assert result["username"] == "testuser"

    @pytest.mark.unit
    async def test_get_by_telegram_id_when_user_not_found_returns_none(
        self,
        user_service: UserService,
        mock_client
    ):
        """
        Test handling of non-existent user.

        GIVEN: User with telegram_id=999999999 does not exist
        WHEN: get_by_telegram_id(999999999) is called
        THEN: API returns 404 HTTPStatusError
              AND method returns None (graceful handling for new users)
        """
        # Arrange: Mock 404 error
        mock_response = MagicMock()
        mock_response.status_code = 404
        error = httpx.HTTPStatusError(
            "404 Not Found",
            request=MagicMock(),
            response=mock_response
        )
        mock_client.get.side_effect = error

        # Act
        result = await user_service.get_by_telegram_id(999999999)

        # Assert: None returned for 404
        assert result is None, \
            "Should return None for non-existent user (not raise exception)"

        # API was called
        mock_client.get.assert_called_once_with(
            "/api/v1/users/by-telegram/999999999"
        )

    @pytest.mark.unit
    async def test_get_by_telegram_id_with_500_error_raises_exception(
        self,
        user_service: UserService,
        mock_client
    ):
        """
        Test handling of server errors (non-404).

        GIVEN: API returns 500 Internal Server Error
        WHEN: get_by_telegram_id() is called
        THEN: HTTPStatusError is re-raised (not suppressed)
              (Only 404 is handled gracefully, other errors propagate)
        """
        # Arrange: Mock 500 error
        mock_response = MagicMock()
        mock_response.status_code = 500
        error = httpx.HTTPStatusError(
            "500 Internal Server Error",
            request=MagicMock(),
            response=mock_response
        )
        mock_client.get.side_effect = error

        # Act & Assert: Error re-raised
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await user_service.get_by_telegram_id(123456789)

        assert exc_info.value.response.status_code == 500

    @pytest.mark.unit
    async def test_get_by_telegram_id_with_network_error_raises_exception(
        self,
        user_service: UserService,
        mock_client
    ):
        """
        Test handling of network errors.

        GIVEN: Network connection fails
        WHEN: get_by_telegram_id() is called
        THEN: Network exception is re-raised (not suppressed)
        """
        # Arrange: Network error
        error = httpx.ConnectError("Connection refused")
        mock_client.get.side_effect = error

        # Act & Assert: Error propagates
        with pytest.raises(httpx.ConnectError):
            await user_service.get_by_telegram_id(123456789)

    @pytest.mark.unit
    @pytest.mark.parametrize("telegram_id", [
        1,
        123456789,
        999999999999,
    ])
    async def test_get_by_telegram_id_handles_various_telegram_ids(
        self,
        user_service: UserService,
        mock_client,
        telegram_id: int
    ):
        """
        Test method handles various telegram_id values.

        GIVEN: Different valid Telegram IDs
        WHEN: get_by_telegram_id() is called
        THEN: Correct API path is constructed for each ID
        """
        # Arrange
        mock_client.get.return_value = {"id": 1, "telegram_id": telegram_id}

        # Act
        result = await user_service.get_by_telegram_id(telegram_id)

        # Assert: Correct path
        expected_path = f"/api/v1/users/by-telegram/{telegram_id}"
        mock_client.get.assert_called_once_with(expected_path)

        assert result["telegram_id"] == telegram_id


class TestUserServiceCreateUser:
    """
    Test suite for create_user() method.

    Handles new user registration from Telegram.
    """

    @pytest.mark.unit
    async def test_create_user_with_all_fields_creates_user_with_default_timezone(
        self,
        user_service: UserService,
        mock_client,
        sample_user_data
    ):
        """
        Test user creation with all fields.

        GIVEN: Telegram user data (telegram_id, username, first_name)
        WHEN: create_user() is called
        THEN: POST request is made to /api/v1/users
              AND timezone defaults to "Europe/Moscow"
              AND created user data is returned
        """
        # Arrange
        mock_client.post.return_value = sample_user_data

        # Act
        result = await user_service.create_user(
            telegram_id=123456789,
            username="testuser",
            first_name="Test"
        )

        # Assert: Correct API call
        mock_client.post.assert_called_once_with(
            "/api/v1/users",
            json={
                "telegram_id": 123456789,
                "username": "testuser",
                "first_name": "Test",
                "timezone": "Europe/Moscow"
            }
        )

        # User data returned
        assert result == sample_user_data
        assert result["telegram_id"] == 123456789

    @pytest.mark.unit
    async def test_create_user_with_none_username_sends_null(
        self,
        user_service: UserService,
        mock_client,
        sample_user_data
    ):
        """
        Test user creation without username.

        GIVEN: Telegram user without username (privacy settings)
        WHEN: create_user() is called with username=None
        THEN: username=None is sent in JSON (not omitted)
        """
        # Arrange
        mock_client.post.return_value = sample_user_data

        # Act
        result = await user_service.create_user(
            telegram_id=123456789,
            username=None,
            first_name="Test"
        )

        # Assert: None sent for username
        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["username"] is None

    @pytest.mark.unit
    async def test_create_user_with_none_first_name_sends_null(
        self,
        user_service: UserService,
        mock_client,
        sample_user_data
    ):
        """
        Test user creation without first name.

        GIVEN: Telegram user without first name
        WHEN: create_user() is called with first_name=None
        THEN: first_name=None is sent in JSON
        """
        # Arrange
        mock_client.post.return_value = sample_user_data

        # Act
        result = await user_service.create_user(
            telegram_id=123456789,
            username="testuser",
            first_name=None
        )

        # Assert: None sent for first_name
        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["first_name"] is None

    @pytest.mark.unit
    async def test_create_user_always_uses_europe_moscow_timezone(
        self,
        user_service: UserService,
        mock_client,
        sample_user_data
    ):
        """
        Test default timezone is always set.

        GIVEN: New user creation
        WHEN: create_user() is called
        THEN: timezone="Europe/Moscow" is always sent (business default)
        """
        # Arrange
        mock_client.post.return_value = sample_user_data

        # Act
        await user_service.create_user(
            telegram_id=123456789,
            username="testuser",
            first_name="Test"
        )

        # Assert: Default timezone
        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["timezone"] == "Europe/Moscow", \
            "Should always set default timezone to Europe/Moscow"

    @pytest.mark.unit
    async def test_create_user_with_duplicate_telegram_id_raises_error(
        self,
        user_service: UserService,
        mock_client
    ):
        """
        Test handling of duplicate user creation.

        GIVEN: User with telegram_id already exists
        WHEN: create_user() is called with same telegram_id
        THEN: HTTPStatusError (409 Conflict) is raised
        """
        # Arrange: Mock 409 conflict
        mock_response = MagicMock()
        mock_response.status_code = 409
        error = httpx.HTTPStatusError(
            "409 Conflict",
            request=MagicMock(),
            response=mock_response
        )
        mock_client.post.side_effect = error

        # Act & Assert
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await user_service.create_user(
                telegram_id=123456789,
                username="testuser",
                first_name="Test"
            )

        assert exc_info.value.response.status_code == 409


class TestUserServiceUpdateLastPollTime:
    """
    Test suite for update_last_poll_time() method.

    Updates user's last poll timestamp for scheduling logic.
    """

    @pytest.mark.unit
    async def test_update_last_poll_time_sends_patch_request_with_iso_format(
        self,
        user_service: UserService,
        mock_client,
        sample_user_data
    ):
        """
        Test poll time update.

        GIVEN: User ID and poll time
        WHEN: update_last_poll_time() is called
        THEN: PATCH request is made to /api/v1/users/{user_id}/last-poll-time
              AND datetime is converted to ISO format string
              AND updated user data is returned
        """
        # Arrange
        poll_time = datetime(2025, 11, 7, 14, 30, 0)
        mock_client.patch.return_value = {
            **sample_user_data,
            "last_poll_time": "2025-11-07T14:30:00"
        }

        # Act
        result = await user_service.update_last_poll_time(
            user_id=1,
            poll_time=poll_time
        )

        # Assert: Correct API call
        mock_client.patch.assert_called_once_with(
            "/api/v1/users/1/last-poll-time",
            json={"poll_time": "2025-11-07T14:30:00"}
        )

        # Updated data returned
        assert result["last_poll_time"] == "2025-11-07T14:30:00"

    @pytest.mark.unit
    async def test_update_last_poll_time_converts_datetime_to_isoformat(
        self,
        user_service: UserService,
        mock_client,
        sample_user_data
    ):
        """
        Test datetime serialization to ISO format.

        GIVEN: datetime object
        WHEN: update_last_poll_time() is called
        THEN: datetime.isoformat() is used for JSON serialization
        """
        # Arrange
        poll_time = datetime(2025, 1, 15, 9, 45, 30)
        mock_client.patch.return_value = sample_user_data

        # Act
        await user_service.update_last_poll_time(
            user_id=1,
            poll_time=poll_time
        )

        # Assert: ISO format used
        call_args = mock_client.patch.call_args
        assert call_args[1]["json"]["poll_time"] == "2025-01-15T09:45:30"

    @pytest.mark.unit
    async def test_update_last_poll_time_with_timezone_aware_datetime(
        self,
        user_service: UserService,
        mock_client,
        sample_user_data
    ):
        """
        Test timezone-aware datetime handling.

        GIVEN: datetime with timezone info
        WHEN: update_last_poll_time() is called
        THEN: Timezone is preserved in ISO format
        """
        # Arrange: Timezone-aware datetime
        from datetime import timezone, timedelta
        tz = timezone(timedelta(hours=3))
        poll_time = datetime(2025, 11, 7, 14, 30, 0, tzinfo=tz)

        mock_client.patch.return_value = sample_user_data

        # Act
        await user_service.update_last_poll_time(
            user_id=1,
            poll_time=poll_time
        )

        # Assert: Timezone in ISO format
        call_args = mock_client.patch.call_args
        iso_time = call_args[1]["json"]["poll_time"]
        assert "+03:00" in iso_time or "03:00" in iso_time, \
            "Should preserve timezone in ISO format"

    @pytest.mark.unit
    @pytest.mark.parametrize("user_id", [1, 5, 100, 999])
    async def test_update_last_poll_time_handles_various_user_ids(
        self,
        user_service: UserService,
        mock_client,
        sample_user_data,
        user_id: int
    ):
        """
        Test method handles various user IDs.

        GIVEN: Different user IDs
        WHEN: update_last_poll_time() is called
        THEN: Correct API path is constructed for each user
        """
        # Arrange
        poll_time = datetime(2025, 11, 7, 12, 0, 0)
        mock_client.patch.return_value = sample_user_data

        # Act
        await user_service.update_last_poll_time(user_id, poll_time)

        # Assert: Correct path
        expected_path = f"/api/v1/users/{user_id}/last-poll-time"
        call_args = mock_client.patch.call_args
        assert call_args[0][0] == expected_path


class TestUserServiceInitialization:
    """
    Test suite for UserService initialization.
    """

    @pytest.mark.unit
    def test_init_stores_client_reference(self, mock_client):
        """
        Test initialization stores client.

        GIVEN: DataAPIClient instance
        WHEN: UserService(client) is instantiated
        THEN: Client is stored for later use
        """
        # Act
        service = UserService(mock_client)

        # Assert
        assert service.client is mock_client, \
            "Should store client reference"

    @pytest.mark.unit
    def test_service_is_stateless(self, mock_client):
        """
        Test service has no mutable state.

        GIVEN: UserService instance
        WHEN: Service is examined
        THEN: Only client reference is stored (no user cache, etc.)
              (Thread-safe for concurrent requests)
        """
        # Act
        service = UserService(mock_client)

        # Assert: No mutable state
        assert not hasattr(service, '_cache'), \
            "Should not cache user data"
        assert not hasattr(service, '_users'), \
            "Should not store user list"


class TestUserServiceEdgeCases:
    """
    Test suite for edge cases and error scenarios.
    """

    @pytest.mark.unit
    async def test_get_by_telegram_id_with_403_error_raises_exception(
        self,
        user_service: UserService,
        mock_client
    ):
        """
        Test handling of permission errors.

        GIVEN: API returns 403 Forbidden
        WHEN: get_by_telegram_id() is called
        THEN: HTTPStatusError is raised (only 404 is handled)
        """
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 403
        error = httpx.HTTPStatusError(
            "403 Forbidden",
            request=MagicMock(),
            response=mock_response
        )
        mock_client.get.side_effect = error

        # Act & Assert
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await user_service.get_by_telegram_id(123456789)

        assert exc_info.value.response.status_code == 403

    @pytest.mark.unit
    async def test_create_user_with_empty_strings_sends_empty_strings(
        self,
        user_service: UserService,
        mock_client,
        sample_user_data
    ):
        """
        Test user creation with empty string fields.

        GIVEN: username="" and first_name=""
        WHEN: create_user() is called
        THEN: Empty strings are sent (not converted to None)
        """
        # Arrange
        mock_client.post.return_value = sample_user_data

        # Act
        await user_service.create_user(
            telegram_id=123456789,
            username="",
            first_name=""
        )

        # Assert: Empty strings preserved
        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["username"] == ""
        assert call_args[1]["json"]["first_name"] == ""
