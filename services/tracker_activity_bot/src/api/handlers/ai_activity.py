"""AI-powered activity creation handlers.

This module implements natural language activity parsing and recording using AI.
Unlike the manual flow, users can type free-form text at any time, and the AI
will attempt to extract category, description, and time information.

Flow:
    1. User sends text message (not in active FSM state)
    2. AI analyzes text with context (categories, recent activities)
    3a. If confidence HIGH and data complete → Show confirmation
    3b. If confidence MEDIUM/LOW → Show 3 suggestions
    4. User selects suggestion or refines input
    5. Activity saved

Architecture:
- Integrates with AIService for parsing
- Uses shared activity creation functions from activity.shared
- Respects existing FSM states (doesn't interrupt active dialogs)
"""

import logging
from datetime import datetime
from typing import Any, Dict

from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext

from src.api.dependencies import ServiceContainer
from src.api.keyboards.ai_suggestions import (
    get_ai_suggestions_keyboard,
    get_ai_confirmation_keyboard
)
from src.api.keyboards.main_menu import get_main_menu_keyboard
from src.api.states.ai_activity import AIActivityStates
from src.application.services.ai_service import AIService
from src.application.services import fsm_timeout_service as fsm_timeout_module
from src.application.utils.formatters import extract_tags, format_time, format_duration
from src.application.utils.decorators import with_typing_action

logger = logging.getLogger(__name__)

router = Router()

# Initialize AI service (shared instance)
ai_service = AIService()


@router.message(F.text, ~F.text.startswith("/"))
@with_typing_action
async def handle_ai_activity_input(
    message: types.Message,
    state: FSMContext,
    services: ServiceContainer
):
    """Handle text input for AI activity parsing.

    This handler catches all text messages that don't start with commands.
    It only processes them if:
    1. AI service is enabled
    2. User is not in an active FSM state
    3. Text is not a button text from keyboards

    Args:
        message: User's text message
        state: FSM context
        services: Service container with HTTP clients

    Flow:
        Text → AI parsing → Confirmation or Suggestions → Save
    """
    # Check if user is in active FSM state
    current_state = await state.get_state()
    if current_state is not None:
        # User is in middle of another flow, don't intercept
        logger.debug(
            "Skipping AI parsing - user in active state",
            extra={
                "telegram_user_id": message.from_user.id,
                "current_state": current_state
            }
        )
        return

    # Check if AI service is enabled
    if not ai_service.enabled:
        logger.debug("AI service disabled, ignoring text message")
        return

    # Ignore button text from main menu
    button_texts = [
        "📝 Записать активность",
        "📊 Мои активности",
        "⚙️ Настройки",
        "📂 Категории"
    ]
    if message.text in button_texts:
        return

    telegram_id = message.from_user.id
    user_input = message.text.strip()

    # Minimum length check
    if len(user_input) < 3:
        await message.answer(
            "🤔 Слишком короткий текст. Напиши подробнее, например:\n"
            "• «читал книгу 2 часа»\n"
            "• «бег с 7:00 до 7:30»\n"
            "• «работа над проектом с 14:00 до 16:00»"
        )
        return

    logger.info(
        "Processing AI activity input",
        extra={
            "telegram_user_id": telegram_id,
            "input_length": len(user_input)
        }
    )

    try:
        # Get user data
        user = await services.user.get_by_telegram_id(telegram_id)
        if not user:
            await message.answer(
                "⚠️ Пользователь не найден. Используй /start для регистрации.",
                reply_markup=get_main_menu_keyboard()
            )
            return

        # Get user categories
        categories = await services.category.get_user_categories(user["id"])
        if not categories:
            await message.answer(
                "⚠️ У тебя нет категорий. Сначала создай категорию через меню.",
                reply_markup=get_main_menu_keyboard()
            )
            return

        # Get recent activities for context
        recent_activities_response = await services.activity.get_user_activities(
            user_id=user["id"],
            limit=20
        )
        recent_activities = (
            recent_activities_response.get("activities", [])
            if isinstance(recent_activities_response, dict)
            else recent_activities_response
        )

        # Parse with AI
        result = await ai_service.parse_activity_text(
            user_input=user_input,
            categories=categories,
            recent_activities=recent_activities,
            user_timezone=user.get("timezone", "UTC")
        )

        if not result:
            # AI failed completely
            await message.answer(
                "⚠️ Не удалось распознать активность. Попробуй сформулировать иначе или "
                "используй кнопку «📝 Записать активность» для ручного ввода.",
                reply_markup=get_main_menu_keyboard()
            )
            return

        # Store parsed data in state
        await state.update_data(
            user_id=user["id"],
            ai_input=user_input,
            ai_result=result.raw_response
        )

        # Determine flow based on completeness and confidence
        if result.is_complete() and result.confidence == "high":
            # HIGH confidence with complete data → Show confirmation
            await _show_confirmation(message, state, result, categories)
        else:
            # MEDIUM/LOW confidence or incomplete → Show suggestions
            await _show_suggestions(message, state, result, categories)

    except Exception as e:
        logger.error(
            "Error processing AI activity input",
            extra={
                "telegram_user_id": telegram_id,
                "error": str(e)
            },
            exc_info=True
        )
        await message.answer(
            "⚠️ Произошла ошибка при обработке. Попробуй ещё раз.",
            reply_markup=get_main_menu_keyboard()
        )


async def _show_confirmation(
    message: types.Message,
    state: FSMContext,
    result: Any,
    categories: list
) -> None:
    """Show confirmation for high-confidence complete parsing.

    Args:
        message: User's message
        state: FSM context
        result: AI parsing result
        categories: User's categories list
    """
    # Find matching category
    category = next(
        (c for c in categories if c["name"] == result.category_name),
        None
    )

    if not category:
        # Category not found, fallback to suggestions
        await _show_suggestions(message, state, result, categories)
        return

    # Format times for display
    start_time = datetime.fromisoformat(result.start_time)
    end_time = datetime.fromisoformat(result.end_time)

    start_str = format_time(start_time)
    end_str = format_time(end_time)
    duration_minutes = int((end_time - start_time).total_seconds() / 60)
    duration_str = format_duration(duration_minutes)

    # Store activity data
    await state.update_data(
        category_id=category["id"],
        description=result.description,
        start_time=result.start_time,
        end_time=result.end_time
    )
    await state.set_state(AIActivityStates.waiting_for_ai_confirmation)

    # Schedule FSM timeout
    if fsm_timeout_module.fsm_timeout_service:
        fsm_timeout_module.fsm_timeout_service.schedule_timeout(
            user_id=message.from_user.id,
            state=AIActivityStates.waiting_for_ai_confirmation,
            bot=message.bot
        )

    # Build confirmation message
    emoji = category.get("emoji", "")
    text = (
        f"✅ **Активность распознана:**\n\n"
        f"{emoji} **{category['name']}**: {result.description}\n"
        f"🕐 {start_str} - {end_str} ({duration_str})\n\n"
        f"Сохранить?"
    )

    await message.answer(text, reply_markup=get_ai_confirmation_keyboard())


async def _show_suggestions(
    message: types.Message,
    state: FSMContext,
    result: Any,
    categories: list
) -> None:
    """Show 3 AI-generated suggestions for user to choose.

    Args:
        message: User's message
        state: FSM context
        result: AI parsing result with alternatives
        categories: User's categories list
    """
    # Build list of suggestions (main result + alternatives)
    suggestions = []

    # Add main suggestion
    if result.category_name and result.description:
        suggestions.append({
            "category": result.category_name,
            "description": result.description,
            "start_time": result.start_time,
            "end_time": result.end_time
        })

    # Add alternatives
    for alt in result.alternatives[:2]:  # Max 2 alternatives
        if alt.get("category") and alt.get("description"):
            suggestions.append(alt)

    if not suggestions:
        # No valid suggestions
        await message.answer(
            "⚠️ Не удалось понять активность. Попробуй переформулировать или "
            "используй кнопку «📝 Записать активность».",
            reply_markup=get_main_menu_keyboard()
        )
        return

    # Store suggestions in state
    await state.update_data(ai_suggestions=suggestions)
    await state.set_state(AIActivityStates.waiting_for_ai_clarification)

    # Schedule FSM timeout
    if fsm_timeout_module.fsm_timeout_service:
        fsm_timeout_module.fsm_timeout_service.schedule_timeout(
            user_id=message.from_user.id,
            state=AIActivityStates.waiting_for_ai_clarification,
            bot=message.bot
        )

    # Build message
    text = (
        "🤔 **Уточни активность:**\n\n"
        "Выбери один из вариантов или введи новый текст для уточнения:"
    )

    await message.answer(
        text,
        reply_markup=get_ai_suggestions_keyboard(suggestions)
    )


@router.callback_query(F.data == "ai_confirm_save")
@with_typing_action
async def handle_ai_confirm_save(
    callback: types.CallbackQuery,
    state: FSMContext,
    services: ServiceContainer
):
    """Save activity after user confirms high-confidence AI parsing.

    Args:
        callback: Callback query from confirmation button
        state: FSM context with stored activity data
        services: Service container
    """
    telegram_id = callback.from_user.id

    try:
        # Get data from state
        data = await state.get_data()
        user_id = data.get("user_id")
        category_id = data.get("category_id")
        description = data.get("description")
        start_time_str = data.get("start_time")
        end_time_str = data.get("end_time")

        if not all([user_id, category_id, description, start_time_str, end_time_str]):
            await callback.message.answer(
                "⚠️ Недостаточно данных. Попробуй ещё раз.",
                reply_markup=get_main_menu_keyboard()
            )
            await state.clear()

            # Cancel FSM timeout
            if fsm_timeout_module.fsm_timeout_service:
                fsm_timeout_module.fsm_timeout_service.cancel_timeout(telegram_id)

            await callback.answer()
            return

        # Parse times
        start_time = datetime.fromisoformat(start_time_str)
        end_time = datetime.fromisoformat(end_time_str)

        # Extract tags
        tags = extract_tags(description)

        # Save activity using shared function
        from src.api.handlers.activity.shared import create_and_save_activity

        await create_and_save_activity(
            message=callback.message,
            state=state,
            services=services,
            telegram_user_id=telegram_id,
            description=description,
            tags=tags,
            post_save_callback=None  # No poll scheduling for AI flow
        )

        await callback.answer("✅ Сохранено!")

    except Exception as e:
        logger.error(
            "Error saving AI-confirmed activity",
            extra={"telegram_user_id": telegram_id, "error": str(e)},
            exc_info=True
        )
        await callback.message.answer(
            "⚠️ Ошибка при сохранении.",
            reply_markup=get_main_menu_keyboard()
        )
        await state.clear()

        # Cancel FSM timeout
        if fsm_timeout_module.fsm_timeout_service:
            fsm_timeout_module.fsm_timeout_service.cancel_timeout(telegram_id)

        await callback.answer()


@router.callback_query(F.data.startswith("ai_suggestion_"))
@with_typing_action
async def handle_ai_suggestion_selection(
    callback: types.CallbackQuery,
    state: FSMContext,
    services: ServiceContainer
):
    """Handle selection of one of the AI suggestions.

    Args:
        callback: Callback query with suggestion index
        state: FSM context
        services: Service container
    """
    telegram_id = callback.from_user.id

    try:
        # Parse suggestion index
        idx_str = callback.data.replace("ai_suggestion_", "")
        idx = int(idx_str)

        # Get suggestions from state
        data = await state.get_data()
        suggestions = data.get("ai_suggestions", [])
        user_id = data.get("user_id")

        if idx >= len(suggestions):
            await callback.answer("⚠️ Неверный выбор")
            return

        suggestion = suggestions[idx]

        # Get user categories to find category_id
        categories = await services.category.get_user_categories(user_id)
        category = next(
            (c for c in categories if c["name"] == suggestion["category"]),
            None
        )

        if not category:
            await callback.message.answer(
                "⚠️ Категория не найдена.",
                reply_markup=get_main_menu_keyboard()
            )
            await state.clear()

            # Cancel FSM timeout
            if fsm_timeout_module.fsm_timeout_service:
                fsm_timeout_module.fsm_timeout_service.cancel_timeout(telegram_id)

            await callback.answer()
            return

        # Check if time data is complete
        if not suggestion.get("start_time") or not suggestion.get("end_time"):
            # Incomplete time data, ask user to clarify
            await callback.message.answer(
                f"⚠️ Не указано время для активности.\n\n"
                f"Используй кнопку «📝 Записать активность» чтобы указать время вручную.",
                reply_markup=get_main_menu_keyboard()
            )
            await state.clear()

            # Cancel FSM timeout
            if fsm_timeout_module.fsm_timeout_service:
                fsm_timeout_module.fsm_timeout_service.cancel_timeout(telegram_id)

            await callback.answer()
            return

        # Parse times
        start_time = datetime.fromisoformat(suggestion["start_time"])
        end_time = datetime.fromisoformat(suggestion["end_time"])
        description = suggestion["description"]

        # Extract tags
        tags = extract_tags(description)

        # Update state with selected suggestion
        await state.update_data(
            category_id=category["id"],
            description=description,
            start_time=suggestion["start_time"],
            end_time=suggestion["end_time"]
        )

        # Save activity using shared function
        from src.api.handlers.activity.shared import create_and_save_activity

        await create_and_save_activity(
            message=callback.message,
            state=state,
            services=services,
            telegram_user_id=telegram_id,
            description=description,
            tags=tags,
            post_save_callback=None  # No poll scheduling for AI flow
        )

        await callback.answer("✅ Сохранено!")

    except Exception as e:
        logger.error(
            "Error processing AI suggestion selection",
            extra={"telegram_user_id": telegram_id, "error": str(e)},
            exc_info=True
        )
        await callback.message.answer(
            "⚠️ Ошибка при сохранении.",
            reply_markup=get_main_menu_keyboard()
        )
        await state.clear()

        # Cancel FSM timeout
        if fsm_timeout_module.fsm_timeout_service:
            fsm_timeout_module.fsm_timeout_service.cancel_timeout(telegram_id)

        await callback.answer()


@router.callback_query(F.data == "ai_request_edit")
@with_typing_action
async def handle_ai_request_edit(
    callback: types.CallbackQuery,
    state: FSMContext
):
    """Handle request to edit/refine AI suggestion.

    User wants to provide more specific text instead of confirming.

    Args:
        callback: Callback query
        state: FSM context
    """
    await state.set_state(AIActivityStates.waiting_for_ai_clarification)

    # Reschedule FSM timeout for clarification state
    if fsm_timeout_module.fsm_timeout_service:
        fsm_timeout_module.fsm_timeout_service.schedule_timeout(
            user_id=callback.from_user.id,
            state=AIActivityStates.waiting_for_ai_clarification,
            bot=callback.message.bot
        )

    await callback.message.answer(
        "✏️ Введи уточнённое описание активности.\n\n"
        "Например:\n"
        "• «читал книгу по Python с 14:00 до 15:30»\n"
        "• «бег в парке 30 минут»"
    )
    await callback.answer()


@router.message(AIActivityStates.waiting_for_ai_clarification)
@with_typing_action
async def handle_ai_clarification_input(
    message: types.Message,
    state: FSMContext,
    services: ServiceContainer
):
    """Handle refined text input when user is in clarification state.

    User provided additional text to clarify the activity.
    Re-run AI parsing with new input.

    Args:
        message: User's refined text
        state: FSM context
        services: Service container
    """
    telegram_id = message.from_user.id
    user_input = message.text.strip()

    if len(user_input) < 3:
        await message.answer(
            "🤔 Слишком короткий текст. Напиши подробнее."
        )
        return

    logger.info(
        "Processing AI clarification input",
        extra={
            "telegram_user_id": telegram_id,
            "input_length": len(user_input)
        }
    )

    try:
        # Get user data
        data = await state.get_data()
        user_id = data.get("user_id")

        # Get user info for timezone
        user = await services.user.get_by_telegram_id(telegram_id)
        if not user:
            await message.answer(
                "⚠️ Пользователь не найден. Используй /start для регистрации.",
                reply_markup=get_main_menu_keyboard()
            )
            await state.clear()

            # Cancel FSM timeout
            if fsm_timeout_module.fsm_timeout_service:
                fsm_timeout_module.fsm_timeout_service.cancel_timeout(telegram_id)

            return

        # Get categories
        categories = await services.category.get_user_categories(user_id)

        # Get recent activities
        recent_activities_response = await services.activity.get_user_activities(
            user_id=user_id,
            limit=20
        )
        recent_activities = (
            recent_activities_response.get("activities", [])
            if isinstance(recent_activities_response, dict)
            else recent_activities_response
        )

        # Parse with AI again
        result = await ai_service.parse_activity_text(
            user_input=user_input,
            categories=categories,
            recent_activities=recent_activities,
            user_timezone=user.get("timezone", "UTC")
        )

        if not result:
            await message.answer(
                "⚠️ Не удалось распознать. Попробуй ещё раз или используй "
                "кнопку «📝 Записать активность».",
                reply_markup=get_main_menu_keyboard()
            )
            await state.clear()

            # Cancel FSM timeout
            if fsm_timeout_module.fsm_timeout_service:
                fsm_timeout_module.fsm_timeout_service.cancel_timeout(telegram_id)

            return

        # Update state
        await state.update_data(
            ai_input=user_input,
            ai_result=result.raw_response
        )

        # Show result
        if result.is_complete() and result.confidence == "high":
            await _show_confirmation(message, state, result, categories)
        else:
            await _show_suggestions(message, state, result, categories)

    except Exception as e:
        logger.error(
            "Error processing AI clarification",
            extra={"telegram_user_id": telegram_id, "error": str(e)},
            exc_info=True
        )
        await message.answer(
            "⚠️ Произошла ошибка. Попробуй ещё раз.",
            reply_markup=get_main_menu_keyboard()
        )
        await state.clear()

        # Cancel FSM timeout
        if fsm_timeout_module.fsm_timeout_service:
            fsm_timeout_module.fsm_timeout_service.cancel_timeout(telegram_id)


@router.callback_query(F.data == "ai_cancel")
async def handle_ai_cancel(callback: types.CallbackQuery, state: FSMContext):
    """Cancel AI activity creation flow.

    Args:
        callback: Callback query
        state: FSM context
    """
    await state.clear()

    # Cancel FSM timeout
    if fsm_timeout_module.fsm_timeout_service:
        fsm_timeout_module.fsm_timeout_service.cancel_timeout(callback.from_user.id)

    await callback.message.answer(
        "❌ Отменено.",
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer()
