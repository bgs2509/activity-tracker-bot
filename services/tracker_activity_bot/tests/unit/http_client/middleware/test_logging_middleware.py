"""
Unit tests for LoggingMiddleware.

Tests logging middleware that logs HTTP request/response details.
Verifies structured logging with request method, URL, body, status code.

Test Coverage:
    - process_request(): Request logging with method, URL, body presence
    - process_response(): Response logging with status code, content length
    - Edge cases: Empty body, large content, error responses

Coverage Target: 100% of logging_middleware.py
Execution Time: < 0.2 seconds

Author: Testing Team
Date: 2025-11-07
"""

import pytest
from unittest.mock import MagicMock, patch
import httpx

from src.infrastructure.http_clients.middleware.logging_middleware import (
    LoggingMiddleware
)


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def logging_middleware():
    """
    Fixture: LoggingMiddleware instance.

    Returns:
        LoggingMiddleware: Middleware instance for testing
    """
    return LoggingMiddleware()


@pytest.fixture
def mock_request():
    """
    Fixture: Mock httpx.Request with typical attributes.

    Returns:
        MagicMock: Mocked HTTP request
    """
    request = MagicMock(spec=httpx.Request)
    request.method = "GET"
    request.url = MagicMock()
    request.url.path = "/api/users"
    request.url.__str__ = lambda self: "http://api.test.com/api/users"
    request.content = b""
    return request


@pytest.fixture
def mock_response():
    """
    Fixture: Mock httpx.Response with request association.

    Returns:
        MagicMock: Mocked HTTP response
    """
    response = MagicMock(spec=httpx.Response)
    response.status_code = 200
    response.content = b'{"data": "test"}'

    # Associate request
    response.request = MagicMock(spec=httpx.Request)
    response.request.method = "GET"
    response.request.url = MagicMock()
    response.request.url.path = "/api/users"
    response.request.url.__str__ = lambda self: "http://api.test.com/api/users"

    return response


# ============================================================================
# TEST SUITES
# ============================================================================

class TestLoggingMiddlewareProcessRequest:
    """
    Test suite for process_request() method.

    Verifies request logging with structured data including
    method, URL, body presence, and content length.
    """

    @pytest.mark.unit
    @patch('src.infrastructure.http_clients.middleware.logging_middleware.logger')
    async def test_process_request_logs_get_request_without_body(
        self,
        mock_logger,
        logging_middleware: LoggingMiddleware,
        mock_request
    ):
        """
        Test logging of GET request without body.

        GIVEN: GET request with no body content
        WHEN: process_request() is called
        THEN: Request details are logged (method, URL, path)
              AND has_body=False, content_length=0
              AND request is returned unmodified
        """
        # Arrange: GET request with empty body
        mock_request.method = "GET"
        mock_request.content = b""

        # Act
        result = await logging_middleware.process_request(mock_request)

        # Assert: Request logged
        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args

        assert call_args[0][0] == "HTTP request", \
            "Should log standard request message"

        # Check logged details
        extra = call_args[1]["extra"]
        assert extra["method"] == "GET"
        assert extra["url"] == "http://api.test.com/api/users"
        assert extra["path"] == "/api/users"
        assert extra["has_body"] is False, \
            "GET request should have has_body=False"
        assert extra["content_length"] == 0, \
            "Empty body should have content_length=0"

        # Request unmodified
        assert result is mock_request

    @pytest.mark.unit
    @patch('src.infrastructure.http_clients.middleware.logging_middleware.logger')
    async def test_process_request_logs_post_request_with_body(
        self,
        mock_logger,
        logging_middleware: LoggingMiddleware,
        mock_request
    ):
        """
        Test logging of POST request with JSON body.

        GIVEN: POST request with JSON body
        WHEN: process_request() is called
        THEN: has_body=True and content_length=<body size> are logged
        """
        # Arrange: POST with JSON body
        mock_request.method = "POST"
        json_body = b'{"name": "John", "email": "john@test.com"}'
        mock_request.content = json_body

        # Act
        result = await logging_middleware.process_request(mock_request)

        # Assert: Body presence logged
        extra = mock_logger.debug.call_args[1]["extra"]

        assert extra["method"] == "POST"
        assert extra["has_body"] is True, \
            "POST with body should have has_body=True"
        assert extra["content_length"] == len(json_body), \
            "Should log actual body size in bytes"

        assert result is mock_request

    @pytest.mark.unit
    @patch('src.infrastructure.http_clients.middleware.logging_middleware.logger')
    async def test_process_request_logs_patch_request_with_body(
        self,
        mock_logger,
        logging_middleware: LoggingMiddleware,
        mock_request
    ):
        """
        Test logging of PATCH request.

        GIVEN: PATCH request with partial update data
        WHEN: process_request() is called
        THEN: Request is logged with body details
        """
        # Arrange
        mock_request.method = "PATCH"
        mock_request.content = b'{"timezone": "UTC"}'

        # Act
        result = await logging_middleware.process_request(mock_request)

        # Assert
        extra = mock_logger.debug.call_args[1]["extra"]
        assert extra["method"] == "PATCH"
        assert extra["has_body"] is True
        assert extra["content_length"] == 19  # len(b'{"timezone": "UTC"}')

        assert result is mock_request

    @pytest.mark.unit
    @patch('src.infrastructure.http_clients.middleware.logging_middleware.logger')
    async def test_process_request_logs_delete_request_without_body(
        self,
        mock_logger,
        logging_middleware: LoggingMiddleware,
        mock_request
    ):
        """
        Test logging of DELETE request.

        GIVEN: DELETE request (typically no body)
        WHEN: process_request() is called
        THEN: Request logged with has_body=False
        """
        # Arrange
        mock_request.method = "DELETE"
        mock_request.content = b""

        # Act
        result = await logging_middleware.process_request(mock_request)

        # Assert
        extra = mock_logger.debug.call_args[1]["extra"]
        assert extra["method"] == "DELETE"
        assert extra["has_body"] is False

        assert result is mock_request

    @pytest.mark.unit
    @patch('src.infrastructure.http_clients.middleware.logging_middleware.logger')
    async def test_process_request_logs_url_components_correctly(
        self,
        mock_logger,
        logging_middleware: LoggingMiddleware,
        mock_request
    ):
        """
        Test URL logging components.

        GIVEN: Request with full URL including domain and path
        WHEN: process_request() is called
        THEN: Both full URL and path are logged separately
        """
        # Arrange: Request with specific URL
        mock_request.url.__str__ = lambda self: "https://api.prod.com:8080/v1/users?limit=10"
        mock_request.url.path = "/v1/users"

        # Act
        await logging_middleware.process_request(mock_request)

        # Assert: Both URL and path logged
        extra = mock_logger.debug.call_args[1]["extra"]
        assert extra["url"] == "https://api.prod.com:8080/v1/users?limit=10", \
            "Should log full URL with query params"
        assert extra["path"] == "/v1/users", \
            "Should log path separately for filtering"

    @pytest.mark.unit
    @patch('src.infrastructure.http_clients.middleware.logging_middleware.logger')
    async def test_process_request_handles_none_content_as_empty(
        self,
        mock_logger,
        logging_middleware: LoggingMiddleware,
        mock_request
    ):
        """
        Test handling of None content.

        GIVEN: Request with content=None (not b"")
        WHEN: process_request() is called
        THEN: Treated as no body (has_body=False, content_length=0)
        """
        # Arrange: None content
        mock_request.content = None

        # Act
        result = await logging_middleware.process_request(mock_request)

        # Assert: Handled as empty
        extra = mock_logger.debug.call_args[1]["extra"]
        assert extra["has_body"] is False, \
            "None content should be treated as no body"
        assert extra["content_length"] == 0

        assert result is mock_request


class TestLoggingMiddlewareProcessResponse:
    """
    Test suite for process_response() method.

    Verifies response logging with status code, content length,
    error detection, and request association.
    """

    @pytest.mark.unit
    @patch('src.infrastructure.http_clients.middleware.logging_middleware.logger')
    async def test_process_response_logs_successful_response(
        self,
        mock_logger,
        logging_middleware: LoggingMiddleware,
        mock_response
    ):
        """
        Test logging of successful 200 response.

        GIVEN: 200 OK response with JSON body
        WHEN: process_response() is called
        THEN: Response details logged (status, content_length, is_error=False)
              AND response is returned unmodified
        """
        # Arrange: 200 response
        mock_response.status_code = 200
        mock_response.content = b'{"users": [{"id": 1}]}'

        # Act
        result = await logging_middleware.process_response(mock_response)

        # Assert: Response logged
        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args

        assert call_args[0][0] == "HTTP response", \
            "Should log standard response message"

        # Check logged details
        extra = call_args[1]["extra"]
        assert extra["method"] == "GET", \
            "Should log request method from response.request"
        assert extra["url"] == "http://api.test.com/api/users"
        assert extra["path"] == "/api/users"
        assert extra["status_code"] == 200
        assert extra["content_length"] == len(b'{"users": [{"id": 1}]}')
        assert extra["is_error"] is False, \
            "200 response should have is_error=False"

        # Response unmodified
        assert result is mock_response

    @pytest.mark.unit
    @patch('src.infrastructure.http_clients.middleware.logging_middleware.logger')
    async def test_process_response_logs_404_error_response(
        self,
        mock_logger,
        logging_middleware: LoggingMiddleware,
        mock_response
    ):
        """
        Test logging of 404 error response.

        GIVEN: 404 Not Found response
        WHEN: process_response() is called
        THEN: is_error=True is logged (status >= 400)
        """
        # Arrange: 404 error
        mock_response.status_code = 404
        mock_response.content = b'{"error": "Not found"}'

        # Act
        result = await logging_middleware.process_response(mock_response)

        # Assert: Error flagged
        extra = mock_logger.debug.call_args[1]["extra"]
        assert extra["status_code"] == 404
        assert extra["is_error"] is True, \
            "404 response should have is_error=True"

        assert result is mock_response

    @pytest.mark.unit
    @patch('src.infrastructure.http_clients.middleware.logging_middleware.logger')
    async def test_process_response_logs_500_error_response(
        self,
        mock_logger,
        logging_middleware: LoggingMiddleware,
        mock_response
    ):
        """
        Test logging of 500 server error.

        GIVEN: 500 Internal Server Error response
        WHEN: process_response() is called
        THEN: is_error=True (5xx errors flagged)
        """
        # Arrange
        mock_response.status_code = 500
        mock_response.content = b'{"error": "Internal server error"}'

        # Act
        await logging_middleware.process_response(mock_response)

        # Assert
        extra = mock_logger.debug.call_args[1]["extra"]
        assert extra["status_code"] == 500
        assert extra["is_error"] is True

    @pytest.mark.unit
    @patch('src.infrastructure.http_clients.middleware.logging_middleware.logger')
    @pytest.mark.parametrize("status_code,is_error", [
        (200, False),
        (201, False),
        (204, False),
        (301, False),
        (302, False),
        (400, True),
        (401, True),
        (403, True),
        (404, True),
        (422, True),
        (500, True),
        (502, True),
        (503, True)
    ])
    async def test_process_response_correctly_flags_error_status_codes(
        self,
        mock_logger,
        logging_middleware: LoggingMiddleware,
        mock_response,
        status_code: int,
        is_error: bool
    ):
        """
        Test is_error flag for various status codes.

        GIVEN: Responses with different status codes
        WHEN: process_response() is called
        THEN: is_error=True for status >= 400, False otherwise
        """
        # Arrange
        mock_response.status_code = status_code
        mock_response.content = b"{}"

        # Act
        await logging_middleware.process_response(mock_response)

        # Assert
        extra = mock_logger.debug.call_args[1]["extra"]
        assert extra["is_error"] is is_error, \
            f"Status {status_code} should have is_error={is_error}"

    @pytest.mark.unit
    @patch('src.infrastructure.http_clients.middleware.logging_middleware.logger')
    async def test_process_response_logs_empty_response_body(
        self,
        mock_logger,
        logging_middleware: LoggingMiddleware,
        mock_response
    ):
        """
        Test logging of response with no body.

        GIVEN: 204 No Content response (empty body)
        WHEN: process_response() is called
        THEN: content_length=0 is logged
        """
        # Arrange: Empty response
        mock_response.status_code = 204
        mock_response.content = b""

        # Act
        result = await logging_middleware.process_response(mock_response)

        # Assert
        extra = mock_logger.debug.call_args[1]["extra"]
        assert extra["content_length"] == 0, \
            "Empty response should have content_length=0"

        assert result is mock_response

    @pytest.mark.unit
    @patch('src.infrastructure.http_clients.middleware.logging_middleware.logger')
    async def test_process_response_logs_large_response_content_length(
        self,
        mock_logger,
        logging_middleware: LoggingMiddleware,
        mock_response
    ):
        """
        Test logging of large response body.

        GIVEN: Response with large body (e.g., 5MB JSON)
        WHEN: process_response() is called
        THEN: Content length is logged correctly
        """
        # Arrange: Large response
        large_body = b"x" * (5 * 1024 * 1024)  # 5MB
        mock_response.content = large_body

        # Act
        await logging_middleware.process_response(mock_response)

        # Assert: Large size logged
        extra = mock_logger.debug.call_args[1]["extra"]
        assert extra["content_length"] == 5 * 1024 * 1024, \
            "Should log large content length accurately"


class TestLoggingMiddlewareIntegration:
    """
    Test suite for request-response logging flow.

    Verifies middleware logs both sides of HTTP transaction.
    """

    @pytest.mark.unit
    @patch('src.infrastructure.http_clients.middleware.logging_middleware.logger')
    async def test_full_request_response_logging_flow(
        self,
        mock_logger,
        logging_middleware: LoggingMiddleware,
        mock_request,
        mock_response
    ):
        """
        Test complete request → response logging.

        GIVEN: HTTP request followed by response
        WHEN: process_request() then process_response() called
        THEN: Both request and response are logged
        """
        # Arrange: Link response to request
        mock_response.request = mock_request

        # Act: Simulate request → response flow
        await logging_middleware.process_request(mock_request)
        await logging_middleware.process_response(mock_response)

        # Assert: Both logged
        assert mock_logger.debug.call_count == 2, \
            "Should log both request and response"

        # First call: request
        request_call = mock_logger.debug.call_args_list[0]
        assert request_call[0][0] == "HTTP request"

        # Second call: response
        response_call = mock_logger.debug.call_args_list[1]
        assert response_call[0][0] == "HTTP response"


class TestLoggingMiddlewareEdgeCases:
    """
    Test suite for edge cases in logging middleware.
    """

    @pytest.mark.unit
    def test_middleware_is_stateless(
        self,
        logging_middleware: LoggingMiddleware
    ):
        """
        Test middleware has no mutable state.

        GIVEN: LoggingMiddleware instance
        WHEN: Middleware is examined
        THEN: No instance variables storing state
              (Thread-safe for concurrent requests)
        """
        # Assert: Stateless
        assert not hasattr(logging_middleware, '_requests'), \
            "Should not store request history"
        assert not hasattr(logging_middleware, '_responses'), \
            "Should not store response history"

    @pytest.mark.unit
    @patch('src.infrastructure.http_clients.middleware.logging_middleware.logger')
    async def test_process_request_returns_same_request_object(
        self,
        mock_logger,
        logging_middleware: LoggingMiddleware,
        mock_request
    ):
        """
        Test request object identity preserved.

        GIVEN: Request object
        WHEN: process_request() is called
        THEN: Exact same object (not copy) is returned
        """
        # Act
        result = await logging_middleware.process_request(mock_request)

        # Assert: Same object
        assert result is mock_request, \
            "Should return same request object (not copy)"

    @pytest.mark.unit
    @patch('src.infrastructure.http_clients.middleware.logging_middleware.logger')
    async def test_process_response_returns_same_response_object(
        self,
        mock_logger,
        logging_middleware: LoggingMiddleware,
        mock_response
    ):
        """
        Test response object identity preserved.

        GIVEN: Response object
        WHEN: process_response() is called
        THEN: Exact same object is returned
        """
        # Act
        result = await logging_middleware.process_response(mock_response)

        # Assert: Same object
        assert result is mock_response, \
            "Should return same response object"

    @pytest.mark.unit
    @patch('src.infrastructure.http_clients.middleware.logging_middleware.logger')
    async def test_process_request_with_zero_content_length(
        self,
        mock_logger,
        logging_middleware: LoggingMiddleware,
        mock_request
    ):
        """
        Test explicit zero-length content handling.

        GIVEN: Request with content=b"" (zero bytes)
        WHEN: process_request() is called
        THEN: has_body=False, content_length=0
        """
        # Arrange
        mock_request.content = b""

        # Act
        await logging_middleware.process_request(mock_request)

        # Assert
        extra = mock_logger.debug.call_args[1]["extra"]
        assert extra["has_body"] is False
        assert extra["content_length"] == 0
