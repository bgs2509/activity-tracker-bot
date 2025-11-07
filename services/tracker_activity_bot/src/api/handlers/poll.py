"""Poll handlers for automatic activity tracking."""
import logging
from datetime import datetime, timedelta, timezone
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.redis import RedisStorage
from apscheduler.triggers.date import DateTrigger

from src.api.states.poll import PollStates
from src.api.dependencies import ServiceContainer
from src.core.config import settings as app_settings
from src.api.keyboards.poll import (
    get_poll_response_keyboard,
    get_poll_category_keyboard,
    get_poll_reminder_keyboard
)
from src.api.keyboards.main_menu import get_main_menu_keyboard
from src.application.services.scheduler_service import scheduler_service
from src.application.services import fsm_timeout_service as fsm_timeout_module
from src.application.utils.decorators import with_typing_action
from src.application.utils.time_helpers import get_poll_interval, calculate_poll_start_time
from src.core.constants import POLL_POSTPONE_MINUTES
from src.core.logging_middleware import log_user_action

router = Router()
logger = logging.getLogger(__name__)


# Redis storage for FSM state checking
# Note: This is a separate instance from the main dispatcher's storage,
# but both connect to the same Redis, so state is shared
_fsm_storage = None


def get_fsm_storage() -> RedisStorage:
    """Get or create FSM storage instance for state checking.

    Returns:
        RedisStorage instance

    Note:
        This creates a shared FSM storage instance for checking user states.
        Must call close_fsm_storage() on shutdown to prevent connection leaks.
    """
    global _fsm_storage
    if _fsm_storage is None:
        _fsm_storage = RedisStorage.from_url(app_settings.redis_url)
        logger.info("Created shared FSM storage instance")
    return _fsm_storage


async def close_fsm_storage() -> None:
    """Close FSM storage and cleanup Redis connections.

    This function must be called during application shutdown to prevent
    connection pool leaks. It's safe to call multiple times.
    """
    global _fsm_storage
    if _fsm_storage is not None:
        await _fsm_storage.close()
        _fsm_storage = None
        logger.info("Closed FSM storage")


async def send_automatic_poll(bot: Bot, user_id: int):
    """Send automatic poll to user.

    This function is called by the scheduler to send periodic polls.

    Args:
        bot: Bot instance
        user_id: Telegram user ID
    """
    from src.api.dependencies import get_service_container
    services = get_service_container()

    try:
        # Get user
        user = await services.user.get_by_telegram_id(user_id)
        if not user:
            logger.error(f"User {user_id} not found for automatic poll")
            return

        # Get settings
        settings = await services.settings.get_settings(user["id"])
        if not settings:
            logger.error(f"Settings not found for user {user_id}")
            return

        # Check if user is in active FSM state (conflict resolution)
        # If user is in dialog, postpone poll to avoid UI confusion
        try:
            storage = get_fsm_storage()
            from aiogram.fsm.storage.base import StorageKey

            # Create storage key for this user
            key = StorageKey(
                bot_id=bot.id,
                chat_id=user_id,
                user_id=user_id
            )

            # Check current FSM state
            current_state = await storage.get_state(key)

            if current_state:
                # User is in active dialog - postpone poll
                logger.info(
                    f"User {user_id} is in FSM state '{current_state}', "
                    f"postponing poll by {POLL_POSTPONE_MINUTES} minutes"
                )

                # Reschedule poll
                next_poll_time = datetime.now(timezone.utc) + timedelta(minutes=POLL_POSTPONE_MINUTES)

                # Remove existing job if any
                if user_id in scheduler_service.jobs:
                    try:
                        scheduler_service.scheduler.remove_job(scheduler_service.jobs[user_id])
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
                logger.info(f"Postponed poll for user {user_id} to {next_poll_time}")

                return  # Skip sending poll now

        except Exception as e:
            # If FSM check fails, continue with poll anyway
            logger.warning(f"Could not check FSM state for user {user_id}: {e}")

        # Calculate time since last poll for accurate message
        interval_minutes = get_poll_interval(settings)

        hours = interval_minutes // 60
        minutes = interval_minutes % 60

        if hours > 0 and minutes > 0:
            time_str = f"{hours}ч {minutes}м"
        elif hours > 0:
            time_str = f"{hours}ч"
        else:
            time_str = f"{minutes}м"

        # Send poll message
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

        # Update last poll time for accurate sleep duration calculation
        try:
            poll_time = datetime.now(timezone.utc)
            await services.user.update_last_poll_time(user["id"], poll_time)
            logger.info(f"Updated last_poll_time for user {user_id}")
        except Exception as e:
            logger.warning(f"Could not update last_poll_time for user {user_id}: {e}")

        logger.info(f"Sent automatic poll to user {user_id}")

    except Exception as e:
        logger.error(f"Error sending automatic poll to user {user_id}: {e}")


@router.callback_query(F.data == "poll_skip")
@with_typing_action
@log_user_action("poll_skip_clicked")
async def handle_poll_skip(callback: types.CallbackQuery, state: FSMContext):
    """Handle 'Skip' poll response - user did nothing."""
    logger.debug(
        "User skipped poll",
        extra={"user_id": callback.from_user.id}
    )
    telegram_id = callback.from_user.id

    try:
        # Get user and settings
        user = await services.user.get_by_telegram_id(telegram_id)
        if not user:
            await callback.message.answer("⚠️ Пользователь не найден.")
            await callback.answer()
            return

        settings = await services.settings.get_settings(user["id"])
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
            send_poll_callback=send_automatic_poll,
            bot=callback.bot
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
@with_typing_action
@log_user_action("poll_sleep_clicked")
async def handle_poll_sleep(callback: types.CallbackQuery, state: FSMContext):
    """Handle 'Sleep' poll response - user was sleeping."""
    logger.debug(
        "User selected sleep in poll",
        extra={"user_id": callback.from_user.id}
    )
    telegram_id = callback.from_user.id

    try:
        # Get user and settings
        user = await services.user.get_by_telegram_id(telegram_id)
        if not user:
            await callback.message.answer("⚠️ Пользователь не найден.")
            await callback.answer()
            return

        settings = await services.settings.get_settings(user["id"])
        if not settings:
            await callback.message.answer("⚠️ Настройки не найдены.")
            await callback.answer()
            return

        # Find or create "Сон" category
        categories = await services.category.get_user_categories(user["id"])
        sleep_category = None
        for cat in categories:
            if cat["name"].lower() == "сон":
                sleep_category = cat
                break

        if not sleep_category:
            # Create sleep category
            sleep_category = await services.category.create_category(
                user_id=user["id"],
                name="Сон",
                emoji="😴"
            )

        # Calculate sleep duration from last poll time
        end_time = datetime.now(timezone.utc)

        last_poll = user.get("last_poll_time")
        if last_poll:
            # Use actual last poll time if available
            start_time = datetime.fromisoformat(last_poll.replace('Z', '+00:00'))
        else:
            # Fallback: use poll interval to estimate sleep duration
            start_time = calculate_poll_start_time(end_time, settings)

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
        user_timezone = user.get("timezone", "Europe/Moscow")
        await scheduler_service.schedule_poll(
            user_id=telegram_id,
            settings=settings,
            user_timezone=user_timezone,
            send_poll_callback=send_automatic_poll,
            bot=callback.bot
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
@with_typing_action
@log_user_action("poll_remind_clicked")
async def handle_poll_remind(callback: types.CallbackQuery, state: FSMContext):
    """Handle 'Remind Later' poll response."""
    logger.debug(
        "User requested reminder for poll",
        extra={"user_id": callback.from_user.id}
    )
    telegram_id = callback.from_user.id

    try:
        # Get user and settings
        user = await services.user.get_by_telegram_id(telegram_id)
        if not user:
            await callback.message.answer("⚠️ Пользователь не найден.")
            await callback.answer()
            return

        settings = await services.settings.get_settings(user["id"])
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
        logger.error(f"Error in handle_poll_remind: {e}")
        await callback.message.answer("⚠️ Произошла ошибка.")
        await callback.answer()


@router.callback_query(F.data == "poll_reminder_ok")
@with_typing_action
async def handle_poll_reminder_ok(callback: types.CallbackQuery, services: ServiceContainer):
    """Handle reminder confirmation."""
    await callback.message.answer(
        "👌 Отлично!",
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "poll_activity")
@with_typing_action
@log_user_action("poll_activity_clicked")
async def handle_poll_activity_start(callback: types.CallbackQuery, state: FSMContext):
    """Handle 'I was doing something' poll response.

    Start activity recording from poll. User will select category,
    and activity will be created with automatic time calculation.
    """
    logger.debug(
        "User started activity from poll",
        extra={"user_id": callback.from_user.id}
    )
    telegram_id = callback.from_user.id

    try:
        # Get user
        user = await services.user.get_by_telegram_id(telegram_id)
        if not user:
            await callback.message.answer("⚠️ Пользователь не найден.")
            await callback.answer()
            return

        # Get categories
        categories = await services.category.get_user_categories(user["id"])

        if not categories:
            await callback.message.answer(
                "⚠️ У тебя нет категорий. Сначала создай категорию.",
                reply_markup=get_main_menu_keyboard()
            )
            await callback.answer()
            return

        # Store user_id in state for later use
        await state.update_data(user_id=user["id"])
        await state.set_state(PollStates.waiting_for_poll_category)

        # Schedule FSM timeout
        if fsm_timeout_module.fsm_timeout_service:
            fsm_timeout_module.fsm_timeout_service.schedule_timeout(
                callback.from_user.id,
                PollStates.waiting_for_poll_category,
                callback.bot
            )

        text = (
            "✏️ Чем ты занимался?\n\n"
            "Выбери категорию активности:"
        )

        await callback.message.answer(
            text,
            reply_markup=get_poll_category_keyboard(categories)
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in handle_poll_activity_start: {e}")
        await callback.message.answer("⚠️ Произошла ошибка.")
        await callback.answer()


@router.callback_query(PollStates.waiting_for_poll_category, F.data.startswith("poll_category_"))
@with_typing_action
async def handle_poll_category_select(callback: types.CallbackQuery, state: FSMContext):
    """Handle category selection in poll activity recording.

    After category is selected, ask user for activity description.
    """
    category_id = int(callback.data.split("_")[-1])
    telegram_id = callback.from_user.id

    try:
        # Get user and settings
        user = await services.user.get_by_telegram_id(telegram_id)
        if not user:
            await callback.message.answer("⚠️ Пользователь не найден.")
            await callback.answer()
            await state.clear()
            if fsm_timeout_module.fsm_timeout_service:
                fsm_timeout_module.fsm_timeout_service.cancel_timeout(callback.from_user.id)
            return

        settings = await services.settings.get_settings(user["id"])
        if not settings:
            await callback.message.answer("⚠️ Настройки не найдены.")
            await callback.answer()
            await state.clear()
            if fsm_timeout_module.fsm_timeout_service:
                fsm_timeout_module.fsm_timeout_service.cancel_timeout(callback.from_user.id)
            return

        # Calculate time range based on poll interval
        end_time = datetime.now(timezone.utc)
        start_time = calculate_poll_start_time(end_time, settings)

        # Save data to state and ask for description
        await state.update_data(
            category_id=category_id,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            settings=settings,
            user_timezone=user.get("timezone", "Europe/Moscow")
        )
        await state.set_state(PollStates.waiting_for_poll_description)

        # Schedule FSM timeout
        if fsm_timeout_module.fsm_timeout_service:
            fsm_timeout_module.fsm_timeout_service.schedule_timeout(
                user_id=callback.from_user.id,
                state=PollStates.waiting_for_poll_description,
                bot=callback.bot
            )

        # Format duration and time
        from src.application.utils.formatters import format_time, format_duration
        start_time_str = format_time(start_time)
        end_time_str = format_time(end_time)
        duration_str = format_duration(interval_minutes)

        text = (
            f"✏️ Опиши активность\n\n"
            f"⏰ {start_time_str} — {end_time_str} ({duration_str})\n\n"
            f"Напиши, чем ты занимался (минимум 3 символа).\n"
            f"Можешь добавить теги через #хештег"
        )

        await callback.message.answer(text, reply_markup=get_main_menu_keyboard())
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in handle_poll_category_select: {e}")
        await callback.message.answer("⚠️ Произошла ошибка.")
        await state.clear()
        if fsm_timeout_module.fsm_timeout_service:
            fsm_timeout_module.fsm_timeout_service.cancel_timeout(callback.from_user.id)
        await callback.answer()


@router.message(PollStates.waiting_for_poll_description)
async def handle_poll_description(message: types.Message, state: FSMContext, services: ServiceContainer):
    """Handle description input for poll activity recording.

    After user provides description, create activity with all collected data.
    """
    description = message.text.strip()

    if not description or len(description) < 3:
        await message.answer("⚠️ Описание должно содержать минимум 3 символа. Попробуй ещё раз.")
        return

    # Extract tags from description
    from src.application.utils.formatters import extract_tags
    tags = extract_tags(description)

    # Get data from state
    data = await state.get_data()
    category_id = data.get("category_id")
    start_time_str = data.get("start_time")
    end_time_str = data.get("end_time")
    settings = data.get("settings")
    user_timezone = data.get("user_timezone")
    user_id = data.get("user_id")

    if not all([category_id, start_time_str, end_time_str, user_id]):
        await message.answer(
            "⚠️ Недостаточно данных для сохранения.",
            reply_markup=get_main_menu_keyboard()
        )
        await state.clear()
        if fsm_timeout_module.fsm_timeout_service:
            fsm_timeout_module.fsm_timeout_service.cancel_timeout(message.from_user.id)
        return

    telegram_id = message.from_user.id

    try:
        # Parse times
        start_time = datetime.fromisoformat(start_time_str)
        end_time = datetime.fromisoformat(end_time_str)

        # Create activity
        await services.activity.create_activity(
            user_id=user_id,
            category_id=category_id,
            description=description,
            tags=tags,
            start_time=start_time,
            end_time=end_time
        )

        # Schedule next poll
        await scheduler_service.schedule_poll(
            user_id=telegram_id,
            settings=settings,
            user_timezone=user_timezone,
            send_poll_callback=send_automatic_poll,
            bot=message.bot
        )

        # Format duration
        duration_minutes = int((end_time - start_time).total_seconds() / 60)
        from src.application.utils.formatters import format_duration
        duration_str = format_duration(duration_minutes)

        await message.answer(
            f"✅ Активность сохранена!\n\n"
            f"{description}\n"
            f"Продолжительность: {duration_str}\n\n"
            f"Следующий опрос придёт по расписанию.",
            reply_markup=get_main_menu_keyboard()
        )
        await state.clear()
        if fsm_timeout_module.fsm_timeout_service:
            fsm_timeout_module.fsm_timeout_service.cancel_timeout(telegram_id)

    except Exception as e:
        logger.error(f"Error in handle_poll_description: {e}")
        await message.answer(
            "⚠️ Произошла ошибка при сохранении активности.",
            reply_markup=get_main_menu_keyboard()
        )
        await state.clear()
        if fsm_timeout_module.fsm_timeout_service:
            fsm_timeout_module.fsm_timeout_service.cancel_timeout(telegram_id)


@router.callback_query(PollStates.waiting_for_poll_category, F.data == "poll_cancel")
@with_typing_action
async def handle_poll_cancel(callback: types.CallbackQuery, state: FSMContext):
    """Handle cancellation of poll activity recording."""
    await state.clear()
    if fsm_timeout_module.fsm_timeout_service:
        fsm_timeout_module.fsm_timeout_service.cancel_timeout(callback.from_user.id)
    await callback.message.answer(
        "❌ Запись активности отменена.",
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
