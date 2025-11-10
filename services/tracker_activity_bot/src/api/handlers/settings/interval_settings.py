"""Interval settings handlers for poll frequency configuration."""

import logging
from typing import Union

import httpx
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext

from src.api.states.settings import SettingsStates
from src.api.dependencies import ServiceContainer
from src.api.keyboards.settings import (
    get_interval_type_keyboard,
    get_weekday_interval_keyboard,
    get_weekend_interval_keyboard,
    get_confirmation_keyboard,
)
from src.application.services import fsm_timeout_service as fsm_timeout_module
from src.application.utils.decorators import with_typing_action
from src.application.utils.formatters import format_duration
from src.core.logging_middleware import log_user_action

from .helpers import get_user_and_settings

router = Router()
logger = logging.getLogger(__name__)


# Constants for validation
WEEKDAY_MIN_INTERVAL = 15
WEEKDAY_MAX_INTERVAL = 360
WEEKEND_MIN_INTERVAL = 15
WEEKEND_MAX_INTERVAL = 480


@router.callback_query(F.data == "settings_intervals")
@with_typing_action
async def show_interval_type(
    callback: types.CallbackQuery,
    services: ServiceContainer
) -> None:
    """
    Show interval type selection menu.

    Allows user to choose between configuring weekday or weekend intervals.

    Args:
        callback: Telegram callback query
        services: Service container (unused but kept for consistency)
    """
    text = (
        "📅 Настройка интервалов опросов\n\n"
        "Как часто бот должен спрашивать о твоей активности?\n\n"
        "Выбери, что хочешь настроить:"
    )

    await callback.message.answer(text, reply_markup=get_interval_type_keyboard())
    await callback.answer()


@router.callback_query(F.data == "interval_weekday")
@with_typing_action
async def show_weekday_intervals(
    callback: types.CallbackQuery,
    services: ServiceContainer
) -> None:
    """
    Show weekday interval selection menu.

    Displays current weekday interval and allows user to select new interval
    from preset options or enter custom value.

    Args:
        callback: Telegram callback query
        services: Service container with data access
    """
    telegram_id = callback.from_user.id

    user, settings = await get_user_and_settings(telegram_id, services)
    if not user or not settings:
        await callback.answer("⚠️ Ошибка получения настроек", show_alert=True)
        return

    current = settings["poll_interval_weekday"]
    hours = current // 60

    text = (
        f"📅 Интервал опросов в будние дни\n\n"
        f"Текущий интервал: каждые {hours}ч\n\n"
        f"Как часто бот должен спрашивать о твоей активности в будние дни?"
    )

    await callback.message.answer(
        text,
        reply_markup=get_weekday_interval_keyboard(current)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set_weekday_"))
@with_typing_action
async def set_weekday_interval(
    callback: types.CallbackQuery,
    services: ServiceContainer
) -> None:
    """
    Set weekday interval from preset options.

    Updates user settings and reschedules automatic poll with new interval.

    Args:
        callback: Telegram callback query with interval data
        services: Service container with data access
    """
    interval = int(callback.data.split("_")[2])

    await _update_interval_and_reschedule(
        telegram_id=callback.from_user.id,
        interval=interval,
        interval_type="weekday",
        services=services,
        bot=callback.bot,
        is_message=False,
        event=callback
    )


@router.callback_query(F.data == "weekday_custom")
@with_typing_action
async def show_weekday_custom_input(
    callback: types.CallbackQuery,
    state: FSMContext
) -> None:
    """
    Show custom weekday interval input prompt.

    Starts FSM state for receiving custom interval value from user.

    Args:
        callback: Telegram callback query
        state: FSM context for state management
    """
    text = (
        "📅 Укажи свой интервал для будних дней\n\n"
        f"Введи количество минут (от {WEEKDAY_MIN_INTERVAL} до {WEEKDAY_MAX_INTERVAL}).\n\n"
        "Примеры:\n"
        "• 90 — каждые 1.5 часа\n"
        "• 150 — каждые 2.5 часа\n\n"
        "Или отправь /cancel для отмены"
    )

    await callback.message.answer(text)
    await state.set_state(SettingsStates.waiting_for_weekday_interval_custom)

    if fsm_timeout_module.fsm_timeout_service:
        fsm_timeout_module.fsm_timeout_service.schedule_timeout(
            callback.from_user.id,
            SettingsStates.waiting_for_weekday_interval_custom,
            callback.bot
        )

    await callback.answer()


@router.message(SettingsStates.waiting_for_weekday_interval_custom)
async def process_weekday_custom_input(
    message: types.Message,
    state: FSMContext,
    services: ServiceContainer
) -> None:
    """
    Process custom weekday interval input from user.

    Validates input and updates settings if valid, otherwise prompts for retry.

    Args:
        message: Telegram message with interval value
        state: FSM context for state management
        services: Service container with data access
    """
    try:
        interval = int(message.text.strip())

        # Validate interval range
        if interval < WEEKDAY_MIN_INTERVAL or interval > WEEKDAY_MAX_INTERVAL:
            await message.answer(
                f"⚠️ Интервал должен быть от {WEEKDAY_MIN_INTERVAL} "
                f"до {WEEKDAY_MAX_INTERVAL} минут.\n"
                "Попробуй ещё раз:"
            )
            return

        # Update and reschedule
        try:
            await _update_interval_and_reschedule(
                telegram_id=message.from_user.id,
                interval=interval,
                interval_type="weekday",
                services=services,
                bot=message.bot,
                is_message=True,
                event=message
            )

            # Clear FSM state
            await state.clear()
            if fsm_timeout_module.fsm_timeout_service:
                fsm_timeout_module.fsm_timeout_service.cancel_timeout(message.from_user.id)

        except httpx.HTTPStatusError as e:
            # Handle API validation errors gracefully
            logger.error(
                "Failed to update weekday interval",
                extra={
                    "user_id": message.from_user.id,
                    "interval": interval,
                    "error": str(e)
                }
            )
            error_detail = "Неизвестная ошибка"
            try:
                error_data = e.response.json()
                error_detail = error_data.get("detail", str(e))
            except Exception:
                pass

            await message.answer(
                f"⚠️ Не удалось сохранить настройки:\n{error_detail}\n\n"
                "Попробуй другое значение или обратись к администратору."
            )

    except ValueError:
        await message.answer(
            "⚠️ Неверный формат! Введи целое число (например: 90):"
        )


@router.callback_query(F.data == "interval_weekend")
@with_typing_action
async def show_weekend_intervals(
    callback: types.CallbackQuery,
    services: ServiceContainer
) -> None:
    """
    Show weekend interval selection menu.

    Displays current weekend interval and allows user to select new interval
    from preset options or enter custom value.

    Args:
        callback: Telegram callback query
        services: Service container with data access
    """
    telegram_id = callback.from_user.id

    user, settings = await get_user_and_settings(telegram_id, services)
    if not user or not settings:
        await callback.answer("⚠️ Ошибка получения настроек", show_alert=True)
        return

    current = settings["poll_interval_weekend"]
    hours = current // 60

    text = (
        f"🎉 Интервал опросов в выходные\n\n"
        f"Текущий интервал: каждые {hours}ч\n\n"
        f"Как часто бот должен спрашивать о твоей активности в выходные дни?"
    )

    await callback.message.answer(
        text,
        reply_markup=get_weekend_interval_keyboard(current)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set_weekend_"))
@with_typing_action
async def set_weekend_interval(
    callback: types.CallbackQuery,
    services: ServiceContainer
) -> None:
    """
    Set weekend interval from preset options.

    Updates user settings and reschedules automatic poll with new interval.

    Args:
        callback: Telegram callback query with interval data
        services: Service container with data access
    """
    interval = int(callback.data.split("_")[2])

    await _update_interval_and_reschedule(
        telegram_id=callback.from_user.id,
        interval=interval,
        interval_type="weekend",
        services=services,
        bot=callback.bot,
        is_message=False,
        event=callback
    )


@router.callback_query(F.data == "weekend_custom")
@with_typing_action
async def show_weekend_custom_input(
    callback: types.CallbackQuery,
    state: FSMContext
) -> None:
    """
    Show custom weekend interval input prompt.

    Starts FSM state for receiving custom interval value from user.

    Args:
        callback: Telegram callback query
        state: FSM context for state management
    """
    text = (
        "🎉 Укажи свой интервал для выходных\n\n"
        f"Введи количество минут (от {WEEKEND_MIN_INTERVAL} до {WEEKEND_MAX_INTERVAL}).\n\n"
        "Примеры:\n"
        "• 120 — каждые 2 часа\n"
        "• 210 — каждые 3.5 часа\n\n"
        "Или отправь /cancel для отмены"
    )

    await callback.message.answer(text)
    await state.set_state(SettingsStates.waiting_for_weekend_interval_custom)

    if fsm_timeout_module.fsm_timeout_service:
        fsm_timeout_module.fsm_timeout_service.schedule_timeout(
            callback.from_user.id,
            SettingsStates.waiting_for_weekend_interval_custom,
            callback.bot
        )

    await callback.answer()


@router.message(SettingsStates.waiting_for_weekend_interval_custom)
async def process_weekend_custom_input(
    message: types.Message,
    state: FSMContext,
    services: ServiceContainer
) -> None:
    """
    Process custom weekend interval input from user.

    Validates input and updates settings if valid, otherwise prompts for retry.

    Args:
        message: Telegram message with interval value
        state: FSM context for state management
        services: Service container with data access
    """
    try:
        interval = int(message.text.strip())

        # Validate interval range
        if interval < WEEKEND_MIN_INTERVAL or interval > WEEKEND_MAX_INTERVAL:
            await message.answer(
                f"⚠️ Интервал должен быть от {WEEKEND_MIN_INTERVAL} "
                f"до {WEEKEND_MAX_INTERVAL} минут.\n"
                "Попробуй ещё раз:"
            )
            return

        # Update and reschedule
        try:
            await _update_interval_and_reschedule(
                telegram_id=message.from_user.id,
                interval=interval,
                interval_type="weekend",
                services=services,
                bot=message.bot,
                is_message=True,
                event=message
            )

            # Clear FSM state
            await state.clear()
            if fsm_timeout_module.fsm_timeout_service:
                fsm_timeout_module.fsm_timeout_service.cancel_timeout(message.from_user.id)

        except httpx.HTTPStatusError as e:
            # Handle API validation errors gracefully
            logger.error(
                "Failed to update weekend interval",
                extra={
                    "user_id": message.from_user.id,
                    "interval": interval,
                    "error": str(e)
                }
            )
            error_detail = "Неизвестная ошибка"
            try:
                error_data = e.response.json()
                error_detail = error_data.get("detail", str(e))
            except Exception:
                pass

            await message.answer(
                f"⚠️ Не удалось сохранить настройки:\n{error_detail}\n\n"
                "Попробуй другое значение или обратись к администратору."
            )

    except ValueError:
        await message.answer(
            "⚠️ Неверный формат! Введи целое число (например: 120):"
        )


# Helper functions (DRY principle)


async def _update_interval_and_reschedule(
    telegram_id: int,
    interval: int,
    interval_type: str,
    services: ServiceContainer,
    bot,
    is_message: bool,
    event: Union[types.Message, types.CallbackQuery]
) -> None:
    """
    Update interval setting and reschedule poll.

    This helper eliminates code duplication between weekday/weekend
    and preset/custom interval handling.

    Args:
        telegram_id: Telegram user ID
        interval: New interval in minutes
        interval_type: "weekday" or "weekend"
        services: Service container with data access
        bot: Bot instance for scheduling
        is_message: True if event is Message, False if CallbackQuery
        event: Message or CallbackQuery event for sending response
    """
    user, settings = await get_user_and_settings(telegram_id, services)
    if not user or not settings:
        logger.error(
            "Cannot update interval - user or settings not found",
            extra={"telegram_id": telegram_id}
        )
        return

    # Update settings in database
    update_field = f"poll_interval_{interval_type}"
    await services.settings.update_settings(
        settings["id"],
        **{update_field: interval}
    )

    # Fetch updated settings and reschedule poll
    updated_settings = await services.settings.get_settings(user["id"])
    from src.api.handlers.poll import send_automatic_poll

    await services.scheduler.schedule_poll(
        user_id=telegram_id,
        settings=updated_settings,
        user_timezone=user.get("timezone", "Europe/Moscow"),
        send_poll_callback=send_automatic_poll,
        bot=bot
    )

    logger.info(
        "Interval updated and poll rescheduled",
        extra={
            "user_id": telegram_id,
            "interval_type": interval_type,
            "new_interval": interval
        }
    )

    # Build success message
    interval_str = format_duration(interval)
    day_type = "будних дней" if interval_type == "weekday" else "выходных"
    day_prefix = "в будние дни" if interval_type == "weekday" else "в выходные дни"

    text = (
        f"✅ Интервал для {day_type} обновлён!\n\n"
        f"Теперь бот будет спрашивать каждые {interval_str} {day_prefix}."
    )

    # Send response based on event type
    if is_message:
        await event.answer(text, reply_markup=get_confirmation_keyboard())
    else:
        await event.message.answer(text, reply_markup=get_confirmation_keyboard())
        await event.answer()
