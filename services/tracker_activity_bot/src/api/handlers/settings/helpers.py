"""Common helper functions for settings handlers (DRY principle)."""

import logging
from typing import Optional, Tuple

from aiogram.types import InlineKeyboardMarkup

from src.api.dependencies import ServiceContainer
from src.api.keyboards.main_menu import get_main_menu_keyboard

logger = logging.getLogger(__name__)


async def get_user_and_settings(
    telegram_id: int,
    services: ServiceContainer
) -> Tuple[Optional[dict], Optional[dict]]:
    """
    Get user and settings by telegram ID.

    This helper function eliminates code duplication across
    settings handlers by centralizing user/settings retrieval logic.

    Args:
        telegram_id: Telegram user ID
        services: Service container with data access

    Returns:
        Tuple of (user dict or None, settings dict or None)

    Example:
        >>> user, settings = await get_user_and_settings(123, services)
        >>> if not user or not settings:
        >>>     await send_error_message(callback)
        >>>     return
    """
    user = await services.user.get_by_telegram_id(telegram_id)
    if not user:
        logger.warning(
            "User not found",
            extra={"telegram_id": telegram_id}
        )
        return None, None

    settings = await services.settings.get_settings(user["id"])
    if not settings:
        logger.warning(
            "Settings not found",
            extra={
                "telegram_id": telegram_id,
                "user_id": user["id"]
            }
        )
        return user, None

    logger.debug(
        "Retrieved user and settings",
        extra={
            "telegram_id": telegram_id,
            "user_id": user["id"]
        }
    )

    return user, settings


def get_error_reply_markup() -> InlineKeyboardMarkup:
    """
    Get reply markup for error messages.

    Returns:
        Main menu keyboard for error cases
    """
    return get_main_menu_keyboard()
