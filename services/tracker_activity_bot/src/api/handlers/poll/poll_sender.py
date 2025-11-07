"""Poll sender module for automatic poll delivery."""

import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from aiogram.fsm.storage.base import StorageKey
from apscheduler.triggers.date import DateTrigger

from src.api.dependencies import get_service_container
from src.api.keyboards.poll import get_poll_response_keyboard
from src.application.services.scheduler_service import scheduler_service
from src.application.utils.time_helpers import get_poll_interval
from src.core.constants import POLL_POSTPONE_MINUTES

from .helpers import get_fsm_storage

logger = logging.getLogger(__name__)


async def send_automatic_poll(bot: Bot, user_id: int) -> None:
    """
    Send automatic poll to user.

    This function is called by the scheduler to send periodic polls.
    It checks for FSM conflicts and postpones if user is in active dialog.

    Args:
        bot: Bot instance
        user_id: Telegram user ID

    Raises:
        Does not raise exceptions - logs errors internally
    """
    services = get_service_container()

    try:
        # Get user
        user = await services.user.get_by_telegram_id(user_id)
        if not user:
            logger.error(
                "User not found for automatic poll",
                extra={"user_id": user_id}
            )
            return

        # Get settings
        settings = await services.settings.get_settings(user["id"])
        if not settings:
            logger.error(
                "Settings not found for user",
                extra={"user_id": user_id}
            )
            return

        # Check if user is in active FSM state (conflict resolution)
        if await _should_postpone_poll(bot, user_id):
            await _postpone_poll(bot, user_id)
            return

        # Send poll message
        await _send_poll_message(bot, user_id, settings)

        # Update last poll time for accurate sleep duration calculation
        await _update_last_poll_time(services, user, user_id)

        logger.info(
            "Sent automatic poll to user",
            extra={"user_id": user_id}
        )

    except Exception as e:
        logger.error(
            "Error sending automatic poll",
            extra={"user_id": user_id, "error": str(e)},
            exc_info=True
        )


async def send_reminder(bot: Bot, user_id: int) -> None:
    """
    Send reminder to user about unanswered poll.

    Args:
        bot: Bot instance
        user_id: Telegram user ID

    Raises:
        Does not raise exceptions - logs errors internally
    """
    try:
        text = (
            "⏰ Напоминание!\n\n"
            "Ты просил напомнить ответить на опрос.\n\n"
            "Чем ты занимался?"
        )

        await bot.send_message(
            chat_id=user_id,
            text=text,
            reply_markup=get_poll_response_keyboard()
        )

        logger.info(
            "Sent reminder to user",
            extra={"user_id": user_id}
        )

    except Exception as e:
        logger.error(
            "Error sending reminder",
            extra={"user_id": user_id, "error": str(e)},
            exc_info=True
        )


# Helper functions (DRY principle)


async def _should_postpone_poll(bot: Bot, user_id: int) -> bool:
    """
    Check if poll should be postponed due to active FSM state.

    Args:
        bot: Bot instance
        user_id: Telegram user ID

    Returns:
        True if poll should be postponed, False otherwise
    """
    try:
        storage = get_fsm_storage()

        # Create storage key for this user
        key = StorageKey(
            bot_id=bot.id,
            chat_id=user_id,
            user_id=user_id
        )

        # Check current FSM state
        current_state = await storage.get_state(key)

        if current_state:
            logger.info(
                "User is in FSM state, postponing poll",
                extra={
                    "user_id": user_id,
                    "state": current_state,
                    "postpone_minutes": POLL_POSTPONE_MINUTES
                }
            )
            return True

    except Exception as e:
        # If FSM check fails, continue with poll anyway
        logger.warning(
            "Could not check FSM state, continuing with poll",
            extra={"user_id": user_id, "error": str(e)}
        )

    return False


async def _postpone_poll(bot: Bot, user_id: int) -> None:
    """
    Postpone poll delivery by configured minutes.

    Args:
        bot: Bot instance
        user_id: Telegram user ID
    """
    try:
        next_poll_time = datetime.now(timezone.utc) + timedelta(
            minutes=POLL_POSTPONE_MINUTES
        )

        # Remove existing job if any
        if user_id in scheduler_service.jobs:
            try:
                scheduler_service.scheduler.remove_job(
                    scheduler_service.jobs[user_id]
                )
            except Exception:
                pass

        # Schedule postponed poll
        # AsyncIOExecutor handles async functions directly
        job = scheduler_service.scheduler.add_job(
            lambda: send_automatic_poll(bot, user_id),
            trigger=DateTrigger(run_date=next_poll_time),
            id=f"poll_postponed_{user_id}_{next_poll_time.timestamp()}",
            replace_existing=True
        )

        scheduler_service.jobs[user_id] = job.id

        logger.info(
            "Postponed poll for user",
            extra={
                "user_id": user_id,
                "next_poll_time": next_poll_time.isoformat()
            }
        )

    except Exception as e:
        logger.error(
            "Error postponing poll",
            extra={"user_id": user_id, "error": str(e)},
            exc_info=True
        )


async def _send_poll_message(bot: Bot, user_id: int, settings: dict) -> None:
    """
    Build and send poll message to user.

    Args:
        bot: Bot instance
        user_id: Telegram user ID
        settings: User settings dict
    """
    # Calculate time since last poll for accurate message
    interval_minutes = get_poll_interval(settings)

    # Format time string
    time_str = _format_interval_time(interval_minutes)

    # Build poll message
    text = (
        "⏰ Время проверки активности!\n\n"
        f"Чем ты занимался последние {time_str}?\n\n"
        "Выбери один из вариантов:"
    )

    await bot.send_message(
        chat_id=user_id,
        text=text,
        reply_markup=get_poll_response_keyboard()
    )


def _format_interval_time(interval_minutes: int) -> str:
    """
    Format interval time in Russian.

    Args:
        interval_minutes: Interval in minutes

    Returns:
        Formatted time string (e.g., "2ч 30м", "3ч", "45м")

    Example:
        >>> _format_interval_time(150)
        '2ч 30м'
        >>> _format_interval_time(180)
        '3ч'
        >>> _format_interval_time(45)
        '45м'
    """
    hours = interval_minutes // 60
    minutes = interval_minutes % 60

    if hours > 0 and minutes > 0:
        return f"{hours}ч {minutes}м"
    elif hours > 0:
        return f"{hours}ч"
    else:
        return f"{minutes}м"


async def _update_last_poll_time(services, user: dict, user_id: int) -> None:
    """
    Update last poll time for user.

    Args:
        services: Service container
        user: User dict
        user_id: Telegram user ID
    """
    try:
        poll_time = datetime.now(timezone.utc)
        await services.user.update_last_poll_time(user["id"], poll_time)

        logger.info(
            "Updated last_poll_time for user",
            extra={"user_id": user_id}
        )

    except Exception as e:
        logger.warning(
            "Could not update last_poll_time",
            extra={"user_id": user_id, "error": str(e)}
        )
