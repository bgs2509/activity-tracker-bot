"""FSM timeout management service.

This service prevents users from getting stuck in FSM states by:
1. Sending reminders after 10 minutes of inactivity
2. Auto-cleaning stale states after 3 more minutes
3. Sending automatic polls immediately after cleanup
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from aiogram import Bot
from aiogram.fsm.state import State
from aiogram.fsm.storage.base import StorageKey
from apscheduler.triggers.date import DateTrigger

from src.core.config import settings as app_settings

logger = logging.getLogger(__name__)


# Context mapping: state -> user-friendly action description
STATE_CONTEXTS = {
    "ActivityStates:waiting_for_start_time": "указать время начала активности",
    "ActivityStates:waiting_for_end_time": "указать время окончания активности",
    "ActivityStates:waiting_for_description": "описать активность",
    "ActivityStates:waiting_for_category": "выбрать категорию активности",
    "CategoryStates:waiting_for_name": "ввести название категории",
    "CategoryStates:waiting_for_emoji": "выбрать эмодзи для категории",
    "SettingsStates:waiting_for_weekday_interval_custom": "указать интервал опросов в будни",
    "SettingsStates:waiting_for_weekend_interval_custom": "указать интервал опросов в выходные",
    "SettingsStates:waiting_for_quiet_hours_start_custom": "указать начало тихих часов",
    "SettingsStates:waiting_for_quiet_hours_end_custom": "указать конец тихих часов",
    "SettingsStates:waiting_for_reminder_delay_custom": "указать задержку напоминания",
    "ActivityStates:waiting_for_category": "выбрать категорию для активности",
}


class FSMTimeoutService:
    """Service for managing FSM state timeouts and reminders."""

    def __init__(self, scheduler):
        """Initialize FSM timeout service.

        Args:
            scheduler: APScheduler instance
        """
        self.scheduler = scheduler
        self.reminder_jobs: Dict[int, str] = {}  # user_id -> reminder_job_id
        self.cleanup_jobs: Dict[int, str] = {}   # user_id -> cleanup_job_id

    def schedule_timeout(
        self,
        user_id: int,
        state: State,
        bot: Bot
    ):
        """Schedule timeout timers for FSM state.

        Starts a 10-minute countdown. If user doesn't respond, sends reminder.

        Args:
            user_id: Telegram user ID
            state: FSM state object
            bot: Bot instance for sending messages
        """
        # Cancel any existing timers for this user
        self.cancel_timeout(user_id)

        # Get human-readable action description
        action = STATE_CONTEXTS.get(state.state, "действие")

        # Schedule reminder in 10 minutes
        reminder_time = datetime.now(timezone.utc) + timedelta(minutes=10)

        try:
            job = self.scheduler.add_job(
                send_reminder,
                trigger=DateTrigger(run_date=reminder_time),
                args=[bot, user_id, state, action],
                id=f"fsm_reminder_{user_id}_{reminder_time.timestamp()}",
                replace_existing=True
            )

            self.reminder_jobs[user_id] = job.id
            logger.info(
                f"Scheduled FSM reminder for user {user_id} "
                f"in state '{state}' at {reminder_time}"
            )

        except Exception as e:
            logger.error(f"Error scheduling FSM reminder for user {user_id}: {e}")

    def cancel_timeout(self, user_id: int):
        """Cancel all timeout timers for user.

        Call this when user completes or cancels the dialog.

        Args:
            user_id: Telegram user ID
        """
        # Cancel reminder timer
        if user_id in self.reminder_jobs:
            try:
                self.scheduler.remove_job(self.reminder_jobs[user_id])
                del self.reminder_jobs[user_id]
                logger.debug(f"Cancelled reminder timer for user {user_id}")
            except Exception as e:
                logger.debug(f"Could not cancel reminder for user {user_id}: {e}")

        # Cancel cleanup timer
        self.cancel_cleanup_timer(user_id)

    def cancel_cleanup_timer(self, user_id: int):
        """Cancel only the cleanup timer (called when user clicks 'Continue').

        Args:
            user_id: Telegram user ID
        """
        if user_id in self.cleanup_jobs:
            try:
                self.scheduler.remove_job(self.cleanup_jobs[user_id])
                del self.cleanup_jobs[user_id]
                logger.debug(f"Cancelled cleanup timer for user {user_id}")
            except Exception as e:
                logger.debug(f"Could not cancel cleanup for user {user_id}: {e}")

    def _schedule_cleanup(self, bot: Bot, user_id: int, state: str):
        """Schedule state cleanup in 3 minutes (internal method).

        Args:
            bot: Bot instance
            user_id: Telegram user ID
            state: FSM state name
        """
        cleanup_time = datetime.now(timezone.utc) + timedelta(minutes=3)

        try:
            job = self.scheduler.add_job(
                cleanup_stale_state,
                trigger=DateTrigger(run_date=cleanup_time),
                args=[bot, user_id, state],
                id=f"fsm_cleanup_{user_id}_{cleanup_time.timestamp()}",
                replace_existing=True
            )

            self.cleanup_jobs[user_id] = job.id
            logger.info(
                f"Scheduled FSM cleanup for user {user_id} "
                f"in state '{state}' at {cleanup_time}"
            )

        except Exception as e:
            logger.error(f"Error scheduling FSM cleanup for user {user_id}: {e}")


async def send_reminder(bot: Bot, user_id: int, state: State, action: str):
    """Send reminder to user about unfinished dialog.

    Checks if user is still in same state, sends reminder with
    'Continue' button, then schedules cleanup.

    Args:
        bot: Bot instance
        user_id: Telegram user ID
        state: Expected FSM state object
        action: Human-readable action description
    """
    try:
        # Get shared FSM storage (reuses existing connection pool)
        from src.api.handlers.poll.helpers import get_fsm_storage
        storage = get_fsm_storage()

        # Check if user is still in same state
        key = StorageKey(
            bot_id=bot.id,
            chat_id=user_id,
            user_id=user_id
        )

        current_state = await storage.get_state(key)

        if current_state != state.state:
            # User already finished or changed state
            logger.info(
                f"User {user_id} no longer in state '{state.state}' "
                f"(current: {current_state}), skipping reminder"
            )
            return

        # Send reminder with 'Continue' button
        from src.api.keyboards.fsm_reminder import get_fsm_reminder_keyboard

        text = (
            f"⏰ Напоминание\n\n"
            f"Ты начал {action}, но не закончил.\n\n"
            f"Хочешь продолжить?"
        )

        await bot.send_message(
            chat_id=user_id,
            text=text,
            reply_markup=get_fsm_reminder_keyboard()
        )

        logger.info(f"Sent FSM reminder to user {user_id}")

        # Schedule cleanup in 3 minutes using global service instance
        if fsm_timeout_service:
            fsm_timeout_service._schedule_cleanup(bot, user_id, state)

        # DON'T close storage - it's shared!

    except Exception as e:
        logger.error(f"Error sending FSM reminder to user {user_id}: {e}")


async def cleanup_stale_state(bot: Bot, user_id: int, state: State):
    """Cleanup stale FSM state and send poll immediately.

    Silently clears FSM state if user didn't respond to reminder,
    then immediately sends automatic poll.

    Args:
        bot: Bot instance
        user_id: Telegram user ID
        state: Expected FSM state object
    """
    try:
        # Get shared FSM storage (reuses existing connection pool)
        from src.api.handlers.poll.helpers import get_fsm_storage
        storage = get_fsm_storage()

        # Check if user is still in same state (didn't click Continue)
        key = StorageKey(
            bot_id=bot.id,
            chat_id=user_id,
            user_id=user_id
        )

        current_state = await storage.get_state(key)

        if current_state != state.state:
            # User already finished or clicked Continue
            logger.info(
                f"User {user_id} no longer in state '{state.state}' "
                f"(current: {current_state}), skipping cleanup"
            )
            return

        # Silently clear FSM state
        await storage.set_state(key, None)
        await storage.set_data(key, {})

        logger.info(f"Cleared stale FSM state for user {user_id}: {state.state}")

        # Send automatic poll immediately
        from src.api.handlers.poll import send_automatic_poll

        try:
            await send_automatic_poll(bot, user_id)
            logger.info(f"Sent immediate poll after FSM cleanup for user {user_id}")
        except Exception as e:
            logger.error(
                f"Error sending poll after FSM cleanup for user {user_id}: {e}"
            )

        # DON'T close storage - it's shared!

    except Exception as e:
        logger.error(f"Error cleaning up FSM state for user {user_id}: {e}")


# Global instance (will be initialized in main.py after scheduler is ready)
fsm_timeout_service: Optional[FSMTimeoutService] = None
