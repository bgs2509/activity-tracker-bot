"""Activity handlers (simplified PoC version)."""
import logging
from datetime import datetime, timezone
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext

from src.api.states.activity import ActivityStates
from src.infrastructure.http_clients.http_client import DataAPIClient
from src.infrastructure.http_clients.activity_service import ActivityService
from src.infrastructure.http_clients.category_service import CategoryService
from src.infrastructure.http_clients.user_service import UserService
from src.api.keyboards.time_select import get_start_time_keyboard, get_end_time_keyboard
from src.api.keyboards.main_menu import get_main_menu_keyboard
from src.application.utils.time_parser import parse_time_input, parse_duration
from src.application.utils.formatters import format_time, format_duration, extract_tags, format_activity_list

router = Router()
logger = logging.getLogger(__name__)

api_client = DataAPIClient()


@router.callback_query(F.data == "add_activity")
async def start_add_activity(callback: types.CallbackQuery, state: FSMContext):
    """Start activity recording process."""
    await state.set_state(ActivityStates.waiting_for_start_time)

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
async def process_start_time(message: types.Message, state: FSMContext):
    """Process start time input."""
    try:
        start_time = parse_time_input(message.text)

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
async def quick_start_time(callback: types.CallbackQuery, state: FSMContext):
    """Handle quick time selection for start time."""
    time_map = {"30m": "30м", "1h": "1ч", "2h": "2ч"}
    time_key = callback.data.replace("time_start_", "")
    time_str = time_map.get(time_key)

    if time_str:
        start_time = parse_time_input(time_str)
        await state.update_data(start_time=start_time.isoformat())
        await state.set_state(ActivityStates.waiting_for_end_time)

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
        await callback.answer()
        return

    start_time = datetime.fromisoformat(start_time_str)

    try:
        # Map callback data to time string
        if time_key == "now":
            # "Сейчас" - current time
            end_time = datetime.now(timezone.utc)
        elif time_key == "30m":
            # "30м длилось" - duration 30 minutes
            end_time = parse_duration("30м", start_time)
        elif time_key == "1h":
            # "1ч длилось" - duration 1 hour
            end_time = parse_duration("1ч", start_time)
        elif time_key == "2h":
            # "2ч длилось" - duration 2 hours
            end_time = parse_duration("2ч", start_time)
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

        start_time_str = format_time(start_time)
        end_time_str = format_time(end_time)
        duration_minutes = int((end_time - start_time).total_seconds() / 60)
        duration_str = format_duration(duration_minutes)

        text = (
            f"✏️ Опиши активность\n\n"
            f"⏰ {start_time_str} — {end_time_str} ({duration_str})\n\n"
            f"Напиши, чем ты занимался.\n"
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

        start_time_str = format_time(start_time)
        end_time_str = format_time(end_time)
        duration_minutes = int((end_time - start_time).total_seconds() / 60)
        duration_str = format_duration(duration_minutes)

        text = (
            f"✏️ Опиши активность\n\n"
            f"⏰ {start_time_str} — {end_time_str} ({duration_str})\n\n"
            f"Напиши, чем ты занимался.\n"
            f"Можешь добавить теги через #хештег"
        )

        await message.answer(text)

    except ValueError as e:
        await message.answer(
            f"⚠️ Не могу распознать время. {str(e)}\n\nПопробуй ещё раз.",
            reply_markup=get_end_time_keyboard()
        )


@router.message(ActivityStates.waiting_for_description)
async def process_description(message: types.Message, state: FSMContext):
    """Process activity description (text message)."""
    description = message.text.strip()

    if not description:
        await message.answer("⚠️ Описание не может быть пустым. Попробуй ещё раз.")
        return

    # Extract tags from description
    tags = extract_tags(description)

    # Save to FSM
    await state.update_data(description=description, tags=tags)
    await state.set_state(ActivityStates.waiting_for_category)

    # Get user's categories
    user_service = UserService(api_client)
    category_service = CategoryService(api_client)
    telegram_id = message.from_user.id

    try:
        user = await user_service.get_by_telegram_id(telegram_id)
        if not user:
            await message.answer(
                "⚠️ Пользователь не найден.",
                reply_markup=get_main_menu_keyboard()
            )
            await state.clear()
            return

        categories = await category_service.get_user_categories(user["id"])

        if not categories:
            await message.answer(
                "⚠️ У тебя нет категорий. Активность будет сохранена без категории.",
                reply_markup=get_main_menu_keyboard()
            )
            # Save without category
            await save_activity(message, state, user["id"], None)
            return

        # For PoC, ask user to reply with category name or number
        category_list = "\n".join([
            f"{i+1}. {cat.get('emoji', '')} {cat['name']}"
            for i, cat in enumerate(categories)
        ])

        await state.update_data(categories=categories)

        text = (
            f"📂 Выбери категорию\n\n"
            f"{category_list}\n\n"
            f"Отправь номер категории или название.\n"
            f"Или отправь \"0\" чтобы пропустить."
        )

        await message.answer(text)

    except Exception as e:
        logger.error(f"Error in process_description: {e}")
        await message.answer(
            "⚠️ Произошла ошибка.",
            reply_markup=get_main_menu_keyboard()
        )
        await state.clear()


@router.message(ActivityStates.waiting_for_category)
async def process_category(message: types.Message, state: FSMContext):
    """Process category selection (text message)."""
    user_service = UserService(api_client)
    telegram_id = message.from_user.id

    try:
        user = await user_service.get_by_telegram_id(telegram_id)
        if not user:
            await message.answer(
                "⚠️ Пользователь не найден.",
                reply_markup=get_main_menu_keyboard()
            )
            await state.clear()
            return

        data = await state.get_data()
        categories = data.get("categories", [])

        category_id = None

        # Check if user wants to skip
        if message.text.strip() == "0":
            category_id = None
        else:
            # Try to parse as number
            try:
                category_num = int(message.text.strip())
                if 1 <= category_num <= len(categories):
                    category_id = categories[category_num - 1]["id"]
                else:
                    await message.answer(
                        f"⚠️ Неверный номер. Выбери от 1 до {len(categories)} или отправь \"0\"."
                    )
                    return
            except ValueError:
                # Try to match by name
                category_name = message.text.strip().lower()
                for cat in categories:
                    if cat["name"].lower() == category_name:
                        category_id = cat["id"]
                        break

                if category_id is None:
                    await message.answer(
                        "⚠️ Категория не найдена. Попробуй ещё раз или отправь \"0\" чтобы пропустить."
                    )
                    return

        # Save activity
        await save_activity(message, state, user["id"], category_id)

    except Exception as e:
        logger.error(f"Error in process_category: {e}")
        await message.answer(
            "⚠️ Произошла ошибка.",
            reply_markup=get_main_menu_keyboard()
        )
        await state.clear()


async def save_activity(message: types.Message, state: FSMContext, user_id: int, category_id: int | None):
    """Save activity to database."""
    activity_service = ActivityService(api_client)

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
        await activity_service.create_activity(
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

    except Exception as e:
        logger.error(f"Error saving activity: {e}")
        await message.answer(
            "⚠️ Ошибка при сохранении активности.",
            reply_markup=get_main_menu_keyboard()
        )
        await state.clear()


@router.callback_query(F.data == "cancel")
async def cancel_action(callback: types.CallbackQuery, state: FSMContext):
    """Cancel current action."""
    await state.clear()
    await callback.message.answer(
        "❌ Действие отменено.",
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "my_activities")
async def show_my_activities(callback: types.CallbackQuery):
    """Show user's recent activities."""
    user_service = UserService(api_client)
    activity_service = ActivityService(api_client)

    telegram_id = callback.from_user.id

    try:
        # Get user
        user = await user_service.get_by_telegram_id(telegram_id)
        if not user:
            await callback.message.answer(
                "⚠️ Пользователь не найден. Отправь /start для регистрации.",
                reply_markup=get_main_menu_keyboard()
            )
            await callback.answer()
            return

        # Get user's activities
        response = await activity_service.get_user_activities(user["id"], limit=10)
        activities = response.get("activities", [])

        # Format and send
        text = format_activity_list(activities)

        await callback.message.answer(text, reply_markup=get_main_menu_keyboard())
        await callback.answer()

    except Exception as e:
        logger.error(f"Error fetching activities: {e}")
        await callback.message.answer(
            "⚠️ Произошла ошибка при получении активностей.",
            reply_markup=get_main_menu_keyboard()
        )
        await callback.answer()


@router.callback_query(F.data == "categories")
async def show_categories(callback: types.CallbackQuery):
    """Show user's categories."""
    user_service = UserService(api_client)
    category_service = CategoryService(api_client)

    telegram_id = callback.from_user.id

    try:
        # Get user
        user = await user_service.get_by_telegram_id(telegram_id)
        if not user:
            await callback.message.answer(
                "⚠️ Пользователь не найден. Отправь /start для регистрации.",
                reply_markup=get_main_menu_keyboard()
            )
            await callback.answer()
            return

        # Get user's categories
        categories = await category_service.get_user_categories(user["id"])

        if not categories:
            text = "У тебя пока нет категорий."
        else:
            lines = ["📂 Твои категории:\n"]
            for cat in categories:
                emoji = cat.get("emoji", "")
                name = cat["name"]
                is_default = " (по умолчанию)" if cat.get("is_default") else ""
                lines.append(f"{emoji} {name}{is_default}")
            text = "\n".join(lines)

        await callback.message.answer(text, reply_markup=get_main_menu_keyboard())
        await callback.answer()

    except Exception as e:
        logger.error(f"Error fetching categories: {e}")
        await callback.message.answer(
            "⚠️ Произошла ошибка при получении категорий.",
            reply_markup=get_main_menu_keyboard()
        )
        await callback.answer()


@router.callback_query(F.data == "help")
async def show_help(callback: types.CallbackQuery):
    """Show help message."""
    text = (
        "❓ Справка по боту\n\n"
        "Этот бот помогает отслеживать твою активность в течение дня.\n\n"
        "📝 Записать активность\n"
        "Начни запись новой активности. Бот попросит указать:\n"
        "• Время начала (14:30, 30м назад, 2ч назад)\n"
        "• Время окончания (16:00, 30м, сейчас)\n"
        "• Описание и категорию\n\n"
        "📋 Мои записи\n"
        "Просмотр последних 10 записанных активностей\n\n"
        "📂 Категории\n"
        "Список всех твоих категорий\n\n"
        "Примеры форматов времени:\n"
        "• 14:30 или 14-30 — точное время\n"
        "• 30м или 30 — минут назад\n"
        "• 2ч или 2h — часов назад\n"
        "• сейчас или 0 — текущее время"
    )

    await callback.message.answer(text, reply_markup=get_main_menu_keyboard())
    await callback.answer()


# Note: Full implementation would include:
# - process_end_time handler
# - process_description handler
# - process_category handler
# - save activity to database
# For PoC, this demonstrates the FSM flow and HTTP-only data access pattern
