"""Main settings menu handler."""

import logging
from datetime import datetime, timezone

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from src.api.dependencies import ServiceContainer
from src.api.keyboards.settings import get_main_settings_keyboard
from src.api.keyboards.main_menu import get_main_menu_keyboard
from src.application.services import fsm_timeout_service as fsm_timeout_module
from src.application.utils.decorators import with_typing_action
from src.application.utils.formatters import format_duration
from src.core.logging_middleware import log_user_action

from .helpers import get_user_and_settings, get_error_reply_markup

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "settings")
@with_typing_action
@log_user_action("settings_button_clicked")
async def show_settings_menu(
    callback: types.CallbackQuery,
    services: ServiceContainer
) -> None:
    """
    Show main settings menu.

    Displays current user settings including:
    - Poll intervals (weekday/weekend)
    - Next scheduled poll time
    - Quiet hours configuration
    - Reminder settings

    Args:
        callback: Telegram callback query from settings button
        services: Service container with data access
    """
    telegram_id = callback.from_user.id

    logger.debug(
        "User opened settings menu",
        extra={"user_id": telegram_id}
    )

    # Get user and settings using DRY helper
    user, settings = await get_user_and_settings(telegram_id, services)

    if not user:
        await callback.message.answer(
            "⚠️ Пользователь не найден.",
            reply_markup=get_error_reply_markup()
        )
        await callback.answer()
        return

    if not settings:
        await callback.message.answer(
            "⚠️ Настройки не найдены.",
            reply_markup=get_error_reply_markup()
        )
        await callback.answer()
        return

    # Format interval strings
    weekday_minutes = settings["poll_interval_weekday"]
    weekday_str = format_duration(weekday_minutes)

    weekend_minutes = settings["poll_interval_weekend"]
    weekend_str = format_duration(weekend_minutes)

    # Format quiet hours
    quiet_enabled = settings["quiet_hours_start"] is not None
    if quiet_enabled:
        quiet_text = (
            f"С {settings['quiet_hours_start'][:5]} "
            f"до {settings['quiet_hours_end'][:5]}"
        )
    else:
        quiet_text = "Выключены"

    # Format reminder status
    reminder_status = (
        "Включены ✅" if settings["reminder_enabled"] else "Выключены ❌"
    )

    # Get next poll time from scheduler
    next_poll_text = await _get_next_poll_text(telegram_id, settings, user, callback, services)

    # Build settings message
    text = _build_settings_text(
        weekday_str=weekday_str,
        weekend_str=weekend_str,
        next_poll_text=next_poll_text,
        quiet_text=quiet_text,
        reminder_status=reminder_status,
        reminder_delay=settings["reminder_delay_minutes"]
    )

    await callback.message.answer(text, reply_markup=get_main_settings_keyboard())
    await callback.answer()


async def _get_next_poll_text(
    telegram_id: int,
    settings: dict,
    user: dict,
    callback: types.CallbackQuery,
    services: ServiceContainer
) -> str:
    """
    Get next poll time text or schedule poll if not scheduled.

    Args:
        telegram_id: Telegram user ID
        settings: User settings dict
        user: User dict
        callback: Callback query for bot access
        services: Service container with scheduler access

    Returns:
        Formatted next poll time text or empty string
    """
    next_poll_text = ""

    logger.info(
        "Checking next poll",
        extra={
            "user_id": telegram_id,
            "jobs_count": len(services.scheduler.jobs)
        }
    )

    if telegram_id in services.scheduler.jobs:
        # Poll already scheduled, get time
        next_poll_text = _format_next_poll_time(telegram_id, services)
    else:
        # No poll scheduled, schedule one now
        logger.info(
            "No poll scheduled, scheduling now",
            extra={"user_id": telegram_id}
        )
        next_poll_text = await _schedule_poll_and_get_time(
            telegram_id,
            settings,
            user,
            callback,
            services
        )

    return next_poll_text


def _format_next_poll_time(telegram_id: int, services: ServiceContainer) -> str:
    """
    Format next poll time for user.

    Args:
        telegram_id: Telegram user ID
        services: Service container with scheduler access

    Returns:
        Formatted time string or empty string if error
    """
    try:
        job_id = services.scheduler.jobs[telegram_id]
        job = services.scheduler.scheduler.get_job(job_id)

        if job and job.next_run_time:
            now = datetime.now(timezone.utc)
            time_until = job.next_run_time - now
            minutes = int(time_until.total_seconds() / 60)

            logger.debug(
                "Next poll time calculated",
                extra={
                    "user_id": telegram_id,
                    "minutes": minutes
                }
            )

            return _format_time_until(minutes)

    except Exception as e:
        logger.warning(
            "Could not get next poll time",
            extra={"user_id": telegram_id, "error": str(e)},
            exc_info=True
        )

    return ""


async def _schedule_poll_and_get_time(
    telegram_id: int,
    settings: dict,
    user: dict,
    callback: types.CallbackQuery,
    services: ServiceContainer
) -> str:
    """
    Schedule poll and return formatted next time.

    Args:
        telegram_id: Telegram user ID
        settings: User settings dict
        user: User dict
        callback: Callback query for bot access
        services: Service container with scheduler access

    Returns:
        Formatted next poll time or empty string
    """
    try:
        from src.api.handlers.poll import send_automatic_poll

        await services.scheduler.schedule_poll(
            user_id=telegram_id,
            settings=settings,
            user_timezone=user.get("timezone", "Europe/Moscow"),
            send_poll_callback=send_automatic_poll,
            bot=callback.bot
        )

        logger.info(
            "Scheduled poll from settings menu",
            extra={"user_id": telegram_id}
        )

        # Get newly scheduled time
        return _format_next_poll_time(telegram_id, services)

    except Exception as e:
        logger.error(
            "Failed to schedule poll",
            extra={"user_id": telegram_id, "error": str(e)},
            exc_info=True
        )
        return ""


def _format_time_until(minutes: int) -> str:
    """
    Format time until next poll in Russian.

    Args:
        minutes: Minutes until next poll

    Returns:
        Formatted Russian time string

    Example:
        >>> _format_time_until(45)
        '⏰ Следующий опрос через 45 минут'
        >>> _format_time_until(125)
        '⏰ Следующий опрос через 2ч 5м'
    """
    if minutes < 60:
        return f"⏰ Следующий опрос через {minutes} минут"

    hours = minutes // 60
    remaining_minutes = minutes % 60

    if remaining_minutes == 0:
        hour_word = "час" if hours == 1 else ("часа" if 1 < hours < 5 else "часов")
        return f"⏰ Следующий опрос через {hours} {hour_word}"

    return f"⏰ Следующий опрос через {hours}ч {remaining_minutes}м"


def _build_settings_text(
    weekday_str: str,
    weekend_str: str,
    next_poll_text: str,
    quiet_text: str,
    reminder_status: str,
    reminder_delay: int
) -> str:
    """
    Build settings menu text.

    Args:
        weekday_str: Formatted weekday interval
        weekend_str: Formatted weekend interval
        next_poll_text: Next poll time text (may be empty)
        quiet_text: Quiet hours text
        reminder_status: Reminder enabled status
        reminder_delay: Reminder delay in minutes

    Returns:
        Formatted settings menu text
    """
    text = (
        "**⚙️ Настройки бота**\n\n"
        "📊 **Текущие настройки:**\n\n"
        "📅 **Интервалы опросов:**\n"
        f"• Будни: каждые {weekday_str}\n"
        f"• Выходные: каждые {weekend_str}\n"
    )

    if next_poll_text:
        text += f"• {next_poll_text}\n"

    text += (
        f"\n🌙 **Тихие часы:**\n"
        f"• {quiet_text}\n"
        "(Бот не будет беспокоить в это время)\n\n"
        f"🔔 **Напоминания:**\n"
        f"• {reminder_status}\n"
        f"• Задержка: {reminder_delay} минут"
    )

    return text


@router.message(Command("cancel"))
async def cancel_settings_fsm(
    message: types.Message,
    state: FSMContext,
    services: ServiceContainer
) -> None:
    """
    Cancel any active FSM state in settings.

    Handles /cancel command to exit from:
    - Custom interval input
    - Custom quiet hours time input
    - Custom reminder delay input

    Args:
        message: Telegram message with /cancel command
        state: FSM context for state management
        services: Service container (unused but kept for consistency)
    """
    current_state = await state.get_state()

    if current_state is None:
        await message.answer(
            "Нечего отменять. Ты сейчас не в процессе настройки.",
            reply_markup=get_main_menu_keyboard()
        )
        return

    await state.clear()

    # Cancel FSM timeout if exists
    if fsm_timeout_module.fsm_timeout_service:
        fsm_timeout_module.fsm_timeout_service.cancel_timeout(message.from_user.id)

    logger.info(
        "Settings FSM cancelled",
        extra={
            "user_id": message.from_user.id,
            "cancelled_state": current_state
        }
    )

    await message.answer(
        "❌ Настройка отменена.",
        reply_markup=get_main_menu_keyboard()
    )


@router.callback_query(F.data == "main_menu")
@with_typing_action
async def return_to_main_menu(
    callback: types.CallbackQuery,
    state: FSMContext
) -> None:
    """
    Return to main menu from settings.

    Clears any active FSM state and shows main menu.

    Args:
        callback: Telegram callback query from menu button
        state: FSM context for state clearing
    """
    await state.clear()

    logger.debug(
        "Returned to main menu from settings",
        extra={"user_id": callback.from_user.id}
    )

    await callback.message.answer(
        "🏠 Главное меню",
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer()
