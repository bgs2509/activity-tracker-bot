"""
Request/response logging middleware.

This middleware logs all HTTP requests and responses with timing information.
"""

import logging
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all HTTP requests and responses.

    Logs request method, path, status code, duration, and correlation ID.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """
        Process request with logging.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            HTTP response
        """
        start_time = time.time()

        # Get correlation ID from request state (set by CorrelationIDMiddleware)
        correlation_id = getattr(request.state, "correlation_id", "unknown")

        # Log incoming request
        logger.info(
            "HTTP request started",
            extra={
                "method": request.method,
                "path": request.url.path,
                "correlation_id": correlation_id,
                "client_host": request.client.host if request.client else "unknown",
                "query_params": str(request.query_params) if request.query_params else None
            }
        )

        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            # Log exceptions
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                "HTTP request failed with exception",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "correlation_id": correlation_id,
                    "duration_ms": round(duration_ms, 2),
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            )
            raise

        # Calculate request duration
        duration_ms = (time.time() - start_time) * 1000

        # Log response
        logger.info(
            "HTTP request completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
                "correlation_id": correlation_id
            }
        )

        return response
