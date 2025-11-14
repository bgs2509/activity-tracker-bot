"""Keyboards for AI activity suggestions.

This module provides keyboard layouts for displaying AI-generated activity
suggestions to the user. Each suggestion shows category, description, and time.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict, Any


def get_ai_suggestions_keyboard(
    suggestions: List[Dict[str, Any]],
    show_cancel: bool = True
) -> InlineKeyboardMarkup:
    """Build keyboard with 3 AI-suggested activity variants.

    Each button shows: Category | Description | Time period

    Args:
        suggestions: List of 3 activity suggestions with category, description,
            start_time, end_time
        show_cancel: Whether to show cancel button

    Returns:
        Inline keyboard with suggestion buttons

    Example:
        >>> suggestions = [
        ...     {
        ...         "category": "Образование",
        ...         "description": "Читал книгу",
        ...         "start_time": "2025-01-15T14:00:00+00:00",
        ...         "end_time": "2025-01-15T15:30:00+00:00"
        ...     },
        ...     ...
        ... ]
        >>> keyboard = get_ai_suggestions_keyboard(suggestions)
    """
    buttons = []

    for idx, suggestion in enumerate(suggestions[:3]):  # Max 3 suggestions
        # Format time display
        time_text = _format_time_range(
            suggestion.get("start_time"),
            suggestion.get("end_time")
        )

        # Build button text: "📚 Образование: Читал книгу | 14:00-15:30 (1ч 30м)"
        category = suggestion.get("category", "Без категории")
        description = suggestion.get("description", "")

        # Truncate description if too long
        if len(description) > 25:
            description = description[:22] + "..."

        button_text = f"{category}: {description}"
        if time_text:
            button_text += f" | {time_text}"

        buttons.append([
            InlineKeyboardButton(
                text=button_text,
                callback_data=f"ai_suggestion_{idx}"
            )
        ])

    # Add cancel button
    if show_cancel:
        buttons.append([
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data="ai_cancel"
            )
        ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_ai_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Build keyboard for confirming AI-parsed complete activity.

    Used when AI has high confidence and all data (category, description, time).

    Returns:
        Inline keyboard with Save/Edit/Cancel buttons
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="✅ Сохранить",
                callback_data="ai_confirm_save"
            )
        ],
        [
            InlineKeyboardButton(
                text="✏️ Изменить",
                callback_data="ai_request_edit"
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data="ai_cancel"
            )
        ]
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _format_time_range(start_time: str | None, end_time: str | None) -> str:
    """Format time range for display in button.

    Args:
        start_time: ISO timestamp or None
        end_time: ISO timestamp or None

    Returns:
        Formatted string like "14:00-15:30 (1ч 30м)" or empty string

    Example:
        >>> _format_time_range("2025-01-15T14:00:00+00:00", "2025-01-15T15:30:00+00:00")
        "14:00-15:30 (1ч 30м)"
    """
    if not start_time or not end_time:
        return ""

    try:
        from datetime import datetime

        start = datetime.fromisoformat(start_time)
        end = datetime.fromisoformat(end_time)

        # Format times
        start_str = start.strftime("%H:%M")
        end_str = end.strftime("%H:%M")

        # Calculate duration
        duration_minutes = int((end - start).total_seconds() / 60)
        hours = duration_minutes // 60
        minutes = duration_minutes % 60

        if hours > 0 and minutes > 0:
            duration_str = f"{hours}ч {minutes}м"
        elif hours > 0:
            duration_str = f"{hours}ч"
        else:
            duration_str = f"{minutes}м"

        return f"{start_str}-{end_str} ({duration_str})"

    except (ValueError, TypeError):
        return ""
