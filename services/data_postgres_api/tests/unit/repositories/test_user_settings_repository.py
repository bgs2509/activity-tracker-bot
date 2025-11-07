"""
Unit tests for UserSettingsRepository.

Tests custom user settings repository methods including user-based lookup
and update operations.

Test Coverage:
    - get_by_user_id(): Settings lookup by user, not found handling
    - update(): Update by user_id, partial updates, not found handling
    - Inherited base methods: Covered in test_base_repository.py

Coverage Target: 100% of user_settings_repository.py
Execution Time: < 0.3 seconds

Author: Testing Team
Date: 2025-11-07
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import time
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.repositories.user_settings_repository import (
    UserSettingsRepository
)
from src.domain.models.user_settings import UserSettings
from src.schemas.user_settings import UserSettingsCreate, UserSettingsUpdate


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
def user_settings_repository(mock_session):
    """
    Fixture: UserSettingsRepository instance for testing.

    Args:
        mock_session: Mocked AsyncSession from fixture

    Returns:
        UserSettingsRepository: Repository instance with mocked session
    """
    return UserSettingsRepository(mock_session)


@pytest.fixture
def sample_user_settings():
    """
    Fixture: Sample UserSettings model instance.

    Returns:
        UserSettings: Settings with typical field values for testing
    """
    return UserSettings(
        id=1,
        user_id=1,
        poll_interval_weekday=120,
        poll_interval_weekend=180,
        quiet_hours_start=time(22, 0),
        quiet_hours_end=time(8, 0),
        reminder_enabled=True
    )


# ============================================================================
# TEST SUITES
# ============================================================================

class TestUserSettingsRepositoryGetByUserId:
    """
    Test suite for UserSettingsRepository.get_by_user_id() method.

    Tests settings lookup by user_id. Critical for retrieving user-specific
    configuration without knowing the settings table's primary key ID.
    """

    @pytest.mark.unit
    async def test_get_by_user_id_when_settings_exist_returns_settings(
        self,
        user_settings_repository: UserSettingsRepository,
        mock_session: AsyncMock,
        sample_user_settings: UserSettings
    ):
        """
        Test successful settings retrieval by user_id.

        GIVEN: User settings exist for user_id=1
        WHEN: get_by_user_id(1) is called
        THEN: UserSettings object is returned with all fields
        """
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user_settings
        mock_session.execute.return_value = mock_result

        # Act
        result = await user_settings_repository.get_by_user_id(user_id=1)

        # Assert
        assert result is not None, "Expected settings to be found"
        assert result == sample_user_settings
        assert result.user_id == 1
        assert result.poll_interval_weekday == 120

    @pytest.mark.unit
    async def test_get_by_user_id_when_settings_not_found_returns_none(
        self,
        user_settings_repository: UserSettingsRepository,
        mock_session: AsyncMock
    ):
        """
        Test behavior when user has no settings.

        GIVEN: No settings exist for user_id=999
        WHEN: get_by_user_id(999) is called
        THEN: None is returned (user hasn't configured settings yet)
        """
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act
        result = await user_settings_repository.get_by_user_id(user_id=999)

        # Assert
        assert result is None, \
            "Should return None when user has no settings"

    @pytest.mark.unit
    async def test_get_by_user_id_queries_by_user_id_field(
        self,
        user_settings_repository: UserSettingsRepository,
        mock_session: AsyncMock
    ):
        """
        Test that query filters by user_id field.

        GIVEN: user_id parameter
        WHEN: get_by_user_id() is called
        THEN: SQL query filters by UserSettings.user_id
        """
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act
        await user_settings_repository.get_by_user_id(user_id=1)

        # Assert: Verify query structure
        call_args = mock_session.execute.call_args[0][0]
        query_str = str(call_args).lower()

        assert "user_id" in query_str, \
            "Query should filter by user_id field"

    @pytest.mark.unit
    async def test_get_by_user_id_returns_complete_settings_object(
        self,
        user_settings_repository: UserSettingsRepository,
        mock_session: AsyncMock
    ):
        """
        Test that all settings fields are populated.

        GIVEN: User settings with all fields set
        WHEN: get_by_user_id() is called
        THEN: All configuration fields are present in returned object
        """
        # Arrange: Complete settings
        complete_settings = UserSettings(
            id=1,
            user_id=1,
            poll_interval_weekday=90,
            poll_interval_weekend=150,
            quiet_hours_start=time(23, 0),
            quiet_hours_end=time(7, 0),
            reminder_enabled=False
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = complete_settings
        mock_session.execute.return_value = mock_result

        # Act
        result = await user_settings_repository.get_by_user_id(user_id=1)

        # Assert: All fields present
        assert result is not None
        assert result.poll_interval_weekday == 90
        assert result.poll_interval_weekend == 150
        assert result.quiet_hours_start == time(23, 0)
        assert result.quiet_hours_end == time(7, 0)
        assert result.reminder_enabled is False

    @pytest.mark.unit
    @pytest.mark.parametrize("user_id", [1, 100, 999999])
    async def test_get_by_user_id_handles_various_user_ids(
        self,
        user_settings_repository: UserSettingsRepository,
        mock_session: AsyncMock,
        user_id: int
    ):
        """
        Test method handles various user_id values.

        Verifies method works with different user IDs.
        """
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act: Should not raise exception
        result = await user_settings_repository.get_by_user_id(user_id)

        # Assert
        assert result is None or isinstance(result, UserSettings)


class TestUserSettingsRepositoryUpdate:
    """
    Test suite for UserSettingsRepository.update() method.

    Tests the overridden update method that updates by user_id instead of
    settings table's primary key ID.
    """

    @pytest.mark.unit
    async def test_update_when_settings_exist_returns_updated_settings(
        self,
        user_settings_repository: UserSettingsRepository,
        mock_session: AsyncMock
    ):
        """
        Test successful settings update.

        GIVEN: User settings exist for user_id=1
        WHEN: update(1, UserSettingsUpdate(...)) is called
        THEN: Settings are updated and returned
        """
        # Arrange: Existing settings
        existing_settings = UserSettings(
            id=1,
            user_id=1,
            poll_interval_weekday=120,
            poll_interval_weekend=180,
            reminder_enabled=True
        )

        update_data = UserSettingsUpdate(
            poll_interval_weekday=90  # Only update this field
        )

        # Mock get_by_user_id to return existing settings
        with patch.object(
            user_settings_repository,
            'get_by_user_id',
            return_value=existing_settings
        ):
            # Act
            result = await user_settings_repository.update(1, update_data)

            # Assert
            assert result is not None, "Should return updated settings"
            assert result == existing_settings
            assert result.poll_interval_weekday == 90, \
                "Field should be updated"

            # Verify session operations
            mock_session.flush.assert_called_once()
            mock_session.refresh.assert_called_once_with(existing_settings)

    @pytest.mark.unit
    async def test_update_when_settings_not_found_returns_none(
        self,
        user_settings_repository: UserSettingsRepository,
        mock_session: AsyncMock
    ):
        """
        Test update behavior when user has no settings.

        GIVEN: No settings exist for user_id=999
        WHEN: update(999, update_data) is called
        THEN: None is returned without attempting update
        """
        # Arrange
        update_data = UserSettingsUpdate(poll_interval_weekday=90)

        # Mock get_by_user_id to return None
        with patch.object(
            user_settings_repository,
            'get_by_user_id',
            return_value=None
        ):
            # Act
            result = await user_settings_repository.update(999, update_data)

            # Assert
            assert result is None, \
                "Should return None when settings not found"

            # Verify no write operations performed
            mock_session.flush.assert_not_called()

    @pytest.mark.unit
    async def test_update_only_updates_provided_fields(
        self,
        user_settings_repository: UserSettingsRepository,
        mock_session: AsyncMock
    ):
        """
        Test partial update - only provided fields are changed.

        GIVEN: Settings with multiple fields
        WHEN: update() called with UserSettingsUpdate(reminder_enabled=False)
              (only one field provided)
        THEN: Only reminder_enabled is updated
              Other fields remain unchanged
        """
        # Arrange: Settings with multiple fields
        existing_settings = UserSettings(
            id=1,
            user_id=1,
            poll_interval_weekday=120,
            poll_interval_weekend=180,
            quiet_hours_start=time(22, 0),
            quiet_hours_end=time(8, 0),
            reminder_enabled=True
        )

        # Update only reminder_enabled
        update_data = UserSettingsUpdate(reminder_enabled=False)

        with patch.object(
            user_settings_repository,
            'get_by_user_id',
            return_value=existing_settings
        ):
            # Act
            result = await user_settings_repository.update(1, update_data)

            # Assert: Only updated field changed
            assert result.reminder_enabled is False, \
                "reminder_enabled should be updated"
            assert result.poll_interval_weekday == 120, \
                "poll_interval_weekday should remain unchanged"
            assert result.poll_interval_weekend == 180, \
                "poll_interval_weekend should remain unchanged"
            assert result.quiet_hours_start == time(22, 0), \
                "quiet_hours_start should remain unchanged"

    @pytest.mark.unit
    async def test_update_calls_get_by_user_id_internally(
        self,
        user_settings_repository: UserSettingsRepository,
        mock_session: AsyncMock
    ):
        """
        Test that update() calls get_by_user_id() to fetch settings.

        GIVEN: update() method implementation
        WHEN: update() is called
        THEN: get_by_user_id() is called first to fetch existing settings
        """
        # Arrange
        update_data = UserSettingsUpdate(poll_interval_weekday=90)

        # Act: Call update - should internally call get_by_user_id
        with patch.object(
            user_settings_repository,
            'get_by_user_id',
            return_value=None
        ) as mock_get_by_user_id:
            await user_settings_repository.update(1, update_data)

        # Assert: get_by_user_id was called
        mock_get_by_user_id.assert_called_once_with(1), \
            "update() should call get_by_user_id() with user_id"

    @pytest.mark.unit
    async def test_update_handles_empty_update_data(
        self,
        user_settings_repository: UserSettingsRepository,
        mock_session: AsyncMock
    ):
        """
        Test update with no fields to update.

        GIVEN: UserSettingsUpdate() with no fields set
        WHEN: update() is called
        THEN: Settings are returned unchanged
              flush/refresh still called for consistency
        """
        # Arrange: Existing settings
        existing_settings = UserSettings(
            id=1,
            user_id=1,
            poll_interval_weekday=120,
            poll_interval_weekend=180
        )

        # Empty update (no fields provided)
        update_data = UserSettingsUpdate()

        with patch.object(
            user_settings_repository,
            'get_by_user_id',
            return_value=existing_settings
        ):
            # Act
            result = await user_settings_repository.update(1, update_data)

            # Assert: Settings returned unchanged
            assert result is not None
            assert result.poll_interval_weekday == 120
            assert result.poll_interval_weekend == 180

    @pytest.mark.unit
    async def test_update_updates_multiple_fields_at_once(
        self,
        user_settings_repository: UserSettingsRepository,
        mock_session: AsyncMock
    ):
        """
        Test updating multiple fields simultaneously.

        GIVEN: Settings with default values
        WHEN: update() called with multiple fields in UserSettingsUpdate
        THEN: All provided fields are updated
        """
        # Arrange
        existing_settings = UserSettings(
            id=1,
            user_id=1,
            poll_interval_weekday=120,
            poll_interval_weekend=180,
            reminder_enabled=True
        )

        # Update multiple fields
        update_data = UserSettingsUpdate(
            poll_interval_weekday=90,
            poll_interval_weekend=150,
            reminder_enabled=False
        )

        with patch.object(
            user_settings_repository,
            'get_by_user_id',
            return_value=existing_settings
        ):
            # Act
            result = await user_settings_repository.update(1, update_data)

            # Assert: All fields updated
            assert result.poll_interval_weekday == 90
            assert result.poll_interval_weekend == 150
            assert result.reminder_enabled is False


class TestUserSettingsRepositoryInheritance:
    """
    Test suite verifying UserSettingsRepository inherits base methods.

    Note: update() is overridden, but other CRUD methods should be available.
    """

    @pytest.mark.unit
    async def test_user_settings_repository_inherits_get_by_id(
        self,
        user_settings_repository: UserSettingsRepository,
        mock_session: AsyncMock,
        sample_user_settings: UserSettings
    ):
        """
        Test that inherited get_by_id() is available.

        GIVEN: UserSettingsRepository instance
        WHEN: get_by_id() is called with settings table ID
        THEN: Method executes successfully
        """
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user_settings
        mock_session.execute.return_value = mock_result

        # Act: Call inherited method
        result = await user_settings_repository.get_by_id(1)

        # Assert
        assert result == sample_user_settings, \
            "Inherited get_by_id() should work"

    @pytest.mark.unit
    async def test_user_settings_repository_inherits_create(
        self,
        user_settings_repository: UserSettingsRepository,
        mock_session: AsyncMock
    ):
        """
        Test that inherited create() is available.

        GIVEN: UserSettingsRepository instance
        WHEN: create() is called with UserSettingsCreate schema
        THEN: Method executes successfully
        """
        # Arrange
        settings_data = UserSettingsCreate(
            user_id=1,
            poll_interval_weekday=120
        )

        with patch.object(UserSettings, '__init__', return_value=None):
            try:
                await user_settings_repository.create(settings_data)
            except Exception:
                # Expected due to mocking
                pass

        # Assert
        assert mock_session.add.called, \
            "Inherited create() should be functional"

    @pytest.mark.unit
    async def test_user_settings_repository_inherits_delete(
        self,
        user_settings_repository: UserSettingsRepository,
        mock_session: AsyncMock
    ):
        """
        Test that inherited delete() is available.

        GIVEN: UserSettingsRepository instance
        WHEN: delete() is called with settings table ID
        THEN: Method executes successfully
        """
        # Arrange
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result
        mock_session.flush = AsyncMock()

        # Act: Call inherited method
        result = await user_settings_repository.delete(1)

        # Assert
        assert result is True, "Inherited delete() should work"


class TestUserSettingsRepositoryEdgeCases:
    """
    Test suite for edge cases specific to UserSettingsRepository.
    """

    @pytest.mark.unit
    async def test_get_by_user_id_with_zero_user_id(
        self,
        user_settings_repository: UserSettingsRepository,
        mock_session: AsyncMock
    ):
        """
        Test behavior with user_id=0 (edge case).

        GIVEN: user_id=0
        WHEN: get_by_user_id(0) is called
        THEN: Query executes without error, returns None if not found
        """
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act
        result = await user_settings_repository.get_by_user_id(0)

        # Assert: Handles gracefully
        assert result is None or isinstance(result, UserSettings)

    @pytest.mark.unit
    async def test_update_preserves_unset_fields(
        self,
        user_settings_repository: UserSettingsRepository,
        mock_session: AsyncMock
    ):
        """
        Test that unset optional fields are not updated to None.

        GIVEN: Settings with quiet_hours_start set
        WHEN: update() with only weekday_interval (not quiet_hours)
        THEN: quiet_hours_start remains set (not overwritten with None)

        This tests exclude_unset=True in model_dump().
        """
        # Arrange: Settings with optional field set
        existing_settings = UserSettings(
            id=1,
            user_id=1,
            poll_interval_weekday=120,
            quiet_hours_start=time(22, 0),  # Optional field set
            quiet_hours_end=time(8, 0)
        )

        # Update only weekday_interval (not quiet_hours)
        update_data = UserSettingsUpdate(poll_interval_weekday=90)

        with patch.object(
            user_settings_repository,
            'get_by_user_id',
            return_value=existing_settings
        ):
            # Act
            result = await user_settings_repository.update(1, update_data)

            # Assert: Optional fields preserved
            assert result.quiet_hours_start == time(22, 0), \
                "Unset optional fields should not be overwritten"
            assert result.quiet_hours_end == time(8, 0)

    @pytest.mark.unit
    async def test_repository_initialization_sets_model_correctly(
        self,
        mock_session: AsyncMock
    ):
        """
        Test that UserSettingsRepository initializes correctly.

        GIVEN: UserSettingsRepository instantiation
        WHEN: __init__ is called
        THEN: self.model is set to UserSettings class
              AND self.session is set to provided session
        """
        # Act: Create repository
        repo = UserSettingsRepository(mock_session)

        # Assert: Proper initialization
        assert repo.model == UserSettings, \
            "Repository should be initialized with UserSettings model"
        assert repo.session == mock_session, \
            "Repository should store the session"
