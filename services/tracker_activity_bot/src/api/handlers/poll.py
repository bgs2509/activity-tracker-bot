"""Poll handlers for automatic activity tracking."""
import logging
from datetime import datetime, timedelta, timezone
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext

from src.api.states.poll import PollStates
from src.infrastructure.http_clients.http_client import DataAPIClient
from src.infrastructure.http_clients.activity_service import ActivityService
from src.infrastructure.http_clients.category_service import CategoryService
from src.infrastructure.http_clients.user_service import UserService
from src.infrastructure.http_clients.user_settings_service import UserSettingsService
from src.api.keyboards.poll import (
    get_poll_response_keyboard,
    get_poll_category_keyboard,
    get_poll_reminder_keyboard
)
from src.api.keyboards.main_menu import get_main_menu_keyboard
from src.application.services.scheduler_service import scheduler_service

router = Router()
logger = logging.getLogger(__name__)

api_client = DataAPIClient()


async def send_automatic_poll(bot: Bot, user_id: int):
    """Send automatic poll to user.

    This function is called by the scheduler to send periodic polls.

    Args:
        bot: Bot instance
        user_id: Telegram user ID
    """
    user_service = UserService(api_client)
    settings_service = UserSettingsService(api_client)

    try:
        # Get user
        user = await user_service.get_by_telegram_id(user_id)
        if not user:
            logger.error(f"User {user_id} not found for automatic poll")
            return

        # Get settings
        settings = await settings_service.get_settings(user["id"])
        if not settings:
            logger.error(f"Settings not found for user {user_id}")
            return

        # Check if user is in active FSM state (conflict resolution)
        # If user is in dialog, skip this poll and reschedule
        try:
            from aiogram.fsm.storage.redis import RedisStorage
            # For now, we'll send the poll anyway
            # In production, check FSM state and skip if user is busy
            pass
        except Exception as e:
            logger.debug(f"Could not check FSM state: {e}")

        # Send poll message
        text = (
            "⏰ Время проверки активности!\n\n"
            "Чем ты занимался последние часы?\n\n"
            "Выбери один из вариантов:"
        )

        await bot.send_message(
            chat_id=user_id,
            text=text,
            reply_markup=get_poll_response_keyboard()
        )

        logger.info(f"Sent automatic poll to user {user_id}")

    except Exception as e:
        logger.error(f"Error sending automatic poll to user {user_id}: {e}")


@router.callback_query(F.data == "poll_skip")
async def handle_poll_skip(callback: types.CallbackQuery, state: FSMContext):
    """Handle 'Skip' poll response - user did nothing."""
    user_service = UserService(api_client)
    settings_service = UserSettingsService(api_client)
    telegram_id = callback.from_user.id

    try:
        # Get user and settings
        user = await user_service.get_by_telegram_id(telegram_id)
        if not user:
            await callback.message.answer("⚠️ Пользователь не найден.")
            await callback.answer()
            return

        settings = await settings_service.get_settings(user["id"])
        if not settings:
            await callback.message.answer("⚠️ Настройки не найдены.")
            await callback.answer()
            return

        # Schedule next poll
        user_timezone = user.get("timezone", "Europe/Moscow")
        await scheduler_service.schedule_poll(
            user_id=telegram_id,
            settings=settings,
            user_timezone=user_timezone,
            send_poll_callback=lambda uid: send_automatic_poll(callback.bot, uid)
        )

        await callback.message.answer(
            "✅ Понятно, ничего не делал.\n\nСледующий опрос придёт по расписанию.",
            reply_markup=get_main_menu_keyboard()
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in handle_poll_skip: {e}")
        await callback.message.answer("⚠️ Произошла ошибка.")
        await callback.answer()


@router.callback_query(F.data == "poll_sleep")
async def handle_poll_sleep(callback: types.CallbackQuery, state: FSMContext):
    """Handle 'Sleep' poll response - user was sleeping."""
    user_service = UserService(api_client)
    settings_service = UserSettingsService(api_client)
    category_service = CategoryService(api_client)
    activity_service = ActivityService(api_client)
    telegram_id = callback.from_user.id

    try:
        # Get user and settings
        user = await user_service.get_by_telegram_id(telegram_id)
        if not user:
            await callback.message.answer("⚠️ Пользователь не найден.")
            await callback.answer()
            return

        settings = await settings_service.get_settings(user["id"])
        if not settings:
            await callback.message.answer("⚠️ Настройки не найдены.")
            await callback.answer()
            return

        # Find or create "Сон" category
        categories = await category_service.get_user_categories(user["id"])
        sleep_category = None
        for cat in categories:
            if cat["name"].lower() == "сон":
                sleep_category = cat
                break

        if not sleep_category:
            # Create sleep category
            sleep_category = await category_service.create_category(
                user_id=user["id"],
                name="Сон",
                emoji="😴"
            )

        # Calculate sleep duration (from last poll time or default 8 hours)
        last_poll = user.get("last_poll_time")
        if last_poll:
            start_time = datetime.fromisoformat(last_poll.replace('Z', '+00:00'))
        else:
            # Default: 8 hours ago
            start_time = datetime.now(timezone.utc) - timedelta(hours=8)

        end_time = datetime.now(timezone.utc)

        # Save sleep activity
        await activity_service.create_activity(
            user_id=user["id"],
            category_id=sleep_category["id"],
            description="Сон",
            tags=["сон"],
            start_time=start_time,
            end_time=end_time
        )

        # Schedule next poll
        user_timezone = user.get("timezone", "Europe/Moscow")
        await scheduler_service.schedule_poll(
            user_id=telegram_id,
            settings=settings,
            user_timezone=user_timezone,
            send_poll_callback=lambda uid: send_automatic_poll(callback.bot, uid)
        )

        duration_hours = (end_time - start_time).total_seconds() / 3600

        await callback.message.answer(
            f"😴 Сон сохранён!\n\nПродолжительность: {duration_hours:.1f}ч\n\n"
            f"Следующий опрос придёт по расписанию.",
            reply_markup=get_main_menu_keyboard()
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in handle_poll_sleep: {e}")
        await callback.message.answer("⚠️ Произошла ошибка.")
        await callback.answer()


@router.callback_query(F.data == "poll_remind")
async def handle_poll_remind(callback: types.CallbackQuery, state: FSMContext):
    """Handle 'Remind Later' poll response."""
    user_service = UserService(api_client)
    settings_service = UserSettingsService(api_client)
    telegram_id = callback.from_user.id

    try:
        # Get user and settings
        user = await user_service.get_by_telegram_id(telegram_id)
        if not user:
            await callback.message.answer("⚠️ Пользователь не найден.")
            await callback.answer()
            return

        settings = await settings_service.get_settings(user["id"])
        if not settings:
            await callback.message.answer("⚠️ Настройки не найдены.")
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
        reminder_time = datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)

        # Schedule reminder using scheduler
        from apscheduler.triggers.date import DateTrigger
        scheduler_service.scheduler.add_job(
            send_reminder,
            trigger=DateTrigger(run_date=reminder_time),
            args=[callback.bot, telegram_id],
            id=f"reminder_{telegram_id}_{reminder_time.timestamp()}",
            replace_existing=True
        )

        await callback.message.answer(
            f"⏸ Хорошо, напомню через {delay_minutes} минут.",
            reply_markup=get_poll_reminder_keyboard()
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in handle_poll_remind: {e}")
        await callback.message.answer("⚠️ Произошла ошибка.")
        await callback.answer()


@router.callback_query(F.data == "poll_reminder_ok")
async def handle_poll_reminder_ok(callback: types.CallbackQuery):
    """Handle reminder confirmation."""
    await callback.message.answer(
        "👌 Отлично!",
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer()


async def send_reminder(bot: Bot, user_id: int):
    """Send reminder to user.

    Args:
        bot: Bot instance
        user_id: Telegram user ID
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

        logger.info(f"Sent reminder to user {user_id}")

    except Exception as e:
        logger.error(f"Error sending reminder to user {user_id}: {e}")


# Note: In simplified PoC, we're not implementing the full
# "I was doing something" flow with category selection.
# This would require additional FSM states and handlers.
# For now, the 3 main scenarios (skip, sleep, remind) are implemented.

# Future enhancement: Add handler for "I was doing something" option
# This would:
# 1. Set FSM state to waiting_for_poll_category
# 2. Show category selection keyboard
# 3. Handle category selection and save activity
