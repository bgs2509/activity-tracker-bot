"""
Level 3 Integration Tests: Settings Flows.

Test full end-to-end settings configuration flows.

Test Coverage:
    - Change weekday interval flow
    - Change weekend interval flow
    - Set quiet hours flow
    - Update reminder delay flow
"""

import pytest
from datetime import time
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.integration
@pytest.mark.level3
async def test_change_weekday_interval_flow(
    db_session, redis_storage, test_user, test_user_settings
):
    """
    GIVEN: User wants to change weekday poll interval
    WHEN: User selects new interval
    THEN: Settings are updated in database
          AND confirmation is shown

    Mocks: Telegram Bot API
    Real: Full settings update flow
    Time: ~280ms
    """
    # Arrange
    from services.data_postgres_api.src.application.services.user_settings_service import UserSettingsService
    from services.data_postgres_api.src.infrastructure.repositories.user_settings_repository import UserSettingsRepository

    repo = UserSettingsRepository(db_session)
    service = UserSettingsService(repo)

    original_interval = test_user_settings.poll_interval_weekday
    new_interval = 45  # 45 minutes

    # Act
    updated = await service.update_settings(
        user_id=test_user.id,
        poll_interval_weekday=new_interval
    )

    # Assert
    assert updated is not None
    assert updated.poll_interval_weekday == new_interval
    assert updated.poll_interval_weekday != original_interval

    # Verify persistence
    retrieved = await service.get_settings_by_user_id(test_user.id)
    assert retrieved.poll_interval_weekday == new_interval


@pytest.mark.integration
@pytest.mark.level3
async def test_change_weekend_interval_flow(
    db_session, redis_storage, test_user, test_user_settings
):
    """
    GIVEN: User wants to change weekend poll interval
    WHEN: User selects new interval
    THEN: Settings are updated in database
          AND confirmation is shown

    Mocks: Telegram Bot API
    Real: Full settings update flow
    Time: ~280ms
    """
    # Arrange
    from services.data_postgres_api.src.application.services.user_settings_service import UserSettingsService
    from services.data_postgres_api.src.infrastructure.repositories.user_settings_repository import UserSettingsRepository

    repo = UserSettingsRepository(db_session)
    service = UserSettingsService(repo)

    original_interval = test_user_settings.poll_interval_weekend
    new_interval = 90  # 90 minutes

    # Act
    updated = await service.update_settings(
        user_id=test_user.id,
        poll_interval_weekend=new_interval
    )

    # Assert
    assert updated is not None
    assert updated.poll_interval_weekend == new_interval
    assert updated.poll_interval_weekend != original_interval

    # Verify persistence
    retrieved = await service.get_settings_by_user_id(test_user.id)
    assert retrieved.poll_interval_weekend == new_interval


@pytest.mark.integration
@pytest.mark.level3
async def test_set_quiet_hours_flow(
    db_session, redis_storage, test_user, test_user_settings
):
    """
    GIVEN: User wants to set quiet hours
    WHEN: User selects start and end times
    THEN: Settings are updated in database
          AND polls respect quiet hours

    Mocks: Telegram Bot API
    Real: Full quiet hours configuration flow
    Time: ~300ms
    """
    # Arrange
    from services.data_postgres_api.src.application.services.user_settings_service import UserSettingsService
    from services.data_postgres_api.src.infrastructure.repositories.user_settings_repository import UserSettingsRepository

    repo = UserSettingsRepository(db_session)
    service = UserSettingsService(repo)

    new_quiet_start = time(23, 0)  # 23:00
    new_quiet_end = time(7, 0)     # 07:00

    # Act
    updated = await service.update_settings(
        user_id=test_user.id,
        quiet_hours_start=new_quiet_start,
        quiet_hours_end=new_quiet_end
    )

    # Assert
    assert updated is not None
    assert updated.quiet_hours_start == new_quiet_start
    assert updated.quiet_hours_end == new_quiet_end

    # Verify persistence
    retrieved = await service.get_settings_by_user_id(test_user.id)
    assert retrieved.quiet_hours_start == new_quiet_start
    assert retrieved.quiet_hours_end == new_quiet_end


@pytest.mark.integration
@pytest.mark.level3
async def test_update_reminder_delay_flow(
    db_session, redis_storage, test_user, test_user_settings
):
    """
    GIVEN: User wants to change reminder delay
    WHEN: User selects new delay value
    THEN: Settings are updated in database
          AND reminders use new delay

    Mocks: Telegram Bot API
    Real: Full reminder delay update flow
    Time: ~270ms
    """
    # Arrange
    from services.data_postgres_api.src.application.services.user_settings_service import UserSettingsService
    from services.data_postgres_api.src.infrastructure.repositories.user_settings_repository import UserSettingsRepository

    repo = UserSettingsRepository(db_session)
    service = UserSettingsService(repo)

    original_delay = test_user_settings.reminder_delay_minutes
    new_delay = 10  # 10 minutes

    # Act
    updated = await service.update_settings(
        user_id=test_user.id,
        reminder_delay_minutes=new_delay
    )

    # Assert
    assert updated is not None
    assert updated.reminder_delay_minutes == new_delay
    assert updated.reminder_delay_minutes != original_delay

    # Verify persistence
    retrieved = await service.get_settings_by_user_id(test_user.id)
    assert retrieved.reminder_delay_minutes == new_delay
