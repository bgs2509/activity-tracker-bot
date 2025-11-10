"""Keyboards for activity management."""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List


def get_recent_activities_keyboard(activities: List[dict]) -> InlineKeyboardMarkup:
    """Get keyboard with recent activities as inline buttons.

    Creates a keyboard with up to 10 recent activity descriptions
    displayed in 2 rows of 5 buttons each. Each button displays
    a truncated version of the activity description.

    Args:
        activities: List of activity dicts with 'id' and 'description' fields.
                   Expected from API response with ActivityResponse schema.

    Returns:
        Keyboard with recent activity buttons in 2 rows (5 buttons per row)
        and an option to enter custom description
    """
    buttons = []

    # Take only first 10 activities
    recent_activities = activities[:10]

    # Create rows with 5 buttons each
    for i in range(0, len(recent_activities), 5):
        row = []
        for j in range(i, min(i + 5, len(recent_activities))):
            activity = recent_activities[j]
            description = activity.get("description", "")

            # Truncate long descriptions to fit button (max ~30 chars)
            display_text = description[:27] + "..." if len(description) > 30 else description

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
