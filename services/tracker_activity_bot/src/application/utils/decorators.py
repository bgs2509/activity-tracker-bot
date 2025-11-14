"""Useful decorators for handlers."""
import logging
from functools import wraps
from typing import Callable

from aiogram import types
from aiogram.enums import ChatAction

logger = logging.getLogger(__name__)


def with_typing_action(func: Callable) -> Callable:
    """Decorator to show typing action before handler execution.

    Automatically shows "typing..." indicator when user clicks inline button
    or sends a message. Improves UX by providing immediate feedback.

    Usage:
        @router.callback_query(F.data == "something")
        @with_typing_action
        async def handler(callback: CallbackQuery, ...):
            # Typing action is automatically shown
            ...
    """
    logger.debug(
        "with_typing_action decorator applied",
        extra={"function_name": func.__name__, "module": func.__module__}
    )

    @wraps(func)
    async def wrapper(event: types.CallbackQuery | types.Message, *args, **kwargs):
        try:
            # Determine chat_id and bot based on event type
            if isinstance(event, types.CallbackQuery):
                chat_id = event.message.chat.id
                bot = event.bot
                event_type = "callback_query"
            else:  # Message
                chat_id = event.chat.id
                bot = event.bot
                event_type = "message"

            logger.debug(
                "typing action wrapper started",
                extra={
                    "function_name": func.__name__,
                    "event_type": event_type,
                    "chat_id": chat_id
                }
            )

            # Show typing action
            await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

            logger.debug(
                "typing action sent",
                extra={
                    "function_name": func.__name__,
                    "chat_id": chat_id,
                    "action": ChatAction.TYPING
                }
            )

            # Execute original handler
            result = await func(event, *args, **kwargs)

            logger.debug(
                "decorated handler completed",
                extra={
                    "function_name": func.__name__,
                    "chat_id": chat_id
                }
            )

            return result
        except Exception as e:
            logger.error(
                "with_typing_action wrapper failed",
                extra={
                    "function_name": func.__name__,
                    "error": str(e)
                },
                exc_info=True
            )
            raise

    return wrapper
