"""
Unit tests for poll sender functionality.

Tests automatic poll sending, FSM conflict detection, poll postponement,
reminder sending, and message formatting.

Test Coverage:
    - send_automatic_poll: Main poll sending flow
    - send_reminder: Unanswered poll reminders
    - FSM conflict detection and postponement
    - Poll message formatting
    - Last poll time tracking
    - Error handling: service failures, user/settings not found

Coverage Target: 100% of poll_sender.py
Execution Time: < 0.5 seconds

Author: Testing Team
Date: 2025-11-07
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, call
from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey

from src.api.handlers.poll.poll_sender import (
    send_automatic_poll,
    send_reminder,
    _should_postpone_poll,
    _postpone_poll,
    _send_poll_message,
    _format_interval_time,
    _update_last_poll_time,
    POLL_POSTPONE_MINUTES
)


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def mock_bot():
    """
    Fixture: Mock Telegram Bot.

    Returns:
        AsyncMock: Mocked bot with send_poll method
    """
    bot = AsyncMock(spec=Bot)
    bot.send_poll = AsyncMock(return_value=MagicMock(message_id=12345))
    bot.send_message = AsyncMock()
    return bot


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
    services.scheduler = MagicMock()
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
        "timezone": "Europe/Moscow"
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
        "is_reminder_enabled": True
    }


@pytest.fixture
def mock_fsm_context():
    """
    Fixture: Mock FSM context.

    Returns:
        AsyncMock: Mocked FSM context
    """
    context = AsyncMock(spec=FSMContext)
    context.get_state = AsyncMock()
    return context


# ============================================================================
# TEST SUITES
# ============================================================================

class TestSendAutomaticPoll:
    """
    Test suite for send_automatic_poll function.

    Tests main poll sending flow with various scenarios.
    """

    @pytest.mark.unit
    async def test_send_automatic_poll_success_sends_poll_to_user(
        self,
        mock_bot,
        mock_services,
        sample_user,
        sample_settings,
        mock_fsm_context
    ):
        """
        Test successful automatic poll sending.

        GIVEN: Valid user and settings exist
              AND no FSM conflict
        WHEN: send_automatic_poll is called
        THEN: Poll is sent to user
              AND last poll time is updated
        """
        # Arrange
        mock_services.user.get_by_telegram_id.return_value = sample_user
        mock_services.settings.get_settings.return_value = sample_settings
        mock_fsm_context.get_state.return_value = None  # No active state

        # Act
        with patch('src.api.handlers.poll.poll_sender.get_services', return_value=mock_services):
            with patch('src.api.handlers.poll.poll_sender.FSMContext', return_value=mock_fsm_context):
                with patch('src.api.handlers.poll.poll_sender._update_last_poll_time') as mock_update:
                    await send_automatic_poll(mock_bot, 123456789)

        # Assert: Poll sent
        mock_bot.send_poll.assert_called_once()
        call_args = mock_bot.send_poll.call_args
        assert call_args.kwargs["chat_id"] == 123456789
        assert "Чем ты сейчас занимаешься?" in call_args.kwargs["question"]

        # Assert: Last poll time updated
        mock_update.assert_called_once()

    @pytest.mark.unit
    async def test_send_automatic_poll_with_user_not_found_logs_error(
        self,
        mock_bot,
        mock_services
    ):
        """
        Test poll sending when user does not exist.

        GIVEN: User does not exist in database
        WHEN: send_automatic_poll is called
        THEN: Error is logged
              AND no poll is sent
        """
        # Arrange
        mock_services.user.get_by_telegram_id.return_value = None

        # Act
        with patch('src.api.handlers.poll.poll_sender.get_services', return_value=mock_services):
            with patch('src.api.handlers.poll.poll_sender.logger') as mock_logger:
                await send_automatic_poll(mock_bot, 123456789)

        # Assert: Error logged
        mock_logger.error.assert_called_once()
        assert "User not found" in str(mock_logger.error.call_args)

        # Assert: No poll sent
        mock_bot.send_poll.assert_not_called()

    @pytest.mark.unit
    async def test_send_automatic_poll_with_settings_not_found_logs_error(
        self,
        mock_bot,
        mock_services,
        sample_user
    ):
        """
        Test poll sending when settings do not exist.

        GIVEN: User exists but settings do not
        WHEN: send_automatic_poll is called
        THEN: Error is logged
              AND no poll is sent
        """
        # Arrange
        mock_services.user.get_by_telegram_id.return_value = sample_user
        mock_services.settings.get_settings.return_value = None

        # Act
        with patch('src.api.handlers.poll.poll_sender.get_services', return_value=mock_services):
            with patch('src.api.handlers.poll.poll_sender.logger') as mock_logger:
                await send_automatic_poll(mock_bot, 123456789)

        # Assert: Error logged
        mock_logger.error.assert_called_once()
        assert "Settings not found" in str(mock_logger.error.call_args)

        # Assert: No poll sent
        mock_bot.send_poll.assert_not_called()

    @pytest.mark.unit
    async def test_send_automatic_poll_with_fsm_conflict_postpones_poll(
        self,
        mock_bot,
        mock_services,
        sample_user,
        sample_settings,
        mock_fsm_context
    ):
        """
        Test poll postponement when FSM conflict detected.

        GIVEN: User is in active FSM state (e.g., creating activity)
        WHEN: send_automatic_poll is called
        THEN: Poll is postponed by POLL_POSTPONE_MINUTES
              AND no poll is sent immediately
        """
        # Arrange
        mock_services.user.get_by_telegram_id.return_value = sample_user
        mock_services.settings.get_settings.return_value = sample_settings
        mock_fsm_context.get_state.return_value = "ActivityForm:waiting_for_description"

        # Act
        with patch('src.api.handlers.poll.poll_sender.get_services', return_value=mock_services):
            with patch('src.api.handlers.poll.poll_sender.FSMContext', return_value=mock_fsm_context):
                with patch('src.api.handlers.poll.poll_sender._postpone_poll') as mock_postpone:
                    with patch('src.api.handlers.poll.poll_sender.logger') as mock_logger:
                        await send_automatic_poll(mock_bot, 123456789)

        # Assert: Poll postponed
        mock_postpone.assert_called_once()
        assert mock_postpone.call_args.kwargs["user_id"] == 123456789

        # Assert: Log message
        mock_logger.info.assert_called()
        assert "postponing poll" in str(mock_logger.info.call_args).lower()

        # Assert: No immediate poll sent
        mock_bot.send_poll.assert_not_called()

    @pytest.mark.unit
    async def test_send_automatic_poll_includes_interval_in_message(
        self,
        mock_bot,
        mock_services,
        sample_user,
        sample_settings,
        mock_fsm_context
    ):
        """
        Test poll message includes interval time.

        GIVEN: Settings with weekday_interval_minutes = 120
        WHEN: send_automatic_poll is called
        THEN: Poll question includes "каждые 2 часа"
        """
        # Arrange
        mock_services.user.get_by_telegram_id.return_value = sample_user
        mock_services.settings.get_settings.return_value = sample_settings
        mock_fsm_context.get_state.return_value = None

        # Act
        with patch('src.api.handlers.poll.poll_sender.get_services', return_value=mock_services):
            with patch('src.api.handlers.poll.poll_sender.FSMContext', return_value=mock_fsm_context):
                with patch('src.api.handlers.poll.poll_sender._update_last_poll_time'):
                    await send_automatic_poll(mock_bot, 123456789)

        # Assert: Message contains interval
        call_args = mock_bot.send_poll.call_args
        question = call_args.kwargs["question"]
        assert "2 часа" in question or "120" in question

    @pytest.mark.unit
    async def test_send_automatic_poll_with_service_error_handles_gracefully(
        self,
        mock_bot,
        mock_services
    ):
        """
        Test error handling when service raises exception.

        GIVEN: Service raises exception during user lookup
        WHEN: send_automatic_poll is called
        THEN: Exception is caught and logged
              AND no poll is sent
        """
        # Arrange
        mock_services.user.get_by_telegram_id.side_effect = Exception("Database error")

        # Act
        with patch('src.api.handlers.poll.poll_sender.get_services', return_value=mock_services):
            with patch('src.api.handlers.poll.poll_sender.logger') as mock_logger:
                await send_automatic_poll(mock_bot, 123456789)

        # Assert: Error logged
        mock_logger.error.assert_called()

        # Assert: No poll sent
        mock_bot.send_poll.assert_not_called()


class TestSendReminder:
    """
    Test suite for send_reminder function.

    Tests reminder sending for unanswered polls.
    """

    @pytest.mark.unit
    async def test_send_reminder_success_sends_message_to_user(
        self,
        mock_bot
    ):
        """
        Test successful reminder sending.

        GIVEN: Valid user_id
        WHEN: send_reminder is called
        THEN: Reminder message is sent to user
        """
        # Act
        with patch('src.api.handlers.poll.poll_sender.logger'):
            await send_reminder(mock_bot, 123456789)

        # Assert: Message sent
        mock_bot.send_message.assert_called_once()
        call_args = mock_bot.send_message.call_args
        assert call_args.kwargs["chat_id"] == 123456789
        assert "не забудь ответить" in call_args.kwargs["text"].lower()

    @pytest.mark.unit
    async def test_send_reminder_with_bot_error_handles_gracefully(
        self,
        mock_bot
    ):
        """
        Test error handling when bot fails to send message.

        GIVEN: Bot raises exception when sending message
        WHEN: send_reminder is called
        THEN: Exception is caught and logged
        """
        # Arrange
        mock_bot.send_message.side_effect = Exception("Network error")

        # Act
        with patch('src.api.handlers.poll.poll_sender.logger') as mock_logger:
            await send_reminder(mock_bot, 123456789)

        # Assert: Error logged
        mock_logger.error.assert_called()


class TestShouldPostponePoll:
    """
    Test suite for _should_postpone_poll function.

    Tests FSM conflict detection logic.
    """

    @pytest.mark.unit
    async def test_should_postpone_poll_with_active_state_returns_true(
        self,
        mock_bot,
        mock_fsm_context
    ):
        """
        Test postponement when user has active FSM state.

        GIVEN: User is in FSM state "ActivityForm:waiting_for_description"
        WHEN: _should_postpone_poll is called
        THEN: Returns True (postpone)
        """
        # Arrange
        mock_fsm_context.get_state.return_value = "ActivityForm:waiting_for_description"

        # Act
        with patch('src.api.handlers.poll.poll_sender.FSMContext', return_value=mock_fsm_context):
            result = await _should_postpone_poll(mock_bot, 123456789)

        # Assert
        assert result is True

    @pytest.mark.unit
    async def test_should_postpone_poll_with_no_state_returns_false(
        self,
        mock_bot,
        mock_fsm_context
    ):
        """
        Test no postponement when user has no FSM state.

        GIVEN: User has no active FSM state (None)
        WHEN: _should_postpone_poll is called
        THEN: Returns False (don't postpone)
        """
        # Arrange
        mock_fsm_context.get_state.return_value = None

        # Act
        with patch('src.api.handlers.poll.poll_sender.FSMContext', return_value=mock_fsm_context):
            result = await _should_postpone_poll(mock_bot, 123456789)

        # Assert
        assert result is False

    @pytest.mark.unit
    async def test_should_postpone_poll_with_error_returns_false_as_fallback(
        self,
        mock_bot,
        mock_fsm_context
    ):
        """
        Test fallback behavior when FSM check fails.

        GIVEN: FSM context raises exception
        WHEN: _should_postpone_poll is called
        THEN: Returns False (fail-safe: send poll anyway)
        """
        # Arrange
        mock_fsm_context.get_state.side_effect = Exception("FSM error")

        # Act
        with patch('src.api.handlers.poll.poll_sender.FSMContext', return_value=mock_fsm_context):
            with patch('src.api.handlers.poll.poll_sender.logger'):
                result = await _should_postpone_poll(mock_bot, 123456789)

        # Assert: Fail-safe returns False
        assert result is False


class TestPostponePoll:
    """
    Test suite for _postpone_poll function.

    Tests poll postponement scheduling logic.
    """

    @pytest.mark.unit
    async def test_postpone_poll_schedules_new_job(
        self,
        mock_bot,
        mock_services,
        sample_user,
        sample_settings
    ):
        """
        Test scheduling postponed poll.

        GIVEN: Valid user and settings
        WHEN: _postpone_poll is called
        THEN: New job is scheduled after POLL_POSTPONE_MINUTES
        """
        # Arrange
        mock_services.user.get_by_telegram_id.return_value = sample_user
        mock_services.settings.get_settings.return_value = sample_settings
        mock_services.scheduler.add_job = MagicMock()

        # Act
        with patch('src.api.handlers.poll.poll_sender.get_services', return_value=mock_services):
            await _postpone_poll(
                mock_bot,
                user_id=123456789,
                scheduler=mock_services.scheduler,
                user_timezone="Europe/Moscow"
            )

        # Assert: Job added
        mock_services.scheduler.add_job.assert_called_once()
        call_args = mock_services.scheduler.add_job.call_args

        # Verify job parameters
        assert call_args[0][0].__name__ == "send_automatic_poll"
        assert "trigger" in call_args[1]

    @pytest.mark.unit
    async def test_postpone_poll_removes_existing_job_first(
        self,
        mock_bot,
        mock_services,
        sample_user,
        sample_settings
    ):
        """
        Test removal of existing job before scheduling new one.

        GIVEN: Existing scheduled job for user
        WHEN: _postpone_poll is called
        THEN: Old job is removed
              AND new job is scheduled
        """
        # Arrange
        mock_services.user.get_by_telegram_id.return_value = sample_user
        mock_services.settings.get_settings.return_value = sample_settings
        mock_services.scheduler.remove_job = MagicMock()
        mock_services.scheduler.add_job = MagicMock()

        # Act
        with patch('src.api.handlers.poll.poll_sender.get_services', return_value=mock_services):
            await _postpone_poll(
                mock_bot,
                user_id=123456789,
                scheduler=mock_services.scheduler,
                user_timezone="Europe/Moscow"
            )

        # Assert: Old job removed
        mock_services.scheduler.remove_job.assert_called()
        job_id = mock_services.scheduler.remove_job.call_args[0][0]
        assert "poll_123456789" in job_id or str(123456789) in job_id


class TestFormatIntervalTime:
    """
    Test suite for _format_interval_time function.

    Tests time interval formatting logic.
    """

    @pytest.mark.unit
    def test_format_interval_time_with_only_hours(self):
        """
        Test formatting with exact hours.

        GIVEN: interval_minutes = 120 (2 hours)
        WHEN: _format_interval_time is called
        THEN: Returns "2 часа"
        """
        # Act
        result = _format_interval_time(120)

        # Assert
        assert "2 часа" in result or "2 ч" in result

    @pytest.mark.unit
    def test_format_interval_time_with_only_minutes(self):
        """
        Test formatting with only minutes.

        GIVEN: interval_minutes = 45
        WHEN: _format_interval_time is called
        THEN: Returns "45 минут"
        """
        # Act
        result = _format_interval_time(45)

        # Assert
        assert "45" in result
        assert "минут" in result or "мин" in result

    @pytest.mark.unit
    def test_format_interval_time_with_hours_and_minutes(self):
        """
        Test formatting with both hours and minutes.

        GIVEN: interval_minutes = 150 (2 hours 30 minutes)
        WHEN: _format_interval_time is called
        THEN: Returns "2 часа 30 минут"
        """
        # Act
        result = _format_interval_time(150)

        # Assert
        assert "2" in result
        assert "30" in result

    @pytest.mark.unit
    def test_format_interval_time_with_single_hour(self):
        """
        Test formatting with 1 hour.

        GIVEN: interval_minutes = 60
        WHEN: _format_interval_time is called
        THEN: Returns "1 час"
        """
        # Act
        result = _format_interval_time(60)

        # Assert
        assert "1" in result
        assert "час" in result


class TestUpdateLastPollTime:
    """
    Test suite for _update_last_poll_time function.

    Tests last poll time tracking.
    """

    @pytest.mark.unit
    async def test_update_last_poll_time_success_updates_user(
        self,
        mock_services,
        sample_user
    ):
        """
        Test successful last poll time update.

        GIVEN: Valid user_id
        WHEN: _update_last_poll_time is called
        THEN: User service updates last_poll_time with current UTC time
        """
        # Arrange
        mock_services.user.update_last_poll_time.return_value = sample_user

        # Act
        with patch('src.api.handlers.poll.poll_sender.get_services', return_value=mock_services):
            await _update_last_poll_time(123456789)

        # Assert: Service called
        mock_services.user.update_last_poll_time.assert_called_once()
        call_args = mock_services.user.update_last_poll_time.call_args

        # Verify user_id
        assert call_args[0][0] == 123456789

        # Verify datetime is recent UTC time
        poll_time = call_args[0][1]
        assert poll_time.tzinfo == timezone.utc
        assert (datetime.now(timezone.utc) - poll_time).total_seconds() < 2

    @pytest.mark.unit
    async def test_update_last_poll_time_with_error_handles_gracefully(
        self,
        mock_services
    ):
        """
        Test error handling when update fails.

        GIVEN: Service raises exception during update
        WHEN: _update_last_poll_time is called
        THEN: Exception is caught and logged
        """
        # Arrange
        mock_services.user.update_last_poll_time.side_effect = Exception("Database error")

        # Act
        with patch('src.api.handlers.poll.poll_sender.get_services', return_value=mock_services):
            with patch('src.api.handlers.poll.poll_sender.logger') as mock_logger:
                await _update_last_poll_time(123456789)

        # Assert: Error logged
        mock_logger.error.assert_called()
