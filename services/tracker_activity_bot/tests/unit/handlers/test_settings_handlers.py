"""
Unit tests for settings handlers.

Tests settings menu display, FSM cancellation, navigation,
and helper functions for formatting.

Test Coverage:
    - show_settings_menu: Display current settings
    - cancel_settings_fsm: Cancel settings FSM
    - return_to_main_menu: Navigate back to main menu
    - _get_next_poll_text: Get next poll time or schedule
    - _format_next_poll_time: Format poll time
    - _schedule_poll_and_get_time: Schedule and get time
    - _format_time_until: Format time in Russian
    - _build_settings_text: Build settings message

Coverage Target: 100% of settings/main_menu.py
Execution Time: < 0.5 seconds

Author: Testing Team
Date: 2025-11-07
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram import types
from aiogram.fsm.context import FSMContext

from src.api.handlers.settings.main_menu import (
    show_settings_menu,
    cancel_settings_fsm,
    return_to_main_menu,
    _get_next_poll_text,
    _format_next_poll_time,
    _schedule_poll_and_get_time,
    _format_time_until,
    _build_settings_text
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
    callback.message.chat = MagicMock()
    callback.message.chat.id = 123456789
    callback.message.answer = AsyncMock()
    callback.answer = AsyncMock()
    callback.bot = MagicMock()
    callback.bot.send_chat_action = AsyncMock()
    return callback


@pytest.fixture
def mock_message():
    """Fixture: Mock Telegram Message."""
    message = MagicMock(spec=types.Message)
    message.from_user = MagicMock(spec=types.User)
    message.from_user.id = 123456789
    message.answer = AsyncMock()
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
    services.user = AsyncMock()
    services.settings = AsyncMock()
    services.scheduler = MagicMock()
    services.scheduler.jobs = {}
    services.scheduler.scheduler = MagicMock()
    services.scheduler.schedule_poll = AsyncMock()
    return services


@pytest.fixture
def sample_user():
    """Fixture: Sample user data."""
    return {
        "id": 1,
        "telegram_id": 123456789,
        "username": "testuser",
        "timezone": "Europe/Moscow"
    }


@pytest.fixture
def sample_settings():
    """Fixture: Sample settings data."""
    return {
        "id": 1,
        "user_id": 1,
        "poll_interval_weekday": 120,  # 2 hours
        "poll_interval_weekend": 180,  # 3 hours
        "quiet_hours_start": "23:00:00",
        "quiet_hours_end": "07:00:00",
        "reminder_enabled": True,
        "reminder_delay_minutes": 15
    }


# ============================================================================
# TEST SUITES
# ============================================================================

class TestShowSettingsMenu:
    """Test suite for show_settings_menu handler."""

    @pytest.mark.unit
    async def test_show_settings_menu_with_valid_data_displays_settings(
        self,
        mock_callback,
        mock_services,
        sample_user,
        sample_settings
    ):
        """
        Test settings menu display.

        GIVEN: User and settings exist
        WHEN: show_settings_menu is called
        THEN: Settings are formatted and displayed
        """
        # Arrange
        with patch('src.api.handlers.settings.main_menu.get_user_and_settings') as mock_get:
            mock_get.return_value = (sample_user, sample_settings)

            with patch('src.api.handlers.settings.main_menu._get_next_poll_text') as mock_next:
                mock_next.return_value = "⏰ Следующий опрос через 45 минут"

                with patch('src.api.handlers.settings.main_menu.format_duration') as mock_format:
                    mock_format.side_effect = ["2 часа", "3 часа"]

                    # Act
                    await show_settings_menu(mock_callback, mock_services)

        # Assert: Settings displayed
        mock_callback.message.answer.assert_called_once()
        message_text = mock_callback.message.answer.call_args[0][0]

        # Verify settings content
        assert "Настройки бота" in message_text
        assert "Будни: каждые 2 часа" in message_text
        assert "Выходные: каждые 3 часа" in message_text
        assert "Следующий опрос через 45 минут" in message_text
        assert "С 23:00 до 07:00" in message_text
        assert "Включены ✅" in message_text
        assert "15 минут" in message_text

        # Assert: Callback answered
        mock_callback.answer.assert_called_once()

    @pytest.mark.unit
    async def test_show_settings_menu_with_quiet_hours_disabled_shows_disabled(
        self,
        mock_callback,
        mock_services,
        sample_user,
        sample_settings
    ):
        """
        Test settings with quiet hours disabled.

        GIVEN: Quiet hours are disabled (start is None)
        WHEN: show_settings_menu is called
        THEN: "Выключены" is shown for quiet hours
        """
        # Arrange
        settings_no_quiet = sample_settings.copy()
        settings_no_quiet["quiet_hours_start"] = None
        settings_no_quiet["quiet_hours_end"] = None

        with patch('src.api.handlers.settings.main_menu.get_user_and_settings') as mock_get:
            mock_get.return_value = (sample_user, settings_no_quiet)

            with patch('src.api.handlers.settings.main_menu._get_next_poll_text') as mock_next:
                mock_next.return_value = ""

                with patch('src.api.handlers.settings.main_menu.format_duration') as mock_format:
                    mock_format.side_effect = ["2 часа", "3 часа"]

                    # Act
                    await show_settings_menu(mock_callback, mock_services)

        # Assert: Quiet hours disabled message
        message_text = mock_callback.message.answer.call_args[0][0]
        assert "Выключены" in message_text

    @pytest.mark.unit
    async def test_show_settings_menu_with_user_not_found_shows_error(
        self,
        mock_callback,
        mock_services
    ):
        """
        Test user not found handling.

        GIVEN: User does not exist
        WHEN: show_settings_menu is called
        THEN: Error message is shown
        """
        # Arrange
        with patch('src.api.handlers.settings.main_menu.get_user_and_settings') as mock_get:
            mock_get.return_value = (None, None)

            # Act
            await show_settings_menu(mock_callback, mock_services)

        # Assert: Error message
        mock_callback.message.answer.assert_called_once()
        message_text = mock_callback.message.answer.call_args[0][0]
        assert "не найден" in message_text

    @pytest.mark.unit
    async def test_show_settings_menu_with_settings_not_found_shows_error(
        self,
        mock_callback,
        mock_services,
        sample_user
    ):
        """
        Test settings not found handling.

        GIVEN: User exists but settings don't
        WHEN: show_settings_menu is called
        THEN: Error message is shown
        """
        # Arrange
        with patch('src.api.handlers.settings.main_menu.get_user_and_settings') as mock_get:
            mock_get.return_value = (sample_user, None)

            # Act
            await show_settings_menu(mock_callback, mock_services)

        # Assert: Error message
        mock_callback.message.answer.assert_called_once()
        message_text = mock_callback.message.answer.call_args[0][0]
        assert "Настройки не найдены" in message_text


class TestCancelSettingsFsm:
    """Test suite for cancel_settings_fsm handler."""

    @pytest.mark.unit
    async def test_cancel_settings_fsm_with_active_state_cancels(
        self,
        mock_message,
        mock_state,
        mock_services
    ):
        """
        Test FSM cancellation with active state.

        GIVEN: User is in settings FSM state
        WHEN: /cancel command is issued
        THEN: State is cleared and message shown
        """
        # Arrange
        mock_state.get_state.return_value = "SettingsStates:waiting_for_interval"

        with patch('src.api.handlers.settings.main_menu.fsm_timeout_module'):
            # Act
            await cancel_settings_fsm(mock_message, mock_state, mock_services)

        # Assert: State cleared
        mock_state.clear.assert_called_once()

        # Assert: Cancellation message
        mock_message.answer.assert_called_once()
        message_text = mock_message.answer.call_args[0][0]
        assert "отменена" in message_text

    @pytest.mark.unit
    async def test_cancel_settings_fsm_without_state_shows_nothing_to_cancel(
        self,
        mock_message,
        mock_state,
        mock_services
    ):
        """
        Test cancellation without active state.

        GIVEN: User is not in any FSM state
        WHEN: /cancel command is issued
        THEN: "Nothing to cancel" message shown
        """
        # Arrange
        mock_state.get_state.return_value = None

        # Act
        await cancel_settings_fsm(mock_message, mock_state, mock_services)

        # Assert: Nothing to cancel message
        mock_message.answer.assert_called_once()
        message_text = mock_message.answer.call_args[0][0]
        assert "Нечего отменять" in message_text

        # Assert: State not cleared
        mock_state.clear.assert_not_called()


class TestReturnToMainMenu:
    """Test suite for return_to_main_menu handler."""

    @pytest.mark.unit
    async def test_return_to_main_menu_clears_state_and_shows_menu(
        self,
        mock_callback,
        mock_state
    ):
        """
        Test main menu navigation.

        GIVEN: User clicks main menu button
        WHEN: return_to_main_menu is called
        THEN: State is cleared and main menu shown
        """
        # Act
        await return_to_main_menu(mock_callback, mock_state)

        # Assert: State cleared
        mock_state.clear.assert_called_once()

        # Assert: Main menu shown
        mock_callback.message.answer.assert_called_once()
        message_text = mock_callback.message.answer.call_args[0][0]
        assert "Главное меню" in message_text


class TestGetNextPollText:
    """Test suite for _get_next_poll_text helper function."""

    @pytest.mark.unit
    async def test_get_next_poll_text_with_scheduled_poll_returns_formatted_time(
        self,
        mock_callback,
        mock_services,
        sample_user,
        sample_settings
    ):
        """
        Test getting next poll time when already scheduled.

        GIVEN: Poll is already scheduled for user
        WHEN: _get_next_poll_text is called
        THEN: Formatted next poll time is returned
        """
        # Arrange
        mock_services.scheduler.jobs = {123456789: "poll_job_123456789"}

        with patch('src.api.handlers.settings.main_menu._format_next_poll_time') as mock_format:
            mock_format.return_value = "⏰ Следующий опрос через 30 минут"

            # Act
            result = await _get_next_poll_text(
                123456789,
                sample_settings,
                sample_user,
                mock_callback,
                mock_services
            )

        # Assert: Format function called
        mock_format.assert_called_once_with(123456789, mock_services)

        # Assert: Correct result
        assert result == "⏰ Следующий опрос через 30 минут"

    @pytest.mark.unit
    async def test_get_next_poll_text_without_scheduled_poll_schedules_and_returns_time(
        self,
        mock_callback,
        mock_services,
        sample_user,
        sample_settings
    ):
        """
        Test scheduling poll when not scheduled.

        GIVEN: No poll scheduled for user
        WHEN: _get_next_poll_text is called
        THEN: Poll is scheduled and time returned
        """
        # Arrange
        mock_services.scheduler.jobs = {}  # No jobs

        with patch('src.api.handlers.settings.main_menu._schedule_poll_and_get_time') as mock_schedule:
            mock_schedule.return_value = "⏰ Следующий опрос через 2 часа"

            # Act
            result = await _get_next_poll_text(
                123456789,
                sample_settings,
                sample_user,
                mock_callback,
                mock_services
            )

        # Assert: Schedule function called
        mock_schedule.assert_called_once()

        # Assert: Correct result
        assert result == "⏰ Следующий опрос через 2 часа"


class TestFormatNextPollTime:
    """Test suite for _format_next_poll_time helper function."""

    @pytest.mark.unit
    def test_format_next_poll_time_with_valid_job_returns_formatted_time(
        self,
        mock_services
    ):
        """
        Test formatting next poll time.

        GIVEN: Scheduled job with next_run_time
        WHEN: _format_next_poll_time is called
        THEN: Time until poll is formatted
        """
        # Arrange
        mock_services.scheduler.jobs = {123456789: "poll_job_123456789"}

        mock_job = MagicMock()
        now = datetime.now(timezone.utc)
        mock_job.next_run_time = now + timedelta(minutes=45)
        mock_services.scheduler.scheduler.get_job.return_value = mock_job

        # Act
        result = _format_next_poll_time(123456789, mock_services)

        # Assert: Formatted time returned
        assert "45 минут" in result

    @pytest.mark.unit
    def test_format_next_poll_time_with_no_job_returns_empty_string(
        self,
        mock_services
    ):
        """
        Test formatting when job not found.

        GIVEN: No scheduled job for user
        WHEN: _format_next_poll_time is called
        THEN: Empty string is returned
        """
        # Arrange
        mock_services.scheduler.jobs = {}
        mock_services.scheduler.scheduler.get_job.return_value = None

        # Act
        result = _format_next_poll_time(123456789, mock_services)

        # Assert: Empty string
        assert result == ""


class TestSchedulePollAndGetTime:
    """Test suite for _schedule_poll_and_get_time helper function."""

    @pytest.mark.unit
    async def test_schedule_poll_and_get_time_schedules_and_returns_time(
        self,
        mock_callback,
        mock_services,
        sample_user,
        sample_settings
    ):
        """
        Test scheduling poll and getting time.

        GIVEN: No poll scheduled
        WHEN: _schedule_poll_and_get_time is called
        THEN: Poll is scheduled and time returned
        """
        # Arrange
        with patch('src.api.handlers.settings.main_menu._format_next_poll_time') as mock_format:
            mock_format.return_value = "⏰ Следующий опрос через 2 часа"

            # Act
            result = await _schedule_poll_and_get_time(
                123456789,
                sample_settings,
                sample_user,
                mock_callback,
                mock_services
            )

        # Assert: Poll scheduled
        mock_services.scheduler.schedule_poll.assert_called_once()
        call_kwargs = mock_services.scheduler.schedule_poll.call_args.kwargs
        assert call_kwargs["user_id"] == 123456789
        assert call_kwargs["user_timezone"] == "Europe/Moscow"

        # Assert: Time returned
        assert result == "⏰ Следующий опрос через 2 часа"

    @pytest.mark.unit
    async def test_schedule_poll_and_get_time_with_error_returns_empty_string(
        self,
        mock_callback,
        mock_services,
        sample_user,
        sample_settings
    ):
        """
        Test error handling in scheduling.

        GIVEN: Scheduler raises exception
        WHEN: _schedule_poll_and_get_time is called
        THEN: Empty string is returned
        """
        # Arrange
        mock_services.scheduler.schedule_poll.side_effect = Exception("Scheduler error")

        # Act
        result = await _schedule_poll_and_get_time(
            123456789,
            sample_settings,
            sample_user,
            mock_callback,
            mock_services
        )

        # Assert: Empty string
        assert result == ""


class TestFormatTimeUntil:
    """Test suite for _format_time_until helper function."""

    @pytest.mark.unit
    def test_format_time_until_with_minutes_only(self):
        """
        Test formatting with only minutes.

        GIVEN: 45 minutes
        WHEN: _format_time_until is called
        THEN: "45 минут" format returned
        """
        # Act
        result = _format_time_until(45)

        # Assert
        assert result == "⏰ Следующий опрос через 45 минут"

    @pytest.mark.unit
    def test_format_time_until_with_exact_hours(self):
        """
        Test formatting with exact hours.

        GIVEN: 120 minutes (2 hours)
        WHEN: _format_time_until is called
        THEN: "2 часа" format returned
        """
        # Act
        result = _format_time_until(120)

        # Assert
        assert "2" in result
        assert "часа" in result

    @pytest.mark.unit
    def test_format_time_until_with_hours_and_minutes(self):
        """
        Test formatting with hours and minutes.

        GIVEN: 125 minutes (2h 5m)
        WHEN: _format_time_until is called
        THEN: "2ч 5м" format returned
        """
        # Act
        result = _format_time_until(125)

        # Assert
        assert "2ч" in result
        assert "5м" in result

    @pytest.mark.unit
    def test_format_time_until_with_one_hour(self):
        """
        Test formatting with 1 hour.

        GIVEN: 60 minutes (1 hour)
        WHEN: _format_time_until is called
        THEN: "1 час" format returned
        """
        # Act
        result = _format_time_until(60)

        # Assert
        assert "1" in result
        assert "час" in result


class TestBuildSettingsText:
    """Test suite for _build_settings_text helper function."""

    @pytest.mark.unit
    def test_build_settings_text_with_all_data(self):
        """
        Test building settings text with all data.

        GIVEN: All settings data provided
        WHEN: _build_settings_text is called
        THEN: Complete formatted text returned
        """
        # Act
        result = _build_settings_text(
            weekday_str="2 часа",
            weekend_str="3 часа",
            next_poll_text="⏰ Следующий опрос через 45 минут",
            quiet_text="С 23:00 до 07:00",
            reminder_status="Включены ✅",
            reminder_delay=15
        )

        # Assert: All sections present
        assert "Настройки бота" in result
        assert "Будни: каждые 2 часа" in result
        assert "Выходные: каждые 3 часа" in result
        assert "Следующий опрос через 45 минут" in result
        assert "С 23:00 до 07:00" in result
        assert "Включены ✅" in result
        assert "15 минут" in result

    @pytest.mark.unit
    def test_build_settings_text_without_next_poll(self):
        """
        Test building settings text without next poll time.

        GIVEN: Empty next_poll_text
        WHEN: _build_settings_text is called
        THEN: Text without next poll section
        """
        # Act
        result = _build_settings_text(
            weekday_str="2 часа",
            weekend_str="3 часа",
            next_poll_text="",  # Empty
            quiet_text="Выключены",
            reminder_status="Выключены ❌",
            reminder_delay=15
        )

        # Assert: Basic sections present
        assert "Настройки бота" in result
        assert "Будни: каждые 2 часа" in result

        # Assert: Next poll section not present
        assert "Следующий опрос" not in result
