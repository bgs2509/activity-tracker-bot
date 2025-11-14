"""
Correlation ID middleware for request tracing.

This middleware adds correlation IDs to all requests for distributed tracing.
Complies with .ai-framework/ standard using X-Request-ID header.
"""

import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

CORRELATION_ID_HEADER = "X-Request-ID"


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add correlation ID to all requests.

    Generates or extracts correlation ID from request headers and
    adds it to response headers for request tracing across services.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """
        Process request with correlation ID.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            HTTP response with correlation ID header
        """
        # Extract correlation ID from request or generate new one
        # Generate UUID if header is missing OR empty string
        correlation_id = request.headers.get(CORRELATION_ID_HEADER)
        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        # Add to request state for access in handlers
        request.state.correlation_id = correlation_id

        # Process request
        response = await call_next(request)

        # Add correlation ID to response headers
        response.headers[CORRELATION_ID_HEADER] = correlation_id

        return response
