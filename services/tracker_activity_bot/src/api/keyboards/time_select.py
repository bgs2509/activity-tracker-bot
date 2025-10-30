"""Time selection keyboards."""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_start_time_keyboard() -> InlineKeyboardMarkup:
    """Get keyboard for start time quick selection."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="30м назад", callback_data="time_start_30m"),
            InlineKeyboardButton(text="1ч назад", callback_data="time_start_1h"),
            InlineKeyboardButton(text="2ч назад", callback_data="time_start_2h"),
        ],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel")],
    ])
    return keyboard


def get_end_time_keyboard() -> InlineKeyboardMarkup:
    """Get keyboard for end time quick selection."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Сейчас", callback_data="time_end_now")],
        [
            InlineKeyboardButton(text="30м длилось", callback_data="time_end_30m"),
            InlineKeyboardButton(text="1ч длилось", callback_data="time_end_1h"),
            InlineKeyboardButton(text="2ч длилось", callback_data="time_end_2h"),
        ],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel")],
    ])
    return keyboard
