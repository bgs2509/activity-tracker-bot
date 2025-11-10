"""
Unit tests for UserSettingsService.

Tests business logic without database dependencies using mocked repository.
"""
import pytest
from datetime import time
from unittest.mock import AsyncMock, Mock

from src.application.services.user_settings_service import UserSettingsService
from src.domain.models.user_settings import UserSettings
from src.schemas.user_settings import UserSettingsCreate, UserSettingsUpdate


@pytest.fixture
def mock_repository():
    """Create mock UserSettingsRepository."""
    return AsyncMock()


@pytest.fixture
def user_settings_service(mock_repository):
    """Create UserSettingsService with mocked repository."""
    return UserSettingsService(repository=mock_repository)


@pytest.fixture
def valid_settings_data():
    """Create valid UserSettingsCreate data."""
    return UserSettingsCreate(
        user_id=1,
        poll_interval_weekday=60,
        poll_interval_weekend=120,
        quiet_hours_start=time(22, 0),
        quiet_hours_end=time(8, 0),
        reminder_enabled=True,
        reminder_delay_minutes=30
    )


@pytest.fixture
def mock_settings():
    """Create mock UserSettings domain model."""
    return UserSettings(
        id=1,
        user_id=1,
        poll_interval_weekday=60,
        poll_interval_weekend=120,
        quiet_hours_start=time(22, 0),
        quiet_hours_end=time(8, 0),
        reminder_enabled=True,
        reminder_delay_minutes=30
    )


# ============================================================================
# Test: create_settings
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_settings_success(user_settings_service, mock_repository, valid_settings_data, mock_settings):
    """Test successful settings creation with valid data."""
    mock_repository.get_by_user_id = AsyncMock(return_value=None)
    mock_repository.create = AsyncMock(return_value=mock_settings)

    result = await user_settings_service.create_settings(valid_settings_data)

    assert result == mock_settings
    mock_repository.get_by_user_id.assert_called_once_with(1)
    mock_repository.create.assert_called_once_with(valid_settings_data)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_settings_already_exists(user_settings_service, mock_repository, valid_settings_data, mock_settings):
    """Test that creating settings when they already exist raises ValueError."""
    mock_repository.get_by_user_id = AsyncMock(return_value=mock_settings)

    with pytest.raises(ValueError, match="Settings already exist for user 1"):
        await user_settings_service.create_settings(valid_settings_data)

    mock_repository.create.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_settings_poll_interval_weekday_too_low(user_settings_service, mock_repository, valid_settings_data):
    """Test that poll interval < 15 minutes raises ValueError."""
    mock_repository.get_by_user_id = AsyncMock(return_value=None)
    valid_settings_data.poll_interval_weekday = 14

    with pytest.raises(ValueError, match="Weekday poll interval \\(14m\\) must be at least 15 minutes"):
        await user_settings_service.create_settings(valid_settings_data)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_settings_poll_interval_weekend_too_low(user_settings_service, mock_repository, valid_settings_data):
    """Test that weekend poll interval < 15 minutes raises ValueError."""
    mock_repository.get_by_user_id = AsyncMock(return_value=None)
    valid_settings_data.poll_interval_weekend = 14

    with pytest.raises(ValueError, match="Weekend poll interval \\(14m\\) must be at least 15 minutes"):
        await user_settings_service.create_settings(valid_settings_data)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_settings_poll_interval_weekday_too_high(user_settings_service, mock_repository, valid_settings_data):
    """Test that poll interval > 1440 minutes raises ValueError."""
    mock_repository.get_by_user_id = AsyncMock(return_value=None)
    valid_settings_data.poll_interval_weekday = 1441

    with pytest.raises(ValueError, match="Weekday poll interval \\(1441m\\) cannot exceed 24 hours"):
        await user_settings_service.create_settings(valid_settings_data)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_settings_poll_interval_weekend_too_high(user_settings_service, mock_repository, valid_settings_data):
    """Test that weekend poll interval > 1440 minutes raises ValueError."""
    mock_repository.get_by_user_id = AsyncMock(return_value=None)
    valid_settings_data.poll_interval_weekend = 1500

    with pytest.raises(ValueError, match="Weekend poll interval \\(1500m\\) cannot exceed 24 hours"):
        await user_settings_service.create_settings(valid_settings_data)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_settings_poll_interval_boundary_min(user_settings_service, mock_repository, valid_settings_data, mock_settings):
    """Test that poll interval exactly 15 minutes is accepted."""
    mock_repository.get_by_user_id = AsyncMock(return_value=None)
    mock_repository.create = AsyncMock(return_value=mock_settings)
    valid_settings_data.poll_interval_weekday = 15
    valid_settings_data.poll_interval_weekend = 15

    result = await user_settings_service.create_settings(valid_settings_data)

    assert result == mock_settings


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_settings_poll_interval_boundary_max(user_settings_service, mock_repository, valid_settings_data, mock_settings):
    """Test that poll interval exactly 1440 minutes is accepted."""
    mock_repository.get_by_user_id = AsyncMock(return_value=None)
    mock_repository.create = AsyncMock(return_value=mock_settings)
    valid_settings_data.poll_interval_weekday = 1440
    valid_settings_data.poll_interval_weekend = 1440

    result = await user_settings_service.create_settings(valid_settings_data)

    assert result == mock_settings


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_settings_invalid_quiet_hours_start_format(user_settings_service, mock_repository):
    """Test that invalid quiet hours start format raises ValidationError."""
    from pydantic import ValidationError

    mock_repository.get_by_user_id = AsyncMock(return_value=None)

    # Pydantic validates when creating schema with invalid time
    with pytest.raises(ValidationError):
        UserSettingsCreate(
            user_id=1,
            poll_interval_weekday=60,
            poll_interval_weekend=120,
            quiet_hours_start="25:00",  # Invalid hour
            quiet_hours_end=time(8, 0)
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_settings_invalid_quiet_hours_end_format(user_settings_service, mock_repository):
    """Test that invalid quiet hours end format raises ValidationError."""
    from pydantic import ValidationError

    mock_repository.get_by_user_id = AsyncMock(return_value=None)

    # Pydantic validates when creating schema with invalid time
    with pytest.raises(ValidationError):
        UserSettingsCreate(
            user_id=1,
            poll_interval_weekday=60,
            poll_interval_weekend=120,
            quiet_hours_start=time(22, 0),
            quiet_hours_end="12:70"  # Invalid minute
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_settings_quiet_hours_boundary_values(user_settings_service, mock_repository, valid_settings_data, mock_settings):
    """Test quiet hours with boundary time values (00:00 and 23:59)."""
    mock_repository.get_by_user_id = AsyncMock(return_value=None)
    mock_repository.create = AsyncMock(return_value=mock_settings)
    valid_settings_data.quiet_hours_start = "00:00"
    valid_settings_data.quiet_hours_end = "23:59"

    result = await user_settings_service.create_settings(valid_settings_data)

    assert result == mock_settings


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_settings_without_quiet_hours(user_settings_service, mock_repository, mock_settings):
    """Test creating settings without quiet hours (optional fields)."""
    settings_data = UserSettingsCreate(
        user_id=1,
        poll_interval_weekday=60,
        poll_interval_weekend=120,
        quiet_hours_start=None,
        quiet_hours_end=None,
        timezone="UTC"
    )
    mock_repository.get_by_user_id = AsyncMock(return_value=None)
    mock_repository.create = AsyncMock(return_value=mock_settings)

    result = await user_settings_service.create_settings(settings_data)

    assert result == mock_settings


# ============================================================================
# Test: get_by_user_id
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_by_user_id_found(user_settings_service, mock_repository, mock_settings):
    """Test retrieving existing settings by user ID."""
    mock_repository.get_by_user_id = AsyncMock(return_value=mock_settings)

    result = await user_settings_service.get_by_user_id(user_id=1)

    assert result == mock_settings
    mock_repository.get_by_user_id.assert_called_once_with(1)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_by_user_id_not_found(user_settings_service, mock_repository):
    """Test retrieving settings for user without settings returns None."""
    mock_repository.get_by_user_id = AsyncMock(return_value=None)

    result = await user_settings_service.get_by_user_id(user_id=999)

    assert result is None


# ============================================================================
# Test: update_settings
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_settings_success(user_settings_service, mock_repository, mock_settings):
    """Test successful settings update."""
    update_data = UserSettingsUpdate(poll_interval_weekday=90)
    updated_settings = UserSettings(
        id=1,
        user_id=1,
        poll_interval_weekday=90,
        poll_interval_weekend=120,
        quiet_hours_start=time(22, 0),
        quiet_hours_end=time(8, 0),
        reminder_enabled=True,
        reminder_delay_minutes=30
    )
    mock_repository.get_by_user_id = AsyncMock(return_value=mock_settings)
    mock_repository.update = AsyncMock(return_value=updated_settings)

    result = await user_settings_service.update_settings(user_id=1, settings_data=update_data)

    assert result == updated_settings
    mock_repository.update.assert_called_once_with(1, update_data)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_settings_not_found(user_settings_service, mock_repository):
    """Test updating settings when they don't exist raises ValueError."""
    update_data = UserSettingsUpdate(poll_interval_weekday=90)
    mock_repository.get_by_user_id = AsyncMock(return_value=None)

    with pytest.raises(ValueError, match="Settings not found for user 1"):
        await user_settings_service.update_settings(user_id=1, settings_data=update_data)

    mock_repository.update.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_settings_poll_interval_validation(user_settings_service, mock_repository, mock_settings):
    """Test that updating poll interval triggers validation."""
    update_data = UserSettingsUpdate(poll_interval_weekday=14)  # Too low
    mock_repository.get_by_user_id = AsyncMock(return_value=mock_settings)

    with pytest.raises(ValueError, match="Weekday poll interval \\(14m\\) must be at least 15 minutes"):
        await user_settings_service.update_settings(user_id=1, settings_data=update_data)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_settings_quiet_hours_validation(user_settings_service, mock_repository, mock_settings):
    """Test that updating quiet hours triggers validation."""
    from pydantic import ValidationError

    mock_repository.get_by_user_id = AsyncMock(return_value=mock_settings)

    # Pydantic validates before service code runs
    with pytest.raises(ValidationError):
        update_data = UserSettingsUpdate(quiet_hours_start="25:00")  # Invalid


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_settings_partial_update(user_settings_service, mock_repository, mock_settings):
    """Test updating only one field doesn't require all fields."""
    update_data = UserSettingsUpdate(reminder_enabled=False)
    updated_settings = UserSettings(
        id=1,
        user_id=1,
        poll_interval_weekday=60,
        poll_interval_weekend=120,
        quiet_hours_start=time(22, 0),
        quiet_hours_end=time(8, 0),
        reminder_enabled=False,
        reminder_delay_minutes=30
    )
    mock_repository.get_by_user_id = AsyncMock(return_value=mock_settings)
    mock_repository.update = AsyncMock(return_value=updated_settings)

    result = await user_settings_service.update_settings(user_id=1, settings_data=update_data)

    assert result.reminder_enabled is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_settings_uses_existing_values_for_validation(user_settings_service, mock_repository, mock_settings):
    """Test that update validation uses existing values when partial update provided."""
    # Update only weekday interval, validation should use existing weekend interval
    update_data = UserSettingsUpdate(poll_interval_weekday=45)
    updated_settings = UserSettings(
        id=1,
        user_id=1,
        poll_interval_weekday=45,
        poll_interval_weekend=120,
        quiet_hours_start=time(22, 0),
        quiet_hours_end=time(8, 0),
        reminder_enabled=True,
        reminder_delay_minutes=30
    )
    mock_repository.get_by_user_id = AsyncMock(return_value=mock_settings)
    mock_repository.update = AsyncMock(return_value=updated_settings)

    result = await user_settings_service.update_settings(user_id=1, settings_data=update_data)

    assert result.poll_interval_weekday == 45
    assert result.poll_interval_weekend == 120  # Unchanged
