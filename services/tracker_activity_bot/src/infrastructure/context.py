"""Context storage for request-scoped data like correlation IDs.

This module provides thread-safe storage for correlation IDs that need
to be propagated across the application stack.
"""

import contextvars
from typing import Optional
import uuid

# Context variable for storing correlation ID
_correlation_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    'correlation_id',
    default=None
)


def get_correlation_id() -> str:
    """Get current correlation ID or generate new one.

    Returns:
        Current correlation ID or newly generated UUID
    """
    correlation_id = _correlation_id.get()
    if not correlation_id:
        correlation_id = str(uuid.uuid4())
        _correlation_id.set(correlation_id)
    return correlation_id


def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID for current context.

    Args:
        correlation_id: Correlation ID to set
    """
    _correlation_id.set(correlation_id)


def clear_correlation_id() -> None:
    """Clear correlation ID from current context."""
    _correlation_id.set(None)
