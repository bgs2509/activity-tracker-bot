"""User-related helper utilities for fetching user data and settings.

This module provides shared utilities for user and settings retrieval,
eliminating code duplication across multiple handler modules.
"""

import logging
from typing import Optional, Tuple

from src.api.dependencies import ServiceContainer

logger = logging.getLogger(__name__)


async def get_user_and_settings(
    telegram_id: int,
    services: ServiceContainer
) -> Tuple[Optional[dict], Optional[dict]]:
    """
    Get user and settings by telegram ID.

    This helper function eliminates code duplication across
    handlers by centralizing user/settings retrieval logic.

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
