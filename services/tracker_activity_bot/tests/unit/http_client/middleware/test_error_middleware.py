"""
Unit tests for ErrorHandlingMiddleware.

Tests error handling middleware that logs HTTP errors with structured data.
Verifies error type detection, logging behavior, and re-raising mechanism.

Test Coverage:
    - should_handle(): Error type detection (HTTP status, timeout, connection, request)
    - handle_error(): Error logging with details, status code extraction
    - Edge cases: Non-HTTP errors, missing response data

Coverage Target: 100% of error_middleware.py
Execution Time: < 0.2 seconds

Author: Testing Team
Date: 2025-11-07
"""

import pytest
from unittest.mock import MagicMock, patch
import httpx

from src.infrastructure.http_clients.middleware.error_middleware import (
    ErrorHandlingMiddleware
)


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def error_middleware():
    """
    Fixture: ErrorHandlingMiddleware instance.

    Returns:
        ErrorHandlingMiddleware: Middleware instance for testing
    """
    return ErrorHandlingMiddleware()


@pytest.fixture
def mock_request():
    """
    Fixture: Mock httpx.Request.

    Returns:
        MagicMock: Mocked HTTP request with typical attributes
    """
    request = MagicMock(spec=httpx.Request)
    request.method = "GET"
    request.url = MagicMock()
    request.url.path = "/api/users"
    request.url.__str__ = lambda self: "http://api.test.com/api/users"
    return request


@pytest.fixture
def mock_response():
    """
    Fixture: Mock httpx.Response.

    Returns:
        MagicMock: Mocked HTTP response with error status
    """
    response = MagicMock(spec=httpx.Response)
    response.status_code = 404
    response.text = "Not found"
    return response


# ============================================================================
# TEST SUITES
# ============================================================================

class TestErrorHandlingMiddlewareShouldHandle:
    """
    Test suite for should_handle() method.

    Verifies correct identification of HTTP-related errors that should be
    logged vs. other exceptions that should be ignored.
    """

    @pytest.mark.unit
    def test_should_handle_returns_true_for_http_status_error(
        self,
        error_middleware: ErrorHandlingMiddleware,
        mock_request,
        mock_response
    ):
        """
        Test handling of HTTP status errors (4xx, 5xx).

        GIVEN: HTTPStatusError exception
        WHEN: should_handle() is called
        THEN: Returns True (middleware will log this error)
        """
        # Arrange
        error = httpx.HTTPStatusError(
            "404 Not Found",
            request=mock_request,
            response=mock_response
        )

        # Act
        result = error_middleware.should_handle(error)

        # Assert
        assert result is True, \
            "Should handle HTTPStatusError (4xx/5xx responses)"

    @pytest.mark.unit
    def test_should_handle_returns_true_for_timeout_exception(
        self,
        error_middleware: ErrorHandlingMiddleware
    ):
        """
        Test handling of timeout errors.

        GIVEN: TimeoutException
        WHEN: should_handle() is called
        THEN: Returns True (timeout errors need logging)
        """
        # Arrange
        error = httpx.TimeoutException("Request timeout")

        # Act
        result = error_middleware.should_handle(error)

        # Assert
        assert result is True, \
            "Should handle TimeoutException"

    @pytest.mark.unit
    def test_should_handle_returns_true_for_connect_error(
        self,
        error_middleware: ErrorHandlingMiddleware
    ):
        """
        Test handling of connection errors.

        GIVEN: ConnectError (network unreachable, DNS failure, etc.)
        WHEN: should_handle() is called
        THEN: Returns True (connection errors need logging)
        """
        # Arrange
        error = httpx.ConnectError("Connection refused")

        # Act
        result = error_middleware.should_handle(error)

        # Assert
        assert result is True, \
            "Should handle ConnectError"

    @pytest.mark.unit
    def test_should_handle_returns_true_for_request_error(
        self,
        error_middleware: ErrorHandlingMiddleware
    ):
        """
        Test handling of generic request errors.

        GIVEN: RequestError (base class for HTTP errors)
        WHEN: should_handle() is called
        THEN: Returns True (all HTTP request errors should be logged)
        """
        # Arrange
        error = httpx.RequestError("Request failed")

        # Act
        result = error_middleware.should_handle(error)

        # Assert
        assert result is True, \
            "Should handle RequestError (base HTTP error class)"

    @pytest.mark.unit
    def test_should_handle_returns_false_for_non_http_errors(
        self,
        error_middleware: ErrorHandlingMiddleware
    ):
        """
        Test rejection of non-HTTP errors.

        GIVEN: Non-HTTP exception (ValueError, KeyError, etc.)
        WHEN: should_handle() is called
        THEN: Returns False (let other error handlers deal with it)
        """
        # Arrange
        errors = [
            ValueError("Invalid value"),
            KeyError("Missing key"),
            RuntimeError("Runtime error"),
            Exception("Generic exception")
        ]

        # Act & Assert
        for error in errors:
            result = error_middleware.should_handle(error)
            assert result is False, \
                f"Should not handle {type(error).__name__} (not HTTP-related)"


class TestErrorHandlingMiddlewareHandleError:
    """
    Test suite for handle_error() method.

    Verifies error logging with structured data and None return
    (to signal error should be re-raised).
    """

    @pytest.mark.unit
    @patch('src.infrastructure.http_clients.middleware.error_middleware.logger')
    async def test_handle_error_logs_http_status_error_with_status_code(
        self,
        mock_logger,
        error_middleware: ErrorHandlingMiddleware,
        mock_request,
        mock_response
    ):
        """
        Test logging of HTTPStatusError with response details.

        GIVEN: HTTPStatusError with status code and response body
        WHEN: handle_error() is called
        THEN: Error is logged with method, URL, status code, response body
              AND None is returned (error will be re-raised)
        """
        # Arrange
        error = httpx.HTTPStatusError(
            "404 Not Found",
            request=mock_request,
            response=mock_response
        )

        # Act
        result = await error_middleware.handle_error(error, mock_request)

        # Assert: Error logged with details
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args

        assert call_args[0][0] == "HTTP request failed", \
            "Should log standard error message"

        # Check logged details
        extra = call_args[1]["extra"]
        assert extra["method"] == "GET", "Should log HTTP method"
        assert extra["url"] == "http://api.test.com/api/users", \
            "Should log full URL"
        assert extra["path"] == "/api/users", "Should log path"
        assert extra["error_type"] == "HTTPStatusError", \
            "Should log error type"
        assert extra["status_code"] == 404, \
            "Should log status code for HTTPStatusError"
        assert extra["response_body"] == "Not found", \
            "Should log response body"

        # Check no traceback logged (exc_info=False)
        assert call_args[1]["exc_info"] is False, \
            "Should not log full traceback for expected HTTP errors"

        # Should return None to re-raise
        assert result is None, \
            "Should return None to signal error re-raising"

    @pytest.mark.unit
    @patch('src.infrastructure.http_clients.middleware.error_middleware.logger')
    async def test_handle_error_logs_timeout_exception_without_status_code(
        self,
        mock_logger,
        error_middleware: ErrorHandlingMiddleware,
        mock_request
    ):
        """
        Test logging of TimeoutException (no response data).

        GIVEN: TimeoutException (no response available)
        WHEN: handle_error() is called
        THEN: Error is logged with request details but no status code
              (Timeout occurs before response is received)
        """
        # Arrange
        error = httpx.TimeoutException("Request timeout")

        # Act
        result = await error_middleware.handle_error(error, mock_request)

        # Assert: Error logged without status code
        mock_logger.error.assert_called_once()
        extra = mock_logger.error.call_args[1]["extra"]

        assert extra["method"] == "GET"
        assert extra["error_type"] == "TimeoutException"
        assert "status_code" not in extra, \
            "Timeout error has no status code (no response received)"
        assert "response_body" not in extra, \
            "Timeout error has no response body"

        assert result is None

    @pytest.mark.unit
    @patch('src.infrastructure.http_clients.middleware.error_middleware.logger')
    async def test_handle_error_logs_connect_error_without_response_data(
        self,
        mock_logger,
        error_middleware: ErrorHandlingMiddleware,
        mock_request
    ):
        """
        Test logging of ConnectError (no response).

        GIVEN: ConnectError (connection failed)
        WHEN: handle_error() is called
        THEN: Error is logged with request details only
        """
        # Arrange
        error = httpx.ConnectError("Connection refused")

        # Act
        result = await error_middleware.handle_error(error, mock_request)

        # Assert
        mock_logger.error.assert_called_once()
        extra = mock_logger.error.call_args[1]["extra"]

        assert extra["error_type"] == "ConnectError"
        assert "status_code" not in extra
        assert result is None

    @pytest.mark.unit
    @patch('src.infrastructure.http_clients.middleware.error_middleware.logger')
    async def test_handle_error_truncates_long_response_body(
        self,
        mock_logger,
        error_middleware: ErrorHandlingMiddleware,
        mock_request,
        mock_response
    ):
        """
        Test response body truncation for large responses.

        GIVEN: HTTPStatusError with response body > 500 characters
        WHEN: handle_error() is called
        THEN: Response body is truncated to first 500 characters
              (Prevent excessive log size)
        """
        # Arrange: Response with 1000 characters
        long_body = "x" * 1000
        mock_response.text = long_body

        error = httpx.HTTPStatusError(
            "400 Bad Request",
            request=mock_request,
            response=mock_response
        )

        # Act
        await error_middleware.handle_error(error, mock_request)

        # Assert: Body truncated to 500 chars
        extra = mock_logger.error.call_args[1]["extra"]
        assert len(extra["response_body"]) == 500, \
            "Should truncate response body to 500 characters"
        assert extra["response_body"] == "x" * 500

    @pytest.mark.unit
    @patch('src.infrastructure.http_clients.middleware.error_middleware.logger')
    async def test_handle_error_includes_error_message_string(
        self,
        mock_logger,
        error_middleware: ErrorHandlingMiddleware,
        mock_request
    ):
        """
        Test error message is logged as string.

        GIVEN: Any HTTP error with message
        WHEN: handle_error() is called
        THEN: Error message is included in logged details
        """
        # Arrange
        error_message = "Connection timeout after 30 seconds"
        error = httpx.TimeoutException(error_message)

        # Act
        await error_middleware.handle_error(error, mock_request)

        # Assert
        extra = mock_logger.error.call_args[1]["extra"]
        assert extra["error"] == error_message, \
            "Should log error message as string"


class TestErrorHandlingMiddlewareEdgeCases:
    """
    Test suite for edge cases in error handling.
    """

    @pytest.mark.unit
    @patch('src.infrastructure.http_clients.middleware.error_middleware.logger')
    async def test_handle_error_with_empty_response_body(
        self,
        mock_logger,
        error_middleware: ErrorHandlingMiddleware,
        mock_request,
        mock_response
    ):
        """
        Test handling of HTTPStatusError with empty response body.

        GIVEN: HTTPStatusError with empty response.text
        WHEN: handle_error() is called
        THEN: Empty string is logged (no error raised)
        """
        # Arrange
        mock_response.text = ""
        error = httpx.HTTPStatusError(
            "204 No Content",
            request=mock_request,
            response=mock_response
        )

        # Act
        result = await error_middleware.handle_error(error, mock_request)

        # Assert: Empty body logged gracefully
        extra = mock_logger.error.call_args[1]["extra"]
        assert extra["response_body"] == "", \
            "Should handle empty response body"
        assert result is None

    @pytest.mark.unit
    @patch('src.infrastructure.http_clients.middleware.error_middleware.logger')
    async def test_handle_error_always_returns_none(
        self,
        mock_logger,
        error_middleware: ErrorHandlingMiddleware,
        mock_request
    ):
        """
        Test that handle_error() always returns None (re-raise).

        GIVEN: Any handled error type
        WHEN: handle_error() is called
        THEN: None is returned (error is logged but not suppressed)
        """
        # Arrange: Test multiple error types
        errors = [
            httpx.TimeoutException("Timeout"),
            httpx.ConnectError("Connection failed"),
            httpx.RequestError("Request error")
        ]

        # Act & Assert: All return None
        for error in errors:
            result = await error_middleware.handle_error(error, mock_request)
            assert result is None, \
                f"{type(error).__name__} should return None for re-raising"

    @pytest.mark.unit
    def test_middleware_initialization_has_no_state(
        self,
        error_middleware: ErrorHandlingMiddleware
    ):
        """
        Test middleware is stateless (no instance variables).

        GIVEN: ErrorHandlingMiddleware instantiation
        WHEN: Middleware is created
        THEN: No mutable state is stored
              (Thread-safe for concurrent requests)
        """
        # Assert: No mutable state
        assert not hasattr(error_middleware, '_state'), \
            "Error middleware should be stateless"
        assert not hasattr(error_middleware, '_errors'), \
            "Should not store error history"
