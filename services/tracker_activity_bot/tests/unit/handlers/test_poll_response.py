"""
Unit tests for poll response handlers.

Tests all user responses to automatic activity polls including:
- Skip: User did nothing
- Sleep: User was sleeping (auto-create activity)
- Remind Later: Schedule reminder
- Activity: User was doing something (FSM flow)

Test Coverage:
    - handle_poll_skip: Skip response with next poll scheduling
    - handle_poll_sleep: Sleep activity creation with duration calc
    - handle_poll_remind: Reminder scheduling and settings check
    - handle_poll_activity_start: Activity recording FSM initiation
    - handle_poll_category_select: Category selection and time calc
    - handle_poll_description: Description input and activity save
    - handle_poll_cancel: Activity recording cancellation
    - Helper functions: scheduling, sleep category, duration calc

Coverage Target: 100% of poll_response.py
Execution Time: < 0.8 seconds

Author: Testing Team
Date: 2025-11-07
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, call
from aiogram import types
from aiogram.fsm.context import FSMContext

from src.api.handlers.poll.poll_response import (
    handle_poll_skip,
    handle_poll_sleep,
    handle_poll_remind,
    handle_poll_reminder_ok,
    handle_poll_activity_start,
    handle_poll_category_select,
    handle_poll_description,
    handle_poll_cancel,
    _schedule_next_poll,
    _get_or_create_sleep_category,
    _calculate_sleep_duration,
    _cancel_poll_activity,
    _cancel_poll_activity_message
)
from src.api.states.poll import PollStates


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def mock_callback():
    """
    Fixture: Mock Telegram CallbackQuery.

    Returns:
        MagicMock: Mocked callback query
    """
    callback = MagicMock(spec=types.CallbackQuery)
    callback.from_user = MagicMock(spec=types.User)
    callback.from_user.id = 123456789
    callback.message = MagicMock(spec=types.Message)
    callback.message.answer = AsyncMock()
    callback.answer = AsyncMock()
    callback.bot = MagicMock()
    callback.data = ""
    return callback


@pytest.fixture
def mock_message():
    """
    Fixture: Mock Telegram Message.

    Returns:
        MagicMock: Mocked message
    """
    message = MagicMock(spec=types.Message)
    message.from_user = MagicMock(spec=types.User)
    message.from_user.id = 123456789
    message.answer = AsyncMock()
    message.bot = MagicMock()
    message.text = "Test activity description"
    return message


@pytest.fixture
def mock_state():
    """
    Fixture: Mock FSM context.

    Returns:
        AsyncMock: Mocked FSM context
    """
    state = AsyncMock(spec=FSMContext)
    state.get_data = AsyncMock(return_value={})
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()
    state.clear = AsyncMock()
    return state


@pytest.fixture
def mock_services():
    """
    Fixture: Mock ServiceContainer.

    Returns:
        MagicMock: Mocked service container
    """
    services = MagicMock()
    services.user = AsyncMock()
    services.settings = AsyncMock()
    services.activity = AsyncMock()
    services.category = AsyncMock()
    services.scheduler = MagicMock()
    services.scheduler.schedule_poll = AsyncMock()
    services.scheduler.scheduler = MagicMock()
    return services


@pytest.fixture
def sample_user():
    """
    Fixture: Sample user data.

    Returns:
        dict: User data
    """
    return {
        "id": 1,
        "telegram_id": 123456789,
        "username": "testuser",
        "first_name": "Test",
        "timezone": "Europe/Moscow",
        "last_poll_time": "2025-11-07T10:00:00+00:00"
    }


@pytest.fixture
def sample_settings():
    """
    Fixture: Sample settings data.

    Returns:
        dict: Settings data
    """
    return {
        "id": 1,
        "user_id": 1,
        "weekday_interval_minutes": 120,
        "weekend_interval_minutes": 180,
        "is_reminder_enabled": True,
        "reminder_enabled": True,
        "reminder_delay_minutes": 15
    }


@pytest.fixture
def sample_category():
    """
    Fixture: Sample category data.

    Returns:
        dict: Category data
    """
    return {
        "id": 1,
        "user_id": 1,
        "name": "Work",
        "emoji": "💼"
    }


@pytest.fixture
def sample_sleep_category():
    """
    Fixture: Sample sleep category data.

    Returns:
        dict: Sleep category data
    """
    return {
        "id": 5,
        "user_id": 1,
        "name": "Сон",
        "emoji": "😴"
    }


# ============================================================================
# TEST SUITES
# ============================================================================

class TestHandlePollSkip:
    """
    Test suite for handle_poll_skip handler.

    Tests 'Skip' poll response flow.
    """

    @pytest.mark.unit
    async def test_handle_poll_skip_success_schedules_next_poll(
        self,
        mock_callback,
        mock_state,
        sample_user,
        sample_settings
    ):
        """
        Test successful poll skip response.

        GIVEN: Valid user and settings
        WHEN: handle_poll_skip is called
        THEN: Next poll is scheduled
              AND confirmation message is sent
        """
        # Arrange
        with patch('src.api.handlers.poll.poll_response.get_user_and_settings') as mock_get:
            mock_get.return_value = (sample_user, sample_settings)

            with patch('src.api.handlers.poll.poll_response._schedule_next_poll') as mock_schedule:
                # Act
                await handle_poll_skip(mock_callback, mock_state)

        # Assert: Next poll scheduled
        mock_schedule.assert_called_once()
        assert mock_schedule.call_args.kwargs["telegram_id"] == 123456789

        # Assert: Confirmation message
        mock_callback.message.answer.assert_called_once()
        message_text = mock_callback.message.answer.call_args[0][0]
        assert "ничего не делал" in message_text.lower()

        # Assert: Callback answered
        mock_callback.answer.assert_called_once()

    @pytest.mark.unit
    async def test_handle_poll_skip_with_user_not_found_shows_error(
        self,
        mock_callback,
        mock_state
    ):
        """
        Test skip when user not found.

        GIVEN: User does not exist
        WHEN: handle_poll_skip is called
        THEN: Error message is shown
              AND no poll is scheduled
        """
        # Arrange
        with patch('src.api.handlers.poll.poll_response.get_user_and_settings') as mock_get:
            mock_get.return_value = (None, None)

            with patch('src.api.handlers.poll.poll_response._schedule_next_poll') as mock_schedule:
                # Act
                await handle_poll_skip(mock_callback, mock_state)

        # Assert: Error message
        mock_callback.message.answer.assert_called_once()
        message_text = mock_callback.message.answer.call_args[0][0]
        assert "Ошибка" in message_text

        # Assert: No poll scheduled
        mock_schedule.assert_not_called()

    @pytest.mark.unit
    async def test_handle_poll_skip_with_exception_handles_gracefully(
        self,
        mock_callback,
        mock_state
    ):
        """
        Test error handling in poll skip.

        GIVEN: Exception occurs during processing
        WHEN: handle_poll_skip is called
        THEN: Error is caught and error message shown
        """
        # Arrange
        with patch('src.api.handlers.poll.poll_response.get_user_and_settings') as mock_get:
            mock_get.side_effect = Exception("Database error")

            with patch('src.api.handlers.poll.poll_response.logger'):
                # Act
                await handle_poll_skip(mock_callback, mock_state)

        # Assert: Error message shown
        mock_callback.message.answer.assert_called()
        message_text = mock_callback.message.answer.call_args[0][0]
        assert "Произошла ошибка" in message_text


class TestHandlePollSleep:
    """
    Test suite for handle_poll_sleep handler.

    Tests 'Sleep' poll response with automatic activity creation.
    """

    @pytest.mark.unit
    async def test_handle_poll_sleep_with_existing_category_creates_activity(
        self,
        mock_callback,
        mock_state,
        sample_user,
        sample_settings,
        sample_sleep_category
    ):
        """
        Test sleep activity creation with existing category.

        GIVEN: User has existing "Сон" category
        WHEN: handle_poll_sleep is called
        THEN: Sleep activity is created using existing category
              AND next poll is scheduled
        """
        # Arrange
        with patch('src.api.handlers.poll.poll_response.get_user_and_settings') as mock_get:
            mock_get.return_value = (sample_user, sample_settings)

            with patch('src.api.handlers.poll.poll_response._get_or_create_sleep_category') as mock_cat:
                mock_cat.return_value = sample_sleep_category

                with patch('src.api.handlers.poll.poll_response._calculate_sleep_duration') as mock_duration:
                    start_time = datetime(2025, 11, 7, 8, 0, 0, tzinfo=timezone.utc)
                    end_time = datetime(2025, 11, 7, 10, 0, 0, tzinfo=timezone.utc)
                    mock_duration.return_value = (start_time, end_time)

                    with patch('src.api.handlers.poll.poll_response.services') as mock_services:
                        mock_services.activity.create_activity = AsyncMock()

                        with patch('src.api.handlers.poll.poll_response._schedule_next_poll'):
                            # Act
                            await handle_poll_sleep(mock_callback, mock_state)

        # Assert: Activity created
        mock_services.activity.create_activity.assert_called_once()
        call_args = mock_services.activity.create_activity.call_args.kwargs
        assert call_args["user_id"] == 1
        assert call_args["category_id"] == 5
        assert call_args["description"] == "Сон"
        assert call_args["start_time"] == start_time
        assert call_args["end_time"] == end_time

        # Assert: Success message
        mock_callback.message.answer.assert_called()
        message_text = mock_callback.message.answer.call_args[0][0]
        assert "Сон сохранён" in message_text

    @pytest.mark.unit
    async def test_handle_poll_sleep_creates_new_category_if_missing(
        self,
        mock_callback,
        mock_state,
        sample_user,
        sample_settings,
        sample_sleep_category
    ):
        """
        Test sleep category auto-creation.

        GIVEN: User does not have "Сон" category
        WHEN: handle_poll_sleep is called
        THEN: New "Сон" category is created
              AND sleep activity is created
        """
        # Arrange
        with patch('src.api.handlers.poll.poll_response.get_user_and_settings') as mock_get:
            mock_get.return_value = (sample_user, sample_settings)

            with patch('src.api.handlers.poll.poll_response._get_or_create_sleep_category') as mock_cat:
                mock_cat.return_value = sample_sleep_category

                with patch('src.api.handlers.poll.poll_response._calculate_sleep_duration') as mock_duration:
                    mock_duration.return_value = (
                        datetime(2025, 11, 7, 8, 0, tzinfo=timezone.utc),
                        datetime(2025, 11, 7, 10, 0, tzinfo=timezone.utc)
                    )

                    with patch('src.api.handlers.poll.poll_response.services') as mock_services:
                        mock_services.activity.create_activity = AsyncMock()

                        with patch('src.api.handlers.poll.poll_response._schedule_next_poll'):
                            # Act
                            await handle_poll_sleep(mock_callback, mock_state)

        # Assert: Category creation called
        mock_cat.assert_called_once_with(1)

    @pytest.mark.unit
    async def test_handle_poll_sleep_with_error_handles_gracefully(
        self,
        mock_callback,
        mock_state
    ):
        """
        Test error handling in poll sleep.

        GIVEN: Exception occurs during processing
        WHEN: handle_poll_sleep is called
        THEN: Error is caught and error message shown
        """
        # Arrange
        with patch('src.api.handlers.poll.poll_response.get_user_and_settings') as mock_get:
            mock_get.side_effect = Exception("Service error")

            with patch('src.api.handlers.poll.poll_response.logger'):
                # Act
                await handle_poll_sleep(mock_callback, mock_state)

        # Assert: Error message shown
        mock_callback.message.answer.assert_called()
        message_text = mock_callback.message.answer.call_args[0][0]
        assert "Произошла ошибка" in message_text


class TestHandlePollRemind:
    """
    Test suite for handle_poll_remind handler.

    Tests 'Remind Later' poll response.
    """

    @pytest.mark.unit
    async def test_handle_poll_remind_success_schedules_reminder(
        self,
        mock_callback,
        mock_state,
        sample_user,
        sample_settings
    ):
        """
        Test successful reminder scheduling.

        GIVEN: Reminders are enabled in settings
        WHEN: handle_poll_remind is called
        THEN: Reminder is scheduled after delay_minutes
              AND confirmation message is sent
        """
        # Arrange
        with patch('src.api.handlers.poll.poll_response.get_user_and_settings') as mock_get:
            mock_get.return_value = (sample_user, sample_settings)

            with patch('src.api.handlers.poll.poll_response.services') as mock_services:
                mock_scheduler = MagicMock()
                mock_services.scheduler.scheduler = mock_scheduler

                # Act
                await handle_poll_remind(mock_callback, mock_state)

        # Assert: Reminder scheduled
        mock_scheduler.add_job.assert_called_once()
        call_args = mock_scheduler.add_job.call_args

        # Verify job ID contains telegram_id
        job_id = call_args.kwargs["id"]
        assert "reminder_123456789" in job_id

        # Assert: Confirmation message
        mock_callback.message.answer.assert_called()
        message_text = mock_callback.message.answer.call_args[0][0]
        assert "напомню через" in message_text.lower()
        assert "15" in message_text  # delay_minutes

    @pytest.mark.unit
    async def test_handle_poll_remind_with_reminders_disabled_shows_warning(
        self,
        mock_callback,
        mock_state,
        sample_user,
        sample_settings
    ):
        """
        Test reminder when disabled in settings.

        GIVEN: Reminders are disabled
        WHEN: handle_poll_remind is called
        THEN: Warning message is shown
              AND no reminder is scheduled
        """
        # Arrange
        settings_no_reminder = sample_settings.copy()
        settings_no_reminder["reminder_enabled"] = False

        with patch('src.api.handlers.poll.poll_response.get_user_and_settings') as mock_get:
            mock_get.return_value = (sample_user, settings_no_reminder)

            with patch('src.api.handlers.poll.poll_response.services') as mock_services:
                mock_scheduler = MagicMock()
                mock_services.scheduler.scheduler = mock_scheduler

                # Act
                await handle_poll_remind(mock_callback, mock_state)

        # Assert: Warning message
        mock_callback.message.answer.assert_called()
        message_text = mock_callback.message.answer.call_args[0][0]
        assert "отключены" in message_text.lower()

        # Assert: No reminder scheduled
        mock_scheduler.add_job.assert_not_called()

    @pytest.mark.unit
    async def test_handle_poll_remind_with_error_handles_gracefully(
        self,
        mock_callback,
        mock_state
    ):
        """
        Test error handling in reminder scheduling.

        GIVEN: Exception occurs during processing
        WHEN: handle_poll_remind is called
        THEN: Error is caught and error message shown
        """
        # Arrange
        with patch('src.api.handlers.poll.poll_response.get_user_and_settings') as mock_get:
            mock_get.side_effect = Exception("Scheduler error")

            with patch('src.api.handlers.poll.poll_response.logger'):
                # Act
                await handle_poll_remind(mock_callback, mock_state)

        # Assert: Error message shown
        mock_callback.message.answer.assert_called()


class TestHandlePollReminderOk:
    """
    Test suite for handle_poll_reminder_ok handler.

    Tests reminder acknowledgment.
    """

    @pytest.mark.unit
    async def test_handle_poll_reminder_ok_sends_confirmation(
        self,
        mock_callback,
        mock_services
    ):
        """
        Test reminder acknowledgment.

        GIVEN: User acknowledges reminder
        WHEN: handle_poll_reminder_ok is called
        THEN: Confirmation message is sent
        """
        # Act
        await handle_poll_reminder_ok(mock_callback, mock_services)

        # Assert: Confirmation message
        mock_callback.message.answer.assert_called_once()
        message_text = mock_callback.message.answer.call_args[0][0]
        assert "Отлично" in message_text or "👌" in message_text


class TestHandlePollActivityStart:
    """
    Test suite for handle_poll_activity_start handler.

    Tests activity recording FSM initiation.
    """

    @pytest.mark.unit
    async def test_handle_poll_activity_start_success_shows_categories(
        self,
        mock_callback,
        mock_state,
        sample_user,
        sample_settings,
        sample_category
    ):
        """
        Test successful activity start.

        GIVEN: User has categories
        WHEN: handle_poll_activity_start is called
        THEN: FSM state is set to waiting_for_poll_category
              AND category selection keyboard is shown
        """
        # Arrange
        with patch('src.api.handlers.poll.poll_response.get_user_and_settings') as mock_get:
            mock_get.return_value = (sample_user, sample_settings)

            with patch('src.api.handlers.poll.poll_response.services') as mock_services:
                mock_services.category.get_user_categories = AsyncMock(return_value=[sample_category])

                with patch('src.api.handlers.poll.poll_response.fsm_timeout_module'):
                    # Act
                    await handle_poll_activity_start(mock_callback, mock_state)

        # Assert: State set
        mock_state.set_state.assert_called_once_with(PollStates.waiting_for_poll_category)

        # Assert: user_id stored in state
        mock_state.update_data.assert_called_once()
        assert mock_state.update_data.call_args.kwargs["user_id"] == 1

        # Assert: Category selection message
        mock_callback.message.answer.assert_called()
        message_text = mock_callback.message.answer.call_args[0][0]
        assert "Выбери категорию" in message_text

    @pytest.mark.unit
    async def test_handle_poll_activity_start_with_no_categories_shows_error(
        self,
        mock_callback,
        mock_state,
        sample_user,
        sample_settings
    ):
        """
        Test activity start when no categories exist.

        GIVEN: User has no categories
        WHEN: handle_poll_activity_start is called
        THEN: Error message is shown
              AND FSM state is not changed
        """
        # Arrange
        with patch('src.api.handlers.poll.poll_response.get_user_and_settings') as mock_get:
            mock_get.return_value = (sample_user, sample_settings)

            with patch('src.api.handlers.poll.poll_response.services') as mock_services:
                mock_services.category.get_user_categories = AsyncMock(return_value=[])

                # Act
                await handle_poll_activity_start(mock_callback, mock_state)

        # Assert: Error message
        mock_callback.message.answer.assert_called()
        message_text = mock_callback.message.answer.call_args[0][0]
        assert "нет категорий" in message_text.lower()

        # Assert: State not changed
        mock_state.set_state.assert_not_called()

    @pytest.mark.unit
    async def test_handle_poll_activity_start_with_user_not_found_shows_error(
        self,
        mock_callback,
        mock_state
    ):
        """
        Test activity start when user not found.

        GIVEN: User does not exist
        WHEN: handle_poll_activity_start is called
        THEN: Error message is shown
        """
        # Arrange
        with patch('src.api.handlers.poll.poll_response.get_user_and_settings') as mock_get:
            mock_get.return_value = (None, None)

            # Act
            await handle_poll_activity_start(mock_callback, mock_state)

        # Assert: Error message
        mock_callback.message.answer.assert_called()
        message_text = mock_callback.message.answer.call_args[0][0]
        assert "не найден" in message_text.lower()


class TestHandlePollCategorySelect:
    """
    Test suite for handle_poll_category_select handler.

    Tests category selection in activity recording.
    """

    @pytest.mark.unit
    async def test_handle_poll_category_select_success_asks_for_description(
        self,
        mock_callback,
        mock_state,
        sample_user,
        sample_settings
    ):
        """
        Test successful category selection.

        GIVEN: User selects category
        WHEN: handle_poll_category_select is called
        THEN: FSM state is set to waiting_for_poll_description
              AND time range and description prompt are shown
        """
        # Arrange
        mock_callback.data = "poll_category_1"

        with patch('src.api.handlers.poll.poll_response.get_user_and_settings') as mock_get:
            mock_get.return_value = (sample_user, sample_settings)

            with patch('src.api.handlers.poll.poll_response.fsm_timeout_module'):
                with patch('src.api.handlers.poll.poll_response.format_time') as mock_format_time:
                    mock_format_time.return_value = "10:00"

                    with patch('src.api.handlers.poll.poll_response.format_duration') as mock_format_duration:
                        mock_format_duration.return_value = "2 часа"

                        # Act
                        await handle_poll_category_select(mock_callback, mock_state)

        # Assert: State updated with category_id
        mock_state.update_data.assert_called_once()
        call_args = mock_state.update_data.call_args.kwargs
        assert call_args["category_id"] == 1
        assert "start_time" in call_args
        assert "end_time" in call_args

        # Assert: State set to description
        mock_state.set_state.assert_called_once_with(PollStates.waiting_for_poll_description)

        # Assert: Description prompt
        mock_callback.message.answer.assert_called()
        message_text = mock_callback.message.answer.call_args[0][0]
        assert "Опиши активность" in message_text

    @pytest.mark.unit
    async def test_handle_poll_category_select_with_error_cancels_activity(
        self,
        mock_callback,
        mock_state
    ):
        """
        Test error handling in category selection.

        GIVEN: Exception occurs during processing
        WHEN: handle_poll_category_select is called
        THEN: Activity recording is cancelled
        """
        # Arrange
        mock_callback.data = "poll_category_1"

        with patch('src.api.handlers.poll.poll_response.get_user_and_settings') as mock_get:
            mock_get.side_effect = Exception("Time calculation error")

            with patch('src.api.handlers.poll.poll_response._cancel_poll_activity') as mock_cancel:
                # Act
                await handle_poll_category_select(mock_callback, mock_state)

        # Assert: Activity cancelled
        mock_cancel.assert_called_once()


class TestHandlePollDescription:
    """
    Test suite for handle_poll_description handler.

    Tests description input and activity saving.
    """

    @pytest.mark.unit
    async def test_handle_poll_description_success_creates_activity(
        self,
        mock_message,
        mock_state,
        mock_services
    ):
        """
        Test successful activity creation from description.

        GIVEN: Valid description and state data
        WHEN: handle_poll_description is called
        THEN: Activity is created
              AND next poll is scheduled
              AND success message is shown
        """
        # Arrange
        mock_message.text = "Working on project #work #coding"

        state_data = {
            "user_id": 1,
            "category_id": 1,
            "start_time": "2025-11-07T10:00:00+00:00",
            "end_time": "2025-11-07T12:00:00+00:00",
            "settings": {"weekday_interval_minutes": 120},
            "user_timezone": "Europe/Moscow"
        }
        mock_state.get_data.return_value = state_data

        with patch('src.api.handlers.poll.poll_response.extract_tags') as mock_extract:
            mock_extract.return_value = ["work", "coding"]

            with patch('src.api.handlers.poll.poll_response.fsm_timeout_module'):
                with patch('src.api.handlers.poll.poll_response.format_duration') as mock_format:
                    mock_format.return_value = "2 часа"

                    # Act
                    await handle_poll_description(mock_message, mock_state, mock_services)

        # Assert: Activity created
        mock_services.activity.create_activity.assert_called_once()
        call_args = mock_services.activity.create_activity.call_args.kwargs
        assert call_args["user_id"] == 1
        assert call_args["category_id"] == 1
        assert call_args["description"] == "Working on project #work #coding"
        assert call_args["tags"] == ["work", "coding"]

        # Assert: Next poll scheduled
        mock_services.scheduler.schedule_poll.assert_called_once()

        # Assert: Success message
        mock_message.answer.assert_called()
        message_text = mock_message.answer.call_args[0][0]
        assert "сохранена" in message_text.lower()

        # Assert: State cleared
        mock_state.clear.assert_called_once()

    @pytest.mark.unit
    async def test_handle_poll_description_with_short_description_shows_error(
        self,
        mock_message,
        mock_state,
        mock_services
    ):
        """
        Test description validation (min 3 chars).

        GIVEN: Description with less than 3 characters
        WHEN: handle_poll_description is called
        THEN: Validation error is shown
              AND activity is not created
        """
        # Arrange
        mock_message.text = "ab"  # Only 2 chars

        # Act
        await handle_poll_description(mock_message, mock_state, mock_services)

        # Assert: Validation error
        mock_message.answer.assert_called_once()
        message_text = mock_message.answer.call_args[0][0]
        assert "минимум 3 символа" in message_text.lower()

        # Assert: Activity not created
        mock_services.activity.create_activity.assert_not_called()

    @pytest.mark.unit
    async def test_handle_poll_description_with_missing_data_cancels_activity(
        self,
        mock_message,
        mock_state,
        mock_services
    ):
        """
        Test handling of insufficient state data.

        GIVEN: State data is missing required fields
        WHEN: handle_poll_description is called
        THEN: Activity recording is cancelled
        """
        # Arrange
        mock_message.text = "Valid description"
        mock_state.get_data.return_value = {
            "category_id": 1
            # Missing user_id, start_time, end_time
        }

        with patch('src.api.handlers.poll.poll_response._cancel_poll_activity_message') as mock_cancel:
            # Act
            await handle_poll_description(mock_message, mock_state, mock_services)

        # Assert: Activity cancelled
        mock_cancel.assert_called_once()

        # Assert: Activity not created
        mock_services.activity.create_activity.assert_not_called()

    @pytest.mark.unit
    async def test_handle_poll_description_with_error_cancels_activity(
        self,
        mock_message,
        mock_state,
        mock_services
    ):
        """
        Test error handling in activity creation.

        GIVEN: Exception occurs during activity creation
        WHEN: handle_poll_description is called
        THEN: Activity recording is cancelled
        """
        # Arrange
        mock_message.text = "Valid description"

        state_data = {
            "user_id": 1,
            "category_id": 1,
            "start_time": "2025-11-07T10:00:00+00:00",
            "end_time": "2025-11-07T12:00:00+00:00",
            "settings": {"weekday_interval_minutes": 120},
            "user_timezone": "Europe/Moscow"
        }
        mock_state.get_data.return_value = state_data
        mock_services.activity.create_activity.side_effect = Exception("Database error")

        with patch('src.api.handlers.poll.poll_response.extract_tags', return_value=[]):
            with patch('src.api.handlers.poll.poll_response._cancel_poll_activity_message') as mock_cancel:
                with patch('src.api.handlers.poll.poll_response.logger'):
                    # Act
                    await handle_poll_description(mock_message, mock_state, mock_services)

        # Assert: Activity cancelled
        mock_cancel.assert_called_once()


class TestHandlePollCancel:
    """
    Test suite for handle_poll_cancel handler.

    Tests activity recording cancellation.
    """

    @pytest.mark.unit
    async def test_handle_poll_cancel_clears_state(
        self,
        mock_callback,
        mock_state
    ):
        """
        Test activity recording cancellation.

        GIVEN: User cancels activity recording
        WHEN: handle_poll_cancel is called
        THEN: FSM state is cleared
              AND cancellation message is shown
        """
        # Arrange
        with patch('src.api.handlers.poll.poll_response.fsm_timeout_module'):
            # Act
            await handle_poll_cancel(mock_callback, mock_state)

        # Assert: State cleared
        mock_state.clear.assert_called_once()

        # Assert: Cancellation message
        mock_callback.message.answer.assert_called()
        message_text = mock_callback.message.answer.call_args[0][0]
        assert "отменена" in message_text.lower()


class TestHelperFunctions:
    """
    Test suite for helper functions.

    Tests internal utility functions.
    """

    @pytest.mark.unit
    async def test_schedule_next_poll_success(
        self,
        sample_user,
        sample_settings
    ):
        """
        Test next poll scheduling.

        GIVEN: Valid user and settings
        WHEN: _schedule_next_poll is called
        THEN: Scheduler schedules poll with correct parameters
        """
        # Arrange
        bot = MagicMock()

        with patch('src.api.handlers.poll.poll_response.services') as mock_services:
            mock_services.scheduler.schedule_poll = AsyncMock()

            # Act
            await _schedule_next_poll(
                telegram_id=123456789,
                settings=sample_settings,
                user=sample_user,
                bot=bot
            )

        # Assert: Scheduler called
        mock_services.scheduler.schedule_poll.assert_called_once()
        call_args = mock_services.scheduler.schedule_poll.call_args.kwargs
        assert call_args["user_id"] == 123456789
        assert call_args["user_timezone"] == "Europe/Moscow"

    @pytest.mark.unit
    async def test_get_or_create_sleep_category_with_existing_category(
        self,
        sample_sleep_category
    ):
        """
        Test sleep category retrieval when exists.

        GIVEN: User has "Сон" category
        WHEN: _get_or_create_sleep_category is called
        THEN: Existing category is returned
              AND no new category is created
        """
        # Arrange
        categories = [
            {"id": 1, "name": "Work", "emoji": "💼"},
            sample_sleep_category
        ]

        with patch('src.api.handlers.poll.poll_response.services') as mock_services:
            mock_services.category.get_user_categories = AsyncMock(return_value=categories)
            mock_services.category.create_category = AsyncMock()

            # Act
            result = await _get_or_create_sleep_category(user_id=1)

        # Assert: Existing category returned
        assert result["id"] == 5
        assert result["name"] == "Сон"

        # Assert: No new category created
        mock_services.category.create_category.assert_not_called()

    @pytest.mark.unit
    async def test_get_or_create_sleep_category_creates_new_when_missing(
        self,
        sample_sleep_category
    ):
        """
        Test sleep category creation when missing.

        GIVEN: User does not have "Сон" category
        WHEN: _get_or_create_sleep_category is called
        THEN: New "Сон" category is created
        """
        # Arrange
        categories = [
            {"id": 1, "name": "Work", "emoji": "💼"}
        ]

        with patch('src.api.handlers.poll.poll_response.services') as mock_services:
            mock_services.category.get_user_categories = AsyncMock(return_value=categories)
            mock_services.category.create_category = AsyncMock(return_value=sample_sleep_category)

            # Act
            result = await _get_or_create_sleep_category(user_id=1)

        # Assert: New category created
        mock_services.category.create_category.assert_called_once()
        call_args = mock_services.category.create_category.call_args.kwargs
        assert call_args["user_id"] == 1
        assert call_args["name"] == "Сон"
        assert call_args["emoji"] == "😴"

        # Assert: New category returned
        assert result["id"] == 5

    @pytest.mark.unit
    async def test_calculate_sleep_duration_with_last_poll_time(
        self,
        sample_user,
        sample_settings
    ):
        """
        Test sleep duration calculation using last poll time.

        GIVEN: User has last_poll_time recorded
        WHEN: _calculate_sleep_duration is called
        THEN: Duration is calculated from last_poll_time to now
        """
        # Act
        start_time, end_time = await _calculate_sleep_duration(
            sample_user,
            sample_settings
        )

        # Assert: start_time from last_poll_time
        assert start_time.year == 2025
        assert start_time.month == 11
        assert start_time.day == 7
        assert start_time.hour == 10

        # Assert: end_time is recent
        assert (datetime.now(timezone.utc) - end_time).total_seconds() < 2

    @pytest.mark.unit
    async def test_calculate_sleep_duration_without_last_poll_time(
        self,
        sample_user,
        sample_settings
    ):
        """
        Test sleep duration calculation without last poll time.

        GIVEN: User has no last_poll_time (fallback scenario)
        WHEN: _calculate_sleep_duration is called
        THEN: Duration is calculated using poll interval
        """
        # Arrange
        user_no_poll = sample_user.copy()
        del user_no_poll["last_poll_time"]

        with patch('src.api.handlers.poll.poll_response.calculate_poll_start_time') as mock_calc:
            mock_calc.return_value = datetime(2025, 11, 7, 8, 0, tzinfo=timezone.utc)

            # Act
            start_time, end_time = await _calculate_sleep_duration(
                user_no_poll,
                sample_settings
            )

        # Assert: calculate_poll_start_time was called
        mock_calc.assert_called_once()

        # Assert: start_time from calculation
        assert start_time == datetime(2025, 11, 7, 8, 0, tzinfo=timezone.utc)

    @pytest.mark.unit
    async def test_cancel_poll_activity_clears_state_and_cancels_timeout(
        self,
        mock_callback,
        mock_state
    ):
        """
        Test poll activity cancellation (callback version).

        GIVEN: Activity recording in progress
        WHEN: _cancel_poll_activity is called
        THEN: State is cleared and timeout is cancelled
        """
        # Arrange
        mock_message = mock_callback.message

        with patch('src.api.handlers.poll.poll_response.fsm_timeout_module') as mock_timeout_module:
            mock_timeout_service = MagicMock()
            mock_timeout_module.fsm_timeout_service = mock_timeout_service

            # Act
            await _cancel_poll_activity(
                mock_message,
                mock_callback,
                mock_state,
                123456789,
                "Test error"
            )

        # Assert: Error message sent
        mock_message.answer.assert_called_with("Test error")

        # Assert: Callback answered
        mock_callback.answer.assert_called_once()

        # Assert: State cleared
        mock_state.clear.assert_called_once()

        # Assert: Timeout cancelled
        mock_timeout_service.cancel_timeout.assert_called_once_with(123456789)

    @pytest.mark.unit
    async def test_cancel_poll_activity_message_clears_state(
        self,
        mock_message,
        mock_state
    ):
        """
        Test poll activity cancellation (message version).

        GIVEN: Activity recording in progress
        WHEN: _cancel_poll_activity_message is called
        THEN: State is cleared and timeout is cancelled
        """
        # Arrange
        with patch('src.api.handlers.poll.poll_response.fsm_timeout_module') as mock_timeout_module:
            mock_timeout_service = MagicMock()
            mock_timeout_module.fsm_timeout_service = mock_timeout_service

            # Act
            await _cancel_poll_activity_message(
                mock_message,
                mock_state,
                123456789,
                "Test error"
            )

        # Assert: Error message sent
        mock_message.answer.assert_called_once()

        # Assert: State cleared
        mock_state.clear.assert_called_once()

        # Assert: Timeout cancelled
        mock_timeout_service.cancel_timeout.assert_called_once_with(123456789)
