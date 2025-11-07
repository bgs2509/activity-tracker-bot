"""Reminder settings handlers for notification configuration."""

import logging

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext

from src.api.states.settings import SettingsStates
from src.api.dependencies import ServiceContainer
from src.api.keyboards.settings import (
    get_reminders_keyboard,
    get_reminder_delay_keyboard,
    get_confirmation_keyboard,
)
from src.application.services import fsm_timeout_service as fsm_timeout_module
from src.application.utils.decorators import with_typing_action
from src.core.logging_middleware import log_user_action

from .helpers import get_user_and_settings

router = Router()
logger = logging.getLogger(__name__)

# Constants for validation
REMINDER_DELAY_MIN = 5
REMINDER_DELAY_MAX = 120


@router.callback_query(F.data == "settings_reminders")
@with_typing_action
async def show_reminders(
    callback: types.CallbackQuery,
    services: ServiceContainer
) -> None:
    """
    Show reminder configuration menu.

    Displays current reminder status and delay settings.

    Args:
        callback: Telegram callback query
        services: Service container with data access
    """
    telegram_id = callback.from_user.id

    user, settings = await get_user_and_settings(telegram_id, services)
    if not user or not settings:
        await callback.answer("⚠️ Ошибка получения настроек", show_alert=True)
        return

    enabled = settings["reminder_enabled"]
    status = "Включены ✅" if enabled else "Выключены ❌"

    text = (
        "🔔 Напоминания\n\n"
        "Если ты не ответил на опрос, бот напомнит через некоторое время.\n\n"
        "Текущие настройки:\n"
        f"• Напоминания: {status}\n"
        f"• Задержка: {settings['reminder_delay_minutes']} минут"
    )

    await callback.message.answer(text, reply_markup=get_reminders_keyboard(enabled))
    await callback.answer()


@router.callback_query(F.data == "reminder_toggle")
@with_typing_action
async def toggle_reminders(
    callback: types.CallbackQuery,
    services: ServiceContainer
) -> None:
    """
    Toggle reminders on/off.

    Enables or disables automatic reminders for unanswered polls.

    Args:
        callback: Telegram callback query
        services: Service container with data access
    """
    telegram_id = callback.from_user.id

    user, settings = await get_user_and_settings(telegram_id, services)
    if not user or not settings:
        await callback.answer("⚠️ Ошибка получения настроек", show_alert=True)
        return

    new_state = not settings["reminder_enabled"]

    await services.settings.update_settings(
        settings["id"],
        reminder_enabled=new_state
    )

    text = "✅ Напоминания включены" if new_state else "✅ Напоминания отключены"

    logger.info(
        "Reminders toggled",
        extra={
            "user_id": telegram_id,
            "new_state": new_state
        }
    )

    await callback.message.answer(text, reply_markup=get_confirmation_keyboard())
    await callback.answer()


@router.callback_query(F.data == "reminder_delay")
@with_typing_action
async def show_reminder_delay(
    callback: types.CallbackQuery,
    services: ServiceContainer
) -> None:
    """
    Show reminder delay selection menu.

    Displays current delay and allows selection of new delay from
    preset options or custom value.

    Args:
        callback: Telegram callback query
        services: Service container with data access
    """
    telegram_id = callback.from_user.id

    user, settings = await get_user_and_settings(telegram_id, services)
    if not user or not settings:
        await callback.answer("⚠️ Ошибка получения настроек", show_alert=True)
        return

    current = settings["reminder_delay_minutes"]

    text = (
        "⏱ Задержка напоминания\n\n"
        "Через сколько минут напомнить, если не ответил на опрос?\n\n"
        f"Текущая задержка: {current} минут"
    )

    await callback.message.answer(
        text,
        reply_markup=get_reminder_delay_keyboard(current)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("reminder_delay_"))
@with_typing_action
async def set_reminder_delay(
    callback: types.CallbackQuery,
    state: FSMContext,
    services: ServiceContainer
) -> None:
    """
    Set reminder delay from preset options or custom.

    If custom selected, starts FSM state for delay input.
    Otherwise, updates delay immediately.

    Args:
        callback: Telegram callback query with delay data
        state: FSM context for state management
        services: Service container with data access
    """
    parts = callback.data.split("_")

    if parts[-1] == "custom":
        # Handle custom input - ask user to enter delay
        text = (
            "⏱ Укажи свою задержку напоминания\n\n"
            f"Введи количество минут (от {REMINDER_DELAY_MIN} до {REMINDER_DELAY_MAX}).\n\n"
            "Примеры:\n"
            "• 10 — напомнить через 10 минут\n"
            "• 45 — напомнить через 45 минут\n\n"
            "Или отправь /cancel для отмены"
        )

        await callback.message.answer(text)
        await state.set_state(SettingsStates.waiting_for_reminder_delay_custom)

        if fsm_timeout_module.fsm_timeout_service:
            fsm_timeout_module.fsm_timeout_service.schedule_timeout(
                callback.from_user.id,
                SettingsStates.waiting_for_reminder_delay_custom,
                callback.bot
            )

        await callback.answer()
        return

    # Preset delay selected
    delay = int(parts[-1])

    await _update_reminder_delay(
        telegram_id=callback.from_user.id,
        delay=delay,
        services=services
    )

    text = (
        f"✅ Задержка напоминания обновлена!\n\n"
        f"Теперь бот будет напоминать через {delay} минут."
    )

    await callback.message.answer(text, reply_markup=get_confirmation_keyboard())
    await callback.answer()


@router.message(SettingsStates.waiting_for_reminder_delay_custom)
async def process_reminder_delay_custom(
    message: types.Message,
    state: FSMContext,
    services: ServiceContainer
) -> None:
    """
    Process custom reminder delay input from user.

    Validates input and updates settings if valid, otherwise prompts for retry.

    Args:
        message: Telegram message with delay value
        state: FSM context for state management
        services: Service container with data access
    """
    try:
        delay = int(message.text.strip())

        # Validate delay range
        if delay < REMINDER_DELAY_MIN or delay > REMINDER_DELAY_MAX:
            await message.answer(
                f"⚠️ Задержка должна быть от {REMINDER_DELAY_MIN} "
                f"до {REMINDER_DELAY_MAX} минут.\n"
                "Попробуй ещё раз:"
            )
            return

        # Update delay
        await _update_reminder_delay(
            telegram_id=message.from_user.id,
            delay=delay,
            services=services
        )

        text = (
            f"✅ Задержка напоминания обновлена!\n\n"
            f"Теперь бот будет напоминать через {delay} минут."
        )

        await message.answer(text, reply_markup=get_confirmation_keyboard())

        # Clear FSM state
        await state.clear()
        if fsm_timeout_module.fsm_timeout_service:
            fsm_timeout_module.fsm_timeout_service.cancel_timeout(message.from_user.id)

    except ValueError:
        await message.answer(
            "⚠️ Неверный формат! Введи целое число (например: 45):"
        )


# Helper functions (DRY principle)


async def _update_reminder_delay(
    telegram_id: int,
    delay: int,
    services: ServiceContainer
) -> None:
    """
    Update reminder delay setting.

    This helper eliminates duplication between preset and custom delay handling.

    Args:
        telegram_id: Telegram user ID
        delay: New delay in minutes
        services: Service container with data access
    """
    user, settings = await get_user_and_settings(telegram_id, services)
    if not user or not settings:
        logger.error(
            "Cannot update reminder delay - user or settings not found",
            extra={"telegram_id": telegram_id}
        )
        return

    await services.settings.update_settings(
        settings["id"],
        reminder_delay_minutes=delay
    )

    logger.info(
        "Reminder delay updated",
        extra={
            "user_id": telegram_id,
            "new_delay": delay
        }
    )
