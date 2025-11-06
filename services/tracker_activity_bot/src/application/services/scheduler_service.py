"""Scheduler service for automatic polls (simplified PoC version)."""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
import pytz

from src.application.utils.timezone_helper import is_in_quiet_hours, is_weekend, get_end_of_quiet_hours

logger = logging.getLogger(__name__)


def _async_job_wrapper(loop: asyncio.AbstractEventLoop, async_func: Callable, *args, **kwargs):
    """Wrapper to run async functions in APScheduler.

    APScheduler jobs run in a thread pool executor without an event loop.
    This wrapper schedules the coroutine in the main event loop using
    run_coroutine_threadsafe().

    Args:
        loop: The main event loop (asyncio.get_running_loop() from main)
        async_func: Async function or lambda returning a coroutine
        *args: Arguments to pass to async_func
        **kwargs: Keyword arguments to pass to async_func
    """
    try:
        # Call the function (might be lambda returning coroutine)
        result = async_func(*args, **kwargs)

        # If it's a coroutine, schedule it in the main event loop
        if asyncio.iscoroutine(result):
            future = asyncio.run_coroutine_threadsafe(result, loop)
            logger.debug(f"Scheduled coroutine in event loop: {async_func.__name__ if hasattr(async_func, '__name__') else 'lambda'}")
        # If async_func itself is a coroutine function, call and schedule it
        elif asyncio.iscoroutinefunction(async_func):
            coro = async_func(*args, **kwargs)
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            logger.debug(f"Scheduled async function in event loop: {async_func.__name__}")
        else:
            # Regular function, just execute
            result
            logger.debug(f"Executed sync function: {async_func.__name__ if hasattr(async_func, '__name__') else 'callable'}")

    except Exception as e:
        logger.error(f"Error executing async job: {e}", exc_info=True)


class SchedulerService:
    """Service for managing poll scheduling."""

    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone=pytz.UTC)
        self.jobs: Dict[int, str] = {}  # user_id -> job_id
        self.loop: asyncio.AbstractEventLoop = None  # Will be set in start()

    def start(self):
        """Start the scheduler and capture the event loop."""
        if not self.scheduler.running:
            # Capture the current event loop for async job execution
            try:
                self.loop = asyncio.get_running_loop()
                logger.debug(f"Captured event loop: {self.loop}")
            except RuntimeError:
                # No running loop yet, will be set later
                logger.warning("No running event loop when starting scheduler")

            self.scheduler.start()
            logger.info("Scheduler started")

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
        send_poll_callback
    ):
        """Schedule next poll for user.

        Args:
            user_id: User ID
            settings: User settings dict with intervals and quiet hours
            user_timezone: User's timezone
            send_poll_callback: Async function to send poll
        """
        # Capture event loop if not already captured
        if self.loop is None:
            try:
                self.loop = asyncio.get_running_loop()
                logger.debug(f"Captured event loop in schedule_poll: {self.loop}")
            except RuntimeError:
                logger.error("No running event loop available for scheduling!")
                return
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

        # Schedule new job with async wrapper
        # Pass event loop as first argument, then callback, then user_id
        job = self.scheduler.add_job(
            _async_job_wrapper,
            trigger=DateTrigger(run_date=next_time),
            args=[self.loop, send_poll_callback, user_id],
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
