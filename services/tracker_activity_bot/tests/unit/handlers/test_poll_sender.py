"""
Unit tests for poll sender functionality.

Tests automatic poll sending, FSM conflict detection, poll postponement,
reminder sending, and message formatting.

Test Coverage:
    - send_automatic_poll: Main poll sending flow (REWRITTEN for Phase 4-6)
    - send_reminder: Unanswered poll reminders
    - send_category_reminder: Category selection reminders (NEW)
    - FSM conflict detection and postponement
    - Poll message formatting
    - Last poll time tracking
    - Error handling: service failures, user/settings not found

Coverage Target: 100% of poll_sender.py
Execution Time: < 1.0 seconds

Author: Testing Team
Date: 2025-11-11 (Updated for Phase 4-6 refactoring)
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, call
from aiogram import Bot
from aiogram.fsm.storage.base import StorageKey

from src.api.handlers.poll.poll_sender import (
    send_automatic_poll,
    send_reminder,
    send_category_reminder,
    _should_postpone_poll,
    _postpone_poll,
    _format_interval_time,
    _update_last_poll_time
)
from src.api.states.activity import ActivityStates
from src.core.constants import POLL_POSTPONE_MINUTES


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def mock_bot():
    """
    Fixture: Mock Telegram Bot.

    Returns:
        AsyncMock: Mocked bot with send_message method
    """
    bot = AsyncMock(spec=Bot)
    bot.send_message = AsyncMock()
    bot.id = 123  # Bot ID for StorageKey
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
    services.activity = AsyncMock()
    services.category = AsyncMock()
    services.scheduler = MagicMock()
    services.scheduler.scheduler = MagicMock()
    services.scheduler.jobs = {}
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
        dict: Settings data with poll interval
    """
    return {
        "id": 1,
        "user_id": 1,
        "poll_interval_minutes": 60,
        "enable_polling": True
    }


@pytest.fixture
def sample_categories():
    """
    Fixture: Sample categories.

    Returns:
        list: Category data
    """
    return [
        {"id": 1, "name": "Work", "emoji": "💼"},
        {"id": 2, "name": "Sport", "emoji": "🏃"},
    ]


@pytest.fixture
def mock_storage():
    """
    Fixture: Mock FSM storage.

    Returns:
        AsyncMock: Mocked FSM storage with state/data operations
    """
    storage = AsyncMock()
    storage.get_state = AsyncMock(return_value=None)
    storage.set_state = AsyncMock()
    storage.update_data = AsyncMock()
    storage.get_data = AsyncMock(return_value={})
    return storage


# ============================================================================
# TEST SUITES
# ============================================================================

class TestSendAutomaticPoll:
    """
    Test suite for send_automatic_poll function.

    Tests new flow: auto-calculate period → show categories immediately
    (no period selection step for automatic polls).
    """

    @pytest.mark.unit
    async def test_send_automatic_poll_success_sends_category_selection(
        self,
        mock_bot,
        mock_services,
        sample_user,
        sample_settings,
        sample_categories,
        mock_storage
    ):
        """
        Test successful automatic poll with category selection.

        GIVEN: Valid user, settings, and categories exist
              AND no FSM conflict
        WHEN: send_automatic_poll is called
        THEN: Period is auto-calculated
              AND state is set to waiting_for_category
              AND category selection message is sent
              AND last poll time is updated
        """
        # Arrange
        mock_services.user.get_by_telegram_id.return_value = sample_user
        mock_services.settings.get_settings.return_value = sample_settings
        mock_services.category.get_user_categories.return_value = sample_categories

        with patch('src.api.handlers.poll.poll_sender.get_service_container', return_value=mock_services):
            with patch('src.api.handlers.poll.poll_sender.get_fsm_storage', return_value=mock_storage):
                with patch('src.api.handlers.poll.poll_sender.calculate_poll_period') as mock_calc:
                    start_time = datetime(2025, 11, 11, 10, 0, tzinfo=timezone.utc)
                    end_time = datetime(2025, 11, 11, 11, 0, tzinfo=timezone.utc)
                    mock_calc.return_value = (start_time, end_time)

                    with patch('src.api.handlers.poll.poll_sender.format_time') as mock_format_time:
                        mock_format_time.side_effect = ["10:00", "11:00"]
                        with patch('src.api.handlers.poll.poll_sender.format_duration') as mock_format_dur:
                            mock_format_dur.return_value = "1 час"

                            # Act
                            await send_automatic_poll(mock_bot, 123456789)

        # Assert: Period calculated
        mock_calc.assert_called_once()

        # Assert: FSM state set to waiting_for_category
        mock_storage.set_state.assert_called_once()
        call_args = mock_storage.set_state.call_args
        assert call_args[0][1] == ActivityStates.waiting_for_category

        # Assert: Period saved to FSM data
        mock_storage.update_data.assert_called_once()
        # Data is passed as second positional argument (after key)
        data_kwargs = mock_storage.update_data.call_args.args[1]
        assert "start_time" in data_kwargs
        assert "end_time" in data_kwargs
        assert data_kwargs["trigger_source"] == "automatic"

        # Assert: Category message sent
        mock_bot.send_message.assert_called_once()
        call_args = mock_bot.send_message.call_args
        assert call_args.kwargs["chat_id"] == 123456789
        assert "категорию" in call_args.kwargs["text"].lower()

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
              AND no message is sent
        """
        # Arrange
        mock_services.user.get_by_telegram_id.return_value = None

        with patch('src.api.handlers.poll.poll_sender.get_service_container', return_value=mock_services):
            with patch('src.api.handlers.poll.poll_sender.logger') as mock_logger:
                # Act
                await send_automatic_poll(mock_bot, 123456789)

        # Assert: Error logged
        mock_logger.error.assert_called_once()
        assert "User not found" in str(mock_logger.error.call_args)

        # Assert: No message sent
        mock_bot.send_message.assert_not_called()

    @pytest.mark.unit
    async def test_send_automatic_poll_with_no_categories_skips_poll(
        self,
        mock_bot,
        mock_services,
        sample_user,
        sample_settings
    ):
        """
        Test poll skipping when user has no categories.

        GIVEN: User exists but has no categories
        WHEN: send_automatic_poll is called
        THEN: Warning is logged
              AND no poll is sent
        """
        # Arrange
        mock_services.user.get_by_telegram_id.return_value = sample_user
        mock_services.settings.get_settings.return_value = sample_settings
        mock_services.category.get_user_categories.return_value = []

        with patch('src.api.handlers.poll.poll_sender.get_service_container', return_value=mock_services):
            with patch('src.api.handlers.poll.poll_sender.logger') as mock_logger:
                # Act
                await send_automatic_poll(mock_bot, 123456789)

        # Assert: Warning logged
        mock_logger.warning.assert_called()
        assert "No categories" in str(mock_logger.warning.call_args)

        # Assert: No message sent
        mock_bot.send_message.assert_not_called()

    @pytest.mark.unit
    async def test_send_automatic_poll_with_fsm_conflict_postpones_poll(
        self,
        mock_bot,
        mock_services,
        sample_user,
        sample_settings,
        mock_storage
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
        mock_storage.get_state.return_value = "ActivityStates:waiting_for_description"

        with patch('src.api.handlers.poll.poll_sender.get_service_container', return_value=mock_services):
            with patch('src.api.handlers.poll.poll_sender.get_fsm_storage', return_value=mock_storage):
                with patch('src.api.handlers.poll.poll_sender._postpone_poll') as mock_postpone:
                    # Act
                    await send_automatic_poll(mock_bot, 123456789)

        # Assert: Poll postponed
        mock_postpone.assert_called_once()

        # Assert: No immediate message sent
        mock_bot.send_message.assert_not_called()

    @pytest.mark.unit
    async def test_send_automatic_poll_stores_settings_for_next_poll(
        self,
        mock_bot,
        mock_services,
        sample_user,
        sample_settings,
        sample_categories,
        mock_storage
    ):
        """
        Test that settings are stored in FSM for scheduling next poll.

        GIVEN: Valid user and settings
        WHEN: send_automatic_poll is called
        THEN: Settings and user_timezone are saved to FSM data
              (needed for scheduling next poll after activity save)
        """
        # Arrange
        mock_services.user.get_by_telegram_id.return_value = sample_user
        mock_services.settings.get_settings.return_value = sample_settings
        mock_services.category.get_user_categories.return_value = sample_categories

        with patch('src.api.handlers.poll.poll_sender.get_service_container', return_value=mock_services):
            with patch('src.api.handlers.poll.poll_sender.get_fsm_storage', return_value=mock_storage):
                with patch('src.api.handlers.poll.poll_sender.calculate_poll_period') as mock_calc:
                    start_time = datetime(2025, 11, 11, 10, 0, tzinfo=timezone.utc)
                    end_time = datetime(2025, 11, 11, 11, 0, tzinfo=timezone.utc)
                    mock_calc.return_value = (start_time, end_time)

                    with patch('src.api.handlers.poll.poll_sender.format_time') as mock_format:
                        mock_format.side_effect = ["10:00", "11:00"]
                        with patch('src.api.handlers.poll.poll_sender.format_duration') as mock_format_dur:
                            mock_format_dur.return_value = "1 час"

                            # Act
                            await send_automatic_poll(mock_bot, 123456789)

        # Assert: Settings stored
        # Data is passed as second positional argument (after key)
        data_kwargs = mock_storage.update_data.call_args.args[1]
        assert "settings" in data_kwargs
        assert data_kwargs["settings"] == sample_settings
        assert data_kwargs["user_timezone"] == "Europe/Moscow"

    @pytest.mark.unit
    async def test_send_automatic_poll_schedules_fsm_timeout(
        self,
        mock_bot,
        mock_services,
        sample_user,
        sample_settings,
        sample_categories,
        mock_storage
    ):
        """
        Test that FSM timeout is scheduled.

        GIVEN: Valid poll setup
        WHEN: send_automatic_poll is called
        THEN: FSM timeout is scheduled for waiting_for_category state
        """
        # Arrange
        mock_services.user.get_by_telegram_id.return_value = sample_user
        mock_services.settings.get_settings.return_value = sample_settings
        mock_services.category.get_user_categories.return_value = sample_categories

        with patch('src.api.handlers.poll.poll_sender.get_service_container', return_value=mock_services):
            with patch('src.api.handlers.poll.poll_sender.get_fsm_storage', return_value=mock_storage):
                with patch('src.api.handlers.poll.poll_sender.calculate_poll_period') as mock_calc:
                    start_time = datetime(2025, 11, 11, 10, 0, tzinfo=timezone.utc)
                    end_time = datetime(2025, 11, 11, 11, 0, tzinfo=timezone.utc)
                    mock_calc.return_value = (start_time, end_time)

                    with patch('src.api.handlers.poll.poll_sender.format_time') as mock_format:
                        mock_format.side_effect = ["10:00", "11:00"]
                        with patch('src.api.handlers.poll.poll_sender.format_duration') as mock_format_dur:
                            mock_format_dur.return_value = "1 час"
                            with patch('src.api.handlers.poll.poll_sender.fsm_timeout_module') as mock_timeout_mod:
                                mock_timeout_mod.fsm_timeout_service = MagicMock()

                                # Act
                                await send_automatic_poll(mock_bot, 123456789)

        # Assert: Timeout scheduled
        mock_timeout_mod.fsm_timeout_service.schedule_timeout.assert_called_once()
        call_kwargs = mock_timeout_mod.fsm_timeout_service.schedule_timeout.call_args.kwargs
        assert call_kwargs["user_id"] == 123456789
        assert call_kwargs["state"] == ActivityStates.waiting_for_category

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

        with patch('src.api.handlers.poll.poll_sender.get_service_container', return_value=mock_services):
            with patch('src.api.handlers.poll.poll_sender.logger') as mock_logger:
                # Act
                await send_automatic_poll(mock_bot, 123456789)

        # Assert: Error logged
        mock_logger.error.assert_called()

        # Assert: No message sent
        mock_bot.send_message.assert_not_called()


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
        assert "напомнить" in call_args.kwargs["text"].lower()

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


class TestSendCategoryReminder:
    """
    Test suite for send_category_reminder function (NEW).

    Tests category selection reminder for poll activity flow.
    """

    @pytest.mark.unit
    async def test_send_category_reminder_success_shows_categories(
        self,
        mock_bot,
        mock_services,
        sample_user,
        sample_settings,
        sample_categories
    ):
        """
        Test successful category reminder with categories.

        GIVEN: User has categories
        WHEN: send_category_reminder is called
        THEN: Category selection message is sent
              AND period is recalculated
        """
        # Arrange
        mock_services.user.get_by_telegram_id.return_value = sample_user
        mock_services.user_settings.get_by_user_id.return_value = sample_settings
        mock_services.category.get_user_categories.return_value = sample_categories

        with patch('src.api.handlers.poll.poll_sender.get_service_container', return_value=mock_services):
            with patch('src.api.handlers.poll.poll_sender.calculate_poll_period') as mock_calc:
                start_time = datetime(2025, 11, 11, 10, 0, tzinfo=timezone.utc)
                end_time = datetime(2025, 11, 11, 11, 0, tzinfo=timezone.utc)
                mock_calc.return_value = (start_time, end_time)

                with patch('src.api.handlers.poll.poll_sender.format_time') as mock_format:
                    mock_format.side_effect = ["10:00", "11:00"]
                    with patch('src.api.handlers.poll.poll_sender.format_duration') as mock_format_dur:
                        mock_format_dur.return_value = "1 час"

                        # Act
                        await send_category_reminder(mock_bot, 123456789)

        # Assert: Message sent
        mock_bot.send_message.assert_called_once()
        call_args = mock_bot.send_message.call_args
        assert call_args.kwargs["chat_id"] == 123456789
        assert "Напоминание" in call_args.kwargs["text"]

    @pytest.mark.unit
    async def test_send_category_reminder_without_categories_shows_error(
        self,
        mock_bot,
        mock_services,
        sample_user
    ):
        """
        Test reminder when user has no categories.

        GIVEN: User has no categories
        WHEN: send_category_reminder is called
        THEN: Error message is sent
        """
        # Arrange
        mock_services.user.get_by_telegram_id.return_value = sample_user
        mock_services.category.get_user_categories.return_value = []

        with patch('src.api.handlers.poll.poll_sender.get_service_container', return_value=mock_services):
            # Act
            await send_category_reminder(mock_bot, 123456789)

        # Assert: Error message sent
        mock_bot.send_message.assert_called_once()
        call_args = mock_bot.send_message.call_args
        assert "нет категорий" in call_args.kwargs["text"].lower()

    @pytest.mark.unit
    async def test_send_category_reminder_with_user_not_found_logs_error(
        self,
        mock_bot,
        mock_services
    ):
        """
        Test reminder when user not found.

        GIVEN: User does not exist
        WHEN: send_category_reminder is called
        THEN: Error is logged
              AND no message is sent
        """
        # Arrange
        mock_services.user.get_by_telegram_id.return_value = None

        with patch('src.api.handlers.poll.poll_sender.get_service_container', return_value=mock_services):
            with patch('src.api.handlers.poll.poll_sender.logger') as mock_logger:
                # Act
                await send_category_reminder(mock_bot, 123456789)

        # Assert: Error logged
        mock_logger.error.assert_called()

        # Assert: No message sent
        mock_bot.send_message.assert_not_called()

    @pytest.mark.unit
    async def test_send_category_reminder_handles_service_error_gracefully(
        self,
        mock_bot,
        mock_services
    ):
        """
        Test error handling in category reminder.

        GIVEN: Service raises exception
        WHEN: send_category_reminder is called
        THEN: Error is caught and logged
        """
        # Arrange
        mock_services.user.get_by_telegram_id.side_effect = Exception("Database error")

        with patch('src.api.handlers.poll.poll_sender.get_service_container', return_value=mock_services):
            with patch('src.api.handlers.poll.poll_sender.logger') as mock_logger:
                # Act
                await send_category_reminder(mock_bot, 123456789)

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
        mock_storage
    ):
        """
        Test postponement when user has active FSM state.

        GIVEN: User is in FSM state "ActivityStates:waiting_for_description"
        WHEN: _should_postpone_poll is called
        THEN: Returns True (postpone)
        """
        # Arrange
        mock_storage.get_state.return_value = "ActivityStates:waiting_for_description"

        with patch('src.api.handlers.poll.poll_sender.get_fsm_storage', return_value=mock_storage):
            # Act
            result = await _should_postpone_poll(mock_bot, 123456789)

        # Assert
        assert result is True

    @pytest.mark.unit
    async def test_should_postpone_poll_with_no_state_returns_false(
        self,
        mock_bot,
        mock_storage
    ):
        """
        Test no postponement when user has no FSM state.

        GIVEN: User has no active FSM state (None)
        WHEN: _should_postpone_poll is called
        THEN: Returns False (don't postpone)
        """
        # Arrange
        mock_storage.get_state.return_value = None

        with patch('src.api.handlers.poll.poll_sender.get_fsm_storage', return_value=mock_storage):
            # Act
            result = await _should_postpone_poll(mock_bot, 123456789)

        # Assert
        assert result is False

    @pytest.mark.unit
    async def test_should_postpone_poll_with_error_returns_false_as_fallback(
        self,
        mock_bot,
        mock_storage
    ):
        """
        Test fallback behavior when FSM check fails.

        GIVEN: FSM storage raises exception
        WHEN: _should_postpone_poll is called
        THEN: Returns False (fail-safe: send poll anyway)
        """
        # Arrange
        mock_storage.get_state.side_effect = Exception("FSM error")

        with patch('src.api.handlers.poll.poll_sender.get_fsm_storage', return_value=mock_storage):
            with patch('src.api.handlers.poll.poll_sender.logger'):
                # Act
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
        mock_services
    ):
        """
        Test scheduling postponed poll.

        GIVEN: Valid services with scheduler
        WHEN: _postpone_poll is called
        THEN: New job is scheduled after POLL_POSTPONE_MINUTES
        """
        # Arrange
        mock_job = MagicMock()
        mock_job.id = "poll_postponed_123456789_123"
        mock_services.scheduler.scheduler.add_job.return_value = mock_job

        # Act
        await _postpone_poll(mock_bot, 123456789, mock_services)

        # Assert: Job added
        mock_services.scheduler.scheduler.add_job.assert_called_once()

        # Assert: Job ID stored
        assert 123456789 in mock_services.scheduler.jobs

    @pytest.mark.unit
    async def test_postpone_poll_removes_existing_job_first(
        self,
        mock_bot,
        mock_services
    ):
        """
        Test removal of existing job before scheduling new one.

        GIVEN: Existing scheduled job for user
        WHEN: _postpone_poll is called
        THEN: Old job is removed
              AND new job is scheduled
        """
        # Arrange
        mock_services.scheduler.jobs[123456789] = "old_job_id"
        mock_job = MagicMock()
        mock_job.id = "new_job_id"
        mock_services.scheduler.scheduler.add_job.return_value = mock_job

        # Act
        await _postpone_poll(mock_bot, 123456789, mock_services)

        # Assert: Old job removed
        mock_services.scheduler.scheduler.remove_job.assert_called_once_with("old_job_id")

        # Assert: New job added
        mock_services.scheduler.scheduler.add_job.assert_called_once()

    @pytest.mark.unit
    async def test_postpone_poll_handles_remove_error_gracefully(
        self,
        mock_bot,
        mock_services
    ):
        """
        Test graceful handling when job removal fails.

        GIVEN: Existing job that cannot be removed (already executed)
        WHEN: _postpone_poll is called
        THEN: Error is caught
              AND new job is still scheduled
        """
        # Arrange
        mock_services.scheduler.jobs[123456789] = "old_job_id"
        mock_services.scheduler.scheduler.remove_job.side_effect = Exception("Job not found")
        mock_job = MagicMock()
        mock_job.id = "new_job_id"
        mock_services.scheduler.scheduler.add_job.return_value = mock_job

        # Act
        await _postpone_poll(mock_bot, 123456789, mock_services)

        # Assert: New job still added
        mock_services.scheduler.scheduler.add_job.assert_called_once()


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
        THEN: Returns "2ч"
        """
        # Act
        result = _format_interval_time(120)

        # Assert
        assert "2ч" in result

    @pytest.mark.unit
    def test_format_interval_time_with_only_minutes(self):
        """
        Test formatting with only minutes.

        GIVEN: interval_minutes = 45
        WHEN: _format_interval_time is called
        THEN: Returns "45м"
        """
        # Act
        result = _format_interval_time(45)

        # Assert
        assert "45м" in result

    @pytest.mark.unit
    def test_format_interval_time_with_hours_and_minutes(self):
        """
        Test formatting with both hours and minutes.

        GIVEN: interval_minutes = 150 (2 hours 30 minutes)
        WHEN: _format_interval_time is called
        THEN: Returns "2ч 30м"
        """
        # Act
        result = _format_interval_time(150)

        # Assert
        assert "2ч" in result
        assert "30м" in result

    @pytest.mark.unit
    def test_format_interval_time_with_single_hour(self):
        """
        Test formatting with 1 hour.

        GIVEN: interval_minutes = 60
        WHEN: _format_interval_time is called
        THEN: Returns "1ч"
        """
        # Act
        result = _format_interval_time(60)

        # Assert
        assert "1ч" in result


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

        GIVEN: Valid services and user
        WHEN: _update_last_poll_time is called
        THEN: User service updates last_poll_time with current UTC time
        """
        # Act
        await _update_last_poll_time(mock_services, sample_user, 123456789)

        # Assert: Service called
        mock_services.user.update_last_poll_time.assert_called_once()
        call_args = mock_services.user.update_last_poll_time.call_args

        # Verify user_id (internal ID, not telegram ID)
        assert call_args[0][0] == 1  # sample_user["id"]

        # Verify datetime is recent UTC time
        poll_time = call_args[0][1]
        assert poll_time.tzinfo == timezone.utc
        assert (datetime.now(timezone.utc) - poll_time).total_seconds() < 2

    @pytest.mark.unit
    async def test_update_last_poll_time_with_error_handles_gracefully(
        self,
        mock_services,
        sample_user
    ):
        """
        Test error handling when update fails.

        GIVEN: Service raises exception during update
        WHEN: _update_last_poll_time is called
        THEN: Exception is caught and logged
        """
        # Arrange
        mock_services.user.update_last_poll_time.side_effect = Exception("Database error")

        with patch('src.api.handlers.poll.poll_sender.logger') as mock_logger:
            # Act
            await _update_last_poll_time(mock_services, sample_user, 123456789)

        # Assert: Error logged
        mock_logger.warning.assert_called()
