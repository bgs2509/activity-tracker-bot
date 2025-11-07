"""
Decorators for bot handlers.

This module provides reusable decorators for common handler patterns,
reducing code duplication and improving maintainability.
"""

import logging
from functools import wraps
from typing import Callable, Any

from aiogram import types

from src.api.dependencies import ServiceContainer
from src.api.keyboards.main_menu import get_main_menu_keyboard

logger = logging.getLogger(__name__)


def require_user(handler: Callable) -> Callable:
    """
    Decorator to automatically retrieve and validate user before handler execution.

    This decorator eliminates the repeated pattern of:
    - Getting user by telegram_id
    - Checking if user exists
    - Returning error if user not found

    The decorator injects 'user' parameter into the handler kwargs.

    Supports both CallbackQuery and Message event types.

    Example:
        @router.callback_query(F.data == "action")
        @require_user
        async def handler(callback: types.CallbackQuery, services: ServiceContainer, user: dict):
            # user is already retrieved and validated
            categories = await services.category.get_user_categories(user["id"])

    Args:
        handler: Async handler function to wrap

    Returns:
        Wrapped handler function with automatic user retrieval
    """
    @wraps(handler)
    async def wrapper(*args, **kwargs) -> Any:
        # Extract event (CallbackQuery or Message) and services from kwargs
        event = None
        services = kwargs.get('services')

        # Find event in args (first argument after self if any)
        for arg in args:
            if isinstance(arg, (types.CallbackQuery, types.Message)):
                event = arg
                break

        if not event:
            logger.error("require_user: Could not find event in handler arguments")
            return

        if not services:
            logger.error("require_user: ServiceContainer not found in kwargs")
            return

        # Get telegram_id from event
        telegram_id = event.from_user.id

        # Retrieve user
        user = await services.user.get_by_telegram_id(telegram_id)

        if not user:
            # User not found - send error message
            error_text = "⚠️ Пользователь не найден. Отправь /start для регистрации."

            if isinstance(event, types.CallbackQuery):
                await event.message.answer(error_text, reply_markup=get_main_menu_keyboard())
                await event.answer()
            elif isinstance(event, types.Message):
                await event.answer(error_text, reply_markup=get_main_menu_keyboard())

            logger.warning(
                "User not found for telegram_id",
                extra={"telegram_id": telegram_id}
            )
            return

        # Inject user into handler kwargs
        kwargs['user'] = user

        # Call original handler
        return await handler(*args, **kwargs)

    return wrapper
