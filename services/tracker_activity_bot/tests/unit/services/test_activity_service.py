"""
Unit tests for ActivityService.

Tests activity service that provides business logic for activity tracking.
Verifies API client integration, datetime serialization, and data formatting.

Test Coverage:
    - create_activity(): Activity creation with tags, time ranges
    - get_user_activities(): Activity retrieval with pagination
    - Datetime handling: ISO format serialization
    - Edge cases: None category, empty tags, various time ranges

Coverage Target: 100% of activity_service.py
Execution Time: < 0.3 seconds

Author: Testing Team
Date: 2025-11-07
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from src.infrastructure.http_clients.activity_service import ActivityService
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
    return client


@pytest.fixture
def activity_service(mock_client):
    """
    Fixture: ActivityService instance with mocked client.

    Args:
        mock_client: Mocked DataAPIClient from fixture

    Returns:
        ActivityService: Service instance for testing
    """
    return ActivityService(mock_client)


@pytest.fixture
def sample_activity_data():
    """
    Fixture: Sample activity data returned from API.

    Returns:
        dict: Activity data with typical fields
    """
    return {
        "id": 1,
        "user_id": 1,
        "category_id": 1,
        "description": "Working on project",
        "tags": "python,testing",
        "start_time": "2025-11-07T10:00:00",
        "end_time": "2025-11-07T12:00:00",
        "duration_minutes": 120
    }


# ============================================================================
# TEST SUITES
# ============================================================================

class TestActivityServiceCreateActivity:
    """
    Test suite for create_activity() method.

    Handles activity creation with time ranges, tags, and categorization.
    Critical for tracking user activities in the bot.
    """

    @pytest.mark.unit
    async def test_create_activity_with_all_fields_sends_correct_request(
        self,
        activity_service: ActivityService,
        mock_client,
        sample_activity_data
    ):
        """
        Test activity creation with all fields.

        GIVEN: Complete activity data (user, category, description, tags, times)
        WHEN: create_activity() is called
        THEN: POST request is made to /api/v1/activities
              AND datetime objects are converted to ISO format
              AND created activity data is returned
        """
        # Arrange
        mock_client.post.return_value = sample_activity_data

        start_time = datetime(2025, 11, 7, 10, 0, 0)
        end_time = datetime(2025, 11, 7, 12, 0, 0)

        # Act
        result = await activity_service.create_activity(
            user_id=1,
            category_id=1,
            description="Working on project",
            tags=["python", "testing"],
            start_time=start_time,
            end_time=end_time
        )

        # Assert: Correct API call
        mock_client.post.assert_called_once_with(
            "/api/v1/activities",
            json={
                "user_id": 1,
                "category_id": 1,
                "description": "Working on project",
                "tags": ["python", "testing"],
                "start_time": "2025-11-07T10:00:00",
                "end_time": "2025-11-07T12:00:00"
            }
        )

        # Activity data returned
        assert result == sample_activity_data
        assert result["duration_minutes"] == 120

    @pytest.mark.unit
    async def test_create_activity_with_none_category_sends_null(
        self,
        activity_service: ActivityService,
        mock_client,
        sample_activity_data
    ):
        """
        Test activity creation without category (uncategorized).

        GIVEN: Activity with category_id=None
        WHEN: create_activity() is called
        THEN: category_id=None is sent in JSON
              (Allows uncategorized activities)
        """
        # Arrange
        mock_client.post.return_value = sample_activity_data

        start_time = datetime(2025, 11, 7, 10, 0, 0)
        end_time = datetime(2025, 11, 7, 11, 0, 0)

        # Act
        result = await activity_service.create_activity(
            user_id=1,
            category_id=None,
            description="Quick task",
            tags=None,
            start_time=start_time,
            end_time=end_time
        )

        # Assert: None sent for category_id
        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["category_id"] is None

    @pytest.mark.unit
    async def test_create_activity_with_none_tags_sends_null(
        self,
        activity_service: ActivityService,
        mock_client,
        sample_activity_data
    ):
        """
        Test activity creation without tags.

        GIVEN: Activity with tags=None
        WHEN: create_activity() is called
        THEN: tags=None is sent in JSON
        """
        # Arrange
        mock_client.post.return_value = sample_activity_data

        start_time = datetime(2025, 11, 7, 10, 0, 0)
        end_time = datetime(2025, 11, 7, 11, 0, 0)

        # Act
        result = await activity_service.create_activity(
            user_id=1,
            category_id=1,
            description="Simple task",
            tags=None,
            start_time=start_time,
            end_time=end_time
        )

        # Assert: None sent for tags
        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["tags"] is None

    @pytest.mark.unit
    async def test_create_activity_with_empty_tags_list_sends_empty_list(
        self,
        activity_service: ActivityService,
        mock_client,
        sample_activity_data
    ):
        """
        Test activity creation with empty tags list.

        GIVEN: Activity with tags=[]
        WHEN: create_activity() is called
        THEN: Empty list is sent (not converted to None)
        """
        # Arrange
        mock_client.post.return_value = sample_activity_data

        start_time = datetime(2025, 11, 7, 10, 0, 0)
        end_time = datetime(2025, 11, 7, 11, 0, 0)

        # Act
        await activity_service.create_activity(
            user_id=1,
            category_id=1,
            description="Task",
            tags=[],
            start_time=start_time,
            end_time=end_time
        )

        # Assert: Empty list preserved
        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["tags"] == []

    @pytest.mark.unit
    async def test_create_activity_with_multiple_tags_sends_list(
        self,
        activity_service: ActivityService,
        mock_client,
        sample_activity_data
    ):
        """
        Test activity creation with multiple tags.

        GIVEN: Activity with tags=["python", "testing", "unit"]
        WHEN: create_activity() is called
        THEN: Tags list is sent as-is (not modified)
        """
        # Arrange
        mock_client.post.return_value = sample_activity_data

        start_time = datetime(2025, 11, 7, 10, 0, 0)
        end_time = datetime(2025, 11, 7, 11, 0, 0)

        # Act
        await activity_service.create_activity(
            user_id=1,
            category_id=1,
            description="Testing",
            tags=["python", "testing", "unit"],
            start_time=start_time,
            end_time=end_time
        )

        # Assert: Tags list preserved
        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["tags"] == ["python", "testing", "unit"]

    @pytest.mark.unit
    async def test_create_activity_converts_datetime_to_isoformat(
        self,
        activity_service: ActivityService,
        mock_client,
        sample_activity_data
    ):
        """
        Test datetime serialization to ISO format.

        GIVEN: datetime objects for start_time and end_time
        WHEN: create_activity() is called
        THEN: datetime.isoformat() is used for JSON serialization
        """
        # Arrange
        mock_client.post.return_value = sample_activity_data

        start_time = datetime(2025, 1, 15, 9, 30, 45)
        end_time = datetime(2025, 1, 15, 11, 15, 30)

        # Act
        await activity_service.create_activity(
            user_id=1,
            category_id=1,
            description="Task",
            tags=None,
            start_time=start_time,
            end_time=end_time
        )

        # Assert: ISO format used
        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["start_time"] == "2025-01-15T09:30:45"
        assert call_args[1]["json"]["end_time"] == "2025-01-15T11:15:30"

    @pytest.mark.unit
    async def test_create_activity_with_timezone_aware_datetime(
        self,
        activity_service: ActivityService,
        mock_client,
        sample_activity_data
    ):
        """
        Test timezone-aware datetime handling.

        GIVEN: datetime objects with timezone info
        WHEN: create_activity() is called
        THEN: Timezone is preserved in ISO format
        """
        # Arrange
        from datetime import timezone, timedelta
        tz = timezone(timedelta(hours=3))

        start_time = datetime(2025, 11, 7, 10, 0, 0, tzinfo=tz)
        end_time = datetime(2025, 11, 7, 12, 0, 0, tzinfo=tz)

        mock_client.post.return_value = sample_activity_data

        # Act
        await activity_service.create_activity(
            user_id=1,
            category_id=1,
            description="Task",
            tags=None,
            start_time=start_time,
            end_time=end_time
        )

        # Assert: Timezone in ISO format
        call_args = mock_client.post.call_args
        start_iso = call_args[1]["json"]["start_time"]
        end_iso = call_args[1]["json"]["end_time"]

        assert "+03:00" in start_iso or "03:00" in start_iso, \
            "Should preserve timezone in start_time"
        assert "+03:00" in end_iso or "03:00" in end_iso, \
            "Should preserve timezone in end_time"

    @pytest.mark.unit
    async def test_create_activity_with_same_start_and_end_time(
        self,
        activity_service: ActivityService,
        mock_client,
        sample_activity_data
    ):
        """
        Test activity creation with zero duration.

        GIVEN: start_time == end_time (instant activity)
        WHEN: create_activity() is called
        THEN: Request is sent without error
              (Backend calculates duration_minutes=0)
        """
        # Arrange
        mock_client.post.return_value = {
            **sample_activity_data,
            "duration_minutes": 0
        }

        same_time = datetime(2025, 11, 7, 10, 0, 0)

        # Act
        result = await activity_service.create_activity(
            user_id=1,
            category_id=1,
            description="Instant task",
            tags=None,
            start_time=same_time,
            end_time=same_time
        )

        # Assert: Request sent successfully
        mock_client.post.assert_called_once()
        assert result["duration_minutes"] == 0

    @pytest.mark.unit
    async def test_create_activity_with_long_description(
        self,
        activity_service: ActivityService,
        mock_client,
        sample_activity_data
    ):
        """
        Test activity creation with long description.

        GIVEN: Description with 500+ characters
        WHEN: create_activity() is called
        THEN: Full description is sent (not truncated)
        """
        # Arrange
        long_description = "x" * 500
        mock_client.post.return_value = sample_activity_data

        start_time = datetime(2025, 11, 7, 10, 0, 0)
        end_time = datetime(2025, 11, 7, 11, 0, 0)

        # Act
        await activity_service.create_activity(
            user_id=1,
            category_id=1,
            description=long_description,
            tags=None,
            start_time=start_time,
            end_time=end_time
        )

        # Assert: Full description sent
        call_args = mock_client.post.call_args
        assert len(call_args[1]["json"]["description"]) == 500

    @pytest.mark.unit
    @pytest.mark.parametrize("user_id,category_id", [
        (1, 1),
        (5, 2),
        (100, None),
        (999, 50)
    ])
    async def test_create_activity_handles_various_ids(
        self,
        activity_service: ActivityService,
        mock_client,
        sample_activity_data,
        user_id: int,
        category_id: int | None
    ):
        """
        Test method handles various user_id and category_id values.

        GIVEN: Different user and category IDs
        WHEN: create_activity() is called
        THEN: Correct IDs are sent in JSON
        """
        # Arrange
        mock_client.post.return_value = sample_activity_data

        start_time = datetime(2025, 11, 7, 10, 0, 0)
        end_time = datetime(2025, 11, 7, 11, 0, 0)

        # Act
        await activity_service.create_activity(
            user_id=user_id,
            category_id=category_id,
            description="Task",
            tags=None,
            start_time=start_time,
            end_time=end_time
        )

        # Assert: Correct IDs sent
        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["user_id"] == user_id
        assert call_args[1]["json"]["category_id"] == category_id


class TestActivityServiceGetUserActivities:
    """
    Test suite for get_user_activities() method.

    Handles activity retrieval with pagination for displaying
    user's activity history.
    """

    @pytest.mark.unit
    async def test_get_user_activities_with_default_limit_requests_10_activities(
        self,
        activity_service: ActivityService,
        mock_client
    ):
        """
        Test activity retrieval with default pagination.

        GIVEN: User ID without explicit limit
        WHEN: get_user_activities(user_id) is called
        THEN: GET request with limit=10 (default)
              AND activities list is returned
        """
        # Arrange
        activities_response = {
            "activities": [
                {"id": 1, "description": "Task 1"},
                {"id": 2, "description": "Task 2"}
            ],
            "total": 2
        }
        mock_client.get.return_value = activities_response

        # Act
        result = await activity_service.get_user_activities(user_id=1)

        # Assert: Correct API call with default limit
        mock_client.get.assert_called_once_with(
            "/api/v1/activities?user_id=1&limit=10"
        )

        # Activities returned
        assert result == activities_response
        assert len(result["activities"]) == 2

    @pytest.mark.unit
    async def test_get_user_activities_with_custom_limit_uses_provided_value(
        self,
        activity_service: ActivityService,
        mock_client
    ):
        """
        Test activity retrieval with custom pagination limit.

        GIVEN: User ID and limit=20
        WHEN: get_user_activities(user_id, limit=20) is called
        THEN: GET request with limit=20
        """
        # Arrange
        mock_client.get.return_value = {"activities": [], "total": 0}

        # Act
        result = await activity_service.get_user_activities(
            user_id=1,
            limit=20
        )

        # Assert: Custom limit used
        mock_client.get.assert_called_once_with(
            "/api/v1/activities?user_id=1&limit=20"
        )

    @pytest.mark.unit
    @pytest.mark.parametrize("limit", [1, 5, 10, 25, 50, 100])
    async def test_get_user_activities_handles_various_limit_values(
        self,
        activity_service: ActivityService,
        mock_client,
        limit: int
    ):
        """
        Test various pagination limit values.

        GIVEN: Different limit values
        WHEN: get_user_activities() is called
        THEN: Correct limit is sent in query parameters
        """
        # Arrange
        mock_client.get.return_value = {"activities": [], "total": 0}

        # Act
        await activity_service.get_user_activities(user_id=1, limit=limit)

        # Assert: Correct limit in URL
        expected_url = f"/api/v1/activities?user_id=1&limit={limit}"
        mock_client.get.assert_called_once_with(expected_url)

    @pytest.mark.unit
    @pytest.mark.parametrize("user_id", [1, 5, 100, 999])
    async def test_get_user_activities_handles_various_user_ids(
        self,
        activity_service: ActivityService,
        mock_client,
        user_id: int
    ):
        """
        Test various user IDs.

        GIVEN: Different user IDs
        WHEN: get_user_activities() is called
        THEN: Correct user_id is sent in query parameters
        """
        # Arrange
        mock_client.get.return_value = {"activities": [], "total": 0}

        # Act
        await activity_service.get_user_activities(user_id=user_id)

        # Assert: Correct user_id in URL
        expected_url = f"/api/v1/activities?user_id={user_id}&limit=10"
        mock_client.get.assert_called_once_with(expected_url)

    @pytest.mark.unit
    async def test_get_user_activities_returns_empty_list_for_new_user(
        self,
        activity_service: ActivityService,
        mock_client
    ):
        """
        Test activity retrieval for user with no activities.

        GIVEN: User with no activities
        WHEN: get_user_activities() is called
        THEN: Empty activities list is returned (no error)
        """
        # Arrange
        empty_response = {"activities": [], "total": 0}
        mock_client.get.return_value = empty_response

        # Act
        result = await activity_service.get_user_activities(user_id=1)

        # Assert: Empty list returned gracefully
        assert result["activities"] == []
        assert result["total"] == 0


class TestActivityServiceInitialization:
    """
    Test suite for ActivityService initialization.
    """

    @pytest.mark.unit
    def test_init_stores_client_reference(self, mock_client):
        """
        Test initialization stores client.

        GIVEN: DataAPIClient instance
        WHEN: ActivityService(client) is instantiated
        THEN: Client is stored for later use
        """
        # Act
        service = ActivityService(mock_client)

        # Assert
        assert service.client is mock_client, \
            "Should store client reference"

    @pytest.mark.unit
    def test_service_is_stateless(self, mock_client):
        """
        Test service has no mutable state.

        GIVEN: ActivityService instance
        WHEN: Service is examined
        THEN: Only client reference is stored
              (Thread-safe for concurrent requests)
        """
        # Act
        service = ActivityService(mock_client)

        # Assert: No mutable state
        assert not hasattr(service, '_cache'), \
            "Should not cache activities"
        assert not hasattr(service, '_activities'), \
            "Should not store activity list"


class TestActivityServiceEdgeCases:
    """
    Test suite for edge cases in activity service.
    """

    @pytest.mark.unit
    async def test_create_activity_with_end_time_before_start_time(
        self,
        activity_service: ActivityService,
        mock_client,
        sample_activity_data
    ):
        """
        Test activity creation with invalid time range.

        GIVEN: end_time < start_time (invalid)
        WHEN: create_activity() is called
        THEN: Request is sent (backend validates and may reject)
        """
        # Arrange
        mock_client.post.return_value = sample_activity_data

        start_time = datetime(2025, 11, 7, 12, 0, 0)
        end_time = datetime(2025, 11, 7, 10, 0, 0)  # Before start!

        # Act: Should not raise in service layer
        result = await activity_service.create_activity(
            user_id=1,
            category_id=1,
            description="Task",
            tags=None,
            start_time=start_time,
            end_time=end_time
        )

        # Assert: Request sent (validation is backend's responsibility)
        mock_client.post.assert_called_once()

    @pytest.mark.unit
    async def test_create_activity_with_special_characters_in_description(
        self,
        activity_service: ActivityService,
        mock_client,
        sample_activity_data
    ):
        """
        Test activity creation with special characters.

        GIVEN: Description with emojis, quotes, newlines
        WHEN: create_activity() is called
        THEN: Special characters are preserved (JSON encoding handles them)
        """
        # Arrange
        description = "Task with 🚀 emoji and \"quotes\" and\nnewlines"
        mock_client.post.return_value = sample_activity_data

        start_time = datetime(2025, 11, 7, 10, 0, 0)
        end_time = datetime(2025, 11, 7, 11, 0, 0)

        # Act
        await activity_service.create_activity(
            user_id=1,
            category_id=1,
            description=description,
            tags=None,
            start_time=start_time,
            end_time=end_time
        )

        # Assert: Special characters preserved
        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["description"] == description

    @pytest.mark.unit
    async def test_get_user_activities_with_limit_zero(
        self,
        activity_service: ActivityService,
        mock_client
    ):
        """
        Test activity retrieval with limit=0.

        GIVEN: limit=0 (edge case)
        WHEN: get_user_activities() is called
        THEN: Request is sent with limit=0
              (Backend may return empty or reject)
        """
        # Arrange
        mock_client.get.return_value = {"activities": [], "total": 0}

        # Act
        await activity_service.get_user_activities(user_id=1, limit=0)

        # Assert: Zero limit sent
        mock_client.get.assert_called_once_with(
            "/api/v1/activities?user_id=1&limit=0"
        )
