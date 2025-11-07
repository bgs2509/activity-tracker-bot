"""
Unit tests for activity management handlers.

Tests viewing activities, canceling FSM flow, FSM timeout handling,
and help messages.

Test Coverage:
    - cancel_action: Cancel current action
    - show_my_activities: View recent activities
    - cancel_activity_fsm: /cancel command handler
    - handle_fsm_reminder_continue: Continue after timeout reminder
    - show_help: Help message display

Coverage Target: 100% of activity_management.py
Execution Time: < 0.4 seconds

Author: Testing Team
Date: 2025-11-07
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram import types
from aiogram.fsm.context import FSMContext

from src.api.handlers.activity.activity_management import (
    cancel_action,
    show_my_activities,
    cancel_activity_fsm,
    handle_fsm_reminder_continue,
    show_help
)


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def mock_callback():
    """Fixture: Mock Telegram CallbackQuery."""
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
    """Fixture: Mock Telegram Message."""
    message = MagicMock(spec=types.Message)
    message.from_user = MagicMock(spec=types.User)
    message.from_user.id = 123456789
    message.answer = AsyncMock()
    message.bot = MagicMock()
    return message


@pytest.fixture
def mock_state():
    """Fixture: Mock FSM context."""
    state = AsyncMock(spec=FSMContext)
    state.get_state = AsyncMock(return_value=None)
    state.clear = AsyncMock()
    return state


@pytest.fixture
def mock_services():
    """Fixture: Mock ServiceContainer."""
    services = MagicMock()
    services.activity = AsyncMock()
    return services


@pytest.fixture
def sample_user():
    """Fixture: Sample user data."""
    return {
        "id": 1,
        "telegram_id": 123456789,
        "username": "testuser"
    }


@pytest.fixture
def sample_activities():
    """Fixture: Sample activities list."""
    return [
        {
            "id": 1,
            "description": "Working on project",
            "start_time": "2025-11-07T14:00:00+00:00",
            "end_time": "2025-11-07T15:30:00+00:00",
            "category": {"name": "Work", "emoji": "💼"}
        },
        {
            "id": 2,
            "description": "Running",
            "start_time": "2025-11-07T10:00:00+00:00",
            "end_time": "2025-11-07T11:00:00+00:00",
            "category": {"name": "Sport", "emoji": "🏃"}
        }
    ]


# ============================================================================
# TEST SUITES
# ============================================================================

class TestCancelAction:
    """Test suite for cancel_action handler."""

    @pytest.mark.unit
    async def test_cancel_action_clears_state_and_shows_message(
        self,
        mock_callback,
        mock_state
    ):
        """
        Test action cancellation.

        GIVEN: User clicks cancel button
        WHEN: cancel_action is called
        THEN: State is cleared
              AND cancellation message is shown
        """
        # Arrange
        with patch('src.api.handlers.activity.activity_management.clear_state_and_timeout') as mock_clear:
            # Act
            await cancel_action(mock_callback, mock_state)

        # Assert: State cleared
        mock_clear.assert_called_once_with(mock_state, 123456789)

        # Assert: Message shown
        mock_callback.message.answer.assert_called_once()
        message_text = mock_callback.message.answer.call_args[0][0]
        assert "отменено" in message_text

        # Assert: Callback answered
        mock_callback.answer.assert_called_once()


class TestShowMyActivities:
    """Test suite for show_my_activities handler."""

    @pytest.mark.unit
    async def test_show_my_activities_with_data_displays_list(
        self,
        mock_callback,
        mock_services,
        sample_user,
        sample_activities
    ):
        """
        Test displaying user's activities.

        GIVEN: User has activities
        WHEN: show_my_activities is called
        THEN: Activities are fetched and formatted
              AND displayed to user
        """
        # Arrange
        mock_services.activity.get_user_activities.return_value = sample_activities

        with patch('src.api.handlers.activity.activity_management.format_activity_list') as mock_format:
            mock_format.return_value = "📋 Мои записи\n\n1. Working on project..."

            # Act
            await show_my_activities(mock_callback, mock_services, sample_user)

        # Assert: Activities fetched
        mock_services.activity.get_user_activities.assert_called_once_with(1, limit=10)

        # Assert: Activities formatted
        mock_format.assert_called_once_with(sample_activities)

        # Assert: Message shown
        mock_callback.message.answer.assert_called_once()
        message_text = mock_callback.message.answer.call_args[0][0]
        assert "Мои записи" in message_text

        # Assert: Callback answered
        mock_callback.answer.assert_called_once()

    @pytest.mark.unit
    async def test_show_my_activities_with_empty_list_shows_empty_message(
        self,
        mock_callback,
        mock_services,
        sample_user
    ):
        """
        Test displaying empty activities list.

        GIVEN: User has no activities
        WHEN: show_my_activities is called
        THEN: Empty list message is shown
        """
        # Arrange
        mock_services.activity.get_user_activities.return_value = []

        with patch('src.api.handlers.activity.activity_management.format_activity_list') as mock_format:
            mock_format.return_value = "📋 У тебя пока нет записей."

            # Act
            await show_my_activities(mock_callback, mock_services, sample_user)

        # Assert: Empty message shown
        mock_callback.message.answer.assert_called_once()

    @pytest.mark.unit
    async def test_show_my_activities_with_error_handles_gracefully(
        self,
        mock_callback,
        mock_services,
        sample_user
    ):
        """
        Test error handling in activities fetching.

        GIVEN: Service raises exception
        WHEN: show_my_activities is called
        THEN: Error is caught and error message shown
        """
        # Arrange
        mock_services.activity.get_user_activities.side_effect = Exception("Database error")

        # Act
        await show_my_activities(mock_callback, mock_services, sample_user)

        # Assert: Error message shown
        mock_callback.message.answer.assert_called_once()
        message_text = mock_callback.message.answer.call_args[0][0]
        assert "Произошла ошибка" in message_text


class TestCancelActivityFsm:
    """Test suite for cancel_activity_fsm (/cancel command)."""

    @pytest.mark.unit
    async def test_cancel_activity_fsm_with_active_state_cancels(
        self,
        mock_message,
        mock_state
    ):
        """
        Test /cancel command with active FSM.

        GIVEN: User is in ActivityStates FSM
        WHEN: /cancel command is issued
        THEN: State is cleared
              AND cancellation message shown
        """
        # Arrange
        mock_state.get_state.return_value = "ActivityStates:waiting_for_start_time"

        with patch('src.api.handlers.activity.activity_management.fsm_timeout_module') as mock_timeout:
            mock_timeout_service = MagicMock()
            mock_timeout.fsm_timeout_service = mock_timeout_service

            # Act
            await cancel_activity_fsm(mock_message, mock_state)

        # Assert: State cleared
        mock_state.clear.assert_called_once()

        # Assert: Timeout cancelled
        mock_timeout_service.cancel_timeout.assert_called_once_with(123456789)

        # Assert: Cancellation message
        mock_message.answer.assert_called_once()
        message_text = mock_message.answer.call_args[0][0]
        assert "отменена" in message_text

    @pytest.mark.unit
    async def test_cancel_activity_fsm_without_active_state_shows_nothing_to_cancel(
        self,
        mock_message,
        mock_state
    ):
        """
        Test /cancel command without active FSM.

        GIVEN: User is not in any FSM state
        WHEN: /cancel command is issued
        THEN: "Nothing to cancel" message shown
        """
        # Arrange
        mock_state.get_state.return_value = None

        # Act
        await cancel_activity_fsm(mock_message, mock_state)

        # Assert: "Nothing to cancel" message
        mock_message.answer.assert_called_once()
        message_text = mock_message.answer.call_args[0][0]
        assert "Нечего отменять" in message_text

        # Assert: State not cleared
        mock_state.clear.assert_not_called()

    @pytest.mark.unit
    async def test_cancel_activity_fsm_with_non_activity_state_shows_nothing_to_cancel(
        self,
        mock_message,
        mock_state
    ):
        """
        Test /cancel command with non-ActivityStates FSM.

        GIVEN: User is in different FSM (e.g., PollStates)
        WHEN: /cancel command is issued
        THEN: "Nothing to cancel" message shown
        """
        # Arrange
        mock_state.get_state.return_value = "PollStates:waiting_for_poll_category"

        # Act
        await cancel_activity_fsm(mock_message, mock_state)

        # Assert: "Nothing to cancel" message
        mock_message.answer.assert_called_once()
        message_text = mock_message.answer.call_args[0][0]
        assert "Нечего отменять" in message_text


class TestHandleFsmReminderContinue:
    """Test suite for handle_fsm_reminder_continue handler."""

    @pytest.mark.unit
    async def test_handle_fsm_reminder_continue_with_active_state_restarts_timeout(
        self,
        mock_callback,
        mock_state
    ):
        """
        Test continuing after FSM timeout reminder.

        GIVEN: User is in ActivityStates and clicked Continue
        WHEN: handle_fsm_reminder_continue is called
        THEN: Cleanup timer is cancelled
              AND timeout timer is restarted
              AND appropriate prompt shown
        """
        # Arrange
        mock_state.get_state.return_value = "ActivityStates:waiting_for_start_time"

        with patch('src.api.handlers.activity.activity_management.fsm_timeout_module') as mock_timeout:
            mock_timeout_service = MagicMock()
            mock_timeout.fsm_timeout_service = mock_timeout_service

            # Act
            await handle_fsm_reminder_continue(mock_callback, mock_state)

        # Assert: Cleanup timer cancelled
        mock_timeout_service.cancel_cleanup_timer.assert_called_once_with(123456789)

        # Assert: Timeout timer restarted
        mock_timeout_service.schedule_timeout.assert_called_once()
        call_kwargs = mock_timeout_service.schedule_timeout.call_args.kwargs
        assert call_kwargs["user_id"] == 123456789

        # Assert: State-specific prompt shown
        mock_callback.message.answer.assert_called_once()
        message_text = mock_callback.message.answer.call_args[0][0]
        assert "время НАЧАЛА" in message_text

        # Assert: Callback answered with success
        mock_callback.answer.assert_called_once_with("✅ Продолжаем!")

    @pytest.mark.unit
    async def test_handle_fsm_reminder_continue_without_state_shows_restart_message(
        self,
        mock_callback,
        mock_state
    ):
        """
        Test continuing without active state.

        GIVEN: User has no active FSM state
        WHEN: handle_fsm_reminder_continue is called
        THEN: "Start from main menu" message shown
        """
        # Arrange
        mock_state.get_state.return_value = None

        with patch('src.api.handlers.activity.activity_management.fsm_timeout_module') as mock_timeout:
            mock_timeout_service = MagicMock()
            mock_timeout.fsm_timeout_service = mock_timeout_service

            # Act
            await handle_fsm_reminder_continue(mock_callback, mock_state)

        # Assert: Cleanup timer cancelled
        mock_timeout_service.cancel_cleanup_timer.assert_called_once()

        # Assert: Message shown
        mock_callback.message.answer.assert_called_once()
        message_text = mock_callback.message.answer.call_args[0][0]
        assert "заново" in message_text.lower()

        # Assert: Timeout not restarted
        mock_timeout_service.schedule_timeout.assert_not_called()

    @pytest.mark.unit
    async def test_handle_fsm_reminder_continue_with_description_state_shows_correct_prompt(
        self,
        mock_callback,
        mock_state
    ):
        """
        Test state-specific prompts.

        GIVEN: User is in waiting_for_description state
        WHEN: handle_fsm_reminder_continue is called
        THEN: "Опиши активность" prompt shown
        """
        # Arrange
        mock_state.get_state.return_value = "ActivityStates:waiting_for_description"

        with patch('src.api.handlers.activity.activity_management.fsm_timeout_module') as mock_timeout:
            mock_timeout_service = MagicMock()
            mock_timeout.fsm_timeout_service = mock_timeout_service

            # Act
            await handle_fsm_reminder_continue(mock_callback, mock_state)

        # Assert: Description prompt shown
        mock_callback.message.answer.assert_called_once()
        message_text = mock_callback.message.answer.call_args[0][0]
        assert "Опиши активность" in message_text

    @pytest.mark.unit
    async def test_handle_fsm_reminder_continue_with_category_state_shows_correct_prompt(
        self,
        mock_callback,
        mock_state
    ):
        """
        Test category state prompt.

        GIVEN: User is in waiting_for_category state
        WHEN: handle_fsm_reminder_continue is called
        THEN: "Выбери категорию" prompt shown
        """
        # Arrange
        mock_state.get_state.return_value = "ActivityStates:waiting_for_category"

        with patch('src.api.handlers.activity.activity_management.fsm_timeout_module') as mock_timeout:
            mock_timeout_service = MagicMock()
            mock_timeout.fsm_timeout_service = mock_timeout_service

            # Act
            await handle_fsm_reminder_continue(mock_callback, mock_state)

        # Assert: Category prompt shown
        mock_callback.message.answer.assert_called_once()
        message_text = mock_callback.message.answer.call_args[0][0]
        assert "Выбери категорию" in message_text


class TestShowHelp:
    """Test suite for show_help handler."""

    @pytest.mark.unit
    async def test_show_help_displays_help_text(
        self,
        mock_callback
    ):
        """
        Test help message display.

        GIVEN: User clicks help button
        WHEN: show_help is called
        THEN: Comprehensive help message is shown
        """
        # Act
        await show_help(mock_callback)

        # Assert: Help message shown
        mock_callback.message.answer.assert_called_once()
        message_text = mock_callback.message.answer.call_args[0][0]

        # Verify key sections present
        assert "Справка" in message_text
        assert "Записать активность" in message_text
        assert "Автоматические опросы" in message_text
        assert "Мои записи" in message_text
        assert "Категории" in message_text
        assert "Настройки" in message_text
        assert "14:30" in message_text  # Time format example

        # Assert: Callback answered
        mock_callback.answer.assert_called_once()
