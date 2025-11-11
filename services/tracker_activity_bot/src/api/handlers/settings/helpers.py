"""Common helper functions for settings handlers (DRY principle)."""

import logging

from aiogram.types import InlineKeyboardMarkup

from src.api.keyboards.main_menu import get_main_menu_keyboard
from src.application.utils.user_helpers import get_user_and_settings  # noqa: F401

logger = logging.getLogger(__name__)


def get_error_reply_markup() -> InlineKeyboardMarkup:
    """
    Get reply markup for error messages.

    Returns:
        Main menu keyboard for error cases
    """
    return get_main_menu_keyboard()
