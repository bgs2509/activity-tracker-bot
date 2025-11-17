"""Telegram-specific utility functions for handling bot interactions."""

import logging
from typing import Optional

from aiogram import types
from aiogram.exceptions import TelegramBadRequest

logger = logging.getLogger(__name__)


async def safe_callback_answer(
    callback: types.CallbackQuery,
    text: Optional[str] = None,
    show_alert: bool = False
) -> bool:
    """Safely answer callback query, handling expired callbacks gracefully.

    Telegram callback queries expire after a certain time (typically a few minutes).
    When a callback expires, trying to answer it raises TelegramBadRequest.
    This function catches expired callbacks and logs them as warnings instead of errors.

    Args:
        callback: Callback query to answer
        text: Optional text to show in notification
        show_alert: Whether to show as an alert (modal) instead of a notification

    Returns:
        True if callback was answered successfully, False if it was expired

    Example:
        ```python
        # Simple answer
        await safe_callback_answer(callback)

        # With notification text
        await safe_callback_answer(callback, "✅ Saved!")

        # With alert
        await safe_callback_answer(callback, "⚠️ Error!", show_alert=True)
        ```
    """
    try:
        if text:
            await callback.answer(text, show_alert=show_alert)
        else:
            await callback.answer()
        return True
    except TelegramBadRequest as e:
        error_msg = str(e).lower()
        if "query is too old" in error_msg or "query id is invalid" in error_msg:
            logger.warning(
                "Callback query expired, cannot answer",
                extra={
                    "callback_data": callback.data,
                    "user_id": callback.from_user.id,
                    "error": str(e)
                }
            )
            return False
        # Re-raise if it's a different TelegramBadRequest
        raise
