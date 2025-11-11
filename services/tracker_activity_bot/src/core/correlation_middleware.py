"""Middleware for correlation ID management in bot handlers.

Automatically generates and propagates correlation IDs for all incoming
telegram events (messages, callbacks, etc.).
"""

import logging
from typing import Callable, Dict, Any, Awaitable
import uuid

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User

from src.infrastructure.context import set_correlation_id, clear_correlation_id

logger = logging.getLogger(__name__)


class CorrelationIDMiddleware(BaseMiddleware):
    """Middleware to generate and manage correlation IDs.

    Creates a unique correlation ID for each incoming telegram event
    and stores it in context for downstream propagation to API calls.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        """Process event with correlation ID.

        Args:
            handler: Next handler in chain
            event: Telegram event (Message, CallbackQuery, etc.)
            data: Handler data dictionary

        Returns:
            Handler result
        """
        # Generate new correlation ID for this request
        correlation_id = str(uuid.uuid4())
        set_correlation_id(correlation_id)

        # Extract user info for logging
        user: Optional[User] = data.get("event_from_user")
        user_id = user.id if user else None

        # Determine event type
        event_type = type(event).__name__

        logger.debug(
            "Correlation ID generated for incoming event",
            extra={
                "correlation_id": correlation_id,
                "event_type": event_type,
                "user_id": user_id
            }
        )

        try:
            # Execute handler with correlation ID in context
            result = await handler(event, data)
            return result
        finally:
            # Clean up context after handler completes
            clear_correlation_id()
