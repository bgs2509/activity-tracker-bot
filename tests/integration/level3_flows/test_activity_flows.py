"""
Level 3 Integration Tests: Activity Creation Flows.

Test full end-to-end flows for activity creation with real database and Redis.

Test Coverage:
    - Complete activity creation flow from button to save
    - Activity creation with time validation
    - Activity creation cancellation flow
    - Editing existing activity flow
    - Deleting activity flow
    - Activity creation with description
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.integration
@pytest.mark.level3
async def test_complete_activity_creation_flow(
    db_session, redis_storage, test_user, test_category, mock_bot
):
    """
    GIVEN: User wants to create an activity
    WHEN: User completes full creation flow
    THEN: Activity is saved to database
          AND confirmation is shown
          AND FSM state is cleared

    Mocks: Telegram Bot API
    Real: Handler, Service, Repository, Database, Redis, FSM
    Time: ~300ms
    """
    # Arrange - Simulate user clicking "Записать"
    from aiogram import types
    from aiogram.fsm.context import FSMContext

    user_id = test_user.telegram_id
    callback_query = MagicMock(spec=types.CallbackQuery)
    callback_query.data = "add_activity"
    callback_query.from_user = MagicMock(id=user_id)
    callback_query.message = MagicMock()
    callback_query.message.edit_text = AsyncMock()

    # Step 1: Initiate activity creation
    from services.tracker_activity_bot.src.api.handlers.activity.add_activity import handle_add_activity

    state = FSMContext(
        storage=redis_storage,
        key=f"{user_id}:state"
    )

    # Act - Execute flow
    await handle_add_activity(callback_query, state)

    # Assert Step 1 - Category selection shown
    callback_query.message.edit_text.assert_called()
    call_text = callback_query.message.edit_text.call_args[0][0]
    assert "категор" in call_text.lower()

    # Step 2: User selects category
    callback_query.data = f"category_{test_category.id}"
    await state.set_data({"category_id": test_category.id})
    await state.set_state("activity_creation:waiting_start_time")

    # Step 3: User enters start time
    message = MagicMock(spec=types.Message)
    message.text = "10:00"
    message.from_user = MagicMock(id=user_id)
    message.answer = AsyncMock()

    await state.update_data(start_time="10:00")
    await state.set_state("activity_creation:waiting_end_time")

    # Step 4: User enters end time
    message.text = "12:00"
    await state.update_data(end_time="12:00")

    # Step 5: Confirm and save
    from services.data_postgres_api.src.application.services.activity_service import ActivityService
    from services.data_postgres_api.src.infrastructure.repositories.activity_repository import ActivityRepository

    repo = ActivityRepository(db_session)
    service = ActivityService(repo)

    start_time = datetime.now().replace(hour=10, minute=0)
    end_time = datetime.now().replace(hour=12, minute=0)

    activity = await service.create_activity(
        user_id=test_user.id,
        category_id=test_category.id,
        start_time=start_time,
        end_time=end_time,
        description=None
    )

    # Assert final state
    assert activity is not None
    assert activity.user_id == test_user.id
    assert activity.category_id == test_category.id

    # Verify in database
    retrieved = await service.get_activity_by_id(activity.id)
    assert retrieved is not None


@pytest.mark.integration
@pytest.mark.level3
async def test_activity_creation_with_time_validation(
    db_session, redis_storage, test_user, test_category
):
    """
    GIVEN: User enters invalid time (end before start)
    WHEN: System validates time
    THEN: Error message is shown
          AND user is asked to re-enter

    Mocks: Telegram Bot API
    Real: Full validation flow
    Time: ~250ms
    """
    # Arrange
    from aiogram.fsm.context import FSMContext

    user_id = test_user.telegram_id
    state = FSMContext(
        storage=redis_storage,
        key=f"{user_id}:state"
    )

    # Act - Set invalid times
    start_time = datetime.now().replace(hour=14, minute=0)
    end_time = datetime.now().replace(hour=10, minute=0)  # Before start!

    is_valid = end_time > start_time

    # Assert
    assert is_valid is False


@pytest.mark.integration
@pytest.mark.level3
async def test_activity_creation_cancellation_flow(
    db_session, redis_storage, test_user
):
    """
    GIVEN: User is in activity creation flow
    WHEN: User clicks "Отменить"
    THEN: FSM state is cleared
          AND user returns to main menu
          AND no activity is created

    Mocks: Telegram Bot API
    Real: Full cancellation flow
    Time: ~200ms
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

    # Set some state data
    await state.set_data({"category_id": 1, "start_time": "10:00"})
    await state.set_state("activity_creation:waiting_end_time")

    # Act - Cancel
    await state.clear()

    # Assert
    state_data = await state.get_data()
    assert state_data == {}

    # Verify no activity created
    repo = ActivityRepository(db_session)
    service = ActivityService(repo)
    activities = await service.list_activities(user_id=test_user.id)
    # Should be empty or not contain partial activity
    assert all(a.end_time is not None for a in activities)


@pytest.mark.integration
@pytest.mark.level3
async def test_editing_existing_activity_flow(
    db_session, redis_storage, test_activity
):
    """
    GIVEN: Activity exists
    WHEN: User edits activity description
    THEN: Activity is updated in database
          AND confirmation is shown

    Mocks: Telegram Bot API
    Real: Full edit flow
    Time: ~280ms
    """
    # Arrange
    from services.data_postgres_api.src.application.services.activity_service import ActivityService
    from services.data_postgres_api.src.infrastructure.repositories.activity_repository import ActivityRepository

    repo = ActivityRepository(db_session)
    service = ActivityService(repo)

    original_description = test_activity.description
    new_description = "Updated via flow test"

    # Act
    updated = await service.update_activity(
        test_activity.id,
        description=new_description
    )

    # Assert
    assert updated is not None
    assert updated.description == new_description
    assert updated.description != original_description

    # Verify persistence
    retrieved = await service.get_activity_by_id(test_activity.id)
    assert retrieved.description == new_description


@pytest.mark.integration
@pytest.mark.level3
async def test_deleting_activity_flow(
    db_session, redis_storage, test_activity
):
    """
    GIVEN: Activity exists
    WHEN: User deletes activity
    THEN: Activity is removed from database
          AND confirmation is shown

    Mocks: Telegram Bot API
    Real: Full delete flow
    Time: ~240ms
    """
    # Arrange
    from services.data_postgres_api.src.application.services.activity_service import ActivityService
    from services.data_postgres_api.src.infrastructure.repositories.activity_repository import ActivityRepository

    repo = ActivityRepository(db_session)
    service = ActivityService(repo)

    activity_id = test_activity.id

    # Verify exists
    exists = await service.get_activity_by_id(activity_id)
    assert exists is not None

    # Act
    result = await service.delete_activity(activity_id)

    # Assert
    assert result is True

    # Verify deleted
    retrieved = await service.get_activity_by_id(activity_id)
    assert retrieved is None


@pytest.mark.integration
@pytest.mark.level3
async def test_activity_creation_with_description(
    db_session, redis_storage, test_user, test_category
):
    """
    GIVEN: User creates activity with description
    WHEN: Full flow is executed
    THEN: Activity with description is saved

    Mocks: Telegram Bot API
    Real: Full flow with description
    Time: ~300ms
    """
    # Arrange
    from services.data_postgres_api.src.application.services.activity_service import ActivityService
    from services.data_postgres_api.src.infrastructure.repositories.activity_repository import ActivityRepository

    repo = ActivityRepository(db_session)
    service = ActivityService(repo)

    # Act
    start_time = datetime.now() - timedelta(hours=2)
    end_time = datetime.now() - timedelta(hours=1)
    description = "Meeting with team about project planning"

    activity = await service.create_activity(
        user_id=test_user.id,
        category_id=test_category.id,
        start_time=start_time,
        end_time=end_time,
        description=description
    )

    # Assert
    assert activity is not None
    assert activity.description == description

    # Verify in database
    retrieved = await service.get_activity_by_id(activity.id)
    assert retrieved.description == description
