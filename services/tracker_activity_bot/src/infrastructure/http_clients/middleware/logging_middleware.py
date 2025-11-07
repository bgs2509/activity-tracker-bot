"""Logging middleware for HTTP client (OCP-compliant)."""

import logging
import httpx


logger = logging.getLogger(__name__)


class LoggingMiddleware:
    """
    Middleware to log HTTP requests and responses.

    Implements structured logging with request/response details
    for debugging and monitoring purposes.

    Example:
        >>> middleware = LoggingMiddleware()
        >>> request = httpx.Request("GET", "https://api.example.com/users")
        >>> logged_request = await middleware.process_request(request)
        # Logs: "HTTP request: GET https://api.example.com/users"
    """

    async def process_request(self, request: httpx.Request) -> httpx.Request:
        """
        Log outgoing HTTP request.

        Args:
            request: HTTP request to log

        Returns:
            Unmodified request
        """
        logger.debug(
            "HTTP request",
            extra={
                "method": request.method,
                "url": str(request.url),
                "path": request.url.path,
                "has_body": bool(request.content),
                "content_length": len(request.content) if request.content else 0
            }
        )
        return request

    async def process_response(self, response: httpx.Response) -> httpx.Response:
        """
        Log incoming HTTP response.

        Args:
            response: HTTP response to log

        Returns:
            Unmodified response
        """
        logger.debug(
            "HTTP response",
            extra={
                "method": response.request.method,
                "url": str(response.request.url),
                "path": response.request.url.path,
                "status_code": response.status_code,
                "content_length": len(response.content),
                "is_error": response.status_code >= 400
            }
        )
        return response
