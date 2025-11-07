"""Category creation FSM flow.

Handles the multi-step process of creating a new category:
1. User initiates creation
2. User enters category name
3. User selects or enters emoji
4. Category is saved via API
"""

import logging
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
import httpx

from src.api.dependencies import ServiceContainer
from src.api.states.category import CategoryStates
from src.application.services import fsm_timeout_service as fsm_timeout_module
from src.api.keyboards.main_menu import get_main_menu_keyboard
from src.application.utils.decorators import with_typing_action

from .helpers import (
    build_emoji_selection_keyboard,
    build_post_creation_keyboard,
    validate_category_name,
    validate_emoji,
)

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "add_category")
@with_typing_action
async def add_category_start(callback: types.CallbackQuery, state: FSMContext):
    """Start category creation flow.

    Entry point for adding a new category.
    Sets FSM state and prompts for category name.

    Args:
        callback: Callback query from button press
        state: FSM context
    """
    text = (
        "Введи название новой категории:\n\n"
        "Например: Хобби, Семья, Транспорт\n\n"
        "Минимум 2 символа, максимум 50 символов"
    )

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data="categories")],
    ])

    await callback.message.edit_text(text, reply_markup=keyboard)
    await state.set_state(CategoryStates.waiting_for_name)

    # Schedule FSM timeout
    if fsm_timeout_module.fsm_timeout_service:
        fsm_timeout_module.fsm_timeout_service.schedule_timeout(
            callback.from_user.id,
            CategoryStates.waiting_for_name,
            callback.bot
        )

    await callback.answer()


@router.message(CategoryStates.waiting_for_name)
async def add_category_name(message: types.Message, state: FSMContext):
    """Process category name input.

    Validates the name and proceeds to emoji selection.

    Args:
        message: User's message with category name
        state: FSM context
    """
    name = message.text.strip()

    # Validate name
    error = validate_category_name(name)
    if error:
        await message.answer(error)
        return

    # Save name to FSM context
    await state.update_data(category_name=name)

    # Request emoji
    text = (
        f'Выбери эмодзи для категории "{name}":\n\n'
        "🎨 Творчество | 🏃 Спорт | 🚗 Транспорт\n"
        "💼 Работа | 🏠 Дом | 🛒 Покупки | 📱 Связь\n\n"
        "Или отправь свой эмодзи текстом (максимум 10 символов)"
    )

    keyboard = build_emoji_selection_keyboard()

    await message.answer(text, reply_markup=keyboard)
    await state.set_state(CategoryStates.waiting_for_emoji)

    # Reschedule timeout for new state
    if fsm_timeout_module.fsm_timeout_service:
        fsm_timeout_module.fsm_timeout_service.schedule_timeout(
            message.from_user.id,
            CategoryStates.waiting_for_emoji,
            message.bot
        )


@router.callback_query(CategoryStates.waiting_for_emoji, F.data.startswith("emoji:"))
@with_typing_action
async def add_category_emoji_button(
    callback: types.CallbackQuery,
    state: FSMContext,
    services: ServiceContainer
):
    """Process emoji selection from inline keyboard.

    Args:
        callback: Callback with emoji selection
        state: FSM context
        services: Service container
    """
    emoji_value = callback.data.split(":", 1)[1]
    emoji = None if emoji_value == "none" else emoji_value

    # Validate emoji length (safety check for button data)
    error = validate_emoji(emoji)
    if error:
        await callback.message.answer(error)
        await callback.answer()
        return

    await create_category_final(
        callback.from_user.id,
        state,
        emoji,
        callback.message,
        services
    )

    await state.clear()
    if fsm_timeout_module.fsm_timeout_service:
        fsm_timeout_module.fsm_timeout_service.cancel_timeout(callback.from_user.id)

    await callback.answer()


@router.message(CategoryStates.waiting_for_emoji)
async def add_category_emoji_text(
    message: types.Message,
    state: FSMContext,
    services: ServiceContainer
):
    """Process emoji sent as text message.

    Args:
        message: User's message with emoji
        state: FSM context
        services: Service container
    """
    emoji = message.text.strip() if message.text else None

    # Validate emoji length
    error = validate_emoji(emoji)
    if error:
        await message.answer(error)
        return

    await create_category_final(
        message.from_user.id,
        state,
        emoji,
        message,
        services
    )

    await state.clear()
    if fsm_timeout_module.fsm_timeout_service:
        fsm_timeout_module.fsm_timeout_service.cancel_timeout(message.from_user.id)


async def create_category_final(
    telegram_id: int,
    state: FSMContext,
    emoji: str | None,
    message: types.Message,
    services: ServiceContainer
):
    """Create category in database.

    Final FSM step: POST /api/v1/categories

    Args:
        telegram_id: Telegram user ID
        state: FSM context
        emoji: Optional emoji for category
        message: Message object to reply to
        services: Service container
    """
    # Get user
    user = await services.user.get_by_telegram_id(telegram_id)
    if not user:
        await message.answer("❌ Пользователь не найден. Используй /start")
        return

    # Get category name from FSM context
    data = await state.get_data()
    name = data.get("category_name")

    try:
        # Create category
        category = await services.category.create_category(
            user_id=user["id"],
            name=name,
            emoji=emoji,
            is_default=False
        )

        emoji_display = emoji if emoji else ""
        text = f"✅ Категория \"{emoji_display} {name}\" успешно добавлена!"

        keyboard = build_post_creation_keyboard()

        await message.answer(text, reply_markup=keyboard)

        logger.info(
            "Category created",
            extra={
                "telegram_id": telegram_id,
                "user_id": user["id"],
                "category_name": name,
                "category_id": category["id"]
            }
        )

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 409:
            # Category already exists
            text = (
                f"⚠️ Категория с названием \"{name}\" уже существует. "
                "Введи другое название."
            )

            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отменить", callback_data="categories")],
            ])

            await message.answer(text, reply_markup=keyboard)
            await state.set_state(CategoryStates.waiting_for_name)

            if fsm_timeout_module.fsm_timeout_service:
                fsm_timeout_module.fsm_timeout_service.schedule_timeout(
                    message.from_user.id,
                    CategoryStates.waiting_for_name,
                    message.bot
                )
        else:
            logger.error(
                f"Error creating category: {e}",
                extra={"status_code": e.response.status_code}
            )
            await message.answer(
                "❌ Произошла ошибка при создании категории. Попробуй позже."
            )


@router.message(Command("cancel"))
async def cancel_category_fsm(message: types.Message, state: FSMContext):
    """Cancel category creation process.

    Handles /cancel command to exit from category management FSM.

    Args:
        message: User's /cancel message
        state: FSM context
    """
    current_state = await state.get_state()

    if current_state is None or not current_state.startswith("CategoryStates"):
        await message.answer(
            "Нечего отменять. Ты сейчас не создаёшь категорию.",
            reply_markup=get_main_menu_keyboard()
        )
        return

    await state.clear()
    if fsm_timeout_module.fsm_timeout_service:
        fsm_timeout_module.fsm_timeout_service.cancel_timeout(message.from_user.id)

    await message.answer(
        "❌ Создание категории отменено.",
        reply_markup=get_main_menu_keyboard()
    )
