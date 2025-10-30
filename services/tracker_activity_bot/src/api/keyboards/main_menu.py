"""Main menu keyboard."""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Get main menu keyboard with improved layout.

    Layout structure:
    - Row 1: Primary actions (Add, View) - most used features
    - Row 2: Management (Categories, Stats) - configuration
    - Row 3: Help (centered) - auxiliary

    Best practices applied:
    - 2 buttons per row for optimal readability
    - Visual grouping by function
    - Compact yet readable layout
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        # Primary actions - most frequently used
        [
            InlineKeyboardButton(text="📝 Записать", callback_data="add_activity"),
            InlineKeyboardButton(text="📋 Мои записи", callback_data="my_activities"),
        ],
        # Management and configuration
        [
            InlineKeyboardButton(text="📂 Категории", callback_data="categories"),
            InlineKeyboardButton(text="📊 Статистика", callback_data="statistics"),
        ],
        # Auxiliary - full width for visual separation
        [
            InlineKeyboardButton(text="❓ Справка", callback_data="help"),
        ],
    ])
    return keyboard
