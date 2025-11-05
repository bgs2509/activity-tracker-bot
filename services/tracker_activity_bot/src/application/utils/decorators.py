"""Useful decorators for handlers."""
from functools import wraps
from typing import Callable

from aiogram import types
from aiogram.enums import ChatAction


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
    @wraps(func)
    async def wrapper(event: types.CallbackQuery | types.Message, *args, **kwargs):
        # Determine chat_id and bot based on event type
        if isinstance(event, types.CallbackQuery):
            chat_id = event.message.chat.id
            bot = event.bot
        else:  # Message
            chat_id = event.chat.id
            bot = event.bot

        # Show typing action
        await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

        # Execute original handler
        return await func(event, *args, **kwargs)

    return wrapper
