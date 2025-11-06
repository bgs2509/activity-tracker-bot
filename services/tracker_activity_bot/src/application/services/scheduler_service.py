"""Scheduler service for automatic polls (simplified PoC version)."""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict

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

    def stop(self):
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped")

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
            except Exception:
                pass

        # Schedule new job - AsyncIOExecutor handles async functions automatically
        job = self.scheduler.add_job(
            send_poll_callback,
            trigger=DateTrigger(run_date=next_time),
            args=[bot, user_id],
            id=f"poll_{user_id}_{next_time.timestamp()}",
            replace_existing=True
        )

        self.jobs[user_id] = job.id
        logger.info(f"Scheduled poll for user {user_id} at {next_time} (in {interval_minutes}m)")

    async def cancel_poll(self, user_id: int):
        """Cancel scheduled poll for user."""
        if user_id in self.jobs:
            try:
                self.scheduler.remove_job(self.jobs[user_id])
                del self.jobs[user_id]
                logger.info(f"Cancelled poll for user {user_id}")
            except Exception as e:
                logger.error(f"Error cancelling poll for user {user_id}: {e}")


# Global instance
scheduler_service = SchedulerService()
