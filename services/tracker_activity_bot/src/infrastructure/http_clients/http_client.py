"""Base HTTP client with middleware support (OCP-compliant)."""

import logging
from typing import Any, List
import httpx

from src.core.config import settings
from .middleware import (
    LoggingMiddleware,
    TimingMiddleware,
    ErrorHandlingMiddleware,
    RequestMiddleware,
    ResponseMiddleware,
    ErrorMiddleware
)


logger = logging.getLogger(__name__)


class DataAPIClient:
    """
    Base HTTP client for communication with data_postgres_api.

    Implements Open/Closed Principle through middleware pipeline.
    New functionality can be added via middleware without modifying this class.

    Example:
        >>> client = DataAPIClient()
        >>> data = await client.get("/users/1")

        >>> # Add custom middleware
        >>> client = DataAPIClient(middlewares=[CustomMiddleware()])

    Attributes:
        base_url: Base URL for API requests
        client: httpx AsyncClient instance
        request_middlewares: List of request processing middleware
        response_middlewares: List of response processing middleware
        error_middlewares: List of error handling middleware
    """

    def __init__(
        self,
        middlewares: List[Any] | None = None,
        base_url: str | None = None,
        timeout: float = 10.0
    ):
        """
        Initialize HTTP client with optional middleware.

        Args:
            middlewares: List of middleware instances (default: logging, timing, error handling)
            base_url: Base URL for requests (default: from settings)
            timeout: Request timeout in seconds

        Example:
            >>> # Use default middleware
            >>> client = DataAPIClient()

            >>> # Custom middleware
            >>> client = DataAPIClient(middlewares=[
            >>>     LoggingMiddleware(),
            >>>     RetryMiddleware(max_retries=3)
            >>> ])
        """
        self.base_url = base_url or settings.data_api_url
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            follow_redirects=True
        )

        # Initialize middleware lists
        self.request_middlewares: List[RequestMiddleware] = []
        self.response_middlewares: List[ResponseMiddleware] = []
        self.error_middlewares: List[ErrorMiddleware] = []

        # Use provided middleware or defaults
        if middlewares is None:
            middlewares = [
                TimingMiddleware(),
                LoggingMiddleware(),
                ErrorHandlingMiddleware()
            ]

        # Categorize middleware by type
        for middleware in middlewares:
            if hasattr(middleware, 'process_request'):
                self.request_middlewares.append(middleware)
            if hasattr(middleware, 'process_response'):
                self.response_middlewares.append(middleware)
            if hasattr(middleware, 'should_handle') and hasattr(middleware, 'handle_error'):
                self.error_middlewares.append(middleware)

        logger.debug(
            "HTTP client initialized",
            extra={
                "base_url": self.base_url,
                "request_middlewares": len(self.request_middlewares),
                "response_middlewares": len(self.response_middlewares),
                "error_middlewares": len(self.error_middlewares)
            }
        )

    async def _process_request(self, request: httpx.Request) -> httpx.Request:
        """
        Process request through middleware pipeline.

        Args:
            request: Original HTTP request

        Returns:
            Processed HTTP request
        """
        for middleware in self.request_middlewares:
            request = await middleware.process_request(request)
        return request

    async def _process_response(self, response: httpx.Response) -> httpx.Response:
        """
        Process response through middleware pipeline.

        Args:
            response: Original HTTP response

        Returns:
            Processed HTTP response
        """
        for middleware in self.response_middlewares:
            response = await middleware.process_response(response)
        return response

    async def _handle_error(
        self,
        error: Exception,
        request: httpx.Request
    ) -> httpx.Response | None:
        """
        Handle error through middleware pipeline.

        Args:
            error: Exception that occurred
            request: Original request that failed

        Returns:
            Response if error was handled, None to re-raise
        """
        for middleware in self.error_middlewares:
            if middleware.should_handle(error):
                result = await middleware.handle_error(error, request)
                if result is not None:
                    return result
        return None

    async def _execute_request(
        self,
        method: str,
        path: str,
        **kwargs
    ) -> Any:
        """
        Execute HTTP request with middleware pipeline.

        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            path: Request path
            **kwargs: Additional request parameters

        Returns:
            Response JSON data or status code

        Raises:
            httpx.HTTPStatusError: For 4xx/5xx responses
            httpx.RequestError: For network/timeout errors
        """
        # Build request
        request = self.client.build_request(method, path, **kwargs)

        # Process through request middleware
        request = await self._process_request(request)

        try:
            # Send request
            response = await self.client.send(request)

            # Process through response middleware
            response = await self._process_response(response)

            # Raise for status
            response.raise_for_status()

            # Return JSON for most methods, status code for DELETE
            if method == "DELETE":
                return response.status_code
            return response.json()

        except Exception as e:
            # Try error middleware
            handled_response = await self._handle_error(e, request)
            if handled_response is not None:
                return handled_response.json() if method != "DELETE" else handled_response.status_code

            # Re-raise if not handled
            raise

    async def get(self, path: str, **kwargs) -> Any:
        """
        Make GET request.

        Args:
            path: Request path
            **kwargs: Query parameters, headers, etc.

        Returns:
            Response JSON data

        Example:
            >>> data = await client.get("/users", params={"limit": 10})
        """
        return await self._execute_request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs) -> Any:
        """
        Make POST request.

        Args:
            path: Request path
            **kwargs: JSON data, form data, headers, etc.

        Returns:
            Response JSON data

        Example:
            >>> user = await client.post("/users", json={"name": "John"})
        """
        return await self._execute_request("POST", path, **kwargs)

    async def patch(self, path: str, **kwargs) -> Any:
        """
        Make PATCH request.

        Args:
            path: Request path
            **kwargs: JSON data, form data, headers, etc.

        Returns:
            Response JSON data

        Example:
            >>> user = await client.patch("/users/1", json={"name": "Jane"})
        """
        return await self._execute_request("PATCH", path, **kwargs)

    async def delete(self, path: str, **kwargs) -> int:
        """
        Make DELETE request.

        Args:
            path: Request path
            **kwargs: Query parameters, headers, etc.

        Returns:
            HTTP status code

        Example:
            >>> status = await client.delete("/users/1")
            >>> assert status == 204
        """
        return await self._execute_request("DELETE", path, **kwargs)

    async def close(self) -> None:
        """
        Close HTTP client and cleanup resources.

        Should be called when client is no longer needed.

        Example:
            >>> client = DataAPIClient()
            >>> try:
            >>>     await client.get("/users")
            >>> finally:
            >>>     await client.close()
        """
        await self.client.aclose()
        logger.debug("HTTP client closed")
