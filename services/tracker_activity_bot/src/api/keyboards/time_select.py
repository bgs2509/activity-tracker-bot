"""Time selection keyboards with improved UX.

Best practices applied:
- Simplified period selection in one step
- 3 buttons per row - optimal for time selection
- Visual grouping by time magnitude
- Clear period options from short to long
- Consistent layout across keyboards
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_period_keyboard() -> InlineKeyboardMarkup:
    """Get keyboard for period quick selection.

    Single-step period selection combining start and end time.
    Layout:
    - Row 1: Short periods (15min, 30min, 1h)
    - Row 2: Medium periods (3h, 8h, 12h)
    - Row 3: Cancel action
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        # Short periods - most frequently used
        [
            InlineKeyboardButton(text="15 минут", callback_data="period_15m"),
            InlineKeyboardButton(text="30 минут", callback_data="period_30m"),
            InlineKeyboardButton(text="1 час", callback_data="period_1h"),
        ],
        # Medium to long periods
        [
            InlineKeyboardButton(text="3 часа", callback_data="period_3h"),
            InlineKeyboardButton(text="8 часов", callback_data="period_8h"),
            InlineKeyboardButton(text="12 часов", callback_data="period_12h"),
        ],
        # Cancel action - separated for clarity
        [
            InlineKeyboardButton(text="❌ Отменить", callback_data="cancel"),
        ],
    ])
    return keyboard


def get_start_time_keyboard() -> InlineKeyboardMarkup:
    """Get keyboard for start time quick selection.

    Layout:
    - Row 1: Short intervals (15m, 30m, 1h) - most common
    - Row 2: Hour intervals (2h, 3h, 8h) - moderate to long past
    - Row 3: Cancel action
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        # Short intervals - most frequently used for quick logging
        [
            InlineKeyboardButton(text="15м назад", callback_data="time_start_15m"),
            InlineKeyboardButton(text="30м назад", callback_data="time_start_30m"),
            InlineKeyboardButton(text="1ч назад", callback_data="time_start_1h"),
        ],
        # Hour intervals - for activities started earlier
        [
            InlineKeyboardButton(text="2ч назад", callback_data="time_start_2h"),
            InlineKeyboardButton(text="3ч назад", callback_data="time_start_3h"),
            InlineKeyboardButton(text="8ч назад", callback_data="time_start_8h"),
        ],
        # Cancel action - separated for clarity
        [
            InlineKeyboardButton(text="❌ Отменить", callback_data="cancel"),
        ],
    ])
    return keyboard


def get_period_keyboard_with_auto() -> InlineKeyboardMarkup:
    """Period keyboard with 'Auto Calculate' button for manual flow.

    Provides quick-select period buttons plus an option to automatically
    calculate period from last activity (similar to automatic poll behavior).

    Returns:
        InlineKeyboardMarkup with auto-calculate option and period buttons

    Layout:
        [⚡️ Авто (от последней активности)]
        [───── или выбери вручную ──────]
        [15 минут] [30 минут]
        [1 час]    [3 часа]
        [8 часов]  [12 часов]
        [❌ Отменить]
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        # Auto-calculate option (prominent at top)
        [InlineKeyboardButton(
            text="⚡️ Авто (от последней активности)",
            callback_data="period_auto"
        )],
        # Visual divider (non-clickable)
        [InlineKeyboardButton(
            text="───── или выбери вручную ──────",
            callback_data="noop"
        )],
        # Quick period selection buttons (2x3 grid)
        [
            InlineKeyboardButton(text="15 минут", callback_data="period_15m"),
            InlineKeyboardButton(text="30 минут", callback_data="period_30m"),
        ],
        [
            InlineKeyboardButton(text="1 час", callback_data="period_1h"),
            InlineKeyboardButton(text="3 часа", callback_data="period_3h"),
        ],
        [
            InlineKeyboardButton(text="8 часов", callback_data="period_8h"),
            InlineKeyboardButton(text="12 часов", callback_data="period_12h"),
        ],
        # Cancel button
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel")],
    ])
    return keyboard


def get_end_time_keyboard() -> InlineKeyboardMarkup:
    """Get keyboard for end time quick selection.

    Layout:
    - Row 1: "Now" button (full width) - most common choice
    - Row 2: Short durations (15m, 30m, 1h)
    - Row 3: Long durations (2h, 3h, 8h)
    - Row 4: Cancel action
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        # "Now" - most frequently used, full width for prominence
        [
            InlineKeyboardButton(text="Сейчас", callback_data="time_end_now"),
        ],
        # Short durations - common activity lengths
        [
            InlineKeyboardButton(text="15м", callback_data="time_end_15m"),
            InlineKeyboardButton(text="30м", callback_data="time_end_30m"),
            InlineKeyboardButton(text="1ч", callback_data="time_end_1h"),
        ],
        # Long durations - extended activities
        [
            InlineKeyboardButton(text="2ч", callback_data="time_end_2h"),
            InlineKeyboardButton(text="3ч", callback_data="time_end_3h"),
            InlineKeyboardButton(text="8ч", callback_data="time_end_8h"),
        ],
        # Cancel action - separated for clarity
        [
            InlineKeyboardButton(text="❌ Отменить", callback_data="cancel"),
        ],
    ])
    return keyboard
