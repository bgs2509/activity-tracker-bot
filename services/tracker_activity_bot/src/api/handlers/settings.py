"""Settings handlers (Step 2 - Automatic polls configuration)."""
import logging
import re
from datetime import time as dt_time

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

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
from src.application.services.scheduler_service import scheduler_service

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

    # Format weekday interval
    weekday_minutes = settings["poll_interval_weekday"]
    if weekday_minutes < 60:
        weekday_str = f"{weekday_minutes}м"
    else:
        weekday_h = weekday_minutes // 60
        weekday_m = weekday_minutes % 60
        if weekday_m == 0:
            weekday_str = f"{weekday_h}ч"
        else:
            weekday_str = f"{weekday_h}ч {weekday_m}м"

    # Format weekend interval
    weekend_minutes = settings["poll_interval_weekend"]
    if weekend_minutes < 60:
        weekend_str = f"{weekend_minutes}м"
    else:
        weekend_h = weekend_minutes // 60
        weekend_m = weekend_minutes % 60
        if weekend_m == 0:
            weekend_str = f"{weekend_h}ч"
        else:
            weekend_str = f"{weekend_h}ч {weekend_m}м"

    quiet_enabled = settings["quiet_hours_start"] is not None
    quiet_text = f"С {settings['quiet_hours_start'][:5]} до {settings['quiet_hours_end'][:5]}" if quiet_enabled else "Выключены"

    reminder_status = "Включены ✅" if settings["reminder_enabled"] else "Выключены ❌"

    # Get next poll time from scheduler
    next_poll_text = ""
    logger.info(f"Checking next poll for user {telegram_id}, jobs dict: {scheduler_service.jobs}")

    if telegram_id in scheduler_service.jobs:
        job_id = scheduler_service.jobs[telegram_id]
        logger.info(f"Found job_id for user {telegram_id}: {job_id}")
        try:
            job = scheduler_service.scheduler.get_job(job_id)
            logger.info(f"Got job from scheduler: {job}, next_run_time: {job.next_run_time if job else None}")
            if job and job.next_run_time:
                from datetime import datetime, timezone
                now = datetime.now(timezone.utc)
                time_until = job.next_run_time - now
                minutes = int(time_until.total_seconds() / 60)
                logger.info(f"Time until next poll: {minutes} minutes")

                if minutes < 60:
                    next_poll_text = f"⏰ Следующий опрос через {minutes} минут"
                else:
                    hours = minutes // 60
                    remaining_minutes = minutes % 60
                    if remaining_minutes == 0:
                        next_poll_text = f"⏰ Следующий опрос через {hours} час{'а' if 1 < hours < 5 else 'ов'}"
                    else:
                        next_poll_text = f"⏰ Следующий опрос через {hours}ч {remaining_minutes}м"
                logger.info(f"Generated next_poll_text: {next_poll_text}")
        except Exception as e:
            logger.warning(f"Could not get next poll time: {e}", exc_info=True)
    else:
        logger.info(f"User {telegram_id} not found in scheduler_service.jobs")

    text = (
        f"⚙️ Настройки бота\n\n"
        f"Текущие настройки:\n\n"
        f"📅 Интервалы опросов:\n"
        f"• Будни: каждые {weekday_str}\n"
        f"• Выходные: каждые {weekend_str}\n"
    )

    if next_poll_text:
        text += f"• {next_poll_text}\n"
    else:
        # If no poll scheduled, schedule one now
        from src.api.handlers.poll import send_automatic_poll
        try:
            await scheduler_service.schedule_poll(
                user_id=telegram_id,
                settings=settings,
                user_timezone=user.get("timezone", "Europe/Moscow"),
                send_poll_callback=lambda uid: send_automatic_poll(callback.bot, uid)
            )
            logger.info(f"Scheduled poll for user {telegram_id} from settings menu")

            # Now get the time
            if telegram_id in scheduler_service.jobs:
                job_id = scheduler_service.jobs[telegram_id]
                job = scheduler_service.scheduler.get_job(job_id)
                if job and job.next_run_time:
                    from datetime import datetime, timezone
                    now = datetime.now(timezone.utc)
                    time_until = job.next_run_time - now
                    minutes = int(time_until.total_seconds() / 60)

                    if minutes < 60:
                        next_poll_text = f"⏰ Следующий опрос через {minutes} минут"
                    else:
                        hours = minutes // 60
                        remaining_minutes = minutes % 60
                        if remaining_minutes == 0:
                            next_poll_text = f"⏰ Следующий опрос через {hours} час{'а' if 1 < hours < 5 else 'ов'}"
                        else:
                            next_poll_text = f"⏰ Следующий опрос через {hours}ч {remaining_minutes}м"

                    text += f"• {next_poll_text}\n"
        except Exception as e:
            logger.error(f"Failed to schedule poll: {e}", exc_info=True)

    text += (
        f"\n🌙 Тихие часы:\n"
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

    # Fetch updated settings and reschedule poll with new interval
    updated_settings = await settings_service.get_settings(user["id"])
    from src.api.handlers.poll import send_automatic_poll
    await scheduler_service.schedule_poll(
        user_id=telegram_id,
        settings=updated_settings,
        user_timezone=user.get("timezone", "Europe/Moscow"),
        send_poll_callback=lambda uid: send_automatic_poll(callback.bot, uid)
    )
    logger.info(f"Rescheduled poll for user {telegram_id} after weekday interval change to {interval} minutes")

    hours = interval // 60
    text = (
        f"✅ Интервал для будних дней обновлён!\n\n"
        f"Теперь бот будет спрашивать каждые {hours}ч в будние дни."
    )

    await callback.message.answer(text, reply_markup=get_confirmation_keyboard())
    await callback.answer()


@router.callback_query(F.data == "weekday_custom")
async def show_weekday_custom_input(callback: types.CallbackQuery, state: FSMContext):
    """Show custom weekday interval input prompt."""
    text = (
        "📅 Укажи свой интервал для будних дней\n\n"
        "Введи количество минут (от 30 до 480).\n\n"
        "Примеры:\n"
        "• 90 — каждые 1.5 часа\n"
        "• 150 — каждые 2.5 часа\n\n"
        "Или отправь /cancel для отмены"
    )

    await callback.message.answer(text)
    await state.set_state(SettingsStates.waiting_for_weekday_interval_custom)
    await callback.answer()


@router.message(SettingsStates.waiting_for_weekday_interval_custom)
async def process_weekday_custom_input(message: types.Message, state: FSMContext):
    """Process custom weekday interval input."""
    try:
        interval = int(message.text.strip())

        # Validation
        if interval < 30 or interval > 480:
            await message.answer(
                "⚠️ Интервал должен быть от 30 до 480 минут (0.5-8 часов).\n"
                "Попробуй ещё раз:"
            )
            return

        user_service = UserService(api_client)
        settings_service = UserSettingsService(api_client)
        telegram_id = message.from_user.id

        user = await user_service.get_by_telegram_id(telegram_id)
        settings = await settings_service.get_settings(user["id"])

        await settings_service.update_settings(settings["id"], poll_interval_weekday=interval)

        # Fetch updated settings and reschedule poll
        updated_settings = await settings_service.get_settings(user["id"])
        from src.api.handlers.poll import send_automatic_poll
        await scheduler_service.schedule_poll(
            user_id=telegram_id,
            settings=updated_settings,
            user_timezone=user.get("timezone", "Europe/Moscow"),
            send_poll_callback=lambda uid: send_automatic_poll(message.bot, uid)
        )
        logger.info(f"Rescheduled poll for user {telegram_id} with custom weekday interval {interval}")

        hours = interval // 60
        minutes = interval % 60
        if hours > 0 and minutes > 0:
            interval_str = f"{hours}ч {minutes}м"
        elif hours > 0:
            interval_str = f"{hours}ч"
        else:
            interval_str = f"{minutes}м"

        text = (
            f"✅ Интервал для будних дней обновлён!\n\n"
            f"Теперь бот будет спрашивать каждые {interval_str} в будние дни."
        )

        await message.answer(text, reply_markup=get_confirmation_keyboard())
        await state.clear()

    except ValueError:
        await message.answer(
            "⚠️ Неверный формат! Введи целое число (например: 90):"
        )


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

    # Fetch updated settings and reschedule poll with new interval
    updated_settings = await settings_service.get_settings(user["id"])
    from src.api.handlers.poll import send_automatic_poll
    await scheduler_service.schedule_poll(
        user_id=telegram_id,
        settings=updated_settings,
        user_timezone=user.get("timezone", "Europe/Moscow"),
        send_poll_callback=lambda uid: send_automatic_poll(callback.bot, uid)
    )
    logger.info(f"Rescheduled poll for user {telegram_id} after weekend interval change to {interval} minutes")

    hours = interval // 60
    text = (
        f"✅ Интервал для выходных обновлён!\n\n"
        f"Теперь бот будет спрашивать каждые {hours}ч в выходные дни."
    )

    await callback.message.answer(text, reply_markup=get_confirmation_keyboard())
    await callback.answer()


@router.callback_query(F.data == "weekend_custom")
async def show_weekend_custom_input(callback: types.CallbackQuery, state: FSMContext):
    """Show custom weekend interval input prompt."""
    text = (
        "🎉 Укажи свой интервал для выходных\n\n"
        "Введи количество минут (от 30 до 600).\n\n"
        "Примеры:\n"
        "• 120 — каждые 2 часа\n"
        "• 210 — каждые 3.5 часа\n\n"
        "Или отправь /cancel для отмены"
    )

    await callback.message.answer(text)
    await state.set_state(SettingsStates.waiting_for_weekend_interval_custom)
    await callback.answer()


@router.message(SettingsStates.waiting_for_weekend_interval_custom)
async def process_weekend_custom_input(message: types.Message, state: FSMContext):
    """Process custom weekend interval input."""
    try:
        interval = int(message.text.strip())

        # Validation
        if interval < 30 or interval > 600:
            await message.answer(
                "⚠️ Интервал должен быть от 30 до 600 минут (0.5-10 часов).\n"
                "Попробуй ещё раз:"
            )
            return

        user_service = UserService(api_client)
        settings_service = UserSettingsService(api_client)
        telegram_id = message.from_user.id

        user = await user_service.get_by_telegram_id(telegram_id)
        settings = await settings_service.get_settings(user["id"])

        await settings_service.update_settings(settings["id"], poll_interval_weekend=interval)

        # Fetch updated settings and reschedule poll
        updated_settings = await settings_service.get_settings(user["id"])
        from src.api.handlers.poll import send_automatic_poll
        await scheduler_service.schedule_poll(
            user_id=telegram_id,
            settings=updated_settings,
            user_timezone=user.get("timezone", "Europe/Moscow"),
            send_poll_callback=lambda uid: send_automatic_poll(message.bot, uid)
        )
        logger.info(f"Rescheduled poll for user {telegram_id} with custom weekend interval {interval}")

        hours = interval // 60
        minutes = interval % 60
        if hours > 0 and minutes > 0:
            interval_str = f"{hours}ч {minutes}м"
        elif hours > 0:
            interval_str = f"{hours}ч"
        else:
            interval_str = f"{minutes}м"

        text = (
            f"✅ Интервал для выходных обновлён!\n\n"
            f"Теперь бот будет спрашивать каждые {interval_str} в выходные дни."
        )

        await message.answer(text, reply_markup=get_confirmation_keyboard())
        await state.clear()

    except ValueError:
        await message.answer(
            "⚠️ Неверный формат! Введи целое число (например: 120):"
        )


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


@router.callback_query(F.data == "quiet_time")
async def show_quiet_time_selection(callback: types.CallbackQuery):
    """Show selection between start and end time."""
    text = (
        "⏰ Изменить время тихих часов\n\n"
        "Что хочешь изменить?"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌙 Время начала", callback_data="quiet_select_start")],
        [InlineKeyboardButton(text="🌅 Время окончания", callback_data="quiet_select_end")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="settings_quiet_hours")],
    ])
    await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "quiet_select_start")
async def show_quiet_start_selection(callback: types.CallbackQuery):
    """Show quiet hours start time selection."""
    user_service = UserService(api_client)
    settings_service = UserSettingsService(api_client)
    telegram_id = callback.from_user.id

    user = await user_service.get_by_telegram_id(telegram_id)
    settings = await settings_service.get_settings(user["id"])

    current_start = settings["quiet_hours_start"]
    current_text = current_start[:5] if current_start else "не установлено"

    text = (
        f"🌙 Время начала тихих часов\n\n"
        f"Текущее время: {current_text}\n\n"
        f"Выбери новое время начала тихих часов:"
    )

    await callback.message.answer(text, reply_markup=get_quiet_hours_start_keyboard())
    await callback.answer()


@router.callback_query(F.data == "quiet_select_end")
async def show_quiet_end_selection(callback: types.CallbackQuery):
    """Show quiet hours end time selection."""
    user_service = UserService(api_client)
    settings_service = UserSettingsService(api_client)
    telegram_id = callback.from_user.id

    user = await user_service.get_by_telegram_id(telegram_id)
    settings = await settings_service.get_settings(user["id"])

    current_end = settings["quiet_hours_end"]
    current_text = current_end[:5] if current_end else "не установлено"

    text = (
        f"🌅 Время окончания тихих часов\n\n"
        f"Текущее время: {current_text}\n\n"
        f"Выбери новое время окончания тихих часов:"
    )

    await callback.message.answer(text, reply_markup=get_quiet_hours_end_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("quiet_start_"))
async def set_quiet_start_time(callback: types.CallbackQuery, state: FSMContext):
    """Set quiet hours start time."""
    # Extract time from callback (e.g., "quiet_start_23:00" -> "23:00")
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
        await callback.answer()
        return

    time_str = parts[-1]  # e.g., "23:00"

    user_service = UserService(api_client)
    settings_service = UserSettingsService(api_client)
    telegram_id = callback.from_user.id

    user = await user_service.get_by_telegram_id(telegram_id)
    settings = await settings_service.get_settings(user["id"])

    # Update with full time format (HH:MM:SS)
    await settings_service.update_settings(
        settings["id"],
        quiet_hours_start=f"{time_str}:00"
    )

    text = f"✅ Время начала тихих часов обновлено!\n\nТеперь тихие часы начинаются в {time_str}"

    await callback.message.answer(text, reply_markup=get_confirmation_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("quiet_end_"))
async def set_quiet_end_time(callback: types.CallbackQuery, state: FSMContext):
    """Set quiet hours end time."""
    # Extract time from callback (e.g., "quiet_end_07:00" -> "07:00")
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
        await callback.answer()
        return

    time_str = parts[-1]  # e.g., "07:00"

    user_service = UserService(api_client)
    settings_service = UserSettingsService(api_client)
    telegram_id = callback.from_user.id

    user = await user_service.get_by_telegram_id(telegram_id)
    settings = await settings_service.get_settings(user["id"])

    # Update with full time format (HH:MM:SS)
    await settings_service.update_settings(
        settings["id"],
        quiet_hours_end=f"{time_str}:00"
    )

    text = f"✅ Время окончания тихих часов обновлено!\n\nТеперь тихие часы заканчиваются в {time_str}"

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
async def set_reminder_delay(callback: types.CallbackQuery, state: FSMContext):
    """Set reminder delay."""
    # Extract delay from callback data (e.g., "reminder_delay_30" -> 30)
    parts = callback.data.split("_")

    if parts[-1] == "custom":
        # Handle custom input - show input prompt
        text = (
            "⏱ Укажи свою задержку напоминания\n\n"
            "Введи количество минут (от 5 до 120).\n\n"
            "Примеры:\n"
            "• 10 — напомнить через 10 минут\n"
            "• 45 — напомнить через 45 минут\n\n"
            "Или отправь /cancel для отмены"
        )

        await callback.message.answer(text)
        await state.set_state(SettingsStates.waiting_for_reminder_delay_custom)
        await callback.answer()
        return

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


@router.message(SettingsStates.waiting_for_reminder_delay_custom)
async def process_reminder_delay_custom(message: types.Message, state: FSMContext):
    """Process custom reminder delay input."""
    try:
        delay = int(message.text.strip())

        # Validation
        if delay < 5 or delay > 120:
            await message.answer(
                "⚠️ Задержка должна быть от 5 до 120 минут.\n"
                "Попробуй ещё раз:"
            )
            return

        user_service = UserService(api_client)
        settings_service = UserSettingsService(api_client)
        telegram_id = message.from_user.id

        user = await user_service.get_by_telegram_id(telegram_id)
        settings = await settings_service.get_settings(user["id"])

        await settings_service.update_settings(settings["id"], reminder_delay_minutes=delay)

        text = f"✅ Задержка напоминания обновлена!\n\nТеперь бот будет напоминать через {delay} минут."

        await message.answer(text, reply_markup=get_confirmation_keyboard())
        await state.clear()

    except ValueError:
        await message.answer(
            "⚠️ Неверный формат! Введи целое число (например: 45):"
        )


@router.message(SettingsStates.waiting_for_quiet_hours_start_custom)
async def process_custom_quiet_start(message: types.Message, state: FSMContext):
    """Process custom quiet hours start time input."""
    time_str = message.text.strip()

    # Validate time format (HH:MM)
    if not re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', time_str):
        await message.answer(
            "⚠️ Неверный формат времени!\n\n"
            "Введи время в формате ЧЧ:ММ\n"
            "Например: 23:00 или 22:30"
        )
        return

    user_service = UserService(api_client)
    settings_service = UserSettingsService(api_client)
    telegram_id = message.from_user.id

    user = await user_service.get_by_telegram_id(telegram_id)
    settings = await settings_service.get_settings(user["id"])

    # Update with full time format (HH:MM:SS)
    await settings_service.update_settings(
        settings["id"],
        quiet_hours_start=f"{time_str}:00"
    )

    text = f"✅ Время начала тихих часов обновлено!\n\nТеперь тихие часы начинаются в {time_str}"

    await message.answer(text, reply_markup=get_confirmation_keyboard())
    await state.clear()


@router.message(SettingsStates.waiting_for_quiet_hours_end_custom)
async def process_custom_quiet_end(message: types.Message, state: FSMContext):
    """Process custom quiet hours end time input."""
    time_str = message.text.strip()

    # Validate time format (HH:MM)
    if not re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', time_str):
        await message.answer(
            "⚠️ Неверный формат времени!\n\n"
            "Введи время в формате ЧЧ:ММ\n"
            "Например: 07:00 или 08:30"
        )
        return

    user_service = UserService(api_client)
    settings_service = UserSettingsService(api_client)
    telegram_id = message.from_user.id

    user = await user_service.get_by_telegram_id(telegram_id)
    settings = await settings_service.get_settings(user["id"])

    # Update with full time format (HH:MM:SS)
    await settings_service.update_settings(
        settings["id"],
        quiet_hours_end=f"{time_str}:00"
    )

    text = f"✅ Время окончания тихих часов обновлено!\n\nТеперь тихие часы заканчиваются в {time_str}"

    await message.answer(text, reply_markup=get_confirmation_keyboard())
    await state.clear()


@router.callback_query(F.data == "main_menu")
async def return_to_main_menu(callback: types.CallbackQuery, state: FSMContext):
    """Return to main menu."""
    await state.clear()
    text = "🏠 Главное меню"
    await callback.message.answer(text, reply_markup=get_main_menu_keyboard())
    await callback.answer()
