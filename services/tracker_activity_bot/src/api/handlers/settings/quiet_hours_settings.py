"""Quiet hours settings handlers for poll silence configuration."""

import logging
import re

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from src.api.states.settings import SettingsStates
from src.api.dependencies import ServiceContainer
from src.api.keyboards.settings import (
    get_quiet_hours_main_keyboard,
    get_quiet_hours_start_keyboard,
    get_quiet_hours_end_keyboard,
    get_confirmation_keyboard,
)
from src.application.services import fsm_timeout_service as fsm_timeout_module
from src.application.utils.decorators import with_typing_action
from src.core.logging_middleware import log_user_action

from .helpers import get_user_and_settings

router = Router()
logger = logging.getLogger(__name__)

# Time validation regex (HH:MM format)
TIME_FORMAT_REGEX = r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$'

# Default quiet hours
DEFAULT_QUIET_START = "23:00:00"
DEFAULT_QUIET_END = "07:00:00"


@router.callback_query(F.data == "settings_quiet_hours")
@with_typing_action
async def show_quiet_hours(
    callback: types.CallbackQuery,
    services: ServiceContainer
) -> None:
    """
    Show quiet hours configuration menu.

    Displays current quiet hours status and time range if enabled.

    Args:
        callback: Telegram callback query
        services: Service container with data access
    """
    telegram_id = callback.from_user.id

    user, settings = await get_user_and_settings(telegram_id, services)
    if not user or not settings:
        await callback.answer("⚠️ Ошибка получения настроек", show_alert=True)
        return

    enabled = settings["quiet_hours_start"] is not None

    text = _build_quiet_hours_text(settings, enabled)

    await callback.message.answer(
        text,
        reply_markup=get_quiet_hours_main_keyboard(enabled)
    )
    await callback.answer()


@router.callback_query(F.data == "quiet_toggle")
@with_typing_action
async def toggle_quiet_hours(
    callback: types.CallbackQuery,
    services: ServiceContainer
) -> None:
    """
    Toggle quiet hours on/off.

    If disabled, enables with default times (23:00-07:00).
    If enabled, disables quiet hours completely.

    Args:
        callback: Telegram callback query
        services: Service container with data access
    """
    telegram_id = callback.from_user.id

    user, settings = await get_user_and_settings(telegram_id, services)
    if not user or not settings:
        await callback.answer("⚠️ Ошибка получения настроек", show_alert=True)
        return

    enabled = settings["quiet_hours_start"] is not None

    if enabled:
        # Disable quiet hours
        await services.settings.update_settings(
            settings["id"],
            quiet_hours_start=None,
            quiet_hours_end=None
        )
        text = (
            "✅ Тихие часы отключены\n\n"
            "Теперь бот будет опрашивать круглосуточно "
            "(в рамках установленных интервалов)."
        )
        logger.info(
            "Quiet hours disabled",
            extra={"user_id": telegram_id}
        )
    else:
        # Enable quiet hours with defaults
        await services.settings.update_settings(
            settings["id"],
            quiet_hours_start=DEFAULT_QUIET_START,
            quiet_hours_end=DEFAULT_QUIET_END
        )
        text = (
            "✅ Тихие часы включены\n\n"
            f"Бот не будет беспокоить с {DEFAULT_QUIET_START[:5]} "
            f"до {DEFAULT_QUIET_END[:5]}"
        )
        logger.info(
            "Quiet hours enabled with defaults",
            extra={
                "user_id": telegram_id,
                "start": DEFAULT_QUIET_START,
                "end": DEFAULT_QUIET_END
            }
        )

    await callback.message.answer(text, reply_markup=get_confirmation_keyboard())
    await callback.answer()


@router.callback_query(F.data == "quiet_time")
@with_typing_action
async def show_quiet_time_selection(
    callback: types.CallbackQuery,
    services: ServiceContainer
) -> None:
    """
    Show selection between start and end time.

    Allows user to choose whether to modify start or end time.

    Args:
        callback: Telegram callback query
        services: Service container (unused but kept for consistency)
    """
    text = (
        "⏰ Изменить время тихих часов\n\n"
        "Что хочешь изменить?"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🌙 Время начала",
            callback_data="quiet_select_start"
        )],
        [InlineKeyboardButton(
            text="🌅 Время окончания",
            callback_data="quiet_select_end"
        )],
        [InlineKeyboardButton(
            text="🔙 К тихим часам",
            callback_data="settings_quiet_hours"
        )],
    ])

    await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "quiet_select_start")
@with_typing_action
async def show_quiet_start_selection(
    callback: types.CallbackQuery,
    services: ServiceContainer
) -> None:
    """
    Show quiet hours start time selection menu.

    Displays current start time and allows selection of new time.

    Args:
        callback: Telegram callback query
        services: Service container with data access
    """
    telegram_id = callback.from_user.id

    user, settings = await get_user_and_settings(telegram_id, services)
    if not user or not settings:
        await callback.answer("⚠️ Ошибка получения настроек", show_alert=True)
        return

    current_start = settings["quiet_hours_start"]
    current_text = current_start[:5] if current_start else "не установлено"

    text = (
        f"🌙 Время начала тихих часов\n\n"
        f"Текущее время: {current_text}\n\n"
        f"Выбери новое время начала тихих часов:"
    )

    await callback.message.answer(
        text,
        reply_markup=get_quiet_hours_start_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "quiet_select_end")
@with_typing_action
async def show_quiet_end_selection(
    callback: types.CallbackQuery,
    services: ServiceContainer
) -> None:
    """
    Show quiet hours end time selection menu.

    Displays current end time and allows selection of new time.

    Args:
        callback: Telegram callback query
        services: Service container with data access
    """
    telegram_id = callback.from_user.id

    user, settings = await get_user_and_settings(telegram_id, services)
    if not user or not settings:
        await callback.answer("⚠️ Ошибка получения настроек", show_alert=True)
        return

    current_end = settings["quiet_hours_end"]
    current_text = current_end[:5] if current_end else "не установлено"

    text = (
        f"🌅 Время окончания тихих часов\n\n"
        f"Текущее время: {current_text}\n\n"
        f"Выбери новое время окончания тихих часов:"
    )

    await callback.message.answer(
        text,
        reply_markup=get_quiet_hours_end_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("quiet_start_"))
@with_typing_action
async def set_quiet_start_time(
    callback: types.CallbackQuery,
    state: FSMContext,
    services: ServiceContainer
) -> None:
    """
    Set quiet hours start time from preset or custom.

    If custom selected, starts FSM state for time input.
    Otherwise, updates start time immediately.

    Args:
        callback: Telegram callback query with time data
        state: FSM context for state management
        services: Service container with data access
    """
    parts = callback.data.split("_")

    if parts[-1] == "custom":
        # Handle custom input - ask user to enter time
        text = (
            "🌙 Укажи время начала тихих часов\n\n"
            "Введи время в формате ЧЧ:ММ\n"
            "Например: 23:00 или 22:30\n\n"
            "Или отправь /cancel для отмены"
        )
        await callback.message.answer(text)
        await state.set_state(SettingsStates.waiting_for_quiet_hours_start_custom)

        if fsm_timeout_module.fsm_timeout_service:
            fsm_timeout_module.fsm_timeout_service.schedule_timeout(
                callback.from_user.id,
                SettingsStates.waiting_for_quiet_hours_start_custom,
                callback.bot
            )

        await callback.answer()
        return

    # Preset time selected
    time_str = parts[-1]  # e.g., "23:00"

    await _update_quiet_time(
        telegram_id=callback.from_user.id,
        time_str=time_str,
        time_type="start",
        services=services
    )

    text = (
        f"✅ Время начала тихих часов обновлено!\n\n"
        f"Теперь тихие часы начинаются в {time_str}"
    )

    await callback.message.answer(text, reply_markup=get_confirmation_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("quiet_end_"))
@with_typing_action
async def set_quiet_end_time(
    callback: types.CallbackQuery,
    state: FSMContext,
    services: ServiceContainer
) -> None:
    """
    Set quiet hours end time from preset or custom.

    If custom selected, starts FSM state for time input.
    Otherwise, updates end time immediately.

    Args:
        callback: Telegram callback query with time data
        state: FSM context for state management
        services: Service container with data access
    """
    parts = callback.data.split("_")

    if parts[-1] == "custom":
        # Handle custom input - ask user to enter time
        text = (
            "🌅 Укажи время окончания тихих часов\n\n"
            "Введи время в формате ЧЧ:ММ\n"
            "Например: 07:00 или 08:30\n\n"
            "Или отправь /cancel для отмены"
        )
        await callback.message.answer(text)
        await state.set_state(SettingsStates.waiting_for_quiet_hours_end_custom)

        if fsm_timeout_module.fsm_timeout_service:
            fsm_timeout_module.fsm_timeout_service.schedule_timeout(
                callback.from_user.id,
                SettingsStates.waiting_for_quiet_hours_end_custom,
                callback.bot
            )

        await callback.answer()
        return

    # Preset time selected
    time_str = parts[-1]  # e.g., "07:00"

    await _update_quiet_time(
        telegram_id=callback.from_user.id,
        time_str=time_str,
        time_type="end",
        services=services
    )

    text = (
        f"✅ Время окончания тихих часов обновлено!\n\n"
        f"Теперь тихие часы заканчиваются в {time_str}"
    )

    await callback.message.answer(text, reply_markup=get_confirmation_keyboard())
    await callback.answer()


@router.message(SettingsStates.waiting_for_quiet_hours_start_custom)
async def process_custom_quiet_start(
    message: types.Message,
    state: FSMContext,
    services: ServiceContainer
) -> None:
    """
    Process custom quiet hours start time input.

    Validates time format and updates setting if valid.

    Args:
        message: Telegram message with time input
        state: FSM context for state management
        services: Service container with data access
    """
    time_str = message.text.strip()

    # Validate time format (HH:MM)
    if not re.match(TIME_FORMAT_REGEX, time_str):
        await message.answer(
            "⚠️ Неверный формат времени!\n\n"
            "Введи время в формате ЧЧ:ММ\n"
            "Например: 23:00 или 22:30"
        )
        return

    await _update_quiet_time(
        telegram_id=message.from_user.id,
        time_str=time_str,
        time_type="start",
        services=services
    )

    text = (
        f"✅ Время начала тихих часов обновлено!\n\n"
        f"Теперь тихие часы начинаются в {time_str}"
    )

    await message.answer(text, reply_markup=get_confirmation_keyboard())
    await state.clear()


@router.message(SettingsStates.waiting_for_quiet_hours_end_custom)
async def process_custom_quiet_end(
    message: types.Message,
    state: FSMContext,
    services: ServiceContainer
) -> None:
    """
    Process custom quiet hours end time input.

    Validates time format and updates setting if valid.

    Args:
        message: Telegram message with time input
        state: FSM context for state management
        services: Service container with data access
    """
    time_str = message.text.strip()

    # Validate time format (HH:MM)
    if not re.match(TIME_FORMAT_REGEX, time_str):
        await message.answer(
            "⚠️ Неверный формат времени!\n\n"
            "Введи время в формате ЧЧ:ММ\n"
            "Например: 07:00 или 08:30"
        )
        return

    await _update_quiet_time(
        telegram_id=message.from_user.id,
        time_str=time_str,
        time_type="end",
        services=services
    )

    text = (
        f"✅ Время окончания тихих часов обновлено!\n\n"
        f"Теперь тихие часы заканчиваются в {time_str}"
    )

    await message.answer(text, reply_markup=get_confirmation_keyboard())
    await state.clear()


# Helper functions (DRY principle)


def _build_quiet_hours_text(settings: dict, enabled: bool) -> str:
    """
    Build quiet hours status text.

    Args:
        settings: User settings dict
        enabled: Whether quiet hours are enabled

    Returns:
        Formatted status text
    """
    base_text = (
        "🌙 Тихие часы\n\n"
        "Это время, когда бот не будет тебя беспокоить опросами.\n\n"
        "Текущие настройки:\n"
    )

    if enabled:
        start = settings["quiet_hours_start"][:5]
        end = settings["quiet_hours_end"][:5]
        return base_text + f"• Включены ✅\n• С {start} до {end}"
    else:
        return base_text + "• Выключены ❌"


async def _update_quiet_time(
    telegram_id: int,
    time_str: str,
    time_type: str,
    services: ServiceContainer
) -> None:
    """
    Update quiet hours time setting.

    This helper eliminates duplication between start/end time handling.

    Args:
        telegram_id: Telegram user ID
        time_str: Time string in HH:MM format
        time_type: "start" or "end"
        services: Service container with data access
    """
    user, settings = await get_user_and_settings(telegram_id, services)
    if not user or not settings:
        logger.error(
            "Cannot update quiet time - user or settings not found",
            extra={"telegram_id": telegram_id}
        )
        return

    # Update with full time format (HH:MM:SS)
    update_field = f"quiet_hours_{time_type}"
    await services.settings.update_settings(
        settings["id"],
        **{update_field: f"{time_str}:00"}
    )

    logger.info(
        "Quiet hours time updated",
        extra={
            "user_id": telegram_id,
            "time_type": time_type,
            "new_time": time_str
        }
    )
