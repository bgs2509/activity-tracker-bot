"""Main menu keyboard."""
from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Get main menu keyboard with improved layout.

    Layout structure:
    - Row 1: Primary actions (Add, View) - most used features
    - Row 2: Help (centered) - auxiliary

    Best practices applied:
    - 2 buttons per row for optimal readability
    - Compact layout with essential features
    - Settings and Categories accessed via commands: /settings and /category

    Note:
        Categories and Settings are now command-based (/category, /settings)
        to reduce visual clutter and improve main menu clarity.
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        # Primary actions - most frequently used
        [
            InlineKeyboardButton(text="📝 Записать", callback_data="add_activity"),
            InlineKeyboardButton(text="📋 Мои записи", callback_data="my_activities"),
        ],
        # Auxiliary - full width for visual separation
        [
            InlineKeyboardButton(text="❓ Справка", callback_data="help"),
        ],
    ])
    return keyboard


def get_persistent_reply_keyboard() -> ReplyKeyboardMarkup:
    """Get persistent reply keyboard with quick access to activity recording.

    This keyboard is always visible at the bottom of the Telegram chat,
    providing instant access to the most important action - recording activity.

    Best practices applied:
    - Single primary action for maximum clarity
    - Always visible (persistent=True) for instant access
    - Compact size (resize_keyboard=True) for better UX
    - Works alongside InlineKeyboards without conflicts

    Returns:
        ReplyKeyboardMarkup: Persistent keyboard with activity recording button
    """
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Записать активность")],
        ],
        resize_keyboard=True,  # Compact size
        persistent=True,       # Always visible
    )
    return keyboard


async def send_main_menu(message: types.Message) -> None:
    """Send main menu with unified text and keyboard.

    This function provides a single point of control for displaying the main menu,
    ensuring consistency across all entry points (/start command, main_menu callbacks, etc.).

    Args:
        message: Telegram message object to send the menu to

    Best practices applied:
    - DRY principle: Single source of truth for main menu display
    - Consistent UX: Same text and keyboard everywhere
    - Easy maintenance: Update in one place to affect all usages
    """
    await message.answer(
        "🏠 Главное меню",
        reply_markup=get_main_menu_keyboard()
    )
