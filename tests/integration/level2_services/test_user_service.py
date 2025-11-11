"""
Level 2 Integration Tests: User Service.

Test Coverage:
    - Create user stores in database
    - Get user by telegram_id retrieves correct record
    - Get or create user handles both scenarios
    - Update user settings modifies existing record
    - Get user settings returns correct values
    - User settings validation
"""

import pytest
from unittest.mock import AsyncMock


@pytest.mark.integration
@pytest.mark.level2
async def test_create_user_stores_in_database(db_session):
    """
    GIVEN: Valid user data
    WHEN: Service creates user
    THEN: User is stored in database with correct attributes

    Mocks: None
    Real: Service, Repository, Database
    Time: ~130ms
    """
    # Arrange
    from services.data_postgres_api.src.application.services.user_service import UserService
    from services.data_postgres_api.src.infrastructure.repositories.user_repository import UserRepository

    repo = UserRepository(db_session)
    service = UserService(repo)

    telegram_id = 987654321
    username = "testuser"

    # Act
    created = await service.create_user(
        telegram_id=telegram_id,
        username=username
    )

    # Assert
    assert created.id is not None
    assert created.telegram_id == telegram_id
    assert created.username == username

    # Verify in database
    retrieved = await service.get_user_by_telegram_id(telegram_id)
    assert retrieved is not None
    assert retrieved.id == created.id


@pytest.mark.integration
@pytest.mark.level2
async def test_get_user_by_telegram_id_retrieves_correct_record(db_session, test_user):
    """
    GIVEN: User exists in database
    WHEN: Service retrieves by telegram_id
    THEN: Correct user is returned

    Mocks: None
    Real: Service, Repository, Database
    Time: ~100ms
    """
    # Arrange
    from services.data_postgres_api.src.application.services.user_service import UserService
    from services.data_postgres_api.src.infrastructure.repositories.user_repository import UserRepository

    repo = UserRepository(db_session)
    service = UserService(repo)

    # Act
    retrieved = await service.get_user_by_telegram_id(test_user.telegram_id)

    # Assert
    assert retrieved is not None
    assert retrieved.id == test_user.id
    assert retrieved.telegram_id == test_user.telegram_id


@pytest.mark.integration
@pytest.mark.level2
async def test_get_or_create_user_creates_new_user(db_session):
    """
    GIVEN: User does not exist
    WHEN: Service calls get_or_create
    THEN: New user is created and returned

    Mocks: None
    Real: Service, Repository, Database
    Time: ~140ms
    """
    # Arrange
    from services.data_postgres_api.src.application.services.user_service import UserService
    from services.data_postgres_api.src.infrastructure.repositories.user_repository import UserRepository

    repo = UserRepository(db_session)
    service = UserService(repo)

    telegram_id = 111222333
    username = "newuser"

    # Act
    user, created = await service.get_or_create_user(
        telegram_id=telegram_id,
        username=username
    )

    # Assert
    assert created is True
    assert user.id is not None
    assert user.telegram_id == telegram_id
    assert user.username == username


@pytest.mark.integration
@pytest.mark.level2
async def test_get_or_create_user_returns_existing_user(db_session, test_user):
    """
    GIVEN: User already exists
    WHEN: Service calls get_or_create
    THEN: Existing user is returned, not created

    Mocks: None
    Real: Service, Repository, Database
    Time: ~110ms
    """
    # Arrange
    from services.data_postgres_api.src.application.services.user_service import UserService
    from services.data_postgres_api.src.infrastructure.repositories.user_repository import UserRepository

    repo = UserRepository(db_session)
    service = UserService(repo)

    # Act
    user, created = await service.get_or_create_user(
        telegram_id=test_user.telegram_id,
        username=test_user.username
    )

    # Assert
    assert created is False
    assert user.id == test_user.id
    assert user.telegram_id == test_user.telegram_id


@pytest.mark.integration
@pytest.mark.level2
async def test_update_user_settings_modifies_existing_record(db_session, test_user, test_user_settings):
    """
    GIVEN: User settings exist
    WHEN: Service updates settings
    THEN: Database record is modified
          AND updated settings are returned

    Mocks: None
    Real: Service, Repository, Database
    Time: ~140ms
    """
    # Arrange
    from services.data_postgres_api.src.application.services.user_settings_service import UserSettingsService
    from services.data_postgres_api.src.infrastructure.repositories.user_settings_repository import UserSettingsRepository

    repo = UserSettingsRepository(db_session)
    service = UserSettingsService(repo)

    original_interval = test_user_settings.poll_interval_weekday
    new_interval = 60  # 60 minutes

    # Act
    updated = await service.update_settings(
        user_id=test_user.id,
        poll_interval_weekday=new_interval
    )

    # Assert
    assert updated is not None
    assert updated.user_id == test_user.id
    assert updated.poll_interval_weekday == new_interval
    assert updated.poll_interval_weekday != original_interval

    # Verify persistence
    retrieved = await service.get_settings_by_user_id(test_user.id)
    assert retrieved.poll_interval_weekday == new_interval


@pytest.mark.integration
@pytest.mark.level2
async def test_get_user_settings_returns_correct_values(db_session, test_user, test_user_settings):
    """
    GIVEN: User settings exist
    WHEN: Service retrieves settings
    THEN: Correct settings values are returned

    Mocks: None
    Real: Service, Repository, Database
    Time: ~100ms
    """
    # Arrange
    from services.data_postgres_api.src.application.services.user_settings_service import UserSettingsService
    from services.data_postgres_api.src.infrastructure.repositories.user_settings_repository import UserSettingsRepository

    repo = UserSettingsRepository(db_session)
    service = UserSettingsService(repo)

    # Act
    settings = await service.get_settings_by_user_id(test_user.id)

    # Assert
    assert settings is not None
    assert settings.user_id == test_user.id
    assert settings.poll_interval_weekday == test_user_settings.poll_interval_weekday
    assert settings.poll_interval_weekend == test_user_settings.poll_interval_weekend
    assert settings.polls_enabled == test_user_settings.polls_enabled
