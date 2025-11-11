"""Shared logic for activity recording flows.

This module contains common functionality used by both manual activity
recording and automatic poll response flows to eliminate code duplication.

Functions:
    validate_description: Validate activity description input
    fetch_and_build_description_prompt: Build description prompt with suggestions
    create_and_save_activity: Create and save activity with error handling

Usage:
    from src.api.handlers.activity.shared import (
        validate_description,
        fetch_and_build_description_prompt,
        create_and_save_activity
    )
"""

import logging
from datetime import datetime
from typing import Callable, Awaitable

from aiogram import types
from aiogram.types import InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext

from src.api.dependencies import ServiceContainer
from src.api.keyboards.activity import get_recent_activities_keyboard
from src.api.keyboards.main_menu import get_main_menu_keyboard
from src.application.utils.formatters import (
    format_time,
    format_duration,
    extract_tags
)
from src.application.services import fsm_timeout_service as fsm_timeout_module

logger = logging.getLogger(__name__)


def validate_description(description: str, min_length: int = 3) -> tuple[bool, str | None]:
    """Validate activity description input.

    Checks that description meets minimum length requirements after
    stripping whitespace.

    Args:
        description: Description text to validate
        min_length: Minimum required length in characters (default: 3)

    Returns:
        Tuple of (is_valid, error_message)
        - If valid: (True, None)
        - If invalid: (False, error_message_string)

    Examples:
        >>> is_valid, error_msg = validate_description("ab")
        >>> if not is_valid:
        ...     await message.answer(error_msg)
        ...     return

        >>> is_valid, _ = validate_description("Работа над проектом")
        >>> assert is_valid is True

    Note:
        The error message is in Russian (user-facing).
    """
    description = description.strip()

    if not description or len(description) < min_length:
        return False, f"⚠️ Описание должно содержать минимум {min_length} символа. Попробуй ещё раз."

    return True, None


async def fetch_and_build_description_prompt(
    services: ServiceContainer,
    user_id: int,
    category_id: int,
    start_time: datetime,
    end_time: datetime,
    limit: int = 20
) -> tuple[str, InlineKeyboardMarkup | None]:
    """Fetch recent activities and build description prompt with keyboard.

    Fetches recent activities for the given category and builds a prompt
    message with inline keyboard showing recent activity suggestions.

    Args:
        services: Service container with data access
        user_id: Internal user ID (not Telegram ID)
        category_id: Category ID to filter activities
        start_time: Activity start time (for display)
        end_time: Activity end time (for display)
        limit: Maximum number of recent activities to fetch (default: 20)

    Returns:
        Tuple of (prompt_text, keyboard)
        - prompt_text: Formatted message with time range and instructions
        - keyboard: InlineKeyboardMarkup with recent activity buttons,
                   or None if no recent activities found

    Examples:
        >>> text, keyboard = await fetch_and_build_description_prompt(
        ...     services, 123, 456, start_time, end_time
        ... )
        >>> await message.answer(text, reply_markup=keyboard)

        # With recent activities:
        # text: "✏️ Опиши активность\\n\\n⏰ 10:00 — 12:00 (2ч)\\n\\nВыбери из последних..."
        # keyboard: InlineKeyboardMarkup with suggestion buttons

        # Without recent activities:
        # text: "✏️ Опиши активность\\n\\n⏰ 10:00 — 12:00 (2ч)\\n\\nНапиши, чем ты занимался..."
        # keyboard: None

    Note:
        All text is in Russian (user-facing).
        Errors are logged but gracefully handled (returns empty activities list).
    """
    # Fetch recent activities
    try:
        response = await services.activity.get_user_activities_by_category(
            user_id=user_id,
            category_id=category_id,
            limit=limit
        )
        recent_activities = (
            response.get("activities", [])
            if isinstance(response, dict)
            else response
        )
    except Exception as e:
        logger.error(
            "Error fetching recent activities for description prompt",
            extra={
                "user_id": user_id,
                "category_id": category_id,
                "error": str(e)
            },
            exc_info=True
        )
        recent_activities = []

    # Format time and duration
    start_time_str = format_time(start_time)
    end_time_str = format_time(end_time)
    duration_minutes = int((end_time - start_time).total_seconds() / 60)
    duration_str = format_duration(duration_minutes)

    # Build prompt text
    text = (
        f"✏️ Опиши активность\n\n"
        f"⏰ {start_time_str} — {end_time_str} ({duration_str})\n\n"
    )

    # Add suggestions or plain prompt
    if recent_activities:
        text += (
            "Выбери из последних или напиши своё (минимум 3 символа).\n"
            "Можешь добавить теги через #хештег"
        )
        keyboard = get_recent_activities_keyboard(recent_activities)
    else:
        text += (
            "Напиши, чем ты занимался (минимум 3 символа).\n"
            "Можешь добавить теги через #хештег"
        )
        keyboard = None

    logger.debug(
        "Built description prompt",
        extra={
            "user_id": user_id,
            "category_id": category_id,
            "recent_activities_count": len(recent_activities),
            "has_keyboard": keyboard is not None
        }
    )

    return text, keyboard


async def create_and_save_activity(
    message: types.Message,
    state: FSMContext,
    services: ServiceContainer,
    telegram_user_id: int,
    description: str,
    tags: list[str],
    post_save_callback: Callable[[dict], Awaitable[None]] | None = None
) -> bool:
    """Create and save activity with validation and error handling.

    Handles the complete flow of saving an activity:
    1. Validates required state data
    2. Parses time strings to datetime objects
    3. Creates activity via API
    4. Calls optional post-save callback (e.g., scheduling next poll)
    5. Sends success message to user
    6. Clears FSM state and cancels timeout
    7. Handles all errors gracefully

    Args:
        message: Message object to send responses to
        state: FSM context containing user_id, category_id, start_time, end_time
        services: Service container with data access
        telegram_user_id: Telegram user ID for FSM timeout cancellation
        description: Activity description text (already validated)
        tags: List of hashtags extracted from description
        post_save_callback: Optional async callback(state_data) called after
                           successful save. Used for flow-specific actions like
                           scheduling next poll. State data dict is passed.

    Returns:
        True if activity was saved successfully, False otherwise

    Examples:
        # Manual flow (no callback)
        >>> success = await create_and_save_activity(
        ...     message, state, services, telegram_id,
        ...     description="Работа", tags=["работа"]
        ... )

        # Automatic poll flow (with callback)
        >>> async def schedule_next_poll(data: dict):
        ...     await services.scheduler.schedule_poll(
        ...         user_id=telegram_id,
        ...         settings=data["settings"],
        ...         user_timezone=data["user_timezone"],
        ...         send_poll_callback=send_automatic_poll,
        ...         bot=message.bot
        ...     )
        >>>
        >>> success = await create_and_save_activity(
        ...     message, state, services, telegram_id,
        ...     description="Встреча", tags=["работа"],
        ...     post_save_callback=schedule_next_poll
        ... )

    Note:
        All user-facing messages are in Russian.
        Errors are logged with context for debugging.
    """
    # Get data from state
    data = await state.get_data()
    user_id = data.get("user_id")
    category_id = data.get("category_id")
    start_time_str = data.get("start_time")
    end_time_str = data.get("end_time")

    # Validate required data
    if not all([user_id, category_id, start_time_str, end_time_str, description]):
        logger.warning(
            "Insufficient data for saving activity",
            extra={
                "has_user_id": user_id is not None,
                "has_category_id": category_id is not None,
                "has_start_time": start_time_str is not None,
                "has_end_time": end_time_str is not None,
                "has_description": bool(description)
            }
        )
        await message.answer(
            "⚠️ Недостаточно данных для сохранения.",
            reply_markup=get_main_menu_keyboard()
        )
        await state.clear()
        return False

    try:
        # Parse time strings
        start_time = datetime.fromisoformat(start_time_str)
        end_time = datetime.fromisoformat(end_time_str)

        # Create activity
        await services.activity.create_activity(
            user_id=user_id,
            category_id=category_id,
            description=description,
            tags=tags,
            start_time=start_time,
            end_time=end_time
        )

        logger.info(
            "Activity created successfully",
            extra={
                "user_id": user_id,
                "category_id": category_id,
                "duration_minutes": int((end_time - start_time).total_seconds() / 60),
                "has_post_save_callback": post_save_callback is not None
            }
        )

        # Call post-save callback if provided (e.g., schedule next poll)
        if post_save_callback:
            try:
                await post_save_callback(data)
                logger.debug("Post-save callback executed successfully")
            except Exception as callback_error:
                logger.error(
                    "Error in post-save callback",
                    extra={"error": str(callback_error)},
                    exc_info=True
                )
                # Don't fail the whole operation if callback fails
                # Activity is already saved at this point

        # Format success message
        duration_minutes = int((end_time - start_time).total_seconds() / 60)
        duration_str = format_duration(duration_minutes)

        success_message = (
            f"✅ Активность сохранена!\n\n"
            f"{description}\n"
            f"Продолжительность: {duration_str}"
        )

        # Add poll-specific message if callback was provided
        if post_save_callback:
            success_message += "\n\nСледующий опрос придёт по расписанию."

        await message.answer(success_message, reply_markup=get_main_menu_keyboard())

        # Clear state and timeout
        await state.clear()

        if fsm_timeout_module.fsm_timeout_service:
            fsm_timeout_module.fsm_timeout_service.cancel_timeout(telegram_user_id)

        return True

    except Exception as e:
        logger.error(
            "Error saving activity",
            extra={
                "user_id": user_id,
                "telegram_user_id": telegram_user_id,
                "error": str(e)
            },
            exc_info=True
        )

        await message.answer(
            "⚠️ Ошибка при сохранении активности.",
            reply_markup=get_main_menu_keyboard()
        )
        await state.clear()

        if fsm_timeout_module.fsm_timeout_service:
            fsm_timeout_module.fsm_timeout_service.cancel_timeout(telegram_user_id)

        return False
