"""Activity management handlers for viewing, canceling, and FSM control."""

import logging

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from src.api.decorators import require_user
from src.api.dependencies import ServiceContainer
from src.api.keyboards.main_menu import get_main_menu_keyboard
from src.application.utils.formatters import format_activity_list
from src.application.utils.decorators import with_typing_action
from src.application.utils.fsm_helpers import clear_state_and_timeout
from src.application.services import fsm_timeout_service as fsm_timeout_module
from src.core.constants import MAX_ACTIVITY_LIMIT

from .helpers import cancel_activity_recording

router = Router()
logger = logging.getLogger(__name__)
async def cancel_action(callback: types.CallbackQuery, state: FSMContext):
    """Cancel current action."""
    await clear_state_and_timeout(state, callback.from_user.id)
    await callback.message.answer(
        "❌ Действие отменено.",
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "my_activities")
@with_typing_action
@require_user
async def show_my_activities(callback: types.CallbackQuery, services: ServiceContainer, user: dict):
    """Show user's recent activities."""
    try:
        # Get user's activities (returns list directly)
        activities = await services.activity.get_user_activities(user["id"], limit=MAX_ACTIVITY_LIMIT)

        # Format and send
        text = format_activity_list(activities)

        await callback.message.answer(text, reply_markup=get_main_menu_keyboard())
        await callback.answer()

    except Exception as e:
        logger.error(f"Error fetching activities: {e}")
        await callback.message.answer(
            "⚠️ Произошла ошибка при получении активностей.",
            reply_markup=get_main_menu_keyboard()
        )
        await callback.answer()


# NOTE: Removed handlers to avoid duplication and clean up YAGNI violations:
# - "categories" callback handler (full implementation in categories.py)
# - "statistics" placeholder handler (not implemented, button removed from menu)


@router.message(Command("cancel"))
async def cancel_activity_fsm(message: types.Message, state: FSMContext):
    """Cancel activity recording process.

    Handles /cancel command to exit from activity recording FSM.
    """
    current_state = await state.get_state()

    if current_state is None or not current_state.startswith("ActivityStates"):
        await message.answer(
            "Нечего отменять. Ты сейчас не записываешь активность.",
            reply_markup=get_main_menu_keyboard()
        )
        return

    await state.clear()
    # Cancel FSM timeout
    if fsm_timeout_module.fsm_timeout_service:
        fsm_timeout_module.fsm_timeout_service.cancel_timeout(message.from_user.id)
    await message.answer(
        "❌ Запись активности отменена.",
        reply_markup=get_main_menu_keyboard()
    )


@router.callback_query(F.data == "fsm_reminder_continue")
@with_typing_action
async def handle_fsm_reminder_continue(callback: types.CallbackQuery, state: FSMContext):
    """Handle 'Continue' button in FSM timeout reminder.

    User clicked 'Continue' button in reminder message, so:
    1. Cancel cleanup timer
    2. Restart 10-minute timeout timer
    3. Show appropriate message based on current state
    """
    user_id = callback.from_user.id

    # Cancel cleanup timer
    if fsm_timeout_module.fsm_timeout_service:
        fsm_timeout_module.fsm_timeout_service.cancel_cleanup_timer(user_id)

    # Get current state
    current_state = await state.get_state()

    if not current_state:
        await callback.message.answer(
            "👌 Хорошо! Можешь начать заново из главного меню.",
            reply_markup=get_main_menu_keyboard()
        )
        await callback.answer()
        return

    # Restart timeout timer
    if fsm_timeout_module.fsm_timeout_service:
        fsm_timeout_module.fsm_timeout_service.schedule_timeout(
            user_id=user_id,
            state=current_state,
            bot=callback.bot
        )

    # Show appropriate message based on state
    state_str = str(current_state)

    if "waiting_for_start_time" in state_str:
        text = "⏰ Укажи время НАЧАЛА активности"
    elif "waiting_for_end_time" in state_str:
        text = "⏰ Укажи время ОКОНЧАНИЯ активности"
    elif "waiting_for_description" in state_str:
        text = "✏️ Опиши активность"
    elif "waiting_for_category" in state_str:
        text = "📂 Выбери категорию"
    elif "waiting_for_name" in state_str:
        text = "📝 Введи название категории"
    elif "waiting_for_emoji" in state_str:
        text = "😀 Выбери эмодзи для категории"
    elif "waiting_for_poll_category" in state_str:
        text = "✏️ Выбери категорию для активности"
    elif "waiting_for_poll_description" in state_str:
        text = "✏️ Опиши активность из опроса"
    elif "interval" in state_str:
        text = "⏰ Введи интервал опроса в минутах"
    elif "quiet_hours" in state_str:
        text = "🌙 Введи время тихих часов"
    elif "reminder" in state_str:
        text = "⏰ Введи задержку напоминания в минутах"
    else:
        text = "Продолжай! Жду твоего ответа."

    await callback.message.answer(text)
    await callback.answer("✅ Продолжаем!")


@router.callback_query(F.data == "help")
@with_typing_action
async def show_help(callback: types.CallbackQuery):
    """Show help message."""
    text = (
        "❓ Справка по боту\n\n"
        "Этот бот помогает отслеживать твою активность в течение дня.\n\n"
        "📝 Записать активность\n"
        "Начни запись новой активности. Бот попросит указать:\n"
        "• Время начала (14:30, 30м назад, 2ч назад)\n"
        "• Время окончания (16:00, 30м, сейчас)\n"
        "• Описание и категорию\n\n"
        "⏰ Автоматические опросы\n"
        "Бот периодически спрашивает о твоей активности:\n"
        "• В будни: каждые 2 часа (по умолчанию)\n"
        "• В выходные: каждые 3 часа (по умолчанию)\n"
        "• С учётом тихих часов (23:00 — 07:00)\n"
        "Настроить интервалы можно в разделе \"Настройки\"\n\n"
        "📋 Мои записи\n"
        "Просмотр последних 10 записанных активностей\n\n"
        "📂 Категории\n"
        "Список всех твоих категорий\n\n"
        "⚙️ Настройки\n"
        "Настройка интервалов опросов, тихих часов и напоминаний\n\n"
        "Примеры форматов времени:\n"
        "• 14:30 или 14-30 — точное время\n"
        "• 30м или 30 — минут назад\n"
        "• 2ч или 2h — часов назад\n"
        "• сейчас или 0 — текущее время"
    )

    await callback.message.answer(text, reply_markup=get_main_menu_keyboard())
    await callback.answer()


# Note: Full implementation would include:
# - process_end_time handler
# - process_description handler
# - process_category handler
# - save activity to database
# For PoC, this demonstrates the FSM flow and HTTP-only data access pattern
