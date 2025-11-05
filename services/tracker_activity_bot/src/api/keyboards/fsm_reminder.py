"""Keyboard for FSM timeout reminders."""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_fsm_reminder_keyboard() -> InlineKeyboardMarkup:
    """Get keyboard for FSM timeout reminder.

    Returns:
        Inline keyboard with Continue button
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="✅ Продолжить",
            callback_data="fsm_reminder_continue"
        )]
    ])
