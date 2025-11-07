"""Error handling middleware for HTTP client (OCP-compliant)."""

import logging
import httpx


logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware:
    """
    Middleware to handle HTTP errors with structured logging.

    Logs detailed error information for debugging and monitoring,
    including error type, status codes, and request context.

    Does not suppress errors - allows them to propagate after logging.

    Example:
        >>> middleware = ErrorHandlingMiddleware()
        >>> try:
        >>>     response = await client.get("/api/resource")
        >>> except httpx.HTTPStatusError as e:
        >>>     # Middleware logs error details before re-raising
        >>>     pass
    """

    def should_handle(self, error: Exception) -> bool:
        """
        Check if error should be handled by this middleware.

        Handles all HTTP-related errors (status errors, timeouts, connection errors).

        Args:
            error: Exception that occurred

        Returns:
            True for HTTP-related errors, False otherwise
        """
        return isinstance(error, (
            httpx.HTTPStatusError,
            httpx.TimeoutException,
            httpx.ConnectError,
            httpx.RequestError
        ))

    async def handle_error(
        self,
        error: Exception,
        request: httpx.Request
    ) -> httpx.Response | None:
        """
        Log error details and re-raise.

        Args:
            error: Exception to handle
            request: Original request that failed

        Returns:
            None (error will be re-raised)

        Raises:
            Original exception after logging
        """
        error_details = {
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "error": str(error),
            "error_type": type(error).__name__
        }

        # Add status code if available
        if isinstance(error, httpx.HTTPStatusError):
            error_details["status_code"] = error.response.status_code
            error_details["response_body"] = error.response.text[:500]  # First 500 chars

        logger.error(
            "HTTP request failed",
            extra=error_details,
            exc_info=False  # Don't log full traceback for expected HTTP errors
        )

        # Return None to re-raise the error
        return None
