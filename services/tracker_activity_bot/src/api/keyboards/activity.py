"""Keyboards for activity management."""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List


def get_recent_activities_keyboard(activities: List[dict]) -> InlineKeyboardMarkup:
    """Get keyboard with recent activities as inline buttons.

    Creates a keyboard with up to 10 recent activity descriptions
    displayed in 2 columns. Each button displays activity description
    split into 2 lines for better readability.

    Args:
        activities: List of activity dicts with 'id' and 'description' fields.
                   Expected from API response with ActivityResponse schema.

    Returns:
        Keyboard with recent activity buttons in 2 columns (5 rows max)
        and an option to enter custom description
    """
    buttons = []

    # Take only first 10 activities
    recent_activities = activities[:10]

    # Create rows with 2 buttons each (2 columns layout)
    for i in range(0, len(recent_activities), 2):
        row = []
        for j in range(i, min(i + 2, len(recent_activities))):
            activity = recent_activities[j]
            description = activity.get("description", "")

            # Split description into 2 lines for better readability
            # Line 1: first ~20 chars, Line 2: next ~20 chars
            display_text = _format_two_line_button(description)

            row.append(InlineKeyboardButton(
                text=display_text,
                callback_data=f"activity_desc_{activity['id']}"
            ))
        buttons.append(row)

    # Add "Enter custom description" button
    buttons.append([InlineKeyboardButton(
        text="✏️ Ввести своё",
        callback_data="activity_custom_desc"
    )])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _format_two_line_button(text: str, max_line_length: int = 20) -> str:
    """Format text for two-line button display.

    Splits text into two lines, attempting to break at word boundaries
    when possible to avoid cutting words in half.

    Args:
        text: Original text to format
        max_line_length: Maximum characters per line (default: 20)

    Returns:
        Formatted text with newline separator for two-line display
    """
    if len(text) <= max_line_length:
        # Short text - display as single line
        return text

    # Try to find good break point near max_line_length
    # Look for space character to avoid splitting words
    break_point = text.rfind(" ", 0, max_line_length)

    if break_point == -1 or break_point < max_line_length // 2:
        # No good break point found, or break is too early - use hard limit
        break_point = max_line_length

    line1 = text[:break_point].strip()
    line2 = text[break_point:].strip()

    # Truncate second line if too long
    if len(line2) > max_line_length:
        line2 = line2[:max_line_length - 3] + "..."

    return f"{line1}\n{line2}"
