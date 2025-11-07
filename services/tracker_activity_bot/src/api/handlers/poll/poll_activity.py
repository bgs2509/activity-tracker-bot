"""Poll activity recording handlers for category selection and description."""

import logging
from datetime import datetime

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext

from src.api.states.poll import PollStates
from src.api.dependencies import ServiceContainer, get_service_container
from src.api.keyboards.poll import get_poll_category_keyboard
from src.api.keyboards.main_menu import get_main_menu_keyboard
from src.application.services import fsm_timeout_service as fsm_timeout_module
from src.application.utils.decorators import with_typing_action
from src.application.utils.formatters import (
    format_time,
    format_duration,
    extract_tags
)
from src.application.utils.time_helpers import calculate_poll_start_time
from src.core.logging_middleware import log_user_action

from .helpers import get_user_and_settings
from .poll_sender import send_automatic_poll

router = Router()
logger = logging.getLogger(__name__)

# Get service container for handlers that don't have it injected
services = get_service_container()


@router.callback_query(F.data == "poll_activity")
@with_typing_action
@log_user_action("poll_activity_clicked")
async def handle_poll_activity_start(
    callback: types.CallbackQuery,
    state: FSMContext
) -> None:
    """
    Handle 'I was doing something' poll response.

    Starts activity recording from poll. User will select category,
    and activity will be created with automatic time calculation.

    Args:
        callback: Telegram callback query
        state: FSM context for state management
    """
    telegram_id = callback.from_user.id

    logger.debug(
        "User started activity from poll",
        extra={"user_id": telegram_id}
    )

    try:
        user, settings = await get_user_and_settings(telegram_id, services)
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
                telegram_id,
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
        logger.error(
            "Error in handle_poll_activity_start",
            extra={"user_id": telegram_id, "error": str(e)},
            exc_info=True
        )
        await callback.message.answer("⚠️ Произошла ошибка.")
        await callback.answer()


@router.callback_query(
    PollStates.waiting_for_poll_category,
    F.data.startswith("poll_category_")
)
@with_typing_action
async def handle_poll_category_select(
    callback: types.CallbackQuery,
    state: FSMContext
) -> None:
    """
    Handle category selection in poll activity recording.

    After category is selected, asks user for activity description
    with time range information.

    Args:
        callback: Telegram callback query with category data
        state: FSM context for state management
    """
    category_id = int(callback.data.split("_")[-1])
    telegram_id = callback.from_user.id

    try:
        user, settings = await get_user_and_settings(telegram_id, services)
        if not user or not settings:
            await _cancel_poll_activity(
                callback.message,
                callback,
                state,
                telegram_id,
                "⚠️ Ошибка получения настроек."
            )
            return

        # Calculate time range based on poll interval
        end_time = datetime.now(datetime.timezone.utc)
        start_time = calculate_poll_start_time(end_time, settings)

        # Calculate interval for display
        from src.application.utils.time_helpers import get_poll_interval
        interval_minutes = get_poll_interval(settings)

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
                user_id=telegram_id,
                state=PollStates.waiting_for_poll_description,
                bot=callback.bot
            )

        # Format duration and time
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
        logger.error(
            "Error in handle_poll_category_select",
            extra={"user_id": telegram_id, "error": str(e)},
            exc_info=True
        )
        await _cancel_poll_activity(
            callback.message,
            callback,
            state,
            telegram_id,
            "⚠️ Произошла ошибка."
        )


@router.message(PollStates.waiting_for_poll_description)
async def handle_poll_description(
    message: types.Message,
    state: FSMContext,
    services: ServiceContainer
) -> None:
    """
    Handle description input for poll activity recording.

    After user provides description, creates activity with all collected data
    and schedules next poll.

    Args:
        message: Telegram message with description text
        state: FSM context with activity data
        services: Service container with data access
    """
    description = message.text.strip()

    # Validate description length
    if not description or len(description) < 3:
        await message.answer(
            "⚠️ Описание должно содержать минимум 3 символа. Попробуй ещё раз."
        )
        return

    # Extract tags from description
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
        await _cancel_poll_activity_message(
            message,
            state,
            message.from_user.id,
            "⚠️ Недостаточно данных для сохранения."
        )
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
        await services.scheduler.schedule_poll(
            user_id=telegram_id,
            settings=settings,
            user_timezone=user_timezone,
            send_poll_callback=send_automatic_poll,
            bot=message.bot
        )

        # Format duration for success message
        duration_minutes = int((end_time - start_time).total_seconds() / 60)
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
        logger.error(
            "Error in handle_poll_description",
            extra={"user_id": telegram_id, "error": str(e)},
            exc_info=True
        )
        await _cancel_poll_activity_message(
            message,
            state,
            telegram_id,
            "⚠️ Произошла ошибка при сохранении активности."
        )


@router.callback_query(
    PollStates.waiting_for_poll_category,
    F.data == "poll_cancel"
)
@with_typing_action
async def handle_poll_cancel(
    callback: types.CallbackQuery,
    state: FSMContext
) -> None:
    """
    Handle cancellation of poll activity recording.

    Clears FSM state and returns user to main menu.

    Args:
        callback: Telegram callback query
        state: FSM context for state clearing
    """
    await state.clear()
    if fsm_timeout_module.fsm_timeout_service:
        fsm_timeout_module.fsm_timeout_service.cancel_timeout(
            callback.from_user.id
        )

    await callback.message.answer(
        "❌ Запись активности отменена.",
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer()


# Helper functions (DRY principle)


async def _cancel_poll_activity(
    message: types.Message,
    callback: types.CallbackQuery,
    state: FSMContext,
    telegram_id: int,
    error_text: str
) -> None:
    """
    Cancel poll activity recording due to error (callback version).

    Args:
        message: Message object to send error to
        callback: Callback query to answer
        state: FSM context to clear
        telegram_id: Telegram user ID
        error_text: Error message to display
    """
    await message.answer(error_text)
    await callback.answer()
    await state.clear()

    if fsm_timeout_module.fsm_timeout_service:
        fsm_timeout_module.fsm_timeout_service.cancel_timeout(telegram_id)


async def _cancel_poll_activity_message(
    message: types.Message,
    state: FSMContext,
    telegram_id: int,
    error_text: str
) -> None:
    """
    Cancel poll activity recording due to error (message version).

    Args:
        message: Message object to send error to
        state: FSM context to clear
        telegram_id: Telegram user ID
        error_text: Error message to display
    """
    await message.answer(
        error_text,
        reply_markup=get_main_menu_keyboard()
    )
    await state.clear()

    if fsm_timeout_module.fsm_timeout_service:
        fsm_timeout_module.fsm_timeout_service.cancel_timeout(telegram_id)
