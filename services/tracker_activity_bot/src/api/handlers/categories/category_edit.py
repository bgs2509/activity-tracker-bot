"""Category edit FSM flow.

Handles the multi-step process of editing a category:
1. User selects category to edit
2. User selects field to edit (name or emoji)
3. User enters new value
4. Category is updated via API
"""

import logging
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
import httpx

from src.api.dependencies import ServiceContainer
from src.api.states.category import CategoryStates
from src.application.services import fsm_timeout_service as fsm_timeout_module
from src.application.utils.decorators import with_typing_action

from .helpers import (
    build_edit_category_keyboard,
    build_edit_field_keyboard,
    build_emoji_selection_keyboard,
    build_post_edit_keyboard,
    validate_category_name,
    validate_emoji,
)

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "edit_category_start")
@with_typing_action
async def edit_category_select(
    callback: types.CallbackQuery,
    services: ServiceContainer
):
    """Show category selection for editing.

    Entry point for editing a category.
    Displays list of categories with edit buttons.

    Args:
        callback: Callback query from button press
        services: Service container
    """
    telegram_id = callback.from_user.id

    # Get user
    user = await services.user.get_by_telegram_id(telegram_id)
    if not user:
        await callback.answer(
            "❌ Пользователь не найден. Используй /start",
            show_alert=True
        )
        return

    # Get categories
    categories = await services.category.get_user_categories(user["id"])

    text = "Выбери категорию для редактирования:"

    keyboard = build_edit_category_keyboard(categories)

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("edit_cat:"))
@with_typing_action
async def edit_category_select_field(
    callback: types.CallbackQuery,
    services: ServiceContainer
):
    """Show field selection for editing.

    Args:
        callback: Callback with category ID to edit
        services: Service container
    """
    category_id = int(callback.data.split(":", 1)[1])
    telegram_id = callback.from_user.id

    # Get user
    user = await services.user.get_by_telegram_id(telegram_id)
    if not user:
        await callback.answer(
            "❌ Пользователь не найден. Используй /start",
            show_alert=True
        )
        return

    # Get category info
    categories = await services.category.get_user_categories(user["id"])
    category = next((cat for cat in categories if cat["id"] == category_id), None)

    if not category:
        await callback.answer("❌ Категория не найдена", show_alert=True)
        return

    emoji = category.get("emoji", "")
    name = category["name"]

    text = (
        f'Редактирование категории "{emoji} {name}"\n\n'
        "Что ты хочешь изменить?"
    )

    keyboard = build_edit_field_keyboard(category_id)

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("edit_field:"))
@with_typing_action
async def edit_category_field_select(
    callback: types.CallbackQuery,
    services: ServiceContainer,
    state: FSMContext
):
    """Handle field selection and prompt for new value.

    Args:
        callback: Callback with field and category ID
        services: Service container
        state: FSM context
    """
    parts = callback.data.split(":", 2)
    field = parts[1]  # "name" or "emoji"
    category_id = int(parts[2])

    telegram_id = callback.from_user.id

    # Get user
    user = await services.user.get_by_telegram_id(telegram_id)
    if not user:
        await callback.answer(
            "❌ Пользователь не найден. Используй /start",
            show_alert=True
        )
        return

    # Get category info
    categories = await services.category.get_user_categories(user["id"])
    category = next((cat for cat in categories if cat["id"] == category_id), None)

    if not category:
        await callback.answer("❌ Категория не найдена", show_alert=True)
        return

    # Save category_id and field to FSM
    await state.update_data(category_id=category_id, edit_field=field)

    if field == "name":
        text = (
            f'Введи новое название для категории "{category["name"]}":\n\n'
            "Минимум 2 символа, максимум 50 символов"
        )

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить", callback_data="categories")],
        ])

        await callback.message.edit_text(text, reply_markup=keyboard)
        await state.set_state(CategoryStates.editing_name)

        # Schedule FSM timeout
        if fsm_timeout_module.fsm_timeout_service:
            fsm_timeout_module.fsm_timeout_service.schedule_timeout(
                callback.from_user.id,
                CategoryStates.editing_name,
                callback.bot
            )

    elif field == "emoji":
        emoji = category.get("emoji", "")
        text = (
            f'Выбери новый эмодзи для категории "{emoji} {category["name"]}":\n\n'
            "🎨 Творчество | 🏃 Спорт | 🚗 Транспорт\n"
            "💼 Работа | 🏠 Дом | 🛒 Покупки | 📱 Связь\n\n"
            "Или отправь свой эмодзи текстом (максимум 10 символов)"
        )

        keyboard = build_emoji_selection_keyboard()

        await callback.message.edit_text(text, reply_markup=keyboard)
        await state.set_state(CategoryStates.editing_emoji)

        # Schedule FSM timeout
        if fsm_timeout_module.fsm_timeout_service:
            fsm_timeout_module.fsm_timeout_service.schedule_timeout(
                callback.from_user.id,
                CategoryStates.editing_emoji,
                callback.bot
            )

    await callback.answer()


@router.message(CategoryStates.editing_name)
async def edit_category_name(
    message: types.Message,
    state: FSMContext,
    services: ServiceContainer
):
    """Process new category name input.

    Args:
        message: User's message with new category name
        state: FSM context
        services: Service container
    """
    name = message.text.strip()

    # Validate name
    error = validate_category_name(name)
    if error:
        await message.answer(error)
        return

    # Get category_id from FSM
    data = await state.get_data()
    category_id = data.get("category_id")

    await update_category_final(
        message.from_user.id,
        category_id,
        name=name,
        emoji=None,
        message=message,
        services=services
    )

    await state.clear()
    if fsm_timeout_module.fsm_timeout_service:
        fsm_timeout_module.fsm_timeout_service.cancel_timeout(message.from_user.id)


@router.callback_query(CategoryStates.editing_emoji, F.data.startswith("emoji:"))
@with_typing_action
async def edit_category_emoji_button(
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

    # Get category_id from FSM
    data = await state.get_data()
    category_id = data.get("category_id")

    await update_category_final(
        callback.from_user.id,
        category_id,
        name=None,
        emoji=emoji,
        message=callback.message,
        services=services
    )

    await state.clear()
    if fsm_timeout_module.fsm_timeout_service:
        fsm_timeout_module.fsm_timeout_service.cancel_timeout(callback.from_user.id)

    await callback.answer()


@router.message(CategoryStates.editing_emoji)
async def edit_category_emoji_text(
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

    # Get category_id from FSM
    data = await state.get_data()
    category_id = data.get("category_id")

    await update_category_final(
        message.from_user.id,
        category_id,
        name=None,
        emoji=emoji,
        message=message,
        services=services
    )

    await state.clear()
    if fsm_timeout_module.fsm_timeout_service:
        fsm_timeout_module.fsm_timeout_service.cancel_timeout(message.from_user.id)


async def update_category_final(
    telegram_id: int,
    category_id: int,
    name: str | None,
    emoji: str | None,
    message: types.Message,
    services: ServiceContainer
):
    """Update category in database.

    Final FSM step: PATCH /api/v1/categories/{id}

    Args:
        telegram_id: Telegram user ID
        category_id: Category ID to update
        name: New name (if editing name)
        emoji: New emoji (if editing emoji)
        message: Message object to reply to
        services: Service container
    """
    # Get user
    user = await services.user.get_by_telegram_id(telegram_id)
    if not user:
        await message.answer("❌ Пользователь не найден. Используй /start")
        return

    try:
        # Update category
        updated_category = await services.category.update_category(
            category_id=category_id,
            name=name,
            emoji=emoji
        )

        emoji_display = updated_category.get("emoji", "")
        category_name = updated_category["name"]

        if name:
            text = f'✅ Название категории изменено на "{emoji_display} {category_name}"'
        else:
            text = f'✅ Эмодзи категории изменён на "{emoji_display} {category_name}"'

        keyboard = build_post_edit_keyboard()

        await message.answer(text, reply_markup=keyboard)

        logger.info(
            "Category updated",
            extra={
                "telegram_id": telegram_id,
                "user_id": user["id"],
                "category_id": category_id,
                "new_name": name,
                "new_emoji": emoji
            }
        )

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 409:
            # Category name already exists
            text = (
                f"⚠️ Категория с названием \"{name}\" уже существует. "
                "Введи другое название."
            )
            await message.answer(text)
        else:
            logger.error(
                f"Error updating category: {e}",
                extra={"status_code": e.response.status_code}
            )
            await message.answer(
                "❌ Произошла ошибка при обновлении категории. Попробуй позже."
            )
