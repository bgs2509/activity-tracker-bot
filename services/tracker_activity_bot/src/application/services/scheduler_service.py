"""Scheduler service for automatic polls (simplified PoC version)."""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.triggers.date import DateTrigger
import pytz

from src.application.utils.timezone_helper import is_in_quiet_hours, is_weekend, get_end_of_quiet_hours

logger = logging.getLogger(__name__)


class SchedulerService:
    """Service for managing poll scheduling.

    Uses AsyncIOExecutor to run async jobs directly in the event loop,
    without needing thread pool executors or coroutine wrappers.
    """

    def __init__(self):
        # Configure executors to use AsyncIOExecutor for async jobs
        executors = {
            'default': AsyncIOExecutor()
        }

        # Create scheduler with AsyncIO executor
        self.scheduler = AsyncIOScheduler(
            executors=executors,
            timezone=pytz.UTC
        )
        self.jobs: Dict[int, str] = {}  # user_id -> job_id

    def start(self):
        """Start the scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler started with AsyncIOExecutor")

    def stop(self, wait: bool = True):
        """
        Stop the scheduler gracefully.

        Args:
            wait: If True, wait for pending jobs to complete before shutdown.
                  Prevents job interruption during graceful shutdown.
                  Default: True for production safety.
        """
        if self.scheduler.running:
            self.scheduler.shutdown(wait=wait)
            if wait:
                logger.info("Scheduler stopped (waited for pending jobs to complete)")
            else:
                logger.info("Scheduler stopped (did not wait for pending jobs)")

    async def schedule_poll(
        self,
        user_id: int,
        settings: dict,
        user_timezone: str,
        send_poll_callback,
        bot
    ):
        """Schedule next poll for user.

        Args:
            user_id: User ID
            settings: User settings dict with intervals and quiet hours
            user_timezone: User's timezone
            send_poll_callback: Async function to send poll
            bot: Bot instance to pass to callback
        """
        logger.info(
            "DEBUG: schedule_poll called",
            extra={
                "user_id": user_id,
                "settings_provided": bool(settings),
                "weekday_interval": settings.get("poll_interval_weekday") if settings else None,
                "weekend_interval": settings.get("poll_interval_weekend") if settings else None,
                "user_timezone": user_timezone,
                "existing_job": user_id in self.jobs
            }
        )

        # Calculate next poll time
        now = datetime.now(pytz.UTC)
        tz = pytz.timezone(user_timezone)

        # Determine interval based on weekday/weekend
        if is_weekend(now, user_timezone):
            interval_minutes = settings["poll_interval_weekend"]
        else:
            interval_minutes = settings["poll_interval_weekday"]

        # Calculate next time
        next_time = now + timedelta(minutes=interval_minutes)

        # Check if next_time is in quiet hours
        quiet_start = settings.get("quiet_hours_start")
        quiet_end = settings.get("quiet_hours_end")

        if quiet_start and quiet_end:
            # Parse time strings
            from datetime import time as dt_time
            if isinstance(quiet_start, str):
                h, m = quiet_start.split(":")[:2]
                quiet_start = dt_time(int(h), int(m))
            if isinstance(quiet_end, str):
                h, m = quiet_end.split(":")[:2]
                quiet_end = dt_time(int(h), int(m))

            if is_in_quiet_hours(next_time, quiet_start, quiet_end, user_timezone):
                # Reschedule to end of quiet hours
                next_time = get_end_of_quiet_hours(quiet_end, user_timezone)
                logger.info(f"Poll for user {user_id} rescheduled to end of quiet hours: {next_time}")

        # Remove existing job if any
        if user_id in self.jobs:
            try:
                self.scheduler.remove_job(self.jobs[user_id])
            except Exception as e:
                logger.warning(
                    "Failed to remove existing poll job",
                    extra={
                        "user_id": user_id,
                        "job_id": self.jobs.get(user_id),
                        "error": str(e),
                        "error_type": type(e).__name__
                    }
                )

        # Schedule new job - AsyncIOExecutor handles async functions automatically
        job = self.scheduler.add_job(
            send_poll_callback,
            trigger=DateTrigger(run_date=next_time),
            args=[bot, user_id],
            id=f"poll_{user_id}_{next_time.timestamp()}",
            replace_existing=True
        )

        self.jobs[user_id] = job.id
        logger.info(
            f"Scheduled poll for user {user_id} at {next_time} (in {interval_minutes}m)",
            extra={
                "user_id": user_id,
                "job_id": job.id,
                "next_poll_time": next_time.isoformat(),
                "interval_minutes": interval_minutes,
                "total_jobs_count": len(self.jobs)
            }
        )

    async def cancel_poll(self, user_id: int):
        """Cancel scheduled poll for user."""
        if user_id in self.jobs:
            try:
                self.scheduler.remove_job(self.jobs[user_id])
                del self.jobs[user_id]
                logger.info(f"Cancelled poll for user {user_id}")
            except Exception as e:
                logger.error(f"Error cancelling poll for user {user_id}: {e}")

    async def restore_scheduled_polls(
        self,
        get_active_users: Callable,
        get_user_settings: Callable,
        send_poll_callback,
        bot
    ):
        """Restore scheduled polls for all active users on bot startup.

        This method is called during bot initialization to restore
        the poll schedule that was lost during restart (APScheduler
        keeps jobs in memory only).

        Args:
            get_active_users: Async function to get all active users from API
            get_user_settings: Async function to get user settings by user_id
            send_poll_callback: Async function to send poll
            bot: Bot instance to pass to callback

        Algorithm:
            1. Get all active users (users with last_poll_time set)
            2. For each user:
               - Get user settings (intervals, quiet hours, timezone)
               - Calculate next poll time based on:
                 * last_poll_time (when user was last polled)
                 * current time
                 * weekday/weekend interval
                 * quiet hours
               - Schedule poll at calculated time
        """
        logger.info("Starting poll schedule restoration")

        try:
            # Get all active users
            users = await get_active_users()

            if not users:
                logger.info("No active users found, nothing to restore")
                return

            logger.info(
                "Found active users to restore polls",
                extra={"count": len(users)}
            )

            restored_count = 0
            skipped_count = 0

            for user in users:
                try:
                    # Get user settings
                    settings = await get_user_settings(user["id"])
                    if not settings:
                        logger.warning(
                            "No settings found for user, skipping",
                            extra={"user_id": user["id"]}
                        )
                        skipped_count += 1
                        continue

                    # Calculate next poll time
                    next_poll_time = self._calculate_next_poll_time(
                        user=user,
                        settings=settings
                    )

                    # Schedule poll
                    await self.schedule_poll(
                        user_id=user["telegram_id"],
                        settings=settings,
                        user_timezone=user.get("timezone", "Europe/Moscow"),
                        send_poll_callback=send_poll_callback,
                        bot=bot
                    )

                    restored_count += 1

                    logger.info(
                        "Restored poll schedule for user",
                        extra={
                            "user_id": user["telegram_id"],
                            "next_poll_time": next_poll_time.isoformat()
                        }
                    )

                except Exception as e:
                    logger.error(
                        "Failed to restore poll for user",
                        extra={
                            "user_id": user.get("telegram_id"),
                            "error": str(e),
                            "error_type": type(e).__name__
                        },
                        exc_info=True
                    )
                    skipped_count += 1

            logger.info(
                "Poll schedule restoration complete",
                extra={
                    "restored": restored_count,
                    "skipped": skipped_count,
                    "total": len(users)
                }
            )

        except Exception as e:
            logger.error(
                "Failed to restore poll schedules",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__
                },
                exc_info=True
            )

    def _calculate_next_poll_time(self, user: dict, settings: dict) -> datetime:
        """Calculate next poll time based on last poll time and intervals.

        Args:
            user: User dict with last_poll_time
            settings: User settings with intervals

        Returns:
            Next poll time as UTC datetime
        """
        now = datetime.now(pytz.UTC)
        user_timezone = pytz.timezone(user.get("timezone", "Europe/Moscow"))

        # Get last poll time
        last_poll_time = user.get("last_poll_time")
        if last_poll_time:
            # If last_poll_time is naive, make it UTC aware
            if last_poll_time.tzinfo is None:
                last_poll_time = pytz.UTC.localize(last_poll_time)
            else:
                last_poll_time = last_poll_time.astimezone(pytz.UTC)
        else:
            # If no last poll time, use current time
            last_poll_time = now

        # Determine interval based on weekday/weekend
        if is_weekend(now, user.get("timezone", "Europe/Moscow")):
            interval_minutes = settings.get("poll_interval_weekend", 120)
        else:
            interval_minutes = settings.get("poll_interval_weekday", 60)

        # Calculate next poll time
        next_time = last_poll_time + timedelta(minutes=interval_minutes)

        # If next_time is in the past, schedule for now + interval
        if next_time < now:
            next_time = now + timedelta(minutes=interval_minutes)

        # Check quiet hours
        quiet_start = settings.get("quiet_hours_start")
        quiet_end = settings.get("quiet_hours_end")

        if quiet_start and quiet_end:
            from datetime import time as dt_time
            if isinstance(quiet_start, str):
                h, m = quiet_start.split(":")[:2]
                quiet_start = dt_time(int(h), int(m))
            if isinstance(quiet_end, str):
                h, m = quiet_end.split(":")[:2]
                quiet_end = dt_time(int(h), int(m))

            if is_in_quiet_hours(next_time, quiet_start, quiet_end, user.get("timezone", "Europe/Moscow")):
                next_time = get_end_of_quiet_hours(quiet_end, user.get("timezone", "Europe/Moscow"))

        return next_time

    @property
    def is_running(self) -> bool:
        """
        Check if scheduler is running.

        Returns:
            True if scheduler is active and running
        """
        return self.scheduler.running


# Global instance (deprecated - use ServiceContainer.scheduler instead)
scheduler_service = SchedulerService()
