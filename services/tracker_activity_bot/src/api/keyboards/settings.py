"""Keyboards for settings configuration."""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_main_settings_keyboard() -> InlineKeyboardMarkup:
    """Get main settings menu keyboard."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Изменить интервалы", callback_data="settings_intervals")],
        [InlineKeyboardButton(text="🌙 Изменить тихие часы", callback_data="settings_quiet_hours")],
        [InlineKeyboardButton(text="🔔 Настроить напоминания", callback_data="settings_reminders")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
    ])
    return keyboard


def get_interval_type_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting interval type (weekday/weekend)."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Будние дни (Пн-Пт)", callback_data="interval_weekday")],
        [InlineKeyboardButton(text="🎉 Выходные (Сб-Вс)", callback_data="interval_weekend")],
        [InlineKeyboardButton(text="🔙 Назад к настройкам", callback_data="settings")],
    ])
    return keyboard


def get_weekday_interval_keyboard(current: int = 120) -> InlineKeyboardMarkup:
    """Keyboard for selecting weekday interval."""
    intervals = [30, 60, 90, 120, 180, 240, 360]
    buttons = []
    for interval in intervals:
        hours = interval // 60
        minutes = interval % 60
        label = f"{hours}ч {minutes}м" if minutes else f"{hours} час{'а' if hours < 5 else 'ов'}"
        if interval == current:
            label = f"✓ {label}"
        buttons.append([InlineKeyboardButton(
            text=label,
            callback_data=f"set_weekday_{interval}"
        )])

    buttons.append([InlineKeyboardButton(text="✏️ Указать своё время", callback_data="weekday_custom")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="settings_intervals")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_weekend_interval_keyboard(current: int = 180) -> InlineKeyboardMarkup:
    """Keyboard for selecting weekend interval."""
    intervals = [30, 60, 120, 180, 240, 360, 480]
    buttons = []
    for interval in intervals:
        hours = interval // 60
        minutes = interval % 60
        label = f"{hours}ч {minutes}м" if minutes else f"{hours} час{'а' if hours < 5 else 'ов'}"
        if interval == current:
            label = f"✓ {label}"
        buttons.append([InlineKeyboardButton(
            text=label,
            callback_data=f"set_weekend_{interval}"
        )])

    buttons.append([InlineKeyboardButton(text="✏️ Указать своё время", callback_data="weekend_custom")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="settings_intervals")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_quiet_hours_main_keyboard(enabled: bool = True) -> InlineKeyboardMarkup:
    """Keyboard for quiet hours configuration."""
    toggle_button = InlineKeyboardButton(
        text="❌ Отключить тихие часы" if enabled else "✅ Включить тихие часы",
        callback_data="quiet_toggle"
    )

    buttons = [
        [toggle_button],
    ]

    # Add time change button only if enabled
    if enabled:
        buttons.append([InlineKeyboardButton(text="⏰ Изменить время", callback_data="quiet_time")])

    # Add back button
    buttons.append([InlineKeyboardButton(text="🔙 Назад к настройкам", callback_data="settings")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_quiet_hours_start_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting quiet hours start time."""
    times = ["21:00", "22:00", "23:00", "00:00", "01:00", "02:00"]
    buttons = [[InlineKeyboardButton(text=t, callback_data=f"quiet_start_{t}") for t in times[i:i+2]]
               for i in range(0, len(times), 2)]

    buttons.append([InlineKeyboardButton(text="✏️ Указать своё время", callback_data="quiet_start_custom")])
    buttons.append([InlineKeyboardButton(text="❌ Отменить", callback_data="settings_quiet_hours")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_quiet_hours_end_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting quiet hours end time."""
    times = ["06:00", "07:00", "08:00", "09:00", "10:00", "11:00"]
    buttons = [[InlineKeyboardButton(text=t, callback_data=f"quiet_end_{t}") for t in times[i:i+2]]
               for i in range(0, len(times), 2)]

    buttons.append([InlineKeyboardButton(text="✏️ Указать своё время", callback_data="quiet_end_custom")])
    buttons.append([InlineKeyboardButton(text="❌ Отменить", callback_data="settings_quiet_hours")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_reminders_keyboard(enabled: bool = True) -> InlineKeyboardMarkup:
    """Keyboard for reminder configuration."""
    toggle_button = InlineKeyboardButton(
        text="❌ Отключить" if enabled else "✅ Включить",
        callback_data="reminder_toggle"
    )

    buttons = [
        [toggle_button],
    ]

    # Add delay change button only if enabled
    if enabled:
        buttons.append([InlineKeyboardButton(text="⏱ Изменить задержку", callback_data="reminder_delay")])

    # Add back button
    buttons.append([InlineKeyboardButton(text="🔙 Назад к настройкам", callback_data="settings")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_reminder_delay_keyboard(current: int = 30) -> InlineKeyboardMarkup:
    """Keyboard for selecting reminder delay."""
    delays = [15, 30, 45, 60, 90]
    buttons = []
    for delay in delays:
        label = f"{delay} минут"
        if delay == current:
            label = f"✓ {label}"
        buttons.append([InlineKeyboardButton(
            text=label,
            callback_data=f"reminder_delay_{delay}"
        )])

    buttons.append([InlineKeyboardButton(text="✏️ Указать своё время", callback_data="reminder_delay_custom")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="settings_reminders")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for confirmations."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ К настройкам", callback_data="settings")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
    ])
    return keyboard
