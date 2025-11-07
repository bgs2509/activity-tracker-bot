"""Poll response handlers for skip, sleep, and remind actions."""

import logging
from datetime import datetime, timedelta, timezone

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from apscheduler.triggers.date import DateTrigger

from src.api.dependencies import ServiceContainer, get_service_container
from src.api.keyboards.poll import get_poll_reminder_keyboard
from src.api.keyboards.main_menu import get_main_menu_keyboard
from src.application.services.scheduler_service import scheduler_service
from src.application.utils.decorators import with_typing_action
from src.application.utils.time_helpers import calculate_poll_start_time
from src.core.logging_middleware import log_user_action

from .helpers import get_user_and_settings
from .poll_sender import send_automatic_poll, send_reminder

router = Router()
logger = logging.getLogger(__name__)

# Get service container for handlers that don't have it injected
services = get_service_container()


@router.callback_query(F.data == "poll_skip")
@with_typing_action
@log_user_action("poll_skip_clicked")
async def handle_poll_skip(
    callback: types.CallbackQuery,
    state: FSMContext
) -> None:
    """
    Handle 'Skip' poll response - user did nothing.

    Schedules next poll and confirms to user that response was recorded.

    Args:
        callback: Telegram callback query
        state: FSM context (unused but kept for consistency)
    """
    telegram_id = callback.from_user.id

    logger.debug(
        "User skipped poll",
        extra={"user_id": telegram_id}
    )

    try:
        user, settings = await get_user_and_settings(telegram_id, services)
        if not user or not settings:
            await callback.message.answer("⚠️ Ошибка получения настроек.")
            await callback.answer()
            return

        # Schedule next poll
        await _schedule_next_poll(
            telegram_id=telegram_id,
            settings=settings,
            user=user,
            bot=callback.bot
        )

        await callback.message.answer(
            "✅ Понятно, ничего не делал.\n\nСледующий опрос придёт по расписанию.",
            reply_markup=get_main_menu_keyboard()
        )
        await callback.answer()

    except Exception as e:
        logger.error(
            "Error in handle_poll_skip",
            extra={"user_id": telegram_id, "error": str(e)},
            exc_info=True
        )
        await callback.message.answer("⚠️ Произошла ошибка.")
        await callback.answer()


@router.callback_query(F.data == "poll_sleep")
@with_typing_action
@log_user_action("poll_sleep_clicked")
async def handle_poll_sleep(
    callback: types.CallbackQuery,
    state: FSMContext
) -> None:
    """
    Handle 'Sleep' poll response - user was sleeping.

    Creates or finds "Сон" category and records sleep activity
    with automatic duration calculation based on poll interval.

    Args:
        callback: Telegram callback query
        state: FSM context (unused but kept for consistency)
    """
    telegram_id = callback.from_user.id

    logger.debug(
        "User selected sleep in poll",
        extra={"user_id": telegram_id}
    )

    try:
        user, settings = await get_user_and_settings(telegram_id, services)
        if not user or not settings:
            await callback.message.answer("⚠️ Ошибка получения настроек.")
            await callback.answer()
            return

        # Find or create "Сон" category
        sleep_category = await _get_or_create_sleep_category(user["id"])

        # Calculate sleep duration from last poll time
        start_time, end_time = await _calculate_sleep_duration(user, settings)

        # Save sleep activity
        await services.activity.create_activity(
            user_id=user["id"],
            category_id=sleep_category["id"],
            description="Сон",
            tags=["сон"],
            start_time=start_time,
            end_time=end_time
        )

        # Schedule next poll
        await _schedule_next_poll(
            telegram_id=telegram_id,
            settings=settings,
            user=user,
            bot=callback.bot
        )

        # Format duration for user message
        duration_hours = (end_time - start_time).total_seconds() / 3600

        await callback.message.answer(
            f"😴 Сон сохранён!\n\nПродолжительность: {duration_hours:.1f}ч\n\n"
            f"Следующий опрос придёт по расписанию.",
            reply_markup=get_main_menu_keyboard()
        )
        await callback.answer()

    except Exception as e:
        logger.error(
            "Error in handle_poll_sleep",
            extra={"user_id": telegram_id, "error": str(e)},
            exc_info=True
        )
        await callback.message.answer("⚠️ Произошла ошибка.")
        await callback.answer()


@router.callback_query(F.data == "poll_remind")
@with_typing_action
@log_user_action("poll_remind_clicked")
async def handle_poll_remind(
    callback: types.CallbackQuery,
    state: FSMContext
) -> None:
    """
    Handle 'Remind Later' poll response.

    Schedules reminder based on user's reminder delay settings.
    If reminders are disabled, notifies user to enable them.

    Args:
        callback: Telegram callback query
        state: FSM context (unused but kept for consistency)
    """
    telegram_id = callback.from_user.id

    logger.debug(
        "User requested reminder for poll",
        extra={"user_id": telegram_id}
    )

    try:
        user, settings = await get_user_and_settings(telegram_id, services)
        if not user or not settings:
            await callback.message.answer("⚠️ Ошибка получения настроек.")
            await callback.answer()
            return

        # Check if reminders are enabled
        if not settings["reminder_enabled"]:
            await callback.message.answer(
                "⚠️ Напоминания отключены в настройках.\n\n"
                "Включи их в разделе \"Настройки\" → \"Напоминания\".",
                reply_markup=get_main_menu_keyboard()
            )
            await callback.answer()
            return

        # Schedule reminder
        delay_minutes = settings["reminder_delay_minutes"]
        reminder_time = datetime.now(timezone.utc) + timedelta(
            minutes=delay_minutes
        )

        # AsyncIOExecutor handles async functions directly
        scheduler_service.scheduler.add_job(
            lambda: send_reminder(callback.bot, telegram_id),
            trigger=DateTrigger(run_date=reminder_time),
            id=f"reminder_{telegram_id}_{reminder_time.timestamp()}",
            replace_existing=True
        )

        await callback.message.answer(
            f"⏸ Хорошо, напомню через {delay_minutes} минут.",
            reply_markup=get_poll_reminder_keyboard()
        )
        await callback.answer()

    except Exception as e:
        logger.error(
            "Error in handle_poll_remind",
            extra={"user_id": telegram_id, "error": str(e)},
            exc_info=True
        )
        await callback.message.answer("⚠️ Произошла ошибка.")
        await callback.answer()


@router.callback_query(F.data == "poll_reminder_ok")
@with_typing_action
async def handle_poll_reminder_ok(
    callback: types.CallbackQuery,
    services: ServiceContainer
) -> None:
    """
    Handle reminder confirmation.

    Simple acknowledgment handler for when user acknowledges
    they've seen the reminder notification.

    Args:
        callback: Telegram callback query
        services: Service container (unused but kept for consistency)
    """
    await callback.message.answer(
        "👌 Отлично!",
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer()


# Helper functions (DRY principle)


async def _schedule_next_poll(
    telegram_id: int,
    settings: dict,
    user: dict,
    bot
) -> None:
    """
    Schedule next automatic poll for user.

    Args:
        telegram_id: Telegram user ID
        settings: User settings dict
        user: User dict
        bot: Bot instance
    """
    user_timezone = user.get("timezone", "Europe/Moscow")

    await scheduler_service.schedule_poll(
        user_id=telegram_id,
        settings=settings,
        user_timezone=user_timezone,
        send_poll_callback=send_automatic_poll,
        bot=bot
    )

    logger.debug(
        "Scheduled next poll",
        extra={"user_id": telegram_id}
    )


async def _get_or_create_sleep_category(user_id: int) -> dict:
    """
    Get or create "Сон" category for user.

    Args:
        user_id: User ID

    Returns:
        Sleep category dict
    """
    categories = await services.category.get_user_categories(user_id)

    # Find existing sleep category
    for cat in categories:
        if cat["name"].lower() == "сон":
            logger.debug(
                "Found existing sleep category",
                extra={"user_id": user_id, "category_id": cat["id"]}
            )
            return cat

    # Create new sleep category
    sleep_category = await services.category.create_category(
        user_id=user_id,
        name="Сон",
        emoji="😴"
    )

    logger.info(
        "Created sleep category",
        extra={"user_id": user_id, "category_id": sleep_category["id"]}
    )

    return sleep_category


async def _calculate_sleep_duration(
    user: dict,
    settings: dict
) -> tuple[datetime, datetime]:
    """
    Calculate sleep duration based on last poll time or interval.

    Args:
        user: User dict
        settings: User settings dict

    Returns:
        Tuple of (start_time, end_time) as datetime objects
    """
    end_time = datetime.now(timezone.utc)

    last_poll = user.get("last_poll_time")
    if last_poll:
        # Use actual last poll time if available
        start_time = datetime.fromisoformat(last_poll.replace('Z', '+00:00'))
        logger.debug(
            "Using last_poll_time for sleep duration",
            extra={"user_id": user.get("telegram_id")}
        )
    else:
        # Fallback: use poll interval to estimate sleep duration
        start_time = calculate_poll_start_time(end_time, settings)
        logger.debug(
            "Using poll interval for sleep duration",
            extra={"user_id": user.get("telegram_id")}
        )

    return start_time, end_time
