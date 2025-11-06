"""Logging middleware and utilities for comprehensive DEBUG logging."""
import logging
import time
from functools import wraps
from typing import Any, Callable, Optional

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update, Message, CallbackQuery
from aiogram.fsm.context import FSMContext

logger = logging.getLogger(__name__)


class FSMLoggingMiddleware(BaseMiddleware):
    """Middleware to automatically log all FSM state transitions."""

    async def __call__(
        self,
        handler: Callable,
        event: TelegramObject,
        data: dict[str, Any]
    ) -> Any:
        """Log FSM state changes around handler execution.

        Args:
            handler: The handler function
            event: The telegram event
            data: Handler data including state

        Returns:
            Handler result
        """
        state: Optional[FSMContext] = data.get("state")
        user_id = None

        # Extract user_id from event
        if hasattr(event, "from_user") and event.from_user:
            user_id = event.from_user.id
        elif isinstance(event, Update):
            if event.message:
                user_id = event.message.from_user.id
            elif event.callback_query:
                user_id = event.callback_query.from_user.id

        # Get state before handler execution
        old_state = None
        old_data = {}
        if state:
            try:
                old_state = await state.get_state()
                old_data = await state.get_data()
            except Exception as e:
                logger.debug(f"Could not get FSM state before handler: {e}")

        # Execute handler
        start_time = time.time()
        try:
            result = await handler(event, data)
            duration_ms = (time.time() - start_time) * 1000

            logger.debug(
                f"Handler executed successfully",
                extra={
                    "user_id": user_id,
                    "handler": handler.__name__,
                    "duration_ms": round(duration_ms, 2),
                    "event_type": type(event).__name__
                }
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.debug(
                f"Handler execution failed",
                extra={
                    "user_id": user_id,
                    "handler": handler.__name__,
                    "duration_ms": round(duration_ms, 2),
                    "error": str(e),
                    "event_type": type(event).__name__
                }
            )
            raise

        # Get state after handler execution
        if state:
            try:
                new_state = await state.get_state()
                new_data = await state.get_data()

                # Log state transition if changed
                if str(old_state) != str(new_state):
                    logger.debug(
                        f"FSM state transition",
                        extra={
                            "user_id": user_id,
                            "from_state": str(old_state),
                            "to_state": str(new_state),
                            "handler": handler.__name__
                        }
                    )

                # Log data changes if any
                if old_data != new_data:
                    added_keys = set(new_data.keys()) - set(old_data.keys())
                    removed_keys = set(old_data.keys()) - set(new_data.keys())
                    changed_keys = {k for k in old_data.keys() & new_data.keys()
                                   if old_data[k] != new_data[k]}

                    if added_keys or removed_keys or changed_keys:
                        logger.debug(
                            f"FSM data changed",
                            extra={
                                "user_id": user_id,
                                "state": str(new_state),
                                "added_keys": list(added_keys),
                                "removed_keys": list(removed_keys),
                                "changed_keys": list(changed_keys)
                            }
                        )

                # Log state clearing
                if old_state is not None and new_state is None:
                    logger.debug(
                        f"FSM state cleared",
                        extra={
                            "user_id": user_id,
                            "previous_state": str(old_state),
                            "handler": handler.__name__
                        }
                    )
            except Exception as e:
                logger.debug(f"Could not get FSM state after handler: {e}")

        return result


class UserActionLoggingMiddleware(BaseMiddleware):
    """Middleware to log all user actions (messages, callbacks)."""

    async def __call__(
        self,
        handler: Callable,
        event: TelegramObject,
        data: dict[str, Any]
    ) -> Any:
        """Log user actions before handler execution.

        Args:
            handler: The handler function
            event: The telegram event
            data: Handler data

        Returns:
            Handler result
        """
        if isinstance(event, Message):
            logger.debug(
                f"User sent message",
                extra={
                    "user_id": event.from_user.id,
                    "username": event.from_user.username,
                    "chat_id": event.chat.id,
                    "message_id": event.message_id,
                    "text_preview": event.text[:100] if event.text else None,
                    "content_type": event.content_type,
                    "has_entities": bool(event.entities)
                }
            )
        elif isinstance(event, CallbackQuery):
            logger.debug(
                f"User pressed button",
                extra={
                    "user_id": event.from_user.id,
                    "username": event.from_user.username,
                    "callback_data": event.data,
                    "message_id": event.message.message_id if event.message else None,
                    "inline_message_id": event.inline_message_id
                }
            )

        return await handler(event, data)


def log_user_action(action_name: str):
    """Decorator to log specific user actions.

    Args:
        action_name: Name of the action being performed

    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user_id from first argument (callback or message)
            user_id = None
            event_info = {}

            if args:
                event = args[0]
                if hasattr(event, "from_user"):
                    user_id = event.from_user.id
                    event_info["username"] = event.from_user.username

                if isinstance(event, CallbackQuery):
                    event_info["callback_data"] = event.data
                    event_info["event_type"] = "callback"
                elif isinstance(event, Message):
                    event_info["text_preview"] = event.text[:50] if event.text else None
                    event_info["event_type"] = "message"

            logger.debug(
                f"User action: {action_name}",
                extra={
                    "user_id": user_id,
                    "action": action_name,
                    "handler": func.__name__,
                    **event_info
                }
            )

            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000

                logger.debug(
                    f"Action completed: {action_name}",
                    extra={
                        "user_id": user_id,
                        "action": action_name,
                        "handler": func.__name__,
                        "duration_ms": round(duration_ms, 2),
                        "success": True
                    }
                )
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.debug(
                    f"Action failed: {action_name}",
                    extra={
                        "user_id": user_id,
                        "action": action_name,
                        "handler": func.__name__,
                        "duration_ms": round(duration_ms, 2),
                        "success": False,
                        "error": str(e)
                    }
                )
                raise

        return wrapper
    return decorator


async def log_bot_message(
    send_func: Callable,
    user_id: int,
    text: str,
    **kwargs
):
    """Wrapper to log bot messages being sent.

    Args:
        send_func: The send function (bot.send_message, message.answer, etc)
        user_id: Telegram user ID
        text: Message text
        **kwargs: Additional arguments for send function

    Returns:
        Result of send function
    """
    has_keyboard = "reply_markup" in kwargs
    keyboard_type = None
    button_count = 0

    if has_keyboard:
        markup = kwargs["reply_markup"]
        if hasattr(markup, "inline_keyboard"):
            keyboard_type = "inline"
            button_count = sum(len(row) for row in markup.inline_keyboard)
        elif hasattr(markup, "keyboard"):
            keyboard_type = "reply"
            button_count = sum(len(row) for row in markup.keyboard)

    logger.debug(
        f"Sending message to user",
        extra={
            "user_id": user_id,
            "text_preview": text[:100],
            "text_length": len(text),
            "has_keyboard": has_keyboard,
            "keyboard_type": keyboard_type,
            "button_count": button_count,
            "parse_mode": kwargs.get("parse_mode")
        }
    )

    start_time = time.time()
    try:
        result = await send_func(text, **kwargs)
        duration_ms = (time.time() - start_time) * 1000

        logger.debug(
            f"Message sent successfully",
            extra={
                "user_id": user_id,
                "message_id": result.message_id if hasattr(result, "message_id") else None,
                "duration_ms": round(duration_ms, 2)
            }
        )
        return result
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.debug(
            f"Failed to send message",
            extra={
                "user_id": user_id,
                "duration_ms": round(duration_ms, 2),
                "error": str(e)
            }
        )
        raise
