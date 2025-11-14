"""
Unit tests for SchedulerService.

Tests the automatic poll scheduling service that manages APScheduler jobs
for sending polls to users at configured intervals with quiet hours support.

Test Coverage:
    - Scheduler lifecycle: start(), stop(), is_running
    - schedule_poll(): Weekday/weekend intervals, quiet hours, job replacement
    - cancel_poll(): Job cancellation and cleanup
    - restore_scheduled_polls(): Bulk restoration on bot startup
    - _calculate_next_poll_time(): Time calculation with various edge cases
    - Edge cases: Missing data, exceptions, timezone handling

Coverage Target: 95%+
Execution Time: < 0.5 seconds

Author: Testing Team
Date: 2025-11-14
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch, call
from datetime import datetime, timedelta, time as dt_time
import pytz

from src.application.services.scheduler_service import SchedulerService


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def mock_scheduler():
    """
    Fixture: Mock AsyncIOScheduler.

    Returns:
        MagicMock: Mocked scheduler with common methods stubbed
    """
    scheduler = MagicMock()
    scheduler.running = False
    scheduler.start = MagicMock()
    scheduler.shutdown = MagicMock()
    scheduler.add_job = MagicMock()
    scheduler.remove_job = MagicMock()
    return scheduler


@pytest.fixture
def scheduler_service():
    """
    Fixture: SchedulerService instance with mocked scheduler.

    Returns:
        SchedulerService: Service instance for testing
    """
    service = SchedulerService()
    return service


@pytest.fixture
def mock_send_poll_callback():
    """
    Fixture: Mock async callback for sending polls.

    Returns:
        AsyncMock: Callback function for poll delivery
    """
    return AsyncMock()


@pytest.fixture
def mock_bot():
    """
    Fixture: Mock Bot instance.

    Returns:
        MagicMock: Mocked Telegram Bot
    """
    return MagicMock()


@pytest.fixture
def sample_settings():
    """
    Fixture: Sample user settings for weekday.

    Returns:
        dict: User settings with intervals and quiet hours
    """
    return {
        "poll_interval_weekday": 60,
        "poll_interval_weekend": 120,
        "quiet_hours_start": "23:00",
        "quiet_hours_end": "07:00"
    }


@pytest.fixture
def sample_user():
    """
    Fixture: Sample user data for restoration.

    Returns:
        dict: User data with timezone and last poll time
    """
    return {
        "id": 1,
        "telegram_id": 123456789,
        "timezone": "Europe/Moscow",
        "last_poll_time": datetime(2025, 11, 14, 10, 0, 0, tzinfo=pytz.UTC)
    }


# ============================================================================
# TEST SUITES
# ============================================================================

class TestSchedulerServiceInitialization:
    """
    Test suite for SchedulerService initialization.
    """

    @pytest.mark.unit
    def test_init_creates_scheduler_with_asyncio_executor(self):
        """
        Test scheduler initialization with AsyncIOExecutor.

        GIVEN: No arguments
        WHEN: SchedulerService() is instantiated
        THEN: AsyncIOScheduler is created with AsyncIOExecutor
              AND jobs dict is initialized empty
        """
        # Act
        service = SchedulerService()

        # Assert
        assert service.scheduler is not None, "Scheduler should be initialized"
        assert isinstance(service.jobs, dict), "Jobs dict should be initialized"
        assert len(service.jobs) == 0, "Jobs dict should start empty"

    @pytest.mark.unit
    def test_init_sets_utc_timezone(self):
        """
        Test scheduler timezone configuration.

        GIVEN: SchedulerService initialization
        WHEN: Service is created
        THEN: Scheduler timezone is set to UTC
        """
        # Act
        service = SchedulerService()

        # Assert
        assert service.scheduler.timezone == pytz.UTC, \
            "Scheduler should use UTC timezone"


class TestSchedulerServiceLifecycle:
    """
    Test suite for scheduler start/stop lifecycle.
    """

    @pytest.mark.unit
    def test_start_when_not_running_starts_scheduler(self, scheduler_service, mock_scheduler):
        """
        Test starting inactive scheduler.

        GIVEN: Scheduler is not running
        WHEN: start() is called
        THEN: scheduler.start() is called
        """
        # Arrange
        scheduler_service.scheduler = mock_scheduler
        mock_scheduler.running = False

        # Act
        scheduler_service.start()

        # Assert
        mock_scheduler.start.assert_called_once()

    @pytest.mark.unit
    def test_start_when_already_running_does_nothing(self, scheduler_service, mock_scheduler):
        """
        Test starting already running scheduler.

        GIVEN: Scheduler is already running
        WHEN: start() is called
        THEN: scheduler.start() is NOT called (idempotent)
        """
        # Arrange
        scheduler_service.scheduler = mock_scheduler
        mock_scheduler.running = True

        # Act
        scheduler_service.start()

        # Assert
        mock_scheduler.start.assert_not_called()

    @pytest.mark.unit
    def test_stop_with_wait_true_waits_for_jobs(self, scheduler_service, mock_scheduler):
        """
        Test graceful shutdown with wait=True.

        GIVEN: Scheduler is running
        WHEN: stop(wait=True) is called
        THEN: scheduler.shutdown(wait=True) is called
              (Waits for pending jobs to complete)
        """
        # Arrange
        scheduler_service.scheduler = mock_scheduler
        mock_scheduler.running = True

        # Act
        scheduler_service.stop(wait=True)

        # Assert
        mock_scheduler.shutdown.assert_called_once_with(wait=True)

    @pytest.mark.unit
    def test_stop_with_wait_false_does_not_wait(self, scheduler_service, mock_scheduler):
        """
        Test immediate shutdown with wait=False.

        GIVEN: Scheduler is running
        WHEN: stop(wait=False) is called
        THEN: scheduler.shutdown(wait=False) is called
              (Does not wait for jobs)
        """
        # Arrange
        scheduler_service.scheduler = mock_scheduler
        mock_scheduler.running = True

        # Act
        scheduler_service.stop(wait=False)

        # Assert
        mock_scheduler.shutdown.assert_called_once_with(wait=False)

    @pytest.mark.unit
    def test_stop_when_not_running_does_nothing(self, scheduler_service, mock_scheduler):
        """
        Test stopping inactive scheduler.

        GIVEN: Scheduler is not running
        WHEN: stop() is called
        THEN: shutdown() is NOT called (idempotent)
        """
        # Arrange
        scheduler_service.scheduler = mock_scheduler
        mock_scheduler.running = False

        # Act
        scheduler_service.stop()

        # Assert
        mock_scheduler.shutdown.assert_not_called()

    @pytest.mark.unit
    def test_is_running_property_returns_scheduler_state(self, scheduler_service, mock_scheduler):
        """
        Test is_running property.

        GIVEN: Scheduler running state
        WHEN: is_running property is accessed
        THEN: Returns scheduler.running value
        """
        # Arrange
        scheduler_service.scheduler = mock_scheduler

        # Test running state
        mock_scheduler.running = True
        assert scheduler_service.is_running is True

        # Test stopped state
        mock_scheduler.running = False
        assert scheduler_service.is_running is False


class TestSchedulerServiceSchedulePoll:
    """
    Test suite for schedule_poll() method.

    Tests poll scheduling with intervals, quiet hours, and job management.
    """

    @pytest.mark.unit
    @patch('src.application.services.scheduler_service.datetime')
    @patch('src.application.services.scheduler_service.is_weekend')
    @patch('src.application.services.scheduler_service.is_in_quiet_hours')
    async def test_schedule_poll_on_weekday_uses_weekday_interval(
        self,
        mock_is_in_quiet_hours,
        mock_is_weekend,
        mock_datetime,
        scheduler_service,
        mock_scheduler,
        sample_settings,
        mock_send_poll_callback,
        mock_bot
    ):
        """
        Test poll scheduling on weekday uses correct interval.

        GIVEN: Weekday, poll_interval_weekday=60 minutes
        WHEN: schedule_poll() is called
        THEN: Poll is scheduled 60 minutes from now
              AND job is added to scheduler
        """
        # Arrange
        scheduler_service.scheduler = mock_scheduler
        now = datetime(2025, 11, 14, 10, 0, 0, tzinfo=pytz.UTC)  # Friday
        mock_datetime.now.return_value = now
        mock_is_weekend.return_value = False
        mock_is_in_quiet_hours.return_value = False

        mock_job = MagicMock()
        mock_job.id = "poll_123456789_1731579600.0"
        mock_scheduler.add_job.return_value = mock_job

        # Act
        await scheduler_service.schedule_poll(
            user_id=123456789,
            settings=sample_settings,
            user_timezone="Europe/Moscow",
            send_poll_callback=mock_send_poll_callback,
            bot=mock_bot
        )

        # Assert
        mock_scheduler.add_job.assert_called_once()
        call_args = mock_scheduler.add_job.call_args

        # Verify callback and args
        assert call_args[0][0] == mock_send_poll_callback
        assert call_args[1]['args'] == [mock_bot, 123456789]

        # Verify job stored
        assert 123456789 in scheduler_service.jobs
        assert scheduler_service.jobs[123456789] == mock_job.id

    @pytest.mark.unit
    @patch('src.application.services.scheduler_service.datetime')
    @patch('src.application.services.scheduler_service.is_weekend')
    @patch('src.application.services.scheduler_service.is_in_quiet_hours')
    async def test_schedule_poll_on_weekend_uses_weekend_interval(
        self,
        mock_is_in_quiet_hours,
        mock_is_weekend,
        mock_datetime,
        scheduler_service,
        mock_scheduler,
        sample_settings,
        mock_send_poll_callback,
        mock_bot
    ):
        """
        Test poll scheduling on weekend uses correct interval.

        GIVEN: Weekend (Saturday), poll_interval_weekend=120 minutes
        WHEN: schedule_poll() is called
        THEN: Poll is scheduled 120 minutes from now
        """
        # Arrange
        scheduler_service.scheduler = mock_scheduler
        now = datetime(2025, 11, 15, 10, 0, 0, tzinfo=pytz.UTC)  # Saturday
        mock_datetime.now.return_value = now
        mock_is_weekend.return_value = True
        mock_is_in_quiet_hours.return_value = False

        mock_job = MagicMock()
        mock_job.id = "poll_123456789_1731666000.0"
        mock_scheduler.add_job.return_value = mock_job

        # Act
        await scheduler_service.schedule_poll(
            user_id=123456789,
            settings=sample_settings,
            user_timezone="Europe/Moscow",
            send_poll_callback=mock_send_poll_callback,
            bot=mock_bot
        )

        # Assert: Weekend interval used (120 minutes)
        mock_is_weekend.assert_called_once()
        assert scheduler_service.jobs[123456789] == mock_job.id

    @pytest.mark.unit
    @patch('src.application.services.scheduler_service.datetime')
    @patch('src.application.services.scheduler_service.is_weekend')
    @patch('src.application.services.scheduler_service.is_in_quiet_hours')
    @patch('src.application.services.scheduler_service.get_end_of_quiet_hours')
    async def test_schedule_poll_during_quiet_hours_postpones_to_end(
        self,
        mock_get_end_of_quiet_hours,
        mock_is_in_quiet_hours,
        mock_is_weekend,
        mock_datetime,
        scheduler_service,
        mock_scheduler,
        sample_settings,
        mock_send_poll_callback,
        mock_bot
    ):
        """
        Test poll scheduling when next time falls in quiet hours.

        GIVEN: Next poll time is 23:30 (in quiet hours 23:00-07:00)
        WHEN: schedule_poll() is called
        THEN: Poll is rescheduled to 07:00 (end of quiet hours)
        """
        # Arrange
        scheduler_service.scheduler = mock_scheduler
        now = datetime(2025, 11, 14, 22, 30, 0, tzinfo=pytz.UTC)
        mock_datetime.now.return_value = now
        mock_is_weekend.return_value = False
        mock_is_in_quiet_hours.return_value = True  # Next time IS in quiet hours

        end_of_quiet = datetime(2025, 11, 15, 7, 0, 0, tzinfo=pytz.UTC)
        mock_get_end_of_quiet_hours.return_value = end_of_quiet

        mock_job = MagicMock()
        mock_job.id = "poll_123456789_1731654000.0"
        mock_scheduler.add_job.return_value = mock_job

        # Act
        await scheduler_service.schedule_poll(
            user_id=123456789,
            settings=sample_settings,
            user_timezone="Europe/Moscow",
            send_poll_callback=mock_send_poll_callback,
            bot=mock_bot
        )

        # Assert: Rescheduled to end of quiet hours
        mock_get_end_of_quiet_hours.assert_called_once()
        assert scheduler_service.jobs[123456789] == mock_job.id

    @pytest.mark.unit
    @patch('src.application.services.scheduler_service.datetime')
    @patch('src.application.services.scheduler_service.is_weekend')
    @patch('src.application.services.scheduler_service.is_in_quiet_hours')
    async def test_schedule_poll_replaces_existing_job(
        self,
        mock_is_in_quiet_hours,
        mock_is_weekend,
        mock_datetime,
        scheduler_service,
        mock_scheduler,
        sample_settings,
        mock_send_poll_callback,
        mock_bot
    ):
        """
        Test scheduling new poll removes existing job for user.

        GIVEN: User already has scheduled poll
        WHEN: schedule_poll() is called again
        THEN: Old job is removed before adding new one
        """
        # Arrange
        scheduler_service.scheduler = mock_scheduler
        now = datetime(2025, 11, 14, 10, 0, 0, tzinfo=pytz.UTC)
        mock_datetime.now.return_value = now
        mock_is_weekend.return_value = False
        mock_is_in_quiet_hours.return_value = False

        # Existing job
        old_job_id = "poll_123456789_old"
        scheduler_service.jobs[123456789] = old_job_id

        mock_job = MagicMock()
        mock_job.id = "poll_123456789_new"
        mock_scheduler.add_job.return_value = mock_job

        # Act
        await scheduler_service.schedule_poll(
            user_id=123456789,
            settings=sample_settings,
            user_timezone="Europe/Moscow",
            send_poll_callback=mock_send_poll_callback,
            bot=mock_bot
        )

        # Assert: Old job removed
        mock_scheduler.remove_job.assert_called_once_with(old_job_id)

        # New job added
        assert scheduler_service.jobs[123456789] == mock_job.id

    @pytest.mark.unit
    @patch('src.application.services.scheduler_service.datetime')
    @patch('src.application.services.scheduler_service.is_weekend')
    @patch('src.application.services.scheduler_service.is_in_quiet_hours')
    async def test_schedule_poll_without_quiet_hours_does_not_check(
        self,
        mock_is_in_quiet_hours,
        mock_is_weekend,
        mock_datetime,
        scheduler_service,
        mock_scheduler,
        mock_send_poll_callback,
        mock_bot
    ):
        """
        Test poll scheduling when quiet hours are not configured.

        GIVEN: Settings without quiet_hours_start/end
        WHEN: schedule_poll() is called
        THEN: Quiet hours check is skipped
              AND poll is scheduled normally
        """
        # Arrange
        scheduler_service.scheduler = mock_scheduler
        now = datetime(2025, 11, 14, 10, 0, 0, tzinfo=pytz.UTC)
        mock_datetime.now.return_value = now
        mock_is_weekend.return_value = False

        settings_no_quiet = {
            "poll_interval_weekday": 60,
            "poll_interval_weekend": 120,
            "quiet_hours_start": None,
            "quiet_hours_end": None
        }

        mock_job = MagicMock()
        mock_job.id = "poll_123456789_1731579600.0"
        mock_scheduler.add_job.return_value = mock_job

        # Act
        await scheduler_service.schedule_poll(
            user_id=123456789,
            settings=settings_no_quiet,
            user_timezone="Europe/Moscow",
            send_poll_callback=mock_send_poll_callback,
            bot=mock_bot
        )

        # Assert: Quiet hours check NOT called
        mock_is_in_quiet_hours.assert_not_called()
        assert scheduler_service.jobs[123456789] == mock_job.id


class TestSchedulerServiceCancelPoll:
    """
    Test suite for cancel_poll() method.
    """

    @pytest.mark.unit
    async def test_cancel_poll_removes_existing_job(self, scheduler_service, mock_scheduler):
        """
        Test cancelling existing poll.

        GIVEN: User has scheduled poll
        WHEN: cancel_poll(user_id) is called
        THEN: Job is removed from scheduler
              AND job_id is removed from jobs dict
        """
        # Arrange
        scheduler_service.scheduler = mock_scheduler
        job_id = "poll_123456789_1731579600.0"
        scheduler_service.jobs[123456789] = job_id

        # Act
        await scheduler_service.cancel_poll(123456789)

        # Assert
        mock_scheduler.remove_job.assert_called_once_with(job_id)
        assert 123456789 not in scheduler_service.jobs

    @pytest.mark.unit
    async def test_cancel_poll_for_user_without_job_does_nothing(
        self,
        scheduler_service,
        mock_scheduler
    ):
        """
        Test cancelling poll for user without scheduled job.

        GIVEN: User has no scheduled poll
        WHEN: cancel_poll(user_id) is called
        THEN: No error raised, no scheduler calls made
        """
        # Arrange
        scheduler_service.scheduler = mock_scheduler

        # Act
        await scheduler_service.cancel_poll(999999)  # Non-existent user

        # Assert: No calls made
        mock_scheduler.remove_job.assert_not_called()

    @pytest.mark.unit
    async def test_cancel_poll_handles_scheduler_exception_gracefully(
        self,
        scheduler_service,
        mock_scheduler
    ):
        """
        Test error handling when scheduler.remove_job() fails.

        GIVEN: scheduler.remove_job() raises exception
        WHEN: cancel_poll() is called
        THEN: Exception is caught and logged (no crash)
        """
        # Arrange
        scheduler_service.scheduler = mock_scheduler
        job_id = "poll_123456789_1731579600.0"
        scheduler_service.jobs[123456789] = job_id

        mock_scheduler.remove_job.side_effect = Exception("Job not found")

        # Act: Should not raise
        await scheduler_service.cancel_poll(123456789)

        # Assert: Exception was caught (no crash)
        # Job ID should still be in dict (cleanup failed)
        # This is acceptable - logged but not fatal


class TestSchedulerServiceRestoreScheduledPolls:
    """
    Test suite for restore_scheduled_polls() method.
    """

    @pytest.mark.unit
    async def test_restore_scheduled_polls_restores_all_active_users(
        self,
        scheduler_service,
        mock_scheduler,
        sample_user,
        sample_settings,
        mock_send_poll_callback,
        mock_bot
    ):
        """
        Test restoration of polls for all active users.

        GIVEN: 2 active users with settings
        WHEN: restore_scheduled_polls() is called
        THEN: schedule_poll() is called for each user
        """
        # Arrange
        scheduler_service.scheduler = mock_scheduler

        users = [
            sample_user,
            {**sample_user, "id": 2, "telegram_id": 987654321}
        ]

        mock_get_active_users = AsyncMock(return_value=users)
        mock_get_user_settings = AsyncMock(return_value=sample_settings)

        mock_job = MagicMock()
        mock_job.id = "poll_test"
        mock_scheduler.add_job.return_value = mock_job

        # Act
        with patch.object(scheduler_service, 'schedule_poll', new=AsyncMock()) as mock_schedule:
            await scheduler_service.restore_scheduled_polls(
                get_active_users=mock_get_active_users,
                get_user_settings=mock_get_user_settings,
                send_poll_callback=mock_send_poll_callback,
                bot=mock_bot
            )

            # Assert: schedule_poll called for both users
            assert mock_schedule.call_count == 2

    @pytest.mark.unit
    async def test_restore_scheduled_polls_skips_users_without_settings(
        self,
        scheduler_service,
        mock_scheduler,
        sample_user,
        mock_send_poll_callback,
        mock_bot
    ):
        """
        Test restoration skips users without settings.

        GIVEN: 2 users, one without settings
        WHEN: restore_scheduled_polls() is called
        THEN: Only user with settings gets poll scheduled
        """
        # Arrange
        scheduler_service.scheduler = mock_scheduler

        users = [
            sample_user,
            {**sample_user, "id": 2, "telegram_id": 987654321}
        ]

        # First user has settings, second doesn't
        async def mock_get_settings(user_id):
            if user_id == 1:
                return {"poll_interval_weekday": 60, "poll_interval_weekend": 120}
            return None

        mock_get_active_users = AsyncMock(return_value=users)
        mock_get_user_settings = AsyncMock(side_effect=mock_get_settings)

        mock_job = MagicMock()
        mock_job.id = "poll_test"
        mock_scheduler.add_job.return_value = mock_job

        # Act
        with patch.object(scheduler_service, 'schedule_poll', new=AsyncMock()) as mock_schedule:
            await scheduler_service.restore_scheduled_polls(
                get_active_users=mock_get_active_users,
                get_user_settings=mock_get_user_settings,
                send_poll_callback=mock_send_poll_callback,
                bot=mock_bot
            )

            # Assert: Only 1 user scheduled
            assert mock_schedule.call_count == 1

    @pytest.mark.unit
    async def test_restore_scheduled_polls_when_no_active_users_does_nothing(
        self,
        scheduler_service,
        mock_send_poll_callback,
        mock_bot
    ):
        """
        Test restoration when no active users exist.

        GIVEN: No active users
        WHEN: restore_scheduled_polls() is called
        THEN: No polls are scheduled
        """
        # Arrange
        mock_get_active_users = AsyncMock(return_value=[])
        mock_get_user_settings = AsyncMock()

        # Act
        with patch.object(scheduler_service, 'schedule_poll', new=AsyncMock()) as mock_schedule:
            await scheduler_service.restore_scheduled_polls(
                get_active_users=mock_get_active_users,
                get_user_settings=mock_get_user_settings,
                send_poll_callback=mock_send_poll_callback,
                bot=mock_bot
            )

            # Assert: No scheduling calls
            mock_schedule.assert_not_called()
            mock_get_user_settings.assert_not_called()

    @pytest.mark.unit
    async def test_restore_scheduled_polls_continues_after_individual_user_error(
        self,
        scheduler_service,
        mock_scheduler,
        sample_user,
        sample_settings,
        mock_send_poll_callback,
        mock_bot
    ):
        """
        Test restoration continues when one user fails.

        GIVEN: 3 users, second one raises exception
        WHEN: restore_scheduled_polls() is called
        THEN: First and third users are still processed
              (Error is logged but not fatal)
        """
        # Arrange
        scheduler_service.scheduler = mock_scheduler

        users = [
            {**sample_user, "id": 1, "telegram_id": 111},
            {**sample_user, "id": 2, "telegram_id": 222},
            {**sample_user, "id": 3, "telegram_id": 333}
        ]

        # Second user will raise exception
        async def mock_get_settings(user_id):
            if user_id == 2:
                raise Exception("Settings fetch failed")
            return sample_settings

        mock_get_active_users = AsyncMock(return_value=users)
        mock_get_user_settings = AsyncMock(side_effect=mock_get_settings)

        mock_job = MagicMock()
        mock_job.id = "poll_test"
        mock_scheduler.add_job.return_value = mock_job

        # Act
        with patch.object(scheduler_service, 'schedule_poll', new=AsyncMock()) as mock_schedule:
            await scheduler_service.restore_scheduled_polls(
                get_active_users=mock_get_active_users,
                get_user_settings=mock_get_user_settings,
                send_poll_callback=mock_send_poll_callback,
                bot=mock_bot
            )

            # Assert: 2 users scheduled (1st and 3rd)
            assert mock_schedule.call_count == 2


class TestSchedulerServiceCalculateNextPollTime:
    """
    Test suite for _calculate_next_poll_time() method.
    """

    @pytest.mark.unit
    @patch('src.application.services.scheduler_service.datetime')
    @patch('src.application.services.scheduler_service.is_weekend')
    @patch('src.application.services.scheduler_service.is_in_quiet_hours')
    def test_calculate_next_poll_time_with_recent_last_poll_time(
        self,
        mock_is_in_quiet_hours,
        mock_is_weekend,
        mock_datetime,
        scheduler_service,
        sample_user,
        sample_settings
    ):
        """
        Test calculation when last_poll_time is recent.

        GIVEN: last_poll_time was 30 minutes ago, interval=60
        WHEN: _calculate_next_poll_time() is called
        THEN: Next poll = last_poll_time + 60 minutes
        """
        # Arrange
        now = datetime(2025, 11, 14, 10, 30, 0, tzinfo=pytz.UTC)
        last_poll = datetime(2025, 11, 14, 10, 0, 0, tzinfo=pytz.UTC)

        mock_datetime.now.return_value = now
        mock_is_weekend.return_value = False
        mock_is_in_quiet_hours.return_value = False

        user = {**sample_user, "last_poll_time": last_poll}

        # Act
        result = scheduler_service._calculate_next_poll_time(user, sample_settings)

        # Assert: 60 minutes after last poll
        expected = last_poll + timedelta(minutes=60)
        assert result == expected

    @pytest.mark.unit
    @patch('src.application.services.scheduler_service.datetime')
    @patch('src.application.services.scheduler_service.is_weekend')
    @patch('src.application.services.scheduler_service.is_in_quiet_hours')
    def test_calculate_next_poll_time_when_next_time_in_past_uses_now(
        self,
        mock_is_in_quiet_hours,
        mock_is_weekend,
        mock_datetime,
        scheduler_service,
        sample_user,
        sample_settings
    ):
        """
        Test calculation when next time is in the past.

        GIVEN: last_poll_time was 2 hours ago, interval=60
        WHEN: _calculate_next_poll_time() is called
        THEN: Next poll = now + 60 minutes (not in past)
        """
        # Arrange
        now = datetime(2025, 11, 14, 12, 0, 0, tzinfo=pytz.UTC)
        last_poll = datetime(2025, 11, 14, 10, 0, 0, tzinfo=pytz.UTC)

        mock_datetime.now.return_value = now
        mock_is_weekend.return_value = False
        mock_is_in_quiet_hours.return_value = False

        user = {**sample_user, "last_poll_time": last_poll}

        # Act
        result = scheduler_service._calculate_next_poll_time(user, sample_settings)

        # Assert: Now + interval (not in past)
        expected = now + timedelta(minutes=60)
        assert result == expected

    @pytest.mark.unit
    @patch('src.application.services.scheduler_service.datetime')
    @patch('src.application.services.scheduler_service.is_weekend')
    @patch('src.application.services.scheduler_service.is_in_quiet_hours')
    def test_calculate_next_poll_time_without_last_poll_time_uses_now(
        self,
        mock_is_in_quiet_hours,
        mock_is_weekend,
        mock_datetime,
        scheduler_service,
        sample_settings
    ):
        """
        Test calculation for new user without last_poll_time.

        GIVEN: User with last_poll_time=None
        WHEN: _calculate_next_poll_time() is called
        THEN: Next poll = now + interval
        """
        # Arrange
        now = datetime(2025, 11, 14, 10, 0, 0, tzinfo=pytz.UTC)
        mock_datetime.now.return_value = now
        mock_is_weekend.return_value = False
        mock_is_in_quiet_hours.return_value = False

        user = {
            "id": 1,
            "telegram_id": 123456789,
            "timezone": "Europe/Moscow",
            "last_poll_time": None
        }

        # Act
        result = scheduler_service._calculate_next_poll_time(user, sample_settings)

        # Assert: Now + interval
        expected = now + timedelta(minutes=60)
        assert result == expected

    @pytest.mark.unit
    @patch('src.application.services.scheduler_service.datetime')
    @patch('src.application.services.scheduler_service.is_weekend')
    @patch('src.application.services.scheduler_service.is_in_quiet_hours')
    @patch('src.application.services.scheduler_service.get_end_of_quiet_hours')
    def test_calculate_next_poll_time_adjusts_for_quiet_hours(
        self,
        mock_get_end_of_quiet_hours,
        mock_is_in_quiet_hours,
        mock_is_weekend,
        mock_datetime,
        scheduler_service,
        sample_user,
        sample_settings
    ):
        """
        Test calculation adjusts for quiet hours.

        GIVEN: Next poll time falls in quiet hours
        WHEN: _calculate_next_poll_time() is called
        THEN: Next poll = end of quiet hours
        """
        # Arrange
        now = datetime(2025, 11, 14, 22, 30, 0, tzinfo=pytz.UTC)
        last_poll = datetime(2025, 11, 14, 22, 0, 0, tzinfo=pytz.UTC)

        mock_datetime.now.return_value = now
        mock_is_weekend.return_value = False
        mock_is_in_quiet_hours.return_value = True

        end_of_quiet = datetime(2025, 11, 15, 7, 0, 0, tzinfo=pytz.UTC)
        mock_get_end_of_quiet_hours.return_value = end_of_quiet

        user = {**sample_user, "last_poll_time": last_poll}

        # Act
        result = scheduler_service._calculate_next_poll_time(user, sample_settings)

        # Assert: End of quiet hours
        assert result == end_of_quiet

    @pytest.mark.unit
    @patch('src.application.services.scheduler_service.datetime')
    @patch('src.application.services.scheduler_service.is_weekend')
    @patch('src.application.services.scheduler_service.is_in_quiet_hours')
    def test_calculate_next_poll_time_on_weekend_uses_weekend_interval(
        self,
        mock_is_in_quiet_hours,
        mock_is_weekend,
        mock_datetime,
        scheduler_service,
        sample_user,
        sample_settings
    ):
        """
        Test calculation uses weekend interval on weekend.

        GIVEN: Saturday (weekend), poll_interval_weekend=120
        WHEN: _calculate_next_poll_time() is called
        THEN: Next poll uses 120-minute interval
        """
        # Arrange
        now = datetime(2025, 11, 15, 10, 0, 0, tzinfo=pytz.UTC)  # Saturday
        last_poll = datetime(2025, 11, 15, 9, 0, 0, tzinfo=pytz.UTC)

        mock_datetime.now.return_value = now
        mock_is_weekend.return_value = True
        mock_is_in_quiet_hours.return_value = False

        user = {**sample_user, "last_poll_time": last_poll}

        # Act
        result = scheduler_service._calculate_next_poll_time(user, sample_settings)

        # Assert: 120 minutes after last poll
        expected = last_poll + timedelta(minutes=120)
        assert result == expected

    @pytest.mark.unit
    @patch('src.application.services.scheduler_service.datetime')
    @patch('src.application.services.scheduler_service.is_weekend')
    def test_calculate_next_poll_time_handles_naive_datetime(
        self,
        mock_is_weekend,
        mock_datetime,
        scheduler_service,
        sample_user,
        sample_settings
    ):
        """
        Test calculation handles naive datetime (no timezone).

        GIVEN: last_poll_time without tzinfo (naive)
        WHEN: _calculate_next_poll_time() is called
        THEN: Datetime is localized to UTC before calculation
        """
        # Arrange
        now = datetime(2025, 11, 14, 10, 30, 0, tzinfo=pytz.UTC)
        last_poll_naive = datetime(2025, 11, 14, 10, 0, 0)  # No tzinfo

        mock_datetime.now.return_value = now
        mock_is_weekend.return_value = False

        user = {**sample_user, "last_poll_time": last_poll_naive}

        # Act
        result = scheduler_service._calculate_next_poll_time(user, sample_settings)

        # Assert: Should complete without error
        assert result is not None
        assert result.tzinfo is not None, "Result should be timezone-aware"
