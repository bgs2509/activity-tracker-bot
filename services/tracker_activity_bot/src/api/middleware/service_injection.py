"""
Service injection middleware for automatic dependency injection.

This middleware automatically injects ServiceContainer into all handlers,
eliminating the need for manual service instantiation.
"""

import logging
from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from src.api.dependencies import get_service_container, ServiceContainer

logger = logging.getLogger(__name__)


class ServiceInjectionMiddleware(BaseMiddleware):
    """
    Middleware that injects ServiceContainer into handler kwargs.

    This middleware automatically provides 'services' parameter to all handlers,
    eliminating repeated service instantiation code.

    Example:
        # Before (manual instantiation):
        user_service = UserService(api_client)
        user = await user_service.get_by_telegram_id(...)

        # After (automatic injection):
        async def handler(..., services: ServiceContainer):
            user = await services.user.get_by_telegram_id(...)
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """
        Inject ServiceContainer into handler data.

        Args:
            handler: Next handler in the chain
            event: Telegram event (Message, CallbackQuery, etc.)
            data: Handler kwargs dict

        Returns:
            Handler result
        """
        # Inject shared service container into handler kwargs
        data["services"] = get_service_container()

        return await handler(event, data)
