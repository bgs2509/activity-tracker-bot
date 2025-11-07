"""
Unit tests for ActivityService.

Tests business logic without database dependencies using mocked repository.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock

from src.application.services.activity_service import ActivityService
from src.domain.models.activity import Activity
from src.schemas.activity import ActivityCreate


@pytest.fixture
def mock_repository():
    """Create mock ActivityRepository."""
    return Mock()


@pytest.fixture
def activity_service(mock_repository):
    """Create ActivityService with mocked repository."""
    return ActivityService(repository=mock_repository)


@pytest.fixture
def valid_activity_data():
    """Create valid ActivityCreate data."""
    start = datetime(2025, 11, 7, 10, 0, 0)
    end = datetime(2025, 11, 7, 11, 30, 0)
    return ActivityCreate(
        user_id=1,
        category_id=1,
        start_time=start,
        end_time=end,
        description="Testing activity"
    )


@pytest.fixture
def mock_activity():
    """Create mock Activity domain model."""
    return Activity(
        id=1,
        user_id=1,
        category_id=1,
        start_time=datetime(2025, 11, 7, 10, 0, 0),
        end_time=datetime(2025, 11, 7, 11, 30, 0),
        duration_minutes=90,
        description="Testing activity"
    )


# ============================================================================
# Test: create_activity
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_activity_success(activity_service, mock_repository, valid_activity_data, mock_activity):
    """Test successful activity creation with valid data."""
    mock_repository.create = AsyncMock(return_value=mock_activity)

    result = await activity_service.create_activity(valid_activity_data)

    assert result == mock_activity
    mock_repository.create.assert_called_once_with(valid_activity_data)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_activity_end_time_before_start_time(activity_service, valid_activity_data):
    """Test that creating activity with end_time <= start_time raises ValueError."""
    # Set end_time equal to start_time
    valid_activity_data.end_time = valid_activity_data.start_time

    with pytest.raises(ValueError, match="End time .* must be after start time"):
        await activity_service.create_activity(valid_activity_data)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_activity_end_time_equals_start_time(activity_service, valid_activity_data):
    """Test that end_time equal to start_time is rejected."""
    valid_activity_data.end_time = valid_activity_data.start_time

    with pytest.raises(ValueError, match="End time .* must be after start time"):
        await activity_service.create_activity(valid_activity_data)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_activity_duration_exceeds_24_hours(activity_service, valid_activity_data):
    """Test that activity duration > 24 hours is rejected."""
    valid_activity_data.end_time = valid_activity_data.start_time + timedelta(hours=25)

    with pytest.raises(ValueError, match="Activity duration .* exceeds maximum allowed duration \\(24h\\)"):
        await activity_service.create_activity(valid_activity_data)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_activity_duration_exactly_24_hours(activity_service, mock_repository, valid_activity_data, mock_activity):
    """Test that activity duration of exactly 24 hours is accepted."""
    valid_activity_data.end_time = valid_activity_data.start_time + timedelta(hours=24)
    mock_repository.create = AsyncMock(return_value=mock_activity)

    result = await activity_service.create_activity(valid_activity_data)

    assert result == mock_activity
    mock_repository.create.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_activity_very_short_duration(activity_service, mock_repository, valid_activity_data, mock_activity):
    """Test that very short activities (1 second) are accepted."""
    valid_activity_data.end_time = valid_activity_data.start_time + timedelta(seconds=1)
    mock_repository.create = AsyncMock(return_value=mock_activity)

    result = await activity_service.create_activity(valid_activity_data)

    assert result == mock_activity
    mock_repository.create.assert_called_once()


# ============================================================================
# Test: get_activity_by_id
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_activity_by_id_found(activity_service, mock_repository, mock_activity):
    """Test retrieving existing activity by ID."""
    mock_repository.get_by_id = AsyncMock(return_value=mock_activity)

    result = await activity_service.get_activity_by_id(activity_id=1)

    assert result == mock_activity
    mock_repository.get_by_id.assert_called_once_with(1)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_activity_by_id_not_found(activity_service, mock_repository):
    """Test retrieving non-existent activity returns None."""
    mock_repository.get_by_id = AsyncMock(return_value=None)

    result = await activity_service.get_activity_by_id(activity_id=999)

    assert result is None
    mock_repository.get_by_id.assert_called_once_with(999)


# ============================================================================
# Test: get_user_activities (pagination)
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_user_activities_default_pagination(activity_service, mock_repository, mock_activity):
    """Test getting user activities with default pagination."""
    mock_repository.get_by_user = AsyncMock(return_value=([mock_activity], 1))

    activities, total = await activity_service.get_user_activities(user_id=1)

    assert activities == [mock_activity]
    assert total == 1
    mock_repository.get_by_user.assert_called_once_with(1, 10, 0)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_user_activities_custom_pagination(activity_service, mock_repository, mock_activity):
    """Test getting user activities with custom limit and offset."""
    mock_repository.get_by_user = AsyncMock(return_value=([mock_activity], 50))

    activities, total = await activity_service.get_user_activities(
        user_id=1,
        limit=20,
        offset=10
    )

    assert activities == [mock_activity]
    assert total == 50
    mock_repository.get_by_user.assert_called_once_with(1, 20, 10)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_user_activities_empty_result(activity_service, mock_repository):
    """Test getting user activities when user has no activities."""
    mock_repository.get_by_user = AsyncMock(return_value=([], 0))

    activities, total = await activity_service.get_user_activities(user_id=1)

    assert activities == []
    assert total == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_user_activities_limit_too_low(activity_service):
    """Test that limit < 1 raises ValueError."""
    with pytest.raises(ValueError, match="Limit must be between 1 and 100, got 0"):
        await activity_service.get_user_activities(user_id=1, limit=0)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_user_activities_limit_too_high(activity_service):
    """Test that limit > 100 raises ValueError."""
    with pytest.raises(ValueError, match="Limit must be between 1 and 100, got 101"):
        await activity_service.get_user_activities(user_id=1, limit=101)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_user_activities_limit_boundary_min(activity_service, mock_repository):
    """Test that limit = 1 is accepted (minimum boundary)."""
    mock_repository.get_by_user = AsyncMock(return_value=([], 0))

    await activity_service.get_user_activities(user_id=1, limit=1)

    mock_repository.get_by_user.assert_called_once_with(1, 1, 0)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_user_activities_limit_boundary_max(activity_service, mock_repository):
    """Test that limit = 100 is accepted (maximum boundary)."""
    mock_repository.get_by_user = AsyncMock(return_value=([], 0))

    await activity_service.get_user_activities(user_id=1, limit=100)

    mock_repository.get_by_user.assert_called_once_with(1, 100, 0)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_user_activities_negative_offset(activity_service):
    """Test that negative offset raises ValueError."""
    with pytest.raises(ValueError, match="Offset must be >= 0, got -1"):
        await activity_service.get_user_activities(user_id=1, offset=-1)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_user_activities_offset_zero(activity_service, mock_repository):
    """Test that offset = 0 is accepted (boundary)."""
    mock_repository.get_by_user = AsyncMock(return_value=([], 0))

    await activity_service.get_user_activities(user_id=1, offset=0)

    mock_repository.get_by_user.assert_called_once_with(1, 10, 0)
