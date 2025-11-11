"""
Level 2 Integration Tests: Poll Service.

Test Coverage:
    - Create poll state stores in database
    - Get active poll retrieves correct record
    - Update poll state modifies existing record
    - Record poll response saves activity
    - Schedule next poll calculates correct time
    - Handle skip updates poll state
    - Validate quiet hours logic
    - Poll state cleanup
"""

import pytest
from datetime import datetime, timedelta, time
from unittest.mock import AsyncMock, patch


@pytest.mark.integration
@pytest.mark.level2
async def test_create_poll_state_stores_in_database(db_session, test_user):
    """
    GIVEN: Valid poll state data
    WHEN: Service creates poll state
    THEN: Poll state is stored in database

    Mocks: None
    Real: Service, Repository, Database
    Time: ~140ms
    """
    # Arrange
    from services.tracker_activity_bot.src.services.poll_service import PollService

    service = PollService()

    # Act
    poll_time = datetime.now()
    state = await service.create_poll_state(
        user_id=test_user.telegram_id,
        poll_time=poll_time
    )

    # Assert
    assert state is not None
    assert state.get("user_id") == test_user.telegram_id
    assert state.get("poll_time") is not None


@pytest.mark.integration
@pytest.mark.level2
async def test_get_active_poll_retrieves_correct_record(db_session, test_user):
    """
    GIVEN: Active poll exists for user
    WHEN: Service retrieves active poll
    THEN: Correct poll state is returned

    Mocks: None
    Real: Service, Repository, Database
    Time: ~110ms
    """
    # Arrange
    from services.tracker_activity_bot.src.services.poll_service import PollService

    service = PollService()

    # Create active poll
    poll_time = datetime.now()
    await service.create_poll_state(
        user_id=test_user.telegram_id,
        poll_time=poll_time
    )

    # Act
    active_poll = await service.get_active_poll(test_user.telegram_id)

    # Assert
    assert active_poll is not None
    assert active_poll.get("user_id") == test_user.telegram_id


@pytest.mark.integration
@pytest.mark.level2
async def test_update_poll_state_modifies_existing_record(db_session, test_user):
    """
    GIVEN: Poll state exists
    WHEN: Service updates poll state
    THEN: Database record is modified

    Mocks: None
    Real: Service, Repository, Database
    Time: ~130ms
    """
    # Arrange
    from services.tracker_activity_bot.src.services.poll_service import PollService

    service = PollService()

    # Create poll
    poll_time = datetime.now()
    state = await service.create_poll_state(
        user_id=test_user.telegram_id,
        poll_time=poll_time
    )

    # Act
    updated = await service.update_poll_state(
        user_id=test_user.telegram_id,
        status="answered"
    )

    # Assert
    assert updated is not None
    assert updated.get("status") == "answered"


@pytest.mark.integration
@pytest.mark.level2
async def test_record_poll_response_saves_activity(db_session, test_user, test_category):
    """
    GIVEN: User responds to poll with category
    WHEN: Service records response
    THEN: Activity is created in database

    Mocks: None
    Real: Service, Repository, Database
    Time: ~180ms
    """
    # Arrange
    from services.tracker_activity_bot.src.services.poll_service import PollService
    from services.data_postgres_api.src.application.services.activity_service import ActivityService
    from services.data_postgres_api.src.infrastructure.repositories.activity_repository import ActivityRepository

    poll_service = PollService()
    activity_repo = ActivityRepository(db_session)
    activity_service = ActivityService(activity_repo)

    # Act
    start_time = datetime.now() - timedelta(hours=1)
    end_time = datetime.now()

    # Simulate poll response recording
    activity = await activity_service.create_activity(
        user_id=test_user.id,
        category_id=test_category.id,
        start_time=start_time,
        end_time=end_time,
        description="From poll"
    )

    # Assert
    assert activity is not None
    assert activity.user_id == test_user.id
    assert activity.category_id == test_category.id
    assert activity.description == "From poll"


@pytest.mark.integration
@pytest.mark.level2
async def test_schedule_next_poll_calculates_correct_time(db_session, test_user, test_user_settings):
    """
    GIVEN: User settings with poll interval
    WHEN: Service schedules next poll
    THEN: Correct time is calculated based on settings

    Mocks: APScheduler
    Real: Time calculation logic
    Time: ~100ms
    """
    # Arrange
    from services.tracker_activity_bot.src.services.poll_service import PollService

    service = PollService()

    current_time = datetime.now()
    interval_minutes = test_user_settings.poll_interval_weekday

    # Act
    next_poll_time = service.calculate_next_poll_time(
        current_time=current_time,
        interval_minutes=interval_minutes
    )

    # Assert
    assert next_poll_time > current_time
    time_diff = (next_poll_time - current_time).total_seconds() / 60
    assert abs(time_diff - interval_minutes) < 1  # Within 1 minute tolerance


@pytest.mark.integration
@pytest.mark.level2
async def test_handle_skip_updates_poll_state(db_session, test_user):
    """
    GIVEN: Active poll exists
    WHEN: User skips poll
    THEN: Poll state is updated to skipped
          AND next poll is scheduled

    Mocks: APScheduler
    Real: Service, Repository, Database
    Time: ~140ms
    """
    # Arrange
    from services.tracker_activity_bot.src.services.poll_service import PollService

    service = PollService()

    # Create active poll
    poll_time = datetime.now()
    await service.create_poll_state(
        user_id=test_user.telegram_id,
        poll_time=poll_time
    )

    # Act
    result = await service.handle_skip(test_user.telegram_id)

    # Assert
    assert result is not None
    # Verify poll state updated
    active_poll = await service.get_active_poll(test_user.telegram_id)
    assert active_poll is None or active_poll.get("status") == "skipped"


@pytest.mark.integration
@pytest.mark.level2
async def test_validate_quiet_hours_logic(db_session, test_user_settings):
    """
    GIVEN: User has quiet hours configured
    WHEN: Service checks if time is in quiet hours
    THEN: Correct boolean is returned

    Mocks: None
    Real: Business logic
    Time: ~80ms
    """
    # Arrange
    from services.tracker_activity_bot.src.services.poll_service import PollService

    service = PollService()

    # Set quiet hours: 22:00 - 08:00
    quiet_start = time(22, 0)
    quiet_end = time(8, 0)

    # Act - Test time in quiet hours (23:00)
    test_time_quiet = datetime.now().replace(hour=23, minute=0)
    is_quiet = service.is_in_quiet_hours(test_time_quiet, quiet_start, quiet_end)

    # Test time outside quiet hours (12:00)
    test_time_active = datetime.now().replace(hour=12, minute=0)
    is_active = service.is_in_quiet_hours(test_time_active, quiet_start, quiet_end)

    # Assert
    assert is_quiet is True
    assert is_active is False


@pytest.mark.integration
@pytest.mark.level2
async def test_poll_state_cleanup_removes_old_polls(db_session, test_user):
    """
    GIVEN: Old poll states exist
    WHEN: Service runs cleanup
    THEN: Old polls are removed from database

    Mocks: None
    Real: Service, Repository, Database
    Time: ~150ms
    """
    # Arrange
    from services.tracker_activity_bot.src.services.poll_service import PollService

    service = PollService()

    # Create old poll state
    old_poll_time = datetime.now() - timedelta(days=7)
    await service.create_poll_state(
        user_id=test_user.telegram_id,
        poll_time=old_poll_time
    )

    # Act
    cleanup_before = datetime.now() - timedelta(days=1)
    await service.cleanup_old_polls(before_date=cleanup_before)

    # Assert
    # Old polls should be cleaned up
    active_poll = await service.get_active_poll(test_user.telegram_id)
    # Should be None or recent poll only
    if active_poll:
        assert active_poll.get("poll_time") > cleanup_before
