"""Poll sender module for automatic poll delivery."""

import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from aiogram.fsm.storage.base import StorageKey
from apscheduler.triggers.date import DateTrigger

from src.api.dependencies import get_service_container
from src.api.keyboards.poll import get_poll_response_keyboard, get_poll_initial_category_keyboard
from src.api.messages.activity_messages import get_category_selection_message
from src.api.states.activity import ActivityStates
from src.application.utils.formatters import format_time, format_duration
from src.application.utils.time_helpers import get_poll_interval, calculate_poll_period
from src.core.constants import POLL_POSTPONE_MINUTES

from .helpers import get_fsm_storage

logger = logging.getLogger(__name__)


async def send_automatic_poll(bot: Bot, user_id: int) -> None:
    """Send automatic poll - SKIPS period selection, goes directly to category.

    This is the entry point for automatic polls triggered by the scheduler.
    It calculates the activity period automatically (from last activity end time)
    and presents the user with category selection immediately, skipping the
    period selection screen entirely.

    Args:
        bot: Telegram Bot instance
        user_id: Telegram user ID (not internal user ID)

    Flow:
        1. Get user, settings, categories
        2. Check for FSM conflicts (user might be in another flow)
        3. Auto-calculate period from last activity
        4. Set FSM state directly to waiting_for_category (SKIP period step)
        5. Store period and context in FSM data
        6. Send category selection message

    Note:
        If user is already in another FSM state, poll is postponed.
    """
    services = get_service_container()

    try:
        # Get user
        user = await services.user.get_by_telegram_id(user_id)
        if not user:
            logger.error(
                "User not found for automatic poll",
                extra={"telegram_user_id": user_id}
            )
            return

        # Get settings
        settings = await services.settings.get_settings(user["id"])
        if not settings:
            logger.warning(
                "Settings not found for user, using defaults",
                extra={"user_id": user["id"]}
            )
            settings = {}  # Will use default values

        # Get categories
        categories = await services.category.get_user_categories(user["id"])
        if not categories:
            logger.warning(
                "No categories for user, skipping poll",
                extra={"user_id": user["id"]}
            )
            # Don't send poll if no categories - nothing to select
            return

        # Check for FSM conflicts (user might be in manual recording flow)
        if await _should_postpone_poll(bot, user_id):
            logger.info(
                "Postponing poll due to FSM conflict",
                extra={"user_id": user_id}
            )
            await _postpone_poll(bot, user_id, services)
            return

        # Auto-calculate period from last activity
        from src.application.utils.time_helpers import calculate_poll_period

        start_time, end_time = await calculate_poll_period(
            services.activity,
            user["id"],
            settings
        )

        logger.info(
            "Auto-calculated period for automatic poll",
            extra={
                "user_id": user["id"],
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_minutes": int((end_time - start_time).total_seconds() / 60)
            }
        )

        # Set FSM state DIRECTLY to category selection (SKIP period step)
        storage = get_fsm_storage()
        key = StorageKey(bot_id=bot.id, chat_id=user_id, user_id=user_id)

        await storage.set_state(key, ActivityStates.waiting_for_category)

        # Store period and context in FSM data
        await storage.update_data(key, {
            "trigger_source": "automatic",  # Mark as automatic flow
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "user_id": user["id"],
            "settings": settings,  # Needed for scheduling next poll
            "user_timezone": user.get("timezone", "Europe/Moscow")  # Needed for scheduling
        })

        # Schedule FSM timeout
        from src.application.services import fsm_timeout_service as fsm_timeout_module
        if fsm_timeout_module.fsm_timeout_service:
            fsm_timeout_module.fsm_timeout_service.schedule_timeout(
                user_id=user_id,
                state=ActivityStates.waiting_for_category,
                bot=bot
            )

        # Format time for display
        start_str = format_time(start_time)
        end_str = format_time(end_time)
        duration_minutes = int((end_time - start_time).total_seconds() / 60)
        duration_str = format_duration(duration_minutes)

        # Build category selection message
        from src.api.messages.activity_messages import get_category_selection_message

        text = get_category_selection_message(
            source="poll",
            start_time=start_str,
            end_time=end_str,
            duration=duration_str,
            add_motivation=True
        )

        # Send message with categories (use poll-specific keyboard)
        from src.api.keyboards.poll import get_poll_category_keyboard

        await bot.send_message(
            chat_id=user_id,
            text=text,
            reply_markup=get_poll_category_keyboard(categories)
        )

        # Update last poll time
        await _update_last_poll_time(services, user, user_id)

        logger.info(
            "Sent automatic poll successfully",
            extra={
                "user_id": user_id,
                "categories_count": len(categories)
            }
        )

    except Exception as e:
        logger.error(
            "Error sending automatic poll",
            extra={
                "user_id": user_id,
                "error": str(e)
            },
            exc_info=True
        )
        # Don't propagate exception - scheduler should continue


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


async def send_category_reminder(bot: Bot, user_id: int) -> None:
    """
    Send reminder to user about category selection.

    This is used when user clicks "Remind Later" button during
    category selection in poll activity recording flow.

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
                "User not found for category reminder",
                extra={"user_id": user_id}
            )
            return

        # Get settings
        settings = await services.user_settings.get_by_user_id(user["id"])

        # Get categories
        categories = await services.category.get_user_categories(user["id"])

        if not categories:
            # If user has no categories, send them to main menu
            text = (
                "⏰ Напоминание!\n\n"
                "У тебя нет категорий. Сначала создай категорию."
            )
            await bot.send_message(
                chat_id=user_id,
                text=text
            )
            return

        # Calculate poll period based on last activity
        start_time, end_time = await calculate_poll_period(
            services.activity,
            user["id"],
            settings
        )

        # Format time and duration for display
        start_time_str = format_time(start_time)
        end_time_str = format_time(end_time)
        duration_minutes = int((end_time - start_time).total_seconds() / 60)
        duration_str = format_duration(duration_minutes)

        # Send category selection message
        category_text = get_category_selection_message(
            source="poll",
            start_time=start_time_str,
            end_time=end_time_str,
            duration=duration_str,
            add_motivation=True
        )
        text = f"⏰ Напоминание!\n\n{category_text}"

        # Import here to avoid circular dependency
        from src.api.keyboards.poll import get_poll_category_keyboard

        await bot.send_message(
            chat_id=user_id,
            text=text,
            reply_markup=get_poll_category_keyboard(categories)
        )

        logger.info(
            "Sent category reminder to user",
            extra={"user_id": user_id}
        )

    except Exception as e:
        logger.error(
            "Error sending category reminder",
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


async def _postpone_poll(bot: Bot, user_id: int, services) -> None:
    """
    Postpone poll delivery by configured minutes.

    Args:
        bot: Bot instance
        user_id: Telegram user ID
        services: Service container with scheduler access
    """
    try:
        next_poll_time = datetime.now(timezone.utc) + timedelta(
            minutes=POLL_POSTPONE_MINUTES
        )

        # Remove existing job if any
        if user_id in services.scheduler.jobs:
            try:
                services.scheduler.scheduler.remove_job(
                    services.scheduler.jobs[user_id]
                )
            except Exception:
                pass

        # Schedule postponed poll
        # AsyncIOExecutor handles async functions directly
        job = services.scheduler.scheduler.add_job(
            lambda: send_automatic_poll(bot, user_id),
            trigger=DateTrigger(run_date=next_poll_time),
            id=f"poll_postponed_{user_id}_{next_poll_time.timestamp()}",
            replace_existing=True
        )

        services.scheduler.jobs[user_id] = job.id

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


async def _send_poll_message(bot: Bot, user_id: int, settings: dict, categories: list) -> None:
    """
    Build and send poll message to user with category selection.

    Args:
        bot: Bot instance
        user_id: Telegram user ID
        settings: User settings dict
        categories: List of user categories
    """
    # Calculate time since last poll for accurate message
    interval_minutes = get_poll_interval(settings)

    # Format time string
    time_str = _format_interval_time(interval_minutes)

    # Build poll message - directly ask for category
    text = (
        "⏰ Время проверки активности!\n\n"
        f"Чем ты занимался последние {time_str}?\n\n"
        "📂 Выбери категорию:"
    )

    await bot.send_message(
        chat_id=user_id,
        text=text,
        reply_markup=get_poll_initial_category_keyboard(categories)
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


async def _set_poll_category_state(bot: Bot, user_id: int) -> None:
    """
    Set FSM state to waiting for category selection.

    Args:
        bot: Bot instance
        user_id: Telegram user ID
    """
    try:
        storage = get_fsm_storage()
        key = StorageKey(
            bot_id=bot.id,
            chat_id=user_id,
            user_id=user_id
        )

        await storage.set_state(key, ActivityStates.waiting_for_category)

        logger.debug(
            "Set FSM state to waiting_for_poll_category",
            extra={"user_id": user_id}
        )

    except Exception as e:
        logger.warning(
            "Could not set FSM state",
            extra={"user_id": user_id, "error": str(e)}
        )
