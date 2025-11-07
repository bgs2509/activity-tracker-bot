"""Activity creation handlers for recording new activities."""

import logging
from datetime import datetime, timezone

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext

from src.api.states.activity import ActivityStates
from src.api.dependencies import ServiceContainer
from src.api.keyboards.time_select import get_start_time_keyboard, get_end_time_keyboard
from src.api.keyboards.main_menu import get_main_menu_keyboard
from src.api.keyboards.poll import get_poll_category_keyboard
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
        "Можешь отправить:\n"
        "• Точное время: 14:30 или 14-30\n"
        "• Минуты назад: 30м или 30\n"
        "• Часы назад: 2ч или 2h\n\n"
        "Примеры:\n"
        "14:30 — началось в 14:30\n"
        "90м — началось 90 минут назад\n"
        "2ч — началось 2 часа назад"
    )

    await callback.message.answer(text, reply_markup=get_start_time_keyboard())
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
            "Можешь отправить:\n"
            "• Точное время: 16:00\n"
            "• Продолжительность: 30м (длилось 30 минут)\n"
            "• \"Сейчас\" или \"0\" — закончилось только что"
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
            "Можешь отправить:\n"
            "• Точное время: 16:00\n"
            "• Продолжительность: 30м\n"
            "• \"Сейчас\" — закончилось только что"
        )

        await callback.message.answer(text, reply_markup=get_end_time_keyboard())

    await callback.answer()


@router.callback_query(F.data.startswith("time_end_"))
@with_typing_action
async def quick_end_time(callback: types.CallbackQuery, state: FSMContext):
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
        elif time_key == "4h":
            # "4ч длилось" - duration 4 hours
            end_time = parse_duration("4ч", start_time)
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

        # Save to FSM and proceed to next step
        await state.update_data(end_time=end_time.isoformat())
        await state.set_state(ActivityStates.waiting_for_description)

        # Schedule FSM timeout
        if fsm_timeout_module.fsm_timeout_service:
            fsm_timeout_module.fsm_timeout_service.schedule_timeout(
                user_id=callback.from_user.id,
                state=ActivityStates.waiting_for_description,
                bot=callback.bot
            )

        start_time_str = format_time(start_time)
        end_time_str = format_time(end_time)
        duration_minutes = int((end_time - start_time).total_seconds() / 60)
        duration_str = format_duration(duration_minutes)

        text = (
            f"✏️ Опиши активность\n\n"
            f"⏰ {start_time_str} — {end_time_str} ({duration_str})\n\n"
            f"Напиши, чем ты занимался (минимум 3 символа).\n"
            f"Можешь добавить теги через #хештег"
        )

        await callback.message.answer(text, reply_markup=get_main_menu_keyboard())
        await callback.answer()

    except ValueError as e:
        logger.error(f"Error parsing end time: {e}")
        await callback.message.answer(
            f"⚠️ Ошибка при обработке времени: {str(e)}",
            reply_markup=get_end_time_keyboard()
        )
        await callback.answer()


@router.message(ActivityStates.waiting_for_end_time)
async def process_end_time(message: types.Message, state: FSMContext):
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

        # Save to FSM and proceed to next step
        await state.update_data(end_time=end_time.isoformat())
        await state.set_state(ActivityStates.waiting_for_description)

        # Schedule FSM timeout
        if fsm_timeout_module.fsm_timeout_service:
            fsm_timeout_module.fsm_timeout_service.schedule_timeout(
                user_id=message.from_user.id,
                state=ActivityStates.waiting_for_description,
                bot=message.bot
            )

        start_time_str = format_time(start_time)
        end_time_str = format_time(end_time)
        duration_minutes = int((end_time - start_time).total_seconds() / 60)
        duration_str = format_duration(duration_minutes)

        text = (
            f"✏️ Опиши активность\n\n"
            f"⏰ {start_time_str} — {end_time_str} ({duration_str})\n\n"
            f"Напиши, чем ты занимался (минимум 3 символа).\n"
            f"Можешь добавить теги через #хештег"
        )

        await message.answer(text, reply_markup=get_main_menu_keyboard())

    except ValueError as e:
        await message.answer(
            f"⚠️ Не могу распознать время. {str(e)}\n\nПопробуй ещё раз.",
            reply_markup=get_end_time_keyboard()
        )


@router.message(ActivityStates.waiting_for_description)
async def process_description(message: types.Message, state: FSMContext, services: ServiceContainer):
    """Process activity description (text message)."""
    description = message.text.strip()

    if not description or len(description) < 3:
        await message.answer("⚠️ Описание должно содержать минимум 3 символа. Попробуй ещё раз.")
        return

    # Extract tags from description
    tags = extract_tags(description)

    # Save to FSM
    await state.update_data(description=description, tags=tags)
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
                "⚠️ У тебя нет категорий. Активность будет сохранена без категории.",
                reply_markup=get_main_menu_keyboard()
            )
            # Save without category
            await save_activity(message, state, user["id"], None, message.from_user.id, services)
            return

        # Store categories and user_id for callback handlers
        await state.update_data(
            categories=categories,
            user_id=user["id"]
        )

        text = (
            "📂 Выбери категорию\n\n"
            "Или отправь \"0\" чтобы пропустить."
        )

        await message.answer(
            text,
            reply_markup=get_poll_category_keyboard(categories)
        )

    except Exception as e:
        logger.error(f"Error in process_description: {e}")
        await message.answer(
            "⚠️ Произошла ошибка.",
            reply_markup=get_main_menu_keyboard()
        )
        await state.clear()


@router.callback_query(ActivityStates.waiting_for_category, F.data.startswith("poll_category_"))
@with_typing_action
async def process_category_callback(callback: types.CallbackQuery, state: FSMContext, services: ServiceContainer):
    """Process category selection via inline button.

    User selected category from inline keyboard. Extract category_id
    from callback_data and proceed to time selection.
    """
    category_id = int(callback.data.split("_")[-1])

    data = await state.get_data()
    categories = data.get("categories", [])
    user_id = data.get("user_id")

    # Find selected category for display
    selected_category = next(
        (cat for cat in categories if cat["id"] == category_id),
        None
    )

    if not selected_category:
        await callback.message.answer("⚠️ Категория не найдена.")
        await callback.answer()
        return

    # Save activity with selected category
    await save_activity(
        callback.message, state, user_id, category_id, callback.from_user.id, services
    )
    await callback.answer()


@router.callback_query(ActivityStates.waiting_for_category, F.data == "poll_cancel")
@with_typing_action
async def cancel_category_selection(callback: types.CallbackQuery, state: FSMContext):
    """Handle cancel button in category selection.

    User clicked cancel button - clear state and return to main menu.
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

            # Save activity without category
            await save_activity(message, state, user["id"], None, message.from_user.id, services)

        except Exception as e:
            logger.error(f"Error in process_category: {e}")
            await message.answer(
                "⚠️ Произошла ошибка.",
                reply_markup=get_main_menu_keyboard()
            )
            await state.clear()
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
    services: ServiceContainer
):
    """Save activity to database."""
    data = await state.get_data()
    start_time_str = data.get("start_time")
    end_time_str = data.get("end_time")
    description = data.get("description")
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

