"""Keyboards for automatic polls."""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List


def get_poll_response_keyboard() -> InlineKeyboardMarkup:
    """Get keyboard for poll response.

    Returns:
        Keyboard with Skip, Sleep, and Remind Later buttons
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Занимался чем-то", callback_data="poll_activity")],
        [InlineKeyboardButton(text="⏭ Пропустить (ничего не делал)", callback_data="poll_skip")],
        [InlineKeyboardButton(text="😴 Спал", callback_data="poll_sleep")],
        [InlineKeyboardButton(text="⏸ Напомнить позже", callback_data="poll_remind")],
    ])
    return keyboard


def get_poll_initial_category_keyboard(categories: List[dict]) -> InlineKeyboardMarkup:
    """Get keyboard for initial category selection in automatic poll.

    This keyboard is used when automatic poll is sent and shows only
    category buttons without additional actions (Remind Later, Cancel).

    Args:
        categories: List of category dicts with 'id' and 'name'

    Returns:
        Keyboard with category buttons only
    """
    buttons = []

    # Add category buttons (2 per row for better UX)
    for i in range(0, len(categories), 2):
        row = []
        for j in range(i, min(i + 2, len(categories))):
            category = categories[j]
            emoji = category.get("emoji", "")
            name = category["name"]
            button_text = f"{emoji} {name}" if emoji else name
            row.append(InlineKeyboardButton(
                text=button_text,
                callback_data=f"poll_category_{category['id']}"
            ))
        buttons.append(row)

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_poll_category_keyboard(categories: List[dict], cancel_callback: str = "poll_cancel") -> InlineKeyboardMarkup:
    """Get keyboard for category selection in poll.

    Args:
        categories: List of category dicts with 'id' and 'name'
        cancel_callback: Callback data for cancel button (default: "poll_cancel")

    Returns:
        Keyboard with category buttons, remind later, and cancel option
    """
    buttons = []

    # Add category buttons (2 per row for better UX)
    for i in range(0, len(categories), 2):
        row = []
        for j in range(i, min(i + 2, len(categories))):
            category = categories[j]
            emoji = category.get("emoji", "")
            name = category["name"]
            button_text = f"{emoji} {name}" if emoji else name
            row.append(InlineKeyboardButton(
                text=button_text,
                callback_data=f"poll_category_{category['id']}"
            ))
        buttons.append(row)

    # Add "Remind Later" button
    buttons.append([InlineKeyboardButton(text="⏸ Напомнить позже", callback_data="poll_category_remind_later")])

    # Add cancel button with custom callback_data
    buttons.append([InlineKeyboardButton(text="❌ Отменить", callback_data=cancel_callback)])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_poll_reminder_keyboard() -> InlineKeyboardMarkup:
    """Get keyboard for reminder confirmation.

    Returns:
        Keyboard with OK button
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👌 Понятно", callback_data="poll_reminder_ok")],
    ])
    return keyboard
