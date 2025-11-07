"""HTTP client middleware protocols for Open/Closed Principle compliance."""

from typing import Protocol, runtime_checkable
import httpx


@runtime_checkable
class RequestMiddleware(Protocol):
    """
    Protocol for request middleware.

    Request middleware can modify outgoing HTTP requests before they are sent.
    Examples: adding headers, logging, authentication, request transformation.
    """

    async def process_request(self, request: httpx.Request) -> httpx.Request:
        """
        Process outgoing HTTP request.

        Middleware can modify request before sending:
        - Add/modify headers
        - Log request details
        - Transform request data
        - Add authentication tokens

        Args:
            request: Outgoing HTTP request

        Returns:
            Modified HTTP request (or original if no changes needed)

        Example:
            >>> class AuthMiddleware:
            >>>     async def process_request(self, request):
            >>>         request.headers["Authorization"] = f"Bearer {token}"
            >>>         return request
        """
        ...


@runtime_checkable
class ResponseMiddleware(Protocol):
    """
    Protocol for response middleware.

    Response middleware can process incoming HTTP responses after they are received.
    Examples: logging, caching, response transformation, metrics collection.
    """

    async def process_response(self, response: httpx.Response) -> httpx.Response:
        """
        Process incoming HTTP response.

        Middleware can:
        - Log response details
        - Transform response data
        - Cache responses
        - Collect metrics

        Args:
            response: Incoming HTTP response

        Returns:
            Modified HTTP response (or original if no changes needed)

        Example:
            >>> class LoggingMiddleware:
            >>>     async def process_response(self, response):
            >>>         logger.info(f"Response: {response.status_code}")
            >>>         return response
        """
        ...


@runtime_checkable
class ErrorMiddleware(Protocol):
    """
    Protocol for error handling middleware.

    Error middleware can handle exceptions that occur during HTTP requests.
    Examples: retry logic, error transformation, fallback responses.
    """

    def should_handle(self, error: Exception) -> bool:
        """
        Check if this middleware should handle the error.

        Args:
            error: Exception that occurred during request

        Returns:
            True if this middleware can handle the error

        Example:
            >>> class RetryMiddleware:
            >>>     def should_handle(self, error):
            >>>         return isinstance(error, httpx.TimeoutException)
        """
        ...

    async def handle_error(
        self,
        error: Exception,
        request: httpx.Request
    ) -> httpx.Response | None:
        """
        Handle or transform the error.

        Args:
            error: Exception to handle
            request: Original request that caused the error

        Returns:
            Response if error was handled, None to re-raise

        Raises:
            Original or transformed exception if not handled

        Example:
            >>> class RetryMiddleware:
            >>>     async def handle_error(self, error, request):
            >>>         if self.retries < self.max_retries:
            >>>             await asyncio.sleep(self.backoff)
            >>>             return await self.retry_request(request)
            >>>         return None  # Re-raise
        """
        ...
