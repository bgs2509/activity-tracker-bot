"""Settings handlers (Step 2 - Automatic polls configuration)."""
import logging
import re
from datetime import time as dt_time

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext

from src.api.states.settings import SettingsStates
from src.infrastructure.http_clients.http_client import DataAPIClient
from src.infrastructure.http_clients.user_service import UserService
from src.infrastructure.http_clients.user_settings_service import UserSettingsService
from src.api.keyboards.settings import (
    get_main_settings_keyboard,
    get_interval_type_keyboard,
    get_weekday_interval_keyboard,
    get_weekend_interval_keyboard,
    get_quiet_hours_main_keyboard,
    get_quiet_hours_start_keyboard,
    get_quiet_hours_end_keyboard,
    get_reminders_keyboard,
    get_reminder_delay_keyboard,
    get_confirmation_keyboard,
)
from src.api.keyboards.main_menu import get_main_menu_keyboard

router = Router()
logger = logging.getLogger(__name__)

api_client = DataAPIClient()


@router.callback_query(F.data == "settings")
async def show_settings_menu(callback: types.CallbackQuery):
    """Show main settings menu."""
    user_service = UserService(api_client)
    settings_service = UserSettingsService(api_client)
    telegram_id = callback.from_user.id

    user = await user_service.get_by_telegram_id(telegram_id)
    if not user:
        await callback.message.answer("⚠️ Пользователь не найден.", reply_markup=get_main_menu_keyboard())
        await callback.answer()
        return

    settings = await settings_service.get_settings(user["id"])
    if not settings:
        await callback.message.answer("⚠️ Настройки не найдены.", reply_markup=get_main_menu_keyboard())
        await callback.answer()
        return

    weekday_h = settings["poll_interval_weekday"] // 60
    weekend_h = settings["poll_interval_weekend"] // 60

    quiet_enabled = settings["quiet_hours_start"] is not None
    quiet_text = f"С {settings['quiet_hours_start'][:5]} до {settings['quiet_hours_end'][:5]}" if quiet_enabled else "Выключены"

    reminder_status = "Включены ✅" if settings["reminder_enabled"] else "Выключены ❌"

    text = (
        f"⚙️ Настройки бота\n\n"
        f"Текущие настройки:\n\n"
        f"📅 Интервалы опросов:\n"
        f"• Будни: каждые {weekday_h}ч\n"
        f"• Выходные: каждые {weekend_h}ч\n\n"
        f"🌙 Тихие часы:\n"
        f"• {quiet_text}\n"
        f"(Бот не будет беспокоить в это время)\n\n"
        f"🔔 Напоминания:\n"
        f"• {reminder_status}\n"
        f"• Задержка: {settings['reminder_delay_minutes']} минут"
    )

    await callback.message.answer(text, reply_markup=get_main_settings_keyboard())
    await callback.answer()


@router.callback_query(F.data == "settings_intervals")
async def show_interval_type(callback: types.CallbackQuery):
    """Show interval type selection."""
    text = (
        "📅 Настройка интервалов опросов\n\n"
        "Как часто бот должен спрашивать о твоей активности?\n\n"
        "Выбери, что хочешь настроить:"
    )
    await callback.message.answer(text, reply_markup=get_interval_type_keyboard())
    await callback.answer()


@router.callback_query(F.data == "interval_weekday")
async def show_weekday_intervals(callback: types.CallbackQuery):
    """Show weekday interval selection."""
    user_service = UserService(api_client)
    settings_service = UserSettingsService(api_client)
    telegram_id = callback.from_user.id

    user = await user_service.get_by_telegram_id(telegram_id)
    settings = await settings_service.get_settings(user["id"])

    current = settings["poll_interval_weekday"]
    hours = current // 60

    text = (
        f"📅 Интервал опросов в будние дни\n\n"
        f"Текущий интервал: каждые {hours}ч\n\n"
        f"Как часто бот должен спрашивать о твоей активности в будние дни?"
    )

    await callback.message.answer(text, reply_markup=get_weekday_interval_keyboard(current))
    await callback.answer()


@router.callback_query(F.data.startswith("set_weekday_"))
async def set_weekday_interval(callback: types.CallbackQuery):
    """Set weekday interval."""
    interval = int(callback.data.split("_")[2])

    user_service = UserService(api_client)
    settings_service = UserSettingsService(api_client)
    telegram_id = callback.from_user.id

    user = await user_service.get_by_telegram_id(telegram_id)
    settings = await settings_service.get_settings(user["id"])

    await settings_service.update_settings(settings["id"], poll_interval_weekday=interval)

    hours = interval // 60
    text = (
        f"✅ Интервал для будних дней обновлён!\n\n"
        f"Теперь бот будет спрашивать каждые {hours}ч в будние дни."
    )

    await callback.message.answer(text, reply_markup=get_confirmation_keyboard())
    await callback.answer()


@router.callback_query(F.data == "interval_weekend")
async def show_weekend_intervals(callback: types.CallbackQuery):
    """Show weekend interval selection."""
    user_service = UserService(api_client)
    settings_service = UserSettingsService(api_client)
    telegram_id = callback.from_user.id

    user = await user_service.get_by_telegram_id(telegram_id)
    settings = await settings_service.get_settings(user["id"])

    current = settings["poll_interval_weekend"]
    hours = current // 60

    text = (
        f"🎉 Интервал опросов в выходные\n\n"
        f"Текущий интервал: каждые {hours}ч\n\n"
        f"Как часто бот должен спрашивать о твоей активности в выходные дни?"
    )

    await callback.message.answer(text, reply_markup=get_weekend_interval_keyboard(current))
    await callback.answer()


@router.callback_query(F.data.startswith("set_weekend_"))
async def set_weekend_interval(callback: types.CallbackQuery):
    """Set weekend interval."""
    interval = int(callback.data.split("_")[2])

    user_service = UserService(api_client)
    settings_service = UserSettingsService(api_client)
    telegram_id = callback.from_user.id

    user = await user_service.get_by_telegram_id(telegram_id)
    settings = await settings_service.get_settings(user["id"])

    await settings_service.update_settings(settings["id"], poll_interval_weekend=interval)

    hours = interval // 60
    text = (
        f"✅ Интервал для выходных обновлён!\n\n"
        f"Теперь бот будет спрашивать каждые {hours}ч в выходные дни."
    )

    await callback.message.answer(text, reply_markup=get_confirmation_keyboard())
    await callback.answer()


@router.callback_query(F.data == "settings_quiet_hours")
async def show_quiet_hours(callback: types.CallbackQuery):
    """Show quiet hours configuration."""
    user_service = UserService(api_client)
    settings_service = UserSettingsService(api_client)
    telegram_id = callback.from_user.id

    user = await user_service.get_by_telegram_id(telegram_id)
    settings = await settings_service.get_settings(user["id"])

    enabled = settings["quiet_hours_start"] is not None

    if enabled:
        text = (
            f"🌙 Тихие часы\n\n"
            f"Это время, когда бот не будет тебя беспокоить опросами.\n\n"
            f"Текущие настройки:\n"
            f"• Включены ✅\n"
            f"• С {settings['quiet_hours_start'][:5]} до {settings['quiet_hours_end'][:5]}"
        )
    else:
        text = (
            f"🌙 Тихие часы\n\n"
            f"Это время, когда бот не будет тебя беспокоить опросами.\n\n"
            f"Текущие настройки:\n"
            f"• Выключены ❌"
        )

    await callback.message.answer(text, reply_markup=get_quiet_hours_main_keyboard(enabled))
    await callback.answer()


@router.callback_query(F.data == "quiet_toggle")
async def toggle_quiet_hours(callback: types.CallbackQuery):
    """Toggle quiet hours on/off."""
    user_service = UserService(api_client)
    settings_service = UserSettingsService(api_client)
    telegram_id = callback.from_user.id

    user = await user_service.get_by_telegram_id(telegram_id)
    settings = await settings_service.get_settings(user["id"])

    enabled = settings["quiet_hours_start"] is not None

    if enabled:
        # Disable quiet hours
        await settings_service.update_settings(
            settings["id"],
            quiet_hours_start=None,
            quiet_hours_end=None
        )
        text = "✅ Тихие часы отключены\n\nТеперь бот будет опрашивать круглосуточно (в рамках установленных интервалов)."
    else:
        # Enable quiet hours with defaults
        await settings_service.update_settings(
            settings["id"],
            quiet_hours_start="23:00:00",
            quiet_hours_end="07:00:00"
        )
        text = "✅ Тихие часы включены\n\nБот не будет беспокоить с 23:00 до 07:00"

    await callback.message.answer(text, reply_markup=get_confirmation_keyboard())
    await callback.answer()


@router.callback_query(F.data == "settings_reminders")
async def show_reminders(callback: types.CallbackQuery):
    """Show reminder configuration."""
    user_service = UserService(api_client)
    settings_service = UserSettingsService(api_client)
    telegram_id = callback.from_user.id

    user = await user_service.get_by_telegram_id(telegram_id)
    settings = await settings_service.get_settings(user["id"])

    enabled = settings["reminder_enabled"]
    status = "Включены ✅" if enabled else "Выключены ❌"

    text = (
        f"🔔 Напоминания\n\n"
        f"Если ты не ответил на опрос, бот напомнит через некоторое время.\n\n"
        f"Текущие настройки:\n"
        f"• Напоминания: {status}\n"
        f"• Задержка: {settings['reminder_delay_minutes']} минут"
    )

    await callback.message.answer(text, reply_markup=get_reminders_keyboard(enabled))
    await callback.answer()


@router.callback_query(F.data == "reminder_toggle")
async def toggle_reminders(callback: types.CallbackQuery):
    """Toggle reminders on/off."""
    user_service = UserService(api_client)
    settings_service = UserSettingsService(api_client)
    telegram_id = callback.from_user.id

    user = await user_service.get_by_telegram_id(telegram_id)
    settings = await settings_service.get_settings(user["id"])

    new_state = not settings["reminder_enabled"]

    await settings_service.update_settings(settings["id"], reminder_enabled=new_state)

    text = "✅ Напоминания включены" if new_state else "✅ Напоминания отключены"

    await callback.message.answer(text, reply_markup=get_confirmation_keyboard())
    await callback.answer()


@router.callback_query(F.data == "reminder_delay")
async def show_reminder_delay(callback: types.CallbackQuery):
    """Show reminder delay selection."""
    user_service = UserService(api_client)
    settings_service = UserSettingsService(api_client)
    telegram_id = callback.from_user.id

    user = await user_service.get_by_telegram_id(telegram_id)
    settings = await settings_service.get_settings(user["id"])

    current = settings["reminder_delay_minutes"]

    text = (
        f"⏱ Задержка напоминания\n\n"
        f"Через сколько минут напомнить, если не ответил на опрос?\n\n"
        f"Текущая задержка: {current} минут"
    )

    await callback.message.answer(text, reply_markup=get_reminder_delay_keyboard(current))
    await callback.answer()


@router.callback_query(F.data.startswith("reminder_delay_"))
async def set_reminder_delay(callback: types.CallbackQuery):
    """Set reminder delay."""
    # Extract delay from callback data (e.g., "reminder_delay_30" -> 30)
    parts = callback.data.split("_")
    if parts[-1] == "custom":
        return  # Handle custom input separately

    delay = int(parts[-1])

    user_service = UserService(api_client)
    settings_service = UserSettingsService(api_client)
    telegram_id = callback.from_user.id

    user = await user_service.get_by_telegram_id(telegram_id)
    settings = await settings_service.get_settings(user["id"])

    await settings_service.update_settings(settings["id"], reminder_delay_minutes=delay)

    text = f"✅ Задержка напоминания обновлена!\n\nТеперь бот будет напоминать через {delay} минут."

    await callback.message.answer(text, reply_markup=get_confirmation_keyboard())
    await callback.answer()


@router.callback_query(F.data == "main_menu")
async def return_to_main_menu(callback: types.CallbackQuery, state: FSMContext):
    """Return to main menu."""
    await state.clear()
    text = "🏠 Главное меню"
    await callback.message.answer(text, reply_markup=get_main_menu_keyboard())
    await callback.answer()
