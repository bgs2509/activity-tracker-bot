"""Main menu keyboard."""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Get main menu keyboard."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Записать активность", callback_data="add_activity")],
        [InlineKeyboardButton(text="📋 Мои записи", callback_data="my_activities")],
        [InlineKeyboardButton(text="📂 Категории", callback_data="categories")],
        [InlineKeyboardButton(text="❓ Справка", callback_data="help")],
    ])
    return keyboard
