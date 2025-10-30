"""Categories management handler.

This handler implements full category management functionality:
- View category list
- Add new category (FSM: name → emoji)
- Delete category (selection → confirmation)

Reference: artifacts/prompts/step-01-v01.md (lines 797-955)
"""
import logging
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import httpx

from src.infrastructure.http_clients.http_client import DataAPIClient
from src.infrastructure.http_clients.category_service import CategoryService
from src.infrastructure.http_clients.user_service import UserService
from src.api.states.category import CategoryStates
from src.api.keyboards.main_menu import get_main_menu_keyboard

router = Router()
logger = logging.getLogger(__name__)

# Global API client (shared with other handlers)
api_client = DataAPIClient()


# ============================================================================
# 1. CATEGORY LIST VIEW
# ============================================================================

@router.callback_query(F.data == "categories")
async def show_categories_list(callback: types.CallbackQuery):
    """
    Show list of user's categories.

    Triggered by: Main menu "📂 Категории" button
    """
    user_service = UserService(api_client)
    category_service = CategoryService(api_client)

    telegram_id = callback.from_user.id

    # Get user
    user = await user_service.get_by_telegram_id(telegram_id)
    if not user:
        await callback.answer("❌ Пользователь не найден. Используй /start", show_alert=True)
        return

    # Get categories
    categories = await category_service.get_user_categories(user["id"])

    # Build category list text
    text = "📂 Твои категории активностей:\n\n"
    for cat in categories:
        emoji = cat.get("emoji", "")
        name = cat["name"]
        text += f"{emoji} {name}\n"

    # Build keyboard
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить категорию", callback_data="add_category")],
        [InlineKeyboardButton(text="❌ Удалить категорию", callback_data="delete_category_start")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
    ])

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


# ============================================================================
# 2. ADD CATEGORY (FSM)
# ============================================================================

@router.callback_query(F.data == "add_category")
async def add_category_start(callback: types.CallbackQuery, state: FSMContext):
    """
    Start adding a new category.

    FSM Step 1: Request category name
    """
    text = (
        "Введи название новой категории:\n\n"
        "Например: Хобби, Семья, Транспорт\n\n"
        "Минимум 2 символа, максимум 50 символов"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data="categories")],
    ])

    await callback.message.edit_text(text, reply_markup=keyboard)
    await state.set_state(CategoryStates.waiting_for_name)
    await callback.answer()


@router.message(CategoryStates.waiting_for_name)
async def add_category_name(message: types.Message, state: FSMContext):
    """
    Process category name input.

    FSM Step 2: Validate name and request emoji
    """
    name = message.text.strip()

    # Validation
    if len(name) < 2:
        await message.answer("⚠️ Название должно содержать минимум 2 символа. Попробуй ещё раз:")
        return

    if len(name) > 50:
        await message.answer("⚠️ Название должно содержать максимум 50 символов. Попробуй ещё раз:")
        return

    # Save name to FSM context
    await state.update_data(category_name=name)

    # Request emoji
    text = (
        f'Выбери эмодзи для категории "{name}":\n\n'
        "Или отправь любой другой эмодзи текстом"
    )

    # Popular emoji keyboard (4 columns)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎨", callback_data="emoji:🎨"),
            InlineKeyboardButton(text="🎵", callback_data="emoji:🎵"),
            InlineKeyboardButton(text="📷", callback_data="emoji:📷"),
            InlineKeyboardButton(text="🎯", callback_data="emoji:🎯"),
        ],
        [
            InlineKeyboardButton(text="✈️", callback_data="emoji:✈️"),
            InlineKeyboardButton(text="🚗", callback_data="emoji:🚗"),
            InlineKeyboardButton(text="🏠", callback_data="emoji:🏠"),
            InlineKeyboardButton(text="👨‍👩‍👧", callback_data="emoji:👨‍👩‍👧"),
        ],
        [
            InlineKeyboardButton(text="💰", callback_data="emoji:💰"),
            InlineKeyboardButton(text="🛒", callback_data="emoji:🛒"),
            InlineKeyboardButton(text="📱", callback_data="emoji:📱"),
            InlineKeyboardButton(text="⚙️", callback_data="emoji:⚙️"),
        ],
        [
            InlineKeyboardButton(text="📞", callback_data="emoji:📞"),
            InlineKeyboardButton(text="🎪", callback_data="emoji:🎪"),
            InlineKeyboardButton(text="🎭", callback_data="emoji:🎭"),
            InlineKeyboardButton(text="🎬", callback_data="emoji:🎬"),
        ],
        [InlineKeyboardButton(text="➖ Без эмодзи", callback_data="emoji:none")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="categories")],
    ])

    await message.answer(text, reply_markup=keyboard)
    await state.set_state(CategoryStates.waiting_for_emoji)


@router.callback_query(CategoryStates.waiting_for_emoji, F.data.startswith("emoji:"))
async def add_category_emoji_button(callback: types.CallbackQuery, state: FSMContext):
    """
    Process emoji selection from keyboard.

    FSM Step 3: Create category
    """
    emoji_value = callback.data.split(":", 1)[1]
    emoji = None if emoji_value == "none" else emoji_value

    await create_category_final(callback.from_user.id, state, emoji, callback.message)
    await state.clear()
    await callback.answer()


@router.message(CategoryStates.waiting_for_emoji)
async def add_category_emoji_text(message: types.Message, state: FSMContext):
    """
    Process emoji sent as text message.

    FSM Step 3: Create category
    """
    emoji = message.text.strip() if message.text else None

    await create_category_final(message.from_user.id, state, emoji, message)
    await state.clear()


async def create_category_final(telegram_id: int, state: FSMContext, emoji: str | None, message: types.Message):
    """
    Create category in database.

    Final FSM step: POST /api/v1/categories
    """
    user_service = UserService(api_client)
    category_service = CategoryService(api_client)

    # Get user
    user = await user_service.get_by_telegram_id(telegram_id)
    if not user:
        await message.answer("❌ Пользователь не найден. Используй /start")
        return

    # Get category name from FSM context
    data = await state.get_data()
    name = data.get("category_name")

    try:
        # Create category
        category = await category_service.create_category(
            user_id=user["id"],
            name=name,
            emoji=emoji,
            is_default=False
        )

        emoji_display = emoji if emoji else ""
        text = f"✅ Категория \"{emoji_display} {name}\" успешно добавлена!"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить ещё категорию", callback_data="add_category")],
            [InlineKeyboardButton(text="📂 К списку категорий", callback_data="categories")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
        ])

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
            text = f"⚠️ Категория с названием \"{name}\" уже существует. Введи другое название."
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отменить", callback_data="categories")],
            ])
            await message.answer(text, reply_markup=keyboard)
            await state.set_state(CategoryStates.waiting_for_name)
        else:
            logger.error(f"Error creating category: {e}", extra={"status_code": e.response.status_code})
            await message.answer("❌ Произошла ошибка при создании категории. Попробуй позже.")


# ============================================================================
# 3. DELETE CATEGORY
# ============================================================================

@router.callback_query(F.data == "delete_category_start")
async def delete_category_select(callback: types.CallbackQuery):
    """
    Show category selection for deletion.

    Step 1: Display categories as inline buttons
    """
    user_service = UserService(api_client)
    category_service = CategoryService(api_client)

    telegram_id = callback.from_user.id

    # Get user
    user = await user_service.get_by_telegram_id(telegram_id)
    if not user:
        await callback.answer("❌ Пользователь не найден. Используй /start", show_alert=True)
        return

    # Get categories
    categories = await category_service.get_user_categories(user["id"])

    text = "Выбери категорию для удаления:"

    # Build category buttons (2 per row)
    buttons = []
    for i, cat in enumerate(categories):
        emoji = cat.get("emoji", "")
        name = cat["name"]
        button = InlineKeyboardButton(
            text=f"{emoji} {name}",
            callback_data=f"delete_cat:{cat['id']}"
        )
        if i % 2 == 0:
            buttons.append([button])
        else:
            buttons[-1].append(button)

    # Add cancel buttons
    buttons.append([InlineKeyboardButton(text="🔙 Назад к списку категорий", callback_data="categories")])
    buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("delete_cat:"))
async def delete_category_confirm(callback: types.CallbackQuery):
    """
    Request confirmation for category deletion.

    Step 2: Show confirmation dialog
    """
    category_id = int(callback.data.split(":", 1)[1])

    user_service = UserService(api_client)
    category_service = CategoryService(api_client)

    telegram_id = callback.from_user.id

    # Get user
    user = await user_service.get_by_telegram_id(telegram_id)
    if not user:
        await callback.answer("❌ Пользователь не найден. Используй /start", show_alert=True)
        return

    # Get category info
    categories = await category_service.get_user_categories(user["id"])
    category = next((cat for cat in categories if cat["id"] == category_id), None)

    if not category:
        await callback.answer("❌ Категория не найдена", show_alert=True)
        return

    emoji = category.get("emoji", "")
    name = category["name"]

    text = (
        f'⚠️ Ты уверен, что хочешь удалить категорию "{emoji} {name}"?\n\n'
        "Все активности с этой категорией останутся, но без категории."
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"delete_confirm:{category_id}")],
        [InlineKeyboardButton(text="❌ Нет, отменить", callback_data="categories")],
    ])

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("delete_confirm:"))
async def delete_category_execute(callback: types.CallbackQuery):
    """
    Execute category deletion.

    Step 3: DELETE /api/v1/categories/{id}
    """
    category_id = int(callback.data.split(":", 1)[1])

    user_service = UserService(api_client)
    category_service = CategoryService(api_client)

    telegram_id = callback.from_user.id

    # Get user
    user = await user_service.get_by_telegram_id(telegram_id)
    if not user:
        await callback.answer("❌ Пользователь не найден. Используй /start", show_alert=True)
        return

    # Get category info before deletion
    categories = await category_service.get_user_categories(user["id"])
    category = next((cat for cat in categories if cat["id"] == category_id), None)

    if not category:
        await callback.answer("❌ Категория не найдена", show_alert=True)
        return

    emoji = category.get("emoji", "")
    name = category["name"]

    try:
        # Delete category
        await category_service.delete_category(category_id)

        text = f"✅ Категория \"{emoji} {name}\" удалена."

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📂 К списку категорий", callback_data="categories")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
        ])

        await callback.message.edit_text(text, reply_markup=keyboard)
        logger.info(
            "Category deleted",
            extra={
                "telegram_id": telegram_id,
                "user_id": user["id"],
                "category_id": category_id,
                "category_name": name
            }
        )

    except ValueError as e:
        # Cannot delete last category
        text = "⚠️ Нельзя удалить последнюю категорию. Должна остаться хотя бы одна."

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📂 К списку категорий", callback_data="categories")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
        ])

        await callback.message.edit_text(text, reply_markup=keyboard)
        logger.warning(
            "Attempted to delete last category",
            extra={"telegram_id": telegram_id, "user_id": user["id"]}
        )

    except httpx.HTTPStatusError as e:
        logger.error(f"Error deleting category: {e}", extra={"status_code": e.response.status_code})
        await callback.answer("❌ Произошла ошибка при удалении категории", show_alert=True)

    await callback.answer()


# ============================================================================
# 4. MAIN MENU NAVIGATION
# ============================================================================

@router.callback_query(F.data == "main_menu")
async def show_main_menu(callback: types.CallbackQuery):
    """Return to main menu."""
    text = "Выбери действие:"
    await callback.message.edit_text(text, reply_markup=get_main_menu_keyboard())
    await callback.answer()
