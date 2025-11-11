"""HTTP client middleware for correlation ID propagation.

Automatically adds X-Correlation-ID header to all outgoing HTTP requests
using the correlation ID from the current context.
"""

import logging
from typing import Optional

import httpx

from src.infrastructure.context import get_correlation_id
from src.infrastructure.http_clients.middleware.base import RequestMiddleware

logger = logging.getLogger(__name__)


class CorrelationIDMiddleware(RequestMiddleware):
    """Middleware to add correlation ID header to HTTP requests.

    Retrieves correlation ID from current context and adds it as
    X-Correlation-ID header for distributed tracing.
    """

    async def process_request(self, request: httpx.Request) -> httpx.Request:
        """Add correlation ID header to outgoing request.

        Args:
            request: HTTP request to process

        Returns:
            Request with X-Correlation-ID header added
        """
        correlation_id = get_correlation_id()

        # Add header
        request.headers["X-Correlation-ID"] = correlation_id

        logger.debug(
            "Added correlation ID to outgoing HTTP request",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "url": str(request.url),
                "path": request.url.path
            }
        )

        return request
