"""Activity creation handlers for recording new activities."""

import logging
from datetime import datetime, timezone

from aiogram import Router, types, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from src.api.states.activity import ActivityStates
from src.api.dependencies import ServiceContainer
from src.api.keyboards.time_select import get_start_time_keyboard, get_end_time_keyboard
from src.api.keyboards.main_menu import get_main_menu_keyboard
from src.api.keyboards.poll import get_poll_category_keyboard
from src.api.keyboards.activity import get_recent_activities_keyboard
from src.application.utils.time_parser import parse_time_input, parse_duration
from src.application.utils.formatters import format_time, format_duration, extract_tags
from src.application.utils.decorators import with_typing_action
from src.application.utils.fsm_helpers import schedule_fsm_timeout
from src.application.services import fsm_timeout_service as fsm_timeout_module
from src.core.logging_middleware import log_user_action

from .helpers import START_TIME_MAP, END_TIME_MAP, validate_start_time, validate_end_time

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "add_activity")
@with_typing_action
@log_user_action("add_activity_started")
async def start_add_activity(callback: types.CallbackQuery, state: FSMContext):
    """Start activity recording process."""
    logger.debug(
        "Starting activity creation",
        extra={
            "user_id": callback.from_user.id,
            "username": callback.from_user.username
        }
    )
    await state.set_state(ActivityStates.waiting_for_start_time)

    # Schedule FSM timeout
    await schedule_fsm_timeout(
        callback.from_user.id,
        ActivityStates.waiting_for_start_time,
        callback.bot
    )

    text = (
        "⏰ Укажи время НАЧАЛА активности\n\n"
        "Примеры:\n"
        "14:30 — началось в 14:30\n"
        "90м — началось 90 минут назад\n"
        "2ч — началось 2 часа назад"
    )

    await callback.message.answer(text, reply_markup=get_start_time_keyboard())
    await callback.answer()


@router.callback_query(
    StateFilter(ActivityStates.waiting_for_start_time, ActivityStates.waiting_for_end_time),
    F.data == "cancel"
)
@with_typing_action
@log_user_action("activity_creation_cancelled")
async def cancel_activity_creation(callback: types.CallbackQuery, state: FSMContext):
    """Cancel activity creation process.

    Handles the cancel button in time selection keyboards.
    Clears FSM state and returns user to main menu.

    Args:
        callback: Telegram callback query from cancel button
        state: FSM context for state management
    """
    logger.debug(
        "Activity creation cancelled",
        extra={
            "user_id": callback.from_user.id,
            "current_state": await state.get_state()
        }
    )

    # Clear FSM state
    await state.clear()

    # Cancel FSM timeout if exists
    if fsm_timeout_module.fsm_timeout_service:
        fsm_timeout_module.fsm_timeout_service.cancel_timeout(callback.from_user.id)

    await callback.message.answer(
        "❌ Запись активности отменена.",
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer()


@router.message(ActivityStates.waiting_for_start_time)
@log_user_action("start_time_input")
async def process_start_time(message: types.Message, state: FSMContext):
    """Process start time input."""
    logger.debug(
        "Processing start time input",
        extra={
            "user_id": message.from_user.id,
            "input_text": message.text
        }
    )
    try:
        start_time = parse_time_input(message.text)
        logger.debug(
            "Start time parsed successfully",
            extra={
                "user_id": message.from_user.id,
                "parsed_time": start_time.isoformat(),
                "input_text": message.text
            }
        )

        # Validate: start time should not be in future
        now_utc = datetime.now(timezone.utc)
        if start_time > now_utc:
            await message.answer(
                "⚠️ Время начала не может быть в будущем. Попробуй ещё раз.",
                reply_markup=get_start_time_keyboard()
            )
            return

        # Save to FSM
        await state.update_data(start_time=start_time.isoformat())
        await state.set_state(ActivityStates.waiting_for_end_time)

        # Schedule FSM timeout
        if fsm_timeout_module.fsm_timeout_service:
            fsm_timeout_module.fsm_timeout_service.schedule_timeout(
                user_id=message.from_user.id,
                state=ActivityStates.waiting_for_end_time,
                bot=message.bot
            )

        start_time_str = format_time(start_time)
        text = (
            f"⏰ Укажи время ОКОНЧАНИЯ активности\n\n"
            f"Началось: {start_time_str}\n\n"
            "Примеры:\n"
            "16:00 — закончилось в 16:00\n"
            "30м — длилось 30 минут\n"
            "0 — закончилось только что"
        )

        await message.answer(text, reply_markup=get_end_time_keyboard())

    except ValueError as e:
        await message.answer(
            f"⚠️ Не могу распознать время. {str(e)}\n\nПопробуй ещё раз.",
            reply_markup=get_start_time_keyboard()
        )


@router.callback_query(F.data.startswith("time_start_"))
@with_typing_action
@log_user_action("quick_start_time_selected")
async def quick_start_time(callback: types.CallbackQuery, state: FSMContext):
    """Handle quick time selection for start time."""
    logger.debug(
        "Quick start time selected",
        extra={
            "user_id": callback.from_user.id,
            "time_key": callback.data.replace("time_start_", "")
        }
    )
    time_map = {
        "5m": "5м",
        "15m": "15м",
        "30m": "30м",
        "1h": "1ч",
        "2h": "2ч",
        "3h": "3ч",
    }
    time_key = callback.data.replace("time_start_", "")
    time_str = time_map.get(time_key)

    if time_str:
        start_time = parse_time_input(time_str)
        await state.update_data(start_time=start_time.isoformat())
        await state.set_state(ActivityStates.waiting_for_end_time)

        # Schedule FSM timeout
        if fsm_timeout_module.fsm_timeout_service:
            fsm_timeout_module.fsm_timeout_service.schedule_timeout(
                user_id=callback.from_user.id,
                state=ActivityStates.waiting_for_end_time,
                bot=callback.bot
            )

        start_time_str = format_time(start_time)
        text = (
            f"⏰ Укажи время ОКОНЧАНИЯ активности\n\n"
            f"Началось: {start_time_str}\n\n"
            "Примеры:\n"
            "16:00 — закончилось в 16:00\n"
            "30м — длилось 30 минут\n"
            "0 — закончилось только что"
        )

        await callback.message.answer(text, reply_markup=get_end_time_keyboard())

    await callback.answer()


@router.callback_query(F.data.startswith("time_end_"))
@with_typing_action
async def quick_end_time(callback: types.CallbackQuery, state: FSMContext, services: ServiceContainer):
    """Handle quick time selection for end time."""
    time_key = callback.data.replace("time_end_", "")

    # Get start_time from state
    data = await state.get_data()
    start_time_str = data.get("start_time")

    if not start_time_str:
        await callback.message.answer(
            "⚠️ Ошибка: время начала не найдено. Попробуй ещё раз.",
            reply_markup=get_main_menu_keyboard()
        )
        await state.clear()
        # Cancel FSM timeout
        if fsm_timeout_module.fsm_timeout_service:
            fsm_timeout_module.fsm_timeout_service.cancel_timeout(callback.from_user.id)
        await callback.answer()
        return

    start_time = datetime.fromisoformat(start_time_str)

    try:
        # Map callback data to time string
        if time_key == "now":
            # "Сейчас" - current time
            end_time = datetime.now(timezone.utc)
        elif time_key == "15m":
            # "15м длилось" - duration 15 minutes
            end_time = parse_duration("15м", start_time)
        elif time_key == "30m":
            # "30м длилось" - duration 30 minutes
            end_time = parse_duration("30м", start_time)
        elif time_key == "1h":
            # "1ч длилось" - duration 1 hour
            end_time = parse_duration("1ч", start_time)
        elif time_key == "2h":
            # "2ч длилось" - duration 2 hours
            end_time = parse_duration("2ч", start_time)
        elif time_key == "3h":
            # "3ч длилось" - duration 3 hours
            end_time = parse_duration("3ч", start_time)
        elif time_key == "8h":
            # "8ч длилось" - duration 8 hours
            end_time = parse_duration("8ч", start_time)
        else:
            await callback.answer("⚠️ Неизвестная команда")
            return

        # Validate: end time should be after start time
        if end_time <= start_time:
            await callback.message.answer(
                "⚠️ Время окончания должно быть позже времени начала. Попробуй ещё раз.",
                reply_markup=get_end_time_keyboard()
            )
            await callback.answer()
            return

        # Save to FSM and proceed to category selection
        await state.update_data(end_time=end_time.isoformat())
        await state.set_state(ActivityStates.waiting_for_category)

        # Schedule FSM timeout
        if fsm_timeout_module.fsm_timeout_service:
            fsm_timeout_module.fsm_timeout_service.schedule_timeout(
                user_id=callback.from_user.id,
                state=ActivityStates.waiting_for_category,
                bot=callback.bot
            )

        # Get user's categories
        telegram_id = callback.from_user.id

        try:
            user = await services.user.get_by_telegram_id(telegram_id)
            if not user:
                await callback.message.answer(
                    "⚠️ Пользователь не найден.",
                    reply_markup=get_main_menu_keyboard()
                )
                await state.clear()
                await callback.answer()
                return

            categories = await services.category.get_user_categories(user["id"])

            if not categories:
                await callback.message.answer(
                    "⚠️ У тебя нет категорий. Создай категорию в настройках.",
                    reply_markup=get_main_menu_keyboard()
                )
                await state.clear()
                await callback.answer()
                return

            # Store user_id for later
            await state.update_data(user_id=user["id"])

            start_time_str = format_time(start_time)
            end_time_str = format_time(end_time)
            duration_minutes = int((end_time - start_time).total_seconds() / 60)
            duration_str = format_duration(duration_minutes)

            text = (
                f"📂 Выбери категорию\n\n"
                f"⏰ {start_time_str} — {end_time_str} ({duration_str})\n\n"
                "Или отправь \"0\" чтобы пропустить."
            )

            await callback.message.answer(
                text,
                reply_markup=get_poll_category_keyboard(categories, cancel_callback="activity_cancel_category")
            )
            await callback.answer()

        except Exception as e:
            logger.error(f"Error in quick_end_time: {e}")
            await callback.message.answer(
                "⚠️ Произошла ошибка.",
                reply_markup=get_main_menu_keyboard()
            )
            await state.clear()
            await callback.answer()

    except ValueError as e:
        logger.error(f"Error parsing end time: {e}")
        await callback.message.answer(
            f"⚠️ Ошибка при обработке времени: {str(e)}",
            reply_markup=get_end_time_keyboard()
        )
        await callback.answer()


@router.message(ActivityStates.waiting_for_end_time)
async def process_end_time(message: types.Message, state: FSMContext, services: ServiceContainer):
    """Process end time input (text message)."""
    # Get start_time from state
    data = await state.get_data()
    start_time_str = data.get("start_time")

    if not start_time_str:
        await message.answer(
            "⚠️ Ошибка: время начала не найдено. Попробуй ещё раз.",
            reply_markup=get_main_menu_keyboard()
        )
        await state.clear()
        # Cancel FSM timeout
        if fsm_timeout_module.fsm_timeout_service:
            fsm_timeout_module.fsm_timeout_service.cancel_timeout(message.from_user.id)
        return

    start_time = datetime.fromisoformat(start_time_str)

    try:
        # Parse end time using parse_duration
        end_time = parse_duration(message.text, start_time)

        # Validate: end time should be after start time
        if end_time <= start_time:
            await message.answer(
                "⚠️ Время окончания должно быть позже времени начала. Попробуй ещё раз.",
                reply_markup=get_end_time_keyboard()
            )
            return

        # Save to FSM and proceed to category selection
        await state.update_data(end_time=end_time.isoformat())
        await state.set_state(ActivityStates.waiting_for_category)

        # Schedule FSM timeout
        if fsm_timeout_module.fsm_timeout_service:
            fsm_timeout_module.fsm_timeout_service.schedule_timeout(
                user_id=message.from_user.id,
                state=ActivityStates.waiting_for_category,
                bot=message.bot
            )

        # Get user's categories
        telegram_id = message.from_user.id

        try:
            user = await services.user.get_by_telegram_id(telegram_id)
            if not user:
                await message.answer(
                    "⚠️ Пользователь не найден.",
                    reply_markup=get_main_menu_keyboard()
                )
                await state.clear()
                return

            categories = await services.category.get_user_categories(user["id"])

            if not categories:
                await message.answer(
                    "⚠️ У тебя нет категорий. Создай категорию в настройках.",
                    reply_markup=get_main_menu_keyboard()
                )
                await state.clear()
                return

            # Store user_id for later
            await state.update_data(user_id=user["id"])

            start_time_str = format_time(start_time)
            end_time_str = format_time(end_time)
            duration_minutes = int((end_time - start_time).total_seconds() / 60)
            duration_str = format_duration(duration_minutes)

            text = (
                f"📂 Выбери категорию\n\n"
                f"⏰ {start_time_str} — {end_time_str} ({duration_str})\n\n"
                "Или отправь \"0\" чтобы пропустить."
            )

            await message.answer(
                text,
                reply_markup=get_poll_category_keyboard(categories, cancel_callback="activity_cancel_category")
            )

        except Exception as e:
            logger.error(f"Error in process_end_time: {e}")
            await message.answer(
                "⚠️ Произошла ошибка.",
                reply_markup=get_main_menu_keyboard()
            )
            await state.clear()

    except ValueError as e:
        await message.answer(
            f"⚠️ Не могу распознать время. {str(e)}\n\nПопробуй ещё раз.",
            reply_markup=get_end_time_keyboard()
        )


@router.callback_query(ActivityStates.waiting_for_description, F.data.startswith("activity_desc_"))
@with_typing_action
async def select_recent_activity(callback: types.CallbackQuery, state: FSMContext, services: ServiceContainer):
    """Handle selection of recent activity from inline buttons.

    User clicked on one of the recent activity buttons - use that description
    to save the activity.
    """
    # Extract activity_id from callback data
    activity_id_str = callback.data.replace("activity_desc_", "")

    try:
        activity_id = int(activity_id_str)
    except ValueError:
        await callback.message.answer("⚠️ Ошибка при обработке выбора.")
        await callback.answer()
        return

    # Get all data from state
    data = await state.get_data()
    user_id = data.get("user_id")
    category_id = data.get("category_id")

    # Fetch the selected activity to get its description
    try:
        # We need to fetch the activity by ID to get its full description
        # For now, we'll ask the user to use get_user_activities and find it
        # But a better approach would be to store descriptions in callback_data or state

        # Get recent activities again to find the description
        if category_id:
            response = await services.activity.get_user_activities_by_category(
                user_id=user_id,
                category_id=category_id,
                limit=10
            )
        else:
            response = await services.activity.get_user_activities(
                user_id=user_id,
                limit=10
            )

        recent_activities = response.get("activities", []) if isinstance(response, dict) else response

        # Find the activity with matching ID
        selected_activity = next(
            (act for act in recent_activities if act.get("id") == activity_id),
            None
        )

        if not selected_activity:
            await callback.message.answer("⚠️ Активность не найдена.")
            await callback.answer()
            return

        description = selected_activity.get("description", "")
        tags = extract_tags(description)

        # Save activity with selected description
        await save_activity(
            callback.message, state, user_id, category_id, callback.from_user.id, services, description, tags
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error selecting recent activity: {e}")
        await callback.message.answer(
            "⚠️ Ошибка при сохранении активности.",
            reply_markup=get_main_menu_keyboard()
        )
        await callback.answer()


@router.callback_query(ActivityStates.waiting_for_description, F.data == "activity_custom_desc")
@with_typing_action
async def enter_custom_description(callback: types.CallbackQuery, state: FSMContext):
    """Handle 'Enter custom description' button.

    User wants to enter their own description instead of selecting from recent activities.
    Just prompt them to enter text and stay in waiting_for_description state.
    """
    data = await state.get_data()
    start_time_str = data.get("start_time")
    end_time_str = data.get("end_time")

    if not all([start_time_str, end_time_str]):
        await callback.message.answer(
            "⚠️ Ошибка: недостаточно данных. Попробуй ещё раз.",
            reply_markup=get_main_menu_keyboard()
        )
        await state.clear()
        await callback.answer()
        return

    start_time = datetime.fromisoformat(start_time_str)
    end_time = datetime.fromisoformat(end_time_str)
    start_time_str_fmt = format_time(start_time)
    end_time_str_fmt = format_time(end_time)
    duration_minutes = int((end_time - start_time).total_seconds() / 60)
    duration_str = format_duration(duration_minutes)

    text = (
        f"✏️ Опиши активность\n\n"
        f"⏰ {start_time_str_fmt} — {end_time_str_fmt} ({duration_str})\n\n"
        f"Напиши, чем ты занимался (минимум 3 символа).\n"
        f"Можешь добавить теги через #хештег"
    )

    await callback.message.answer(text, reply_markup=get_main_menu_keyboard())
    await callback.answer()


@router.message(ActivityStates.waiting_for_description)
async def process_description(message: types.Message, state: FSMContext, services: ServiceContainer):
    """Process activity description (text message).

    Description is entered as text - save activity with all collected data.
    """
    description = message.text.strip()

    if not description or len(description) < 3:
        await message.answer("⚠️ Описание должно содержать минимум 3 символа. Попробуй ещё раз.")
        return

    # Extract tags from description
    tags = extract_tags(description)

    # Get all data from state
    data = await state.get_data()
    user_id = data.get("user_id")
    category_id = data.get("category_id")

    # Save activity
    await save_activity(
        message, state, user_id, category_id, message.from_user.id, services, description, tags
    )


@router.callback_query(ActivityStates.waiting_for_category, F.data.startswith("poll_category_"))
@with_typing_action
async def process_category_callback(callback: types.CallbackQuery, state: FSMContext, services: ServiceContainer):
    """Process category selection via inline button.

    User selected category from inline keyboard. Now fetch recent activities
    for this category and show them as inline buttons for description input.
    """
    category_id = int(callback.data.split("_")[-1])

    data = await state.get_data()
    user_id = data.get("user_id")
    start_time_str = data.get("start_time")
    end_time_str = data.get("end_time")

    if not all([user_id, start_time_str, end_time_str]):
        await callback.message.answer(
            "⚠️ Ошибка: недостаточно данных. Попробуй ещё раз.",
            reply_markup=get_main_menu_keyboard()
        )
        await state.clear()
        await callback.answer()
        return

    # Save selected category_id to state
    await state.update_data(category_id=category_id)
    await state.set_state(ActivityStates.waiting_for_description)

    # Schedule FSM timeout
    if fsm_timeout_module.fsm_timeout_service:
        fsm_timeout_module.fsm_timeout_service.schedule_timeout(
            user_id=callback.from_user.id,
            state=ActivityStates.waiting_for_description,
            bot=callback.bot
        )

    # Get recent activities for this category
    try:
        response = await services.activity.get_user_activities_by_category(
            user_id=user_id,
            category_id=category_id,
            limit=10
        )
        recent_activities = response.get("activities", []) if isinstance(response, dict) else response

        start_time = datetime.fromisoformat(start_time_str)
        end_time = datetime.fromisoformat(end_time_str)
        start_time_str_fmt = format_time(start_time)
        end_time_str_fmt = format_time(end_time)
        duration_minutes = int((end_time - start_time).total_seconds() / 60)
        duration_str = format_duration(duration_minutes)

        text = (
            f"✏️ Опиши активность\n\n"
            f"⏰ {start_time_str_fmt} — {end_time_str_fmt} ({duration_str})\n\n"
        )

        if recent_activities:
            text += "Выбери из последних активностей или напиши своё (минимум 3 символа):"
            keyboard = get_recent_activities_keyboard(recent_activities)
        else:
            text += "Напиши, чем ты занимался (минимум 3 символа).\nМожешь добавить теги через #хештег"
            keyboard = get_main_menu_keyboard()

        await callback.message.answer(text, reply_markup=keyboard)
        await callback.answer()

    except Exception as e:
        logger.error(f"Error fetching recent activities: {e}")
        # Fallback: just ask for description without suggestions
        start_time = datetime.fromisoformat(start_time_str)
        end_time = datetime.fromisoformat(end_time_str)
        start_time_str_fmt = format_time(start_time)
        end_time_str_fmt = format_time(end_time)
        duration_minutes = int((end_time - start_time).total_seconds() / 60)
        duration_str = format_duration(duration_minutes)

        text = (
            f"✏️ Опиши активность\n\n"
            f"⏰ {start_time_str_fmt} — {end_time_str_fmt} ({duration_str})\n\n"
            f"Напиши, чем ты занимался (минимум 3 символа).\n"
            f"Можешь добавить теги через #хештег"
        )

        await callback.message.answer(text, reply_markup=get_main_menu_keyboard())
        await callback.answer()


@router.callback_query(ActivityStates.waiting_for_category, F.data == "activity_cancel_category")
@with_typing_action
async def cancel_category_selection(callback: types.CallbackQuery, state: FSMContext):
    """Handle cancel button in category selection.

    User clicked cancel button - clear state and return to main menu.
    Note: Uses 'activity_cancel_category' instead of 'poll_cancel' to avoid
    conflicts with poll handler which uses the same callback_data but different state.
    """
    await state.clear()
    await callback.message.answer(
        "❌ Запись активности отменена.",
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer()


@router.message(ActivityStates.waiting_for_category)
async def process_category(message: types.Message, state: FSMContext, services: ServiceContainer):
    """Process category selection (text message).

    Fallback text handler - only allows "0" to skip category.
    Main selection should be done via inline buttons.
    """
    text = message.text.strip()

    # Only allow "0" to skip category - main selection via inline buttons
    if text == "0":
        data = await state.get_data()
        user_id = data.get("user_id")
        start_time_str = data.get("start_time")
        end_time_str = data.get("end_time")

        if not all([user_id, start_time_str, end_time_str]):
            await message.answer(
                "⚠️ Ошибка: недостаточно данных. Попробуй ещё раз.",
                reply_markup=get_main_menu_keyboard()
            )
            await state.clear()
            return

        # Skip category - proceed to description without category_id
        await state.update_data(category_id=None)
        await state.set_state(ActivityStates.waiting_for_description)

        # Schedule FSM timeout
        if fsm_timeout_module.fsm_timeout_service:
            fsm_timeout_module.fsm_timeout_service.schedule_timeout(
                user_id=message.from_user.id,
                state=ActivityStates.waiting_for_description,
                bot=message.bot
            )

        start_time = datetime.fromisoformat(start_time_str)
        end_time = datetime.fromisoformat(end_time_str)
        start_time_str_fmt = format_time(start_time)
        end_time_str_fmt = format_time(end_time)
        duration_minutes = int((end_time - start_time).total_seconds() / 60)
        duration_str = format_duration(duration_minutes)

        text = (
            f"✏️ Опиши активность\n\n"
            f"⏰ {start_time_str_fmt} — {end_time_str_fmt} ({duration_str})\n\n"
            f"Напиши, чем ты занимался (минимум 3 символа).\n"
            f"Можешь добавить теги через #хештег"
        )

        await message.answer(text, reply_markup=get_main_menu_keyboard())

    else:
        # Ignore other text input - user should use inline buttons
        await message.answer(
            "⚠️ Пожалуйста, используй кнопки для выбора категории.\n"
            "Или отправь \"0\" чтобы пропустить."
        )


async def save_activity(
    message: types.Message,
    state: FSMContext,
    user_id: int,
    category_id: int | None,
    telegram_user_id: int,
    services: ServiceContainer,
    description: str | None = None,
    tags: list[str] | None = None
):
    """Save activity to database.

    Args:
        message: Telegram message object
        state: FSM context
        user_id: Internal user ID
        category_id: Category ID or None
        telegram_user_id: Telegram user ID
        services: Service container
        description: Activity description (if not provided, will get from state)
        tags: Activity tags (if not provided, will get from state)
    """
    data = await state.get_data()
    start_time_str = data.get("start_time")
    end_time_str = data.get("end_time")

    # Use provided description/tags or get from state
    if description is None:
        description = data.get("description")
    if tags is None:
        tags = data.get("tags", [])

    if not all([start_time_str, end_time_str, description]):
        await message.answer(
            "⚠️ Недостаточно данных для сохранения.",
            reply_markup=get_main_menu_keyboard()
        )
        await state.clear()
        return

    try:
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

        duration_minutes = int((end_time - start_time).total_seconds() / 60)
        duration_str = format_duration(duration_minutes)

        await message.answer(
            f"✅ Активность сохранена!\n\n"
            f"{description}\n"
            f"Продолжительность: {duration_str}",
            reply_markup=get_main_menu_keyboard()
        )
        await state.clear()
        # Cancel FSM timeout
        if fsm_timeout_module.fsm_timeout_service:
            fsm_timeout_module.fsm_timeout_service.cancel_timeout(telegram_user_id)

    except Exception as e:
        logger.error(f"Error saving activity: {e}")
        await message.answer(
            "⚠️ Ошибка при сохранении активности.",
            reply_markup=get_main_menu_keyboard()
        )
        await state.clear()
        # Cancel FSM timeout
        if fsm_timeout_module.fsm_timeout_service:
            fsm_timeout_module.fsm_timeout_service.cancel_timeout(telegram_user_id)

