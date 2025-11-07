"""Timing middleware for HTTP client (OCP-compliant)."""

import logging
import time
import httpx


logger = logging.getLogger(__name__)


class TimingMiddleware:
    """
    Middleware to measure HTTP request/response timing.

    Tracks request duration and logs performance metrics
    for monitoring and optimization purposes.

    Stores timing data in request/response state for use by other middleware.

    Example:
        >>> middleware = TimingMiddleware()
        >>> # Request starts timer
        >>> request = await middleware.process_request(request)
        >>> # Response calculates duration
        >>> response = await middleware.process_response(response)
        # Logs: "HTTP timing: 245.67ms"
    """

    def __init__(self):
        """Initialize timing middleware with empty timing storage."""
        self._timings = {}  # {request_id: start_time}

    async def process_request(self, request: httpx.Request) -> httpx.Request:
        """
        Start timing for HTTP request.

        Stores start time keyed by request URL for later duration calculation.

        Args:
            request: HTTP request starting

        Returns:
            Unmodified request
        """
        request_id = id(request)
        self._timings[request_id] = time.time()
        return request

    async def process_response(self, response: httpx.Response) -> httpx.Response:
        """
        Calculate and log request duration.

        Args:
            response: HTTP response received

        Returns:
            Unmodified response
        """
        request_id = id(response.request)
        start_time = self._timings.pop(request_id, None)

        if start_time:
            duration_ms = (time.time() - start_time) * 1000

            logger.debug(
                "HTTP timing",
                extra={
                    "method": response.request.method,
                    "url": str(response.request.url),
                    "path": response.request.url.path,
                    "duration_ms": round(duration_ms, 2),
                    "status_code": response.status_code
                }
            )

        return response
