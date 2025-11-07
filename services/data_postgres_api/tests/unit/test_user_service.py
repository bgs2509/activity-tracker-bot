"""
Unit tests for UserService.

Tests business logic without database dependencies using mocked repository.
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock

from src.application.services.user_service import UserService
from src.domain.models.user import User
from src.schemas.user import UserCreate


@pytest.fixture
def mock_repository():
    """Create mock UserRepository."""
    return Mock()


@pytest.fixture
def user_service(mock_repository):
    """Create UserService with mocked repository."""
    return UserService(repository=mock_repository)


@pytest.fixture
def valid_user_data():
    """Create valid UserCreate data."""
    return UserCreate(
        telegram_id=123456789,
        first_name="John",
        last_name="Doe",
        username="johndoe",
        language_code="en"
    )


@pytest.fixture
def mock_user():
    """Create mock User domain model."""
    return User(
        id=1,
        telegram_id=123456789,
        first_name="John",
        last_name="Doe",
        username="johndoe",
        language_code="en",
        created_at=datetime(2025, 11, 7, 10, 0, 0),
        last_poll_time=None
    )


# ============================================================================
# Test: create_user
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_user_success(user_service, mock_repository, valid_user_data, mock_user):
    """Test successful user creation with unique Telegram ID."""
    mock_repository.get_by_telegram_id = AsyncMock(return_value=None)
    mock_repository.create = AsyncMock(return_value=mock_user)

    result = await user_service.create_user(valid_user_data)

    assert result == mock_user
    mock_repository.get_by_telegram_id.assert_called_once_with(123456789)
    mock_repository.create.assert_called_once_with(valid_user_data)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_user_duplicate_telegram_id(user_service, mock_repository, valid_user_data, mock_user):
    """Test that creating user with duplicate Telegram ID raises ValueError."""
    mock_repository.get_by_telegram_id = AsyncMock(return_value=mock_user)

    with pytest.raises(ValueError, match="User with Telegram ID 123456789 already exists"):
        await user_service.create_user(valid_user_data)

    mock_repository.create.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_user_without_optional_fields(user_service, mock_repository):
    """Test creating user without optional fields (last_name, username)."""
    user_data = UserCreate(
        telegram_id=987654321,
        first_name="Jane",
        last_name=None,
        username=None,
        language_code="ru"
    )
    created_user = User(
        id=2,
        telegram_id=987654321,
        first_name="Jane",
        last_name=None,
        username=None,
        language_code="ru",
        created_at=datetime.now()
    )
    mock_repository.get_by_telegram_id = AsyncMock(return_value=None)
    mock_repository.create = AsyncMock(return_value=created_user)

    result = await user_service.create_user(user_data)

    assert result == created_user
    assert result.last_name is None
    assert result.username is None


# ============================================================================
# Test: get_by_telegram_id
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_by_telegram_id_found(user_service, mock_repository, mock_user):
    """Test retrieving existing user by Telegram ID."""
    mock_repository.get_by_telegram_id = AsyncMock(return_value=mock_user)

    result = await user_service.get_by_telegram_id(telegram_id=123456789)

    assert result == mock_user
    mock_repository.get_by_telegram_id.assert_called_once_with(123456789)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_by_telegram_id_not_found(user_service, mock_repository):
    """Test retrieving non-existent user returns None."""
    mock_repository.get_by_telegram_id = AsyncMock(return_value=None)

    result = await user_service.get_by_telegram_id(telegram_id=999999999)

    assert result is None


# ============================================================================
# Test: get_by_id
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_by_id_found(user_service, mock_repository, mock_user):
    """Test retrieving existing user by internal ID."""
    mock_repository.get_by_id = AsyncMock(return_value=mock_user)

    result = await user_service.get_by_id(user_id=1)

    assert result == mock_user
    mock_repository.get_by_id.assert_called_once_with(1)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_by_id_not_found(user_service, mock_repository):
    """Test retrieving non-existent user by ID returns None."""
    mock_repository.get_by_id = AsyncMock(return_value=None)

    result = await user_service.get_by_id(user_id=999)

    assert result is None


# ============================================================================
# Test: update_last_poll_time
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_last_poll_time_success(user_service, mock_repository, mock_user):
    """Test successful update of last poll time."""
    poll_time = datetime(2025, 11, 7, 12, 0, 0)
    updated_user = User(
        id=1,
        telegram_id=123456789,
        first_name="John",
        last_name="Doe",
        username="johndoe",
        language_code="en",
        created_at=datetime(2025, 11, 7, 10, 0, 0),
        last_poll_time=poll_time
    )
    mock_repository.get_by_id = AsyncMock(return_value=mock_user)
    mock_repository.update_last_poll_time = AsyncMock(return_value=updated_user)

    result = await user_service.update_last_poll_time(user_id=1, poll_time=poll_time)

    assert result == updated_user
    assert result.last_poll_time == poll_time
    mock_repository.get_by_id.assert_called_once_with(1)
    mock_repository.update_last_poll_time.assert_called_once_with(1, poll_time)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_last_poll_time_user_not_found(user_service, mock_repository):
    """Test that updating last poll time for non-existent user raises ValueError."""
    poll_time = datetime(2025, 11, 7, 12, 0, 0)
    mock_repository.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(ValueError, match="User 999 not found"):
        await user_service.update_last_poll_time(user_id=999, poll_time=poll_time)

    mock_repository.update_last_poll_time.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_last_poll_time_multiple_updates(user_service, mock_repository, mock_user):
    """Test multiple consecutive poll time updates."""
    poll_time1 = datetime(2025, 11, 7, 12, 0, 0)
    poll_time2 = datetime(2025, 11, 7, 14, 0, 0)

    updated_user1 = User(
        id=1,
        telegram_id=123456789,
        first_name="John",
        last_name="Doe",
        username="johndoe",
        language_code="en",
        created_at=datetime(2025, 11, 7, 10, 0, 0),
        last_poll_time=poll_time1
    )
    updated_user2 = User(
        id=1,
        telegram_id=123456789,
        first_name="John",
        last_name="Doe",
        username="johndoe",
        language_code="en",
        created_at=datetime(2025, 11, 7, 10, 0, 0),
        last_poll_time=poll_time2
    )

    mock_repository.get_by_id = AsyncMock(return_value=mock_user)
    mock_repository.update_last_poll_time = AsyncMock(side_effect=[updated_user1, updated_user2])

    result1 = await user_service.update_last_poll_time(user_id=1, poll_time=poll_time1)
    result2 = await user_service.update_last_poll_time(user_id=1, poll_time=poll_time2)

    assert result1.last_poll_time == poll_time1
    assert result2.last_poll_time == poll_time2
    assert mock_repository.update_last_poll_time.call_count == 2
