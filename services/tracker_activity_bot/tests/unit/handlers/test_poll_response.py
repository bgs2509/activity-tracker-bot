"""
Unit tests for poll response handlers.

Tests automatic poll response handling and helper functions for
poll-driven activity tracking.

Test Coverage:
    - handle_poll_cancel(): Automatic poll cancellation with FSM cleanup
    - _schedule_next_poll(): Poll scheduling via scheduler service
    - _get_or_create_sleep_category(): Sleep category management
    - _calculate_sleep_duration(): Duration calculation with 24h cap
    - _cancel_poll_activity(): FSM cancellation (callback version)
    - _cancel_poll_activity_message(): FSM cancellation (message version)

Coverage Target: 85%+
Execution Time: < 0.5 seconds

Author: Testing Team
Date: 2025-11-14
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timedelta, timezone

from aiogram import types
from aiogram.fsm.context import FSMContext

from src.api.handlers.poll.poll_response import (
    handle_poll_cancel,
    _schedule_next_poll,
    _get_or_create_sleep_category,
    _calculate_sleep_duration,
    _cancel_poll_activity,
    _cancel_poll_activity_message
)


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def mock_callback():
    """
    Fixture: Mock Telegram CallbackQuery.

    Returns:
        MagicMock: Mocked callback query with from_user and message
    """
    callback = MagicMock(spec=types.CallbackQuery)
    callback.from_user = MagicMock(spec=types.User)
    callback.from_user.id = 123456789
    callback.message = MagicMock(spec=types.Message)
    callback.message.answer = AsyncMock()
    callback.answer = AsyncMock()
    callback.bot = MagicMock()
    return callback


@pytest.fixture
def mock_message():
    """
    Fixture: Mock Telegram Message.

    Returns:
        MagicMock: Mocked message with answer method
    """
    message = MagicMock(spec=types.Message)
    message.answer = AsyncMock()
    return message


@pytest.fixture
def mock_state():
    """
    Fixture: Mock FSMContext.

    Returns:
        AsyncMock: Mocked FSM context for state management
    """
    state = AsyncMock(spec=FSMContext)
    state.get_data = AsyncMock(return_value={})
    state.update_data = AsyncMock()
    state.clear = AsyncMock()
    state.set_state = AsyncMock()
    return state


@pytest.fixture
def mock_services():
    """
    Fixture: Mock ServiceContainer.

    Returns:
        MagicMock: Mocked services with scheduler, category, activity
    """
    services = MagicMock()
    services.scheduler = MagicMock()
    services.scheduler.schedule_poll = AsyncMock()
    services.category = MagicMock()
    services.category.get_user_categories = AsyncMock()
    services.category.create_category = AsyncMock()
    services.activity = MagicMock()
    services.activity.create_activity = AsyncMock()
    return services


@pytest.fixture
def sample_user():
    """
    Fixture: Sample user data.

    Returns:
        dict: User data with timezone and last poll time
    """
    return {
        "id": 1,
        "telegram_id": 123456789,
        "timezone": "Europe/Moscow",
        "last_poll_time": "2025-11-14T10:00:00+00:00"
    }


@pytest.fixture
def sample_settings():
    """
    Fixture: Sample user settings.

    Returns:
        dict: Settings with poll intervals
    """
    return {
        "poll_interval_weekday": 60,
        "poll_interval_weekend": 120,
        "quiet_hours_start": None,
        "quiet_hours_end": None
    }


# ============================================================================
# TEST SUITES - handle_poll_cancel()
# ============================================================================

class TestHandlePollCancel:
    """
    Test suite for handle_poll_cancel() handler.
    """

    @pytest.mark.unit
    @patch('src.api.handlers.poll.poll_response.fsm_timeout_module')
    async def test_handle_poll_cancel_in_automatic_flow_cancels_successfully(
        self,
        mock_fsm_timeout_module,
        mock_callback,
        mock_state
    ):
        """
        Test poll cancellation in automatic flow.

        GIVEN: User is in automatic poll flow (trigger_source="automatic")
        WHEN: handle_poll_cancel() is called
        THEN: FSM state is cleared
              AND FSM timeout is cancelled
              AND cancellation message is sent
        """
        # Arrange
        mock_state.get_data.return_value = {"trigger_source": "automatic"}
        mock_fsm_timeout_service = MagicMock()
        mock_fsm_timeout_service.cancel_timeout = MagicMock()
        mock_fsm_timeout_module.fsm_timeout_service = mock_fsm_timeout_service

        # Act
        await handle_poll_cancel(mock_callback, mock_state)

        # Assert
        mock_state.clear.assert_called_once()
        mock_fsm_timeout_service.cancel_timeout.assert_called_once_with(123456789)
        mock_callback.message.answer.assert_called_once()
        assert "❌ Опрос отменён" in mock_callback.message.answer.call_args[0][0]
        mock_callback.answer.assert_called_once()

    @pytest.mark.unit
    async def test_handle_poll_cancel_in_manual_flow_shows_warning(
        self,
        mock_callback,
        mock_state
    ):
        """
        Test poll cancellation in manual flow (not automatic).

        GIVEN: User is in manual flow (trigger_source="manual")
        WHEN: handle_poll_cancel() is called
        THEN: Warning is shown
              AND FSM state is NOT cleared
        """
        # Arrange
        mock_state.get_data.return_value = {"trigger_source": "manual"}

        # Act
        await handle_poll_cancel(mock_callback, mock_state)

        # Assert
        mock_callback.answer.assert_called_once_with("⚠️ Используй другую кнопку отмены")
        mock_state.clear.assert_not_called()

    @pytest.mark.unit
    async def test_handle_poll_cancel_without_trigger_source_shows_warning(
        self,
        mock_callback,
        mock_state
    ):
        """
        Test poll cancellation without trigger_source in state.

        GIVEN: State data doesn't have trigger_source (defaults to "manual")
        WHEN: handle_poll_cancel() is called
        THEN: Warning is shown (treated as manual flow)
        """
        # Arrange
        mock_state.get_data.return_value = {}  # No trigger_source

        # Act
        await handle_poll_cancel(mock_callback, mock_state)

        # Assert
        mock_callback.answer.assert_called_once_with("⚠️ Используй другую кнопку отмены")
        mock_state.clear.assert_not_called()

    @pytest.mark.unit
    @patch('src.api.handlers.poll.poll_response.fsm_timeout_module')
    async def test_handle_poll_cancel_without_timeout_service_still_works(
        self,
        mock_fsm_timeout_module,
        mock_callback,
        mock_state
    ):
        """
        Test poll cancellation when FSM timeout service is not available.

        GIVEN: fsm_timeout_service is None
        WHEN: handle_poll_cancel() is called
        THEN: Cancellation proceeds without error (timeout cancellation skipped)
        """
        # Arrange
        mock_state.get_data.return_value = {"trigger_source": "automatic"}
        mock_fsm_timeout_module.fsm_timeout_service = None

        # Act: Should not raise
        await handle_poll_cancel(mock_callback, mock_state)

        # Assert
        mock_state.clear.assert_called_once()
        mock_callback.message.answer.assert_called_once()


# ============================================================================
# TEST SUITES - _schedule_next_poll()
# ============================================================================

class TestScheduleNextPoll:
    """
    Test suite for _schedule_next_poll() helper function.
    """

    @pytest.mark.unit
    @patch('src.api.handlers.poll.poll_response.services')
    @patch('src.api.handlers.poll.poll_response.send_automatic_poll')
    async def test_schedule_next_poll_calls_scheduler_service(
        self,
        mock_send_poll,
        mock_services_module,
        sample_user,
        sample_settings,
        mock_callback
    ):
        """
        Test poll scheduling calls scheduler service.

        GIVEN: User and settings data
        WHEN: _schedule_next_poll() is called
        THEN: services.scheduler.schedule_poll() is called with correct params
        """
        # Arrange
        mock_services_module.scheduler = MagicMock()
        mock_services_module.scheduler.schedule_poll = AsyncMock()

        # Act
        await _schedule_next_poll(
            telegram_id=123456789,
            settings=sample_settings,
            user=sample_user,
            bot=mock_callback.bot
        )

        # Assert
        mock_services_module.scheduler.schedule_poll.assert_called_once_with(
            user_id=123456789,
            settings=sample_settings,
            user_timezone="Europe/Moscow",
            send_poll_callback=mock_send_poll,
            bot=mock_callback.bot
        )

    @pytest.mark.unit
    @patch('src.api.handlers.poll.poll_response.services')
    @patch('src.api.handlers.poll.poll_response.send_automatic_poll')
    async def test_schedule_next_poll_uses_default_timezone_if_missing(
        self,
        mock_send_poll,
        mock_services_module,
        sample_settings,
        mock_callback
    ):
        """
        Test poll scheduling with missing timezone.

        GIVEN: User data without timezone
        WHEN: _schedule_next_poll() is called
        THEN: Default timezone "Europe/Moscow" is used
        """
        # Arrange
        user_no_tz = {"id": 1, "telegram_id": 123456789}
        mock_services_module.scheduler = MagicMock()
        mock_services_module.scheduler.schedule_poll = AsyncMock()

        # Act
        await _schedule_next_poll(
            telegram_id=123456789,
            settings=sample_settings,
            user=user_no_tz,
            bot=mock_callback.bot
        )

        # Assert: Default timezone used
        call_args = mock_services_module.scheduler.schedule_poll.call_args
        assert call_args[1]["user_timezone"] == "Europe/Moscow"


# ============================================================================
# TEST SUITES - _get_or_create_sleep_category()
# ============================================================================

class TestGetOrCreateSleepCategory:
    """
    Test suite for _get_or_create_sleep_category() helper function.
    """

    @pytest.mark.unit
    @patch('src.api.handlers.poll.poll_response.services')
    async def test_get_or_create_sleep_category_returns_existing_category(
        self,
        mock_services_module
    ):
        """
        Test finding existing sleep category.

        GIVEN: User has existing "Сон" category
        WHEN: _get_or_create_sleep_category() is called
        THEN: Existing category is returned
              AND no new category is created
        """
        # Arrange
        existing_categories = [
            {"id": 1, "name": "Работа", "emoji": "💼"},
            {"id": 2, "name": "Сон", "emoji": "😴"},
            {"id": 3, "name": "Спорт", "emoji": "⚽"}
        ]

        mock_services_module.category = MagicMock()
        mock_services_module.category.get_user_categories = AsyncMock(
            return_value=existing_categories
        )
        mock_services_module.category.create_category = AsyncMock()

        # Act
        result = await _get_or_create_sleep_category(user_id=1)

        # Assert
        assert result["id"] == 2
        assert result["name"] == "Сон"

        # No category created
        mock_services_module.category.create_category.assert_not_called()

    @pytest.mark.unit
    @patch('src.api.handlers.poll.poll_response.services')
    async def test_get_or_create_sleep_category_creates_new_category(
        self,
        mock_services_module
    ):
        """
        Test creating new sleep category when it doesn't exist.

        GIVEN: User has no "Сон" category
        WHEN: _get_or_create_sleep_category() is called
        THEN: New sleep category is created
              AND returned to caller
        """
        # Arrange
        existing_categories = [
            {"id": 1, "name": "Работа", "emoji": "💼"}
        ]

        new_sleep_category = {"id": 2, "name": "Сон", "emoji": "😴"}

        mock_services_module.category = MagicMock()
        mock_services_module.category.get_user_categories = AsyncMock(
            return_value=existing_categories
        )
        mock_services_module.category.create_category = AsyncMock(
            return_value=new_sleep_category
        )

        # Act
        result = await _get_or_create_sleep_category(user_id=1)

        # Assert
        assert result == new_sleep_category

        # Category was created
        mock_services_module.category.create_category.assert_called_once_with(
            user_id=1,
            name="Сон",
            emoji="😴"
        )

    @pytest.mark.unit
    @patch('src.api.handlers.poll.poll_response.services')
    async def test_get_or_create_sleep_category_case_insensitive_search(
        self,
        mock_services_module
    ):
        """
        Test sleep category search is case-insensitive.

        GIVEN: User has category named "СОН" (uppercase)
        WHEN: _get_or_create_sleep_category() is called
        THEN: Existing category is found (case-insensitive match)
        """
        # Arrange
        existing_categories = [
            {"id": 1, "name": "СОН", "emoji": "😴"}  # Uppercase
        ]

        mock_services_module.category = MagicMock()
        mock_services_module.category.get_user_categories = AsyncMock(
            return_value=existing_categories
        )

        # Act
        result = await _get_or_create_sleep_category(user_id=1)

        # Assert: Found despite case difference
        assert result["id"] == 1
        assert result["name"] == "СОН"


# ============================================================================
# TEST SUITES - _calculate_sleep_duration()
# ============================================================================

class TestCalculateSleepDuration:
    """
    Test suite for _calculate_sleep_duration() helper function.
    """

    @pytest.mark.unit
    async def test_calculate_sleep_duration_with_last_poll_time_uses_it(
        self,
        sample_user,
        sample_settings
    ):
        """
        Test duration calculation with last_poll_time.

        GIVEN: User has last_poll_time set
        WHEN: _calculate_sleep_duration() is called
        THEN: start_time = last_poll_time
              AND end_time = now
        """
        # Arrange
        user_with_last_poll = {
            **sample_user,
            "last_poll_time": "2025-11-14T10:00:00+00:00"
        }

        # Act
        with patch('src.api.handlers.poll.poll_response.datetime') as mock_datetime:
            mock_now = datetime(2025, 11, 14, 12, 0, 0, tzinfo=timezone.utc)
            mock_datetime.now.return_value = mock_now
            mock_datetime.fromisoformat = datetime.fromisoformat

            start_time, end_time = await _calculate_sleep_duration(
                user=user_with_last_poll,
                settings=sample_settings
            )

        # Assert
        assert start_time == datetime(2025, 11, 14, 10, 0, 0, tzinfo=timezone.utc)
        assert end_time == mock_now

    @pytest.mark.unit
    @patch('src.api.handlers.poll.poll_response.calculate_poll_start_time')
    async def test_calculate_sleep_duration_without_last_poll_uses_interval(
        self,
        mock_calc_start,
        sample_settings
    ):
        """
        Test duration calculation without last_poll_time.

        GIVEN: User has no last_poll_time
        WHEN: _calculate_sleep_duration() is called
        THEN: calculate_poll_start_time() is used as fallback
        """
        # Arrange
        user_no_last_poll = {
            "id": 1,
            "telegram_id": 123456789,
            "last_poll_time": None
        }

        mock_start_time = datetime(2025, 11, 14, 11, 0, 0, tzinfo=timezone.utc)
        mock_calc_start.return_value = mock_start_time

        # Act
        with patch('src.api.handlers.poll.poll_response.datetime') as mock_datetime:
            mock_now = datetime(2025, 11, 14, 12, 0, 0, tzinfo=timezone.utc)
            mock_datetime.now.return_value = mock_now

            start_time, end_time = await _calculate_sleep_duration(
                user=user_no_last_poll,
                settings=sample_settings
            )

        # Assert: Fallback used
        mock_calc_start.assert_called_once()
        assert start_time == mock_start_time
        assert end_time == mock_now

    @pytest.mark.unit
    async def test_calculate_sleep_duration_caps_at_24_hours(
        self,
        sample_settings
    ):
        """
        Test duration is capped at 24 hours maximum.

        GIVEN: Duration would exceed 24 hours
        WHEN: _calculate_sleep_duration() is called
        THEN: start_time is adjusted to cap at 24h
        """
        # Arrange
        user_long_sleep = {
            "id": 1,
            "telegram_id": 123456789,
            "last_poll_time": "2025-11-12T10:00:00+00:00"  # 2 days ago
        }

        # Act
        with patch('src.api.handlers.poll.poll_response.datetime') as mock_datetime:
            mock_now = datetime(2025, 11, 14, 12, 0, 0, tzinfo=timezone.utc)
            mock_datetime.now.return_value = mock_now
            mock_datetime.fromisoformat = datetime.fromisoformat
            mock_datetime.timedelta = timedelta

            start_time, end_time = await _calculate_sleep_duration(
                user=user_long_sleep,
                settings=sample_settings
            )

        # Assert: Duration is exactly 24 hours
        duration = end_time - start_time
        assert duration.total_seconds() == 24 * 3600  # 24 hours


# ============================================================================
# TEST SUITES - _cancel_poll_activity()
# ============================================================================

class TestCancelPollActivity:
    """
    Test suite for _cancel_poll_activity() helper function.
    """

    @pytest.mark.unit
    @patch('src.api.handlers.poll.poll_response.fsm_timeout_module')
    async def test_cancel_poll_activity_clears_state_and_sends_error(
        self,
        mock_fsm_timeout_module,
        mock_message,
        mock_callback,
        mock_state
    ):
        """
        Test cancelling poll activity (callback version).

        GIVEN: Error occurred during poll activity
        WHEN: _cancel_poll_activity() is called
        THEN: Error message is sent
              AND callback is answered
              AND FSM state is cleared
              AND timeout is cancelled
        """
        # Arrange
        mock_fsm_timeout_service = MagicMock()
        mock_fsm_timeout_service.cancel_timeout = MagicMock()
        mock_fsm_timeout_module.fsm_timeout_service = mock_fsm_timeout_service

        # Act
        await _cancel_poll_activity(
            message=mock_message,
            callback=mock_callback,
            state=mock_state,
            telegram_id=123456789,
            error_text="⚠️ Ошибка"
        )

        # Assert
        mock_message.answer.assert_called_once_with("⚠️ Ошибка")
        mock_callback.answer.assert_called_once()
        mock_state.clear.assert_called_once()
        mock_fsm_timeout_service.cancel_timeout.assert_called_once_with(123456789)


# ============================================================================
# TEST SUITES - _cancel_poll_activity_message()
# ============================================================================

class TestCancelPollActivityMessage:
    """
    Test suite for _cancel_poll_activity_message() helper function.
    """

    @pytest.mark.unit
    @patch('src.api.handlers.poll.poll_response.fsm_timeout_module')
    @patch('src.api.handlers.poll.poll_response.get_main_menu_keyboard')
    async def test_cancel_poll_activity_message_clears_state_and_sends_error(
        self,
        mock_get_keyboard,
        mock_fsm_timeout_module,
        mock_message,
        mock_state
    ):
        """
        Test cancelling poll activity (message version).

        GIVEN: Error occurred during poll activity
        WHEN: _cancel_poll_activity_message() is called
        THEN: Error message with main menu is sent
              AND FSM state is cleared
              AND timeout is cancelled
        """
        # Arrange
        mock_keyboard = MagicMock()
        mock_get_keyboard.return_value = mock_keyboard

        mock_fsm_timeout_service = MagicMock()
        mock_fsm_timeout_service.cancel_timeout = MagicMock()
        mock_fsm_timeout_module.fsm_timeout_service = mock_fsm_timeout_service

        # Act
        await _cancel_poll_activity_message(
            message=mock_message,
            state=mock_state,
            telegram_id=123456789,
            error_text="⚠️ Ошибка"
        )

        # Assert
        mock_message.answer.assert_called_once_with(
            "⚠️ Ошибка",
            reply_markup=mock_keyboard
        )
        mock_state.clear.assert_called_once()
        mock_fsm_timeout_service.cancel_timeout.assert_called_once_with(123456789)

    @pytest.mark.unit
    @patch('src.api.handlers.poll.poll_response.fsm_timeout_module')
    @patch('src.api.handlers.poll.poll_response.get_main_menu_keyboard')
    async def test_cancel_poll_activity_message_without_timeout_service(
        self,
        mock_get_keyboard,
        mock_fsm_timeout_module,
        mock_message,
        mock_state
    ):
        """
        Test cancellation when timeout service is unavailable.

        GIVEN: fsm_timeout_service is None
        WHEN: _cancel_poll_activity_message() is called
        THEN: Proceeds without error (timeout cancellation skipped)
        """
        # Arrange
        mock_get_keyboard.return_value = MagicMock()
        mock_fsm_timeout_module.fsm_timeout_service = None

        # Act: Should not raise
        await _cancel_poll_activity_message(
            message=mock_message,
            state=mock_state,
            telegram_id=123456789,
            error_text="⚠️ Ошибка"
        )

        # Assert
        mock_message.answer.assert_called_once()
        mock_state.clear.assert_called_once()
