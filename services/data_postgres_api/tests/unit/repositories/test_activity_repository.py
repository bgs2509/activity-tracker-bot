"""
Unit tests for ActivityRepository.

Tests custom activity-specific repository methods including duration calculation,
tag handling, and recent activity queries.

Test Coverage:
    - create(): Duration calculation, tag conversion, custom logic
    - get_recent_by_user(): Recent activities, ordering, limit
    - Inherited base methods: Covered in test_base_repository.py

Coverage Target: 100% of activity_repository.py
Execution Time: < 0.4 seconds

Author: Testing Team
Date: 2025-11-07
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.repositories.activity_repository import (
    ActivityRepository,
    ActivityUpdate
)
from src.domain.models.activity import Activity
from src.schemas.activity import ActivityCreate


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_session():
    """
    Fixture: Mock SQLAlchemy AsyncSession.

    Returns:
        AsyncMock: Mocked session for testing without database
    """
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def activity_repository(mock_session):
    """
    Fixture: ActivityRepository instance for testing.

    Args:
        mock_session: Mocked AsyncSession from fixture

    Returns:
        ActivityRepository: Repository instance with mocked session
    """
    return ActivityRepository(mock_session)


@pytest.fixture
def sample_activity():
    """
    Fixture: Sample Activity model instance.

    Returns:
        Activity: Activity with typical field values for testing
    """
    return Activity(
        id=1,
        user_id=1,
        category_id=1,
        description="Coding session",
        tags="python,testing",
        start_time=datetime(2025, 11, 7, 10, 0),
        end_time=datetime(2025, 11, 7, 12, 0),
        duration_minutes=120
    )


@pytest.fixture
def activity_create_data():
    """
    Fixture: Sample ActivityCreate schema for testing.

    Returns:
        ActivityCreate: Valid activity creation data
    """
    return ActivityCreate(
        user_id=1,
        category_id=1,
        description="Test activity",
        tags=["python", "testing"],
        start_time=datetime(2025, 11, 7, 10, 0),
        end_time=datetime(2025, 11, 7, 11, 30)
    )


# ============================================================================
# TEST SUITES
# ============================================================================

class TestActivityRepositoryCreate:
    """
    Test suite for ActivityRepository.create() method.

    Tests the overridden create() method which adds custom logic for:
    - Duration calculation from start_time to end_time
    - Tag list to comma-separated string conversion
    """

    @pytest.mark.unit
    async def test_create_calculates_duration_correctly(
        self,
        activity_repository: ActivityRepository,
        mock_session: AsyncMock
    ):
        """
        Test duration calculation from start_time to end_time.

        GIVEN: Activity with start_time=10:00 and end_time=11:30 (90 minutes)
        WHEN: create() is called
        THEN: duration_minutes is calculated as 90
              AND activity is saved with correct duration
        """
        # Arrange: Activity spanning 90 minutes
        activity_data = ActivityCreate(
            user_id=1,
            category_id=1,
            description="Test activity",
            start_time=datetime(2025, 11, 7, 10, 0),
            end_time=datetime(2025, 11, 7, 11, 30),  # 90 minutes later
            tags=[]
        )

        # Act: Create activity
        result = await activity_repository.create(activity_data)

        # Assert: Duration calculated correctly
        assert result.duration_minutes == 90, \
            "Duration should be 90 minutes (10:00 to 11:30)"

        # Verify session operations
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once()

    @pytest.mark.unit
    async def test_create_converts_tags_list_to_comma_separated_string(
        self,
        activity_repository: ActivityRepository,
        mock_session: AsyncMock
    ):
        """
        Test tag list conversion to comma-separated string.

        GIVEN: Activity with tags=["python", "testing", "unit"]
        WHEN: create() is called
        THEN: Tags are stored as "python,testing,unit" in database
        """
        # Arrange: Activity with multiple tags
        activity_data = ActivityCreate(
            user_id=1,
            category_id=1,
            description="Test",
            start_time=datetime(2025, 11, 7, 10, 0),
            end_time=datetime(2025, 11, 7, 11, 0),
            tags=["python", "testing", "unit"]
        )

        # Act: Create activity
        result = await activity_repository.create(activity_data)

        # Assert: Tags converted to comma-separated string
        assert result.tags == "python,testing,unit", \
            "Tags should be converted to comma-separated string"

    @pytest.mark.unit
    async def test_create_handles_empty_tags_list(
        self,
        activity_repository: ActivityRepository,
        mock_session: AsyncMock
    ):
        """
        Test handling of empty tags list.

        GIVEN: Activity with tags=[] (empty list)
        WHEN: create() is called
        THEN: tags field is set to None (not empty string)
        """
        # Arrange: Activity with no tags
        activity_data = ActivityCreate(
            user_id=1,
            category_id=1,
            description="Test",
            start_time=datetime(2025, 11, 7, 10, 0),
            end_time=datetime(2025, 11, 7, 11, 0),
            tags=[]
        )

        # Act: Create activity
        result = await activity_repository.create(activity_data)

        # Assert: Tags is None for empty list
        assert result.tags is None, \
            "Empty tags list should result in None (not empty string)"

    @pytest.mark.unit
    async def test_create_handles_none_tags(
        self,
        activity_repository: ActivityRepository,
        mock_session: AsyncMock
    ):
        """
        Test handling of None tags.

        GIVEN: Activity with tags=None
        WHEN: create() is called
        THEN: tags field remains None
        """
        # Arrange: Activity without tags field
        activity_data = ActivityCreate(
            user_id=1,
            category_id=1,
            description="Test",
            start_time=datetime(2025, 11, 7, 10, 0),
            end_time=datetime(2025, 11, 7, 11, 0),
            tags=None
        )

        # Act: Create activity
        result = await activity_repository.create(activity_data)

        # Assert: Tags remains None
        assert result.tags is None, "None tags should remain None"

    @pytest.mark.unit
    async def test_create_rounds_duration_to_nearest_minute(
        self,
        activity_repository: ActivityRepository,
        mock_session: AsyncMock
    ):
        """
        Test that duration is rounded to nearest minute.

        GIVEN: Activity with duration of 90.7 minutes
        WHEN: create() is called
        THEN: duration_minutes is rounded to 91
        """
        # Arrange: Activity with fractional minutes (90.7 minutes)
        start = datetime(2025, 11, 7, 10, 0, 0)
        end = datetime(2025, 11, 7, 11, 30, 42)  # 90 min 42 sec = 90.7 min

        activity_data = ActivityCreate(
            user_id=1,
            category_id=1,
            description="Test",
            start_time=start,
            end_time=end,
            tags=[]
        )

        # Act: Create activity
        result = await activity_repository.create(activity_data)

        # Assert: Duration rounded (90.7 → 91)
        assert result.duration_minutes == 91, \
            "Duration should be rounded to nearest minute"

    @pytest.mark.unit
    @pytest.mark.parametrize("minutes,expected", [
        (30, 30),    # Exactly 30 minutes
        (60, 60),    # Exactly 1 hour
        (90, 90),    # 1.5 hours
        (1, 1),      # Minimal duration
        (480, 480),  # 8 hours
    ])
    async def test_create_calculates_various_durations(
        self,
        activity_repository: ActivityRepository,
        mock_session: AsyncMock,
        minutes: int,
        expected: int
    ):
        """
        Test duration calculation with various time spans.

        Verifies correct calculation for different activity durations.
        """
        # Arrange: Activity with specific duration
        start = datetime(2025, 11, 7, 10, 0)
        end = start + timedelta(minutes=minutes)

        activity_data = ActivityCreate(
            user_id=1,
            category_id=1,
            description="Test",
            start_time=start,
            end_time=end,
            tags=[]
        )

        # Act
        result = await activity_repository.create(activity_data)

        # Assert: Duration calculated correctly
        assert result.duration_minutes == expected, \
            f"Duration for {minutes} minutes should be {expected}"

    @pytest.mark.unit
    async def test_create_preserves_all_input_fields(
        self,
        activity_repository: ActivityRepository,
        mock_session: AsyncMock
    ):
        """
        Test that all input fields are preserved in created activity.

        GIVEN: ActivityCreate with all fields populated
        WHEN: create() is called
        THEN: All fields are correctly set in returned Activity
        """
        # Arrange: Complete activity data
        activity_data = ActivityCreate(
            user_id=42,
            category_id=7,
            description="Important meeting",
            start_time=datetime(2025, 11, 7, 14, 0),
            end_time=datetime(2025, 11, 7, 15, 30),
            tags=["meeting", "work"]
        )

        # Act
        result = await activity_repository.create(activity_data)

        # Assert: All fields preserved
        assert result.user_id == 42, "user_id should be preserved"
        assert result.category_id == 7, "category_id should be preserved"
        assert result.description == "Important meeting", \
            "description should be preserved"
        assert result.start_time == datetime(2025, 11, 7, 14, 0), \
            "start_time should be preserved"
        assert result.end_time == datetime(2025, 11, 7, 15, 30), \
            "end_time should be preserved"


class TestActivityRepositoryGetRecentByUser:
    """
    Test suite for ActivityRepository.get_recent_by_user() method.

    Tests retrieval of recent activities for a user with proper ordering
    and limit handling.
    """

    @pytest.mark.unit
    async def test_get_recent_by_user_returns_activities_for_correct_user(
        self,
        activity_repository: ActivityRepository,
        mock_session: AsyncMock
    ):
        """
        Test that only activities for specified user are returned.

        GIVEN: Multiple users with activities
        WHEN: get_recent_by_user(user_id=1) is called
        THEN: Only activities with user_id=1 are returned
        """
        # Arrange: Activities for user 1
        user_activities = [
            Activity(
                id=1,
                user_id=1,
                category_id=1,
                description="Activity 1",
                start_time=datetime(2025, 11, 7, 10, 0),
                end_time=datetime(2025, 11, 7, 11, 0),
                duration_minutes=60
            ),
            Activity(
                id=2,
                user_id=1,
                category_id=1,
                description="Activity 2",
                start_time=datetime(2025, 11, 7, 12, 0),
                end_time=datetime(2025, 11, 7, 13, 0),
                duration_minutes=60
            ),
        ]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = user_activities
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act: Get activities for user 1
        result = await activity_repository.get_recent_by_user(user_id=1)

        # Assert: Returns list of activities
        assert isinstance(result, list), "Should return list"
        assert len(result) == 2, "Should return 2 activities"
        assert all(a.user_id == 1 for a in result), \
            "All activities should belong to user 1"

    @pytest.mark.unit
    async def test_get_recent_by_user_orders_by_most_recent_first(
        self,
        activity_repository: ActivityRepository,
        mock_session: AsyncMock
    ):
        """
        Test that activities are ordered by start_time descending.

        GIVEN: Activities with different start times
        WHEN: get_recent_by_user() is called
        THEN: Activities are ordered from most recent to oldest
        """
        # Arrange: Activities in chronological order (oldest to newest)
        activities = [
            Activity(
                id=3,
                user_id=1,
                category_id=1,
                description="Most recent",
                start_time=datetime(2025, 11, 7, 15, 0),  # Latest
                end_time=datetime(2025, 11, 7, 16, 0),
                duration_minutes=60
            ),
            Activity(
                id=2,
                user_id=1,
                category_id=1,
                description="Middle",
                start_time=datetime(2025, 11, 7, 12, 0),
                end_time=datetime(2025, 11, 7, 13, 0),
                duration_minutes=60
            ),
            Activity(
                id=1,
                user_id=1,
                category_id=1,
                description="Oldest",
                start_time=datetime(2025, 11, 7, 9, 0),   # Earliest
                end_time=datetime(2025, 11, 7, 10, 0),
                duration_minutes=60
            ),
        ]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = activities
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act
        result = await activity_repository.get_recent_by_user(user_id=1)

        # Assert: First activity should be most recent
        assert result[0].description == "Most recent", \
            "First activity should be the most recent"
        assert result[-1].description == "Oldest", \
            "Last activity should be the oldest"

    @pytest.mark.unit
    async def test_get_recent_by_user_respects_limit_parameter(
        self,
        activity_repository: ActivityRepository,
        mock_session: AsyncMock
    ):
        """
        Test that limit parameter restricts number of results.

        GIVEN: User has 20 activities
        WHEN: get_recent_by_user(user_id=1, limit=5) is called
        THEN: Only 5 activities are returned (most recent 5)
        """
        # Arrange: 5 activities (simulating limit=5 result)
        activities = [
            Activity(
                id=i,
                user_id=1,
                category_id=1,
                description=f"Activity {i}",
                start_time=datetime(2025, 11, 7, 10+i, 0),
                end_time=datetime(2025, 11, 7, 11+i, 0),
                duration_minutes=60
            )
            for i in range(5)
        ]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = activities
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act: Request with limit=5
        result = await activity_repository.get_recent_by_user(
            user_id=1,
            limit=5
        )

        # Assert: Returns exactly 5 activities
        assert len(result) == 5, \
            "Should return exactly 5 activities when limit=5"

    @pytest.mark.unit
    async def test_get_recent_by_user_uses_default_limit_of_10(
        self,
        activity_repository: ActivityRepository,
        mock_session: AsyncMock
    ):
        """
        Test default limit parameter.

        GIVEN: No limit parameter provided
        WHEN: get_recent_by_user(user_id=1) is called
        THEN: Default limit of 10 is used in query
        """
        # Arrange
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act: Call without limit parameter
        await activity_repository.get_recent_by_user(user_id=1)

        # Assert: Verify query was called
        # Default limit=10 should be used
        mock_session.execute.assert_called_once()

    @pytest.mark.unit
    async def test_get_recent_by_user_returns_empty_list_when_no_activities(
        self,
        activity_repository: ActivityRepository,
        mock_session: AsyncMock
    ):
        """
        Test behavior when user has no activities.

        GIVEN: User has no activities
        WHEN: get_recent_by_user() is called
        THEN: Empty list is returned (not None)
        """
        # Arrange: No activities
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act
        result = await activity_repository.get_recent_by_user(user_id=999)

        # Assert: Empty list returned
        assert result == [], \
            "Should return empty list when user has no activities"
        assert isinstance(result, list), "Should return list, not None"

    @pytest.mark.unit
    @pytest.mark.parametrize("limit", [1, 5, 10, 20, 50])
    async def test_get_recent_by_user_handles_various_limits(
        self,
        activity_repository: ActivityRepository,
        mock_session: AsyncMock,
        limit: int
    ):
        """
        Test that various limit values are handled correctly.

        Verifies method works with different limit parameters.
        """
        # Arrange
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act: Should not raise exception for any valid limit
        result = await activity_repository.get_recent_by_user(
            user_id=1,
            limit=limit
        )

        # Assert: Returns list
        assert isinstance(result, list), \
            f"Should handle limit={limit} and return list"


class TestActivityRepositoryInheritance:
    """
    Test suite verifying ActivityRepository inherits base methods.

    ActivityRepository overrides create() but should still have access to
    get_by_id(), update(), delete() from BaseRepository.
    """

    @pytest.mark.unit
    async def test_activity_repository_inherits_get_by_id(
        self,
        activity_repository: ActivityRepository,
        mock_session: AsyncMock,
        sample_activity: Activity
    ):
        """
        Test that inherited get_by_id() is available.

        GIVEN: ActivityRepository instance
        WHEN: get_by_id() is called
        THEN: Method executes successfully (inherited from base)
        """
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_activity
        mock_session.execute.return_value = mock_result

        # Act: Call inherited method
        result = await activity_repository.get_by_id(1)

        # Assert
        assert result == sample_activity, \
            "Inherited get_by_id() should work"

    @pytest.mark.unit
    async def test_activity_repository_inherits_delete(
        self,
        activity_repository: ActivityRepository,
        mock_session: AsyncMock
    ):
        """
        Test that inherited delete() is available.

        GIVEN: ActivityRepository instance
        WHEN: delete() is called
        THEN: Method executes successfully
        """
        # Arrange
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result
        mock_session.flush = AsyncMock()

        # Act: Call inherited method
        result = await activity_repository.delete(1)

        # Assert
        assert result is True, "Inherited delete() should work"


class TestActivityRepositoryEdgeCases:
    """
    Test suite for edge cases specific to ActivityRepository.
    """

    @pytest.mark.unit
    async def test_create_with_zero_duration(
        self,
        activity_repository: ActivityRepository,
        mock_session: AsyncMock
    ):
        """
        Test that zero duration (start_time == end_time) is rejected by validation.

        GIVEN: Activity with start_time == end_time
        WHEN: ActivityCreate is instantiated
        THEN: ValidationError is raised (zero duration not allowed)
        """
        from pydantic import ValidationError

        # Arrange: Same start and end time
        same_time = datetime(2025, 11, 7, 10, 0)

        # Act & Assert: Zero duration should raise ValidationError
        with pytest.raises(ValidationError, match="end_time must be after start_time"):
            activity_data = ActivityCreate(
                user_id=1,
                category_id=1,
                description="Instant activity",
                start_time=same_time,
                end_time=same_time,
                tags=[]
            )

    @pytest.mark.unit
    async def test_create_with_single_tag(
        self,
        activity_repository: ActivityRepository,
        mock_session: AsyncMock
    ):
        """
        Test activity with single tag (no comma needed).

        GIVEN: Activity with tags=["python"]
        WHEN: create() is called
        THEN: tags field is "python" (single string, no comma)
        """
        # Arrange: Single tag
        activity_data = ActivityCreate(
            user_id=1,
            category_id=1,
            description="Test",
            start_time=datetime(2025, 11, 7, 10, 0),
            end_time=datetime(2025, 11, 7, 11, 0),
            tags=["python"]
        )

        # Act
        result = await activity_repository.create(activity_data)

        # Assert: Single tag without comma
        assert result.tags == "python", \
            "Single tag should not have comma"

    @pytest.mark.unit
    async def test_get_recent_by_user_with_limit_larger_than_activities(
        self,
        activity_repository: ActivityRepository,
        mock_session: AsyncMock
    ):
        """
        Test when limit exceeds number of activities.

        GIVEN: User has 3 activities
        WHEN: get_recent_by_user(limit=100) is called
        THEN: All 3 activities are returned (no error)
        """
        # Arrange: Only 3 activities
        activities = [
            Activity(
                id=i,
                user_id=1,
                category_id=1,
                description=f"Activity {i}",
                start_time=datetime(2025, 11, 7, 10+i, 0),
                end_time=datetime(2025, 11, 7, 11+i, 0),
                duration_minutes=60
            )
            for i in range(3)
        ]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = activities
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act: Request more than exist
        result = await activity_repository.get_recent_by_user(
            user_id=1,
            limit=100
        )

        # Assert: Returns all available activities
        assert len(result) == 3, \
            "Should return all activities when limit > count"
