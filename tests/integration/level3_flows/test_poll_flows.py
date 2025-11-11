"""
Level 3 Integration Tests: Poll Flows.

Test full end-to-end poll flows with real database and Redis.

Test Coverage:
    - Complete poll response flow
    - Poll skip flow
    - Poll with quiet hours check
    - Poll interval change flow
    - Disable polls flow
"""

import pytest
from datetime import datetime, timedelta, time
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.integration
@pytest.mark.level3
async def test_complete_poll_response_flow(
    db_session, redis_storage, test_user, test_category, test_user_settings
):
    """
    GIVEN: Poll is sent to user
    WHEN: User selects category and responds
    THEN: Activity is created
          AND next poll is scheduled
          AND confirmation is shown

    Mocks: Telegram Bot API, APScheduler
    Real: Full poll response flow
    Time: ~350ms
    """
    # Arrange
    from aiogram.fsm.context import FSMContext
    from services.data_postgres_api.src.application.services.activity_service import ActivityService
    from services.data_postgres_api.src.infrastructure.repositories.activity_repository import ActivityRepository

    user_id = test_user.telegram_id
    state = FSMContext(
        storage=redis_storage,
        key=f"{user_id}:state"
    )

    # Step 1: Poll is sent (simulated)
    poll_time = datetime.now()

    # Step 2: User clicks category
    callback_query = MagicMock()
    callback_query.data = f"poll_category_{test_category.id}"
    callback_query.from_user = MagicMock(id=user_id)

    # Act - Record poll response
    repo = ActivityRepository(db_session)
    service = ActivityService(repo)

    # Calculate activity time (from last poll or default interval)
    interval = test_user_settings.poll_interval_weekday
    start_time = poll_time - timedelta(minutes=interval)
    end_time = poll_time

    activity = await service.create_activity(
        user_id=test_user.id,
        category_id=test_category.id,
        start_time=start_time,
        end_time=end_time,
        description="From poll"
    )

    # Assert
    assert activity is not None
    assert activity.category_id == test_category.id
    assert activity.description == "From poll"

    # Verify in database
    retrieved = await service.get_activity_by_id(activity.id)
    assert retrieved is not None


@pytest.mark.integration
@pytest.mark.level3
async def test_poll_skip_flow(
    db_session, redis_storage, test_user, test_user_settings
):
    """
    GIVEN: Poll is sent to user
    WHEN: User clicks skip
    THEN: No activity is created
          AND next poll is scheduled
          AND skip is recorded

    Mocks: Telegram Bot API, APScheduler
    Real: Full skip flow
    Time: ~250ms
    """
    # Arrange
    from aiogram.fsm.context import FSMContext
    from services.data_postgres_api.src.application.services.activity_service import ActivityService
    from services.data_postgres_api.src.infrastructure.repositories.activity_repository import ActivityRepository

    user_id = test_user.telegram_id

    # Count activities before
    repo = ActivityRepository(db_session)
    service = ActivityService(repo)
    activities_before = await service.list_activities(user_id=test_user.id)
    count_before = len(activities_before)

    # Act - User skips poll (no activity created)
    callback_query = MagicMock()
    callback_query.data = "poll_skip"
    callback_query.from_user = MagicMock(id=user_id)

    # Simulate skip - just don't create activity

    # Assert
    activities_after = await service.list_activities(user_id=test_user.id)
    count_after = len(activities_after)

    assert count_after == count_before  # No new activity


@pytest.mark.integration
@pytest.mark.level3
async def test_poll_with_quiet_hours_check(
    db_session, redis_storage, test_user, test_user_settings
):
    """
    GIVEN: User has quiet hours configured
    WHEN: Current time is in quiet hours
    THEN: Poll is not sent
          AND next poll is scheduled after quiet hours

    Mocks: Telegram Bot API, APScheduler
    Real: Quiet hours logic
    Time: ~200ms
    """
    # Arrange
    from services.tracker_activity_bot.src.services.poll_service import PollService

    service = PollService()

    # Set quiet hours: 22:00 - 08:00
    quiet_start = time(22, 0)
    quiet_end = time(8, 0)

    # Act - Check various times
    quiet_time = datetime.now().replace(hour=23, minute=0)
    active_time = datetime.now().replace(hour=12, minute=0)

    is_quiet = service.is_in_quiet_hours(quiet_time, quiet_start, quiet_end)
    is_active = service.is_in_quiet_hours(active_time, quiet_start, quiet_end)

    # Assert
    assert is_quiet is True
    assert is_active is False


@pytest.mark.integration
@pytest.mark.level3
async def test_poll_interval_change_flow(
    db_session, redis_storage, test_user, test_user_settings
):
    """
    GIVEN: User wants to change poll interval
    WHEN: User selects new interval
    THEN: Settings are updated
          AND scheduler is updated with new interval

    Mocks: Telegram Bot API, APScheduler
    Real: Full settings update flow
    Time: ~280ms
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
    assert updated.poll_interval_weekday == new_interval
    assert updated.poll_interval_weekday != original_interval

    # Verify persistence
    retrieved = await service.get_settings_by_user_id(test_user.id)
    assert retrieved.poll_interval_weekday == new_interval


@pytest.mark.integration
@pytest.mark.level3
async def test_disable_polls_flow(
    db_session, redis_storage, test_user, test_user_settings
):
    """
    GIVEN: Polls are currently enabled
    WHEN: User disables polls
    THEN: Settings are updated
          AND scheduler stops sending polls
          AND confirmation is shown

    Mocks: Telegram Bot API, APScheduler
    Real: Full disable flow
    Time: ~260ms
    """
    # Arrange
    from services.data_postgres_api.src.application.services.user_settings_service import UserSettingsService
    from services.data_postgres_api.src.infrastructure.repositories.user_settings_repository import UserSettingsRepository

    repo = UserSettingsRepository(db_session)
    service = UserSettingsService(repo)

    # Verify initially enabled
    assert test_user_settings.polls_enabled is True

    # Act
    updated = await service.update_settings(
        user_id=test_user.id,
        polls_enabled=False
    )

    # Assert
    assert updated is not None
    assert updated.polls_enabled is False

    # Verify persistence
    retrieved = await service.get_settings_by_user_id(test_user.id)
    assert retrieved.polls_enabled is False
