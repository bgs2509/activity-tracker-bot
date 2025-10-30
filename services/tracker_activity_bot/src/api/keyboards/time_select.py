"""Time selection keyboards with improved UX.

Best practices applied:
- Comprehensive time options (5m, 15m, 30m, 1h, 2h, 3h, 4h)
- 3 buttons per row - optimal for time selection
- Visual grouping by time magnitude
- Prominent "Now" button for end time
- Consistent layout across keyboards
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_start_time_keyboard() -> InlineKeyboardMarkup:
    """Get keyboard for start time quick selection.

    Layout:
    - Row 1: Short intervals (5m, 15m, 30m) - most common
    - Row 2: Hour intervals (1h, 2h, 3h) - moderate past
    - Row 3: Cancel action
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        # Short intervals - most frequently used for quick logging
        [
            InlineKeyboardButton(text="⏱ 5м назад", callback_data="time_start_5m"),
            InlineKeyboardButton(text="⏱ 15м назад", callback_data="time_start_15m"),
            InlineKeyboardButton(text="⏱ 30м назад", callback_data="time_start_30m"),
        ],
        # Hour intervals - for activities started earlier
        [
            InlineKeyboardButton(text="🕐 1ч назад", callback_data="time_start_1h"),
            InlineKeyboardButton(text="🕑 2ч назад", callback_data="time_start_2h"),
            InlineKeyboardButton(text="🕒 3ч назад", callback_data="time_start_3h"),
        ],
        # Cancel action - separated for clarity
        [
            InlineKeyboardButton(text="❌ Отменить", callback_data="cancel"),
        ],
    ])
    return keyboard


def get_end_time_keyboard() -> InlineKeyboardMarkup:
    """Get keyboard for end time quick selection.

    Layout:
    - Row 1: "Now" button (full width) - most common choice
    - Row 2: Short durations (15m, 30m, 1h)
    - Row 3: Long durations (2h, 3h, 4h)
    - Row 4: Cancel action
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        # "Now" - most frequently used, full width for prominence
        [
            InlineKeyboardButton(text="🎯 Сейчас", callback_data="time_end_now"),
        ],
        # Short durations - common activity lengths
        [
            InlineKeyboardButton(text="⏱ 15м", callback_data="time_end_15m"),
            InlineKeyboardButton(text="⏱ 30м", callback_data="time_end_30m"),
            InlineKeyboardButton(text="🕐 1ч", callback_data="time_end_1h"),
        ],
        # Long durations - extended activities
        [
            InlineKeyboardButton(text="🕑 2ч", callback_data="time_end_2h"),
            InlineKeyboardButton(text="🕒 3ч", callback_data="time_end_3h"),
            InlineKeyboardButton(text="🕓 4ч", callback_data="time_end_4h"),
        ],
        # Cancel action - separated for clarity
        [
            InlineKeyboardButton(text="❌ Отменить", callback_data="cancel"),
        ],
    ])
    return keyboard
