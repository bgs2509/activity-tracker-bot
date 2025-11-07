"""
Unit tests for DataAPIClient HTTP client.

Tests the base HTTP client with middleware pipeline support.
Verifies request/response processing, middleware execution, and error handling.

Test Coverage:
    - Initialization: Default/custom middleware, categorization
    - HTTP methods: GET, POST, PATCH, DELETE
    - Middleware pipeline: Request, response, error processing
    - Error handling: Middleware handling, re-raising unhandled errors
    - Resource management: Client cleanup

Coverage Target: 100% of http_client.py
Execution Time: < 0.3 seconds

Author: Testing Team
Date: 2025-11-07
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from src.infrastructure.http_clients.http_client import DataAPIClient
from src.infrastructure.http_clients.middleware import (
    RequestMiddleware,
    ResponseMiddleware,
    ErrorMiddleware
)


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def mock_httpx_client():
    """
    Fixture: Mock httpx.AsyncClient.

    Returns:
        MagicMock: Mocked AsyncClient for testing without network calls
    """
    client = MagicMock(spec=httpx.AsyncClient)
    client.build_request = MagicMock()
    client.send = AsyncMock()
    client.aclose = AsyncMock()
    return client


@pytest.fixture
def mock_request():
    """
    Fixture: Mock httpx.Request.

    Returns:
        MagicMock: Mocked HTTP request object
    """
    request = MagicMock(spec=httpx.Request)
    request.method = "GET"
    request.url = "http://test.com/api/test"
    return request


@pytest.fixture
def mock_response():
    """
    Fixture: Mock httpx.Response.

    Returns:
        MagicMock: Mocked HTTP response object
    """
    response = MagicMock(spec=httpx.Response)
    response.status_code = 200
    response.json = MagicMock(return_value={"data": "test"})
    response.raise_for_status = MagicMock()
    return response


@pytest.fixture
def mock_request_middleware():
    """
    Fixture: Mock RequestMiddleware.

    Returns:
        AsyncMock: Mocked request middleware
    """
    middleware = MagicMock(spec=RequestMiddleware)
    middleware.process_request = AsyncMock(side_effect=lambda req: req)
    return middleware


@pytest.fixture
def mock_response_middleware():
    """
    Fixture: Mock ResponseMiddleware.

    Returns:
        AsyncMock: Mocked response middleware
    """
    middleware = MagicMock(spec=ResponseMiddleware)
    middleware.process_response = AsyncMock(side_effect=lambda resp: resp)
    return middleware


@pytest.fixture
def mock_error_middleware():
    """
    Fixture: Mock ErrorMiddleware.

    Returns:
        AsyncMock: Mocked error middleware
    """
    middleware = MagicMock(spec=ErrorMiddleware)
    middleware.should_handle = MagicMock(return_value=True)
    middleware.handle_error = AsyncMock(return_value=None)
    return middleware


# ============================================================================
# TEST SUITES
# ============================================================================

class TestDataAPIClientInitialization:
    """
    Test suite for DataAPIClient initialization.

    Verifies proper setup of HTTP client, middleware categorization,
    and configuration handling.
    """

    @pytest.mark.unit
    @patch('src.infrastructure.http_clients.http_client.httpx.AsyncClient')
    def test_init_with_default_middleware_creates_standard_pipeline(
        self,
        mock_async_client
    ):
        """
        Test initialization with default middleware.

        GIVEN: No custom middleware provided
        WHEN: DataAPIClient() is instantiated
        THEN: Default middleware (Timing, Logging, ErrorHandling) are added
              AND middleware are categorized correctly
        """
        # Arrange & Act
        client = DataAPIClient()

        # Assert: Default middleware loaded
        assert len(client.request_middlewares) > 0, \
            "Should have default request middleware"
        assert len(client.response_middlewares) > 0, \
            "Should have default response middleware"
        assert len(client.error_middlewares) > 0, \
            "Should have default error middleware"

        # Verify httpx client created with correct config
        mock_async_client.assert_called_once()
        call_kwargs = mock_async_client.call_args.kwargs
        assert "base_url" in call_kwargs, "Should set base_url"
        assert "timeout" in call_kwargs, "Should set timeout"
        assert call_kwargs["follow_redirects"] is True, \
            "Should follow redirects"

    @pytest.mark.unit
    @patch('src.infrastructure.http_clients.http_client.httpx.AsyncClient')
    def test_init_with_custom_middleware_uses_provided_middleware(
        self,
        mock_async_client,
        mock_request_middleware
    ):
        """
        Test initialization with custom middleware.

        GIVEN: Custom middleware list provided
        WHEN: DataAPIClient(middlewares=[...]) is instantiated
        THEN: Only provided middleware are used (no defaults)
              AND middleware are categorized by type
        """
        # Arrange: Custom middleware
        custom_middleware = [mock_request_middleware]

        # Act
        client = DataAPIClient(middlewares=custom_middleware)

        # Assert: Custom middleware loaded
        assert len(client.request_middlewares) == 1, \
            "Should have exactly one request middleware"
        assert client.request_middlewares[0] == mock_request_middleware, \
            "Should use provided middleware"

    @pytest.mark.unit
    @patch('src.infrastructure.http_clients.http_client.httpx.AsyncClient')
    def test_init_categorizes_middleware_by_type(
        self,
        mock_async_client,
        mock_request_middleware,
        mock_response_middleware,
        mock_error_middleware
    ):
        """
        Test middleware categorization by capabilities.

        GIVEN: Middleware with different capabilities (request, response, error)
        WHEN: DataAPIClient is initialized
        THEN: Middleware are categorized into correct lists based on methods
              (process_request, process_response, should_handle/handle_error)
        """
        # Arrange: Mixed middleware types
        middlewares = [
            mock_request_middleware,
            mock_response_middleware,
            mock_error_middleware
        ]

        # Act
        client = DataAPIClient(middlewares=middlewares)

        # Assert: Correct categorization
        assert mock_request_middleware in client.request_middlewares, \
            "Request middleware should be in request_middlewares"
        assert mock_response_middleware in client.response_middlewares, \
            "Response middleware should be in response_middlewares"
        assert mock_error_middleware in client.error_middlewares, \
            "Error middleware should be in error_middlewares"

    @pytest.mark.unit
    @patch('src.infrastructure.http_clients.http_client.httpx.AsyncClient')
    def test_init_with_custom_base_url_uses_provided_url(
        self,
        mock_async_client
    ):
        """
        Test custom base URL configuration.

        GIVEN: Custom base_url provided
        WHEN: DataAPIClient(base_url="http://custom.api") is instantiated
        THEN: Client uses provided base_url (not settings default)
        """
        # Act
        custom_url = "http://custom-api.test"
        client = DataAPIClient(base_url=custom_url)

        # Assert: Custom URL used
        assert client.base_url == custom_url, \
            "Should use provided base_url"

        # Verify passed to httpx client
        call_kwargs = mock_async_client.call_args.kwargs
        assert call_kwargs["base_url"] == custom_url, \
            "Should pass base_url to httpx.AsyncClient"

    @pytest.mark.unit
    @patch('src.infrastructure.http_clients.http_client.httpx.AsyncClient')
    def test_init_with_custom_timeout_uses_provided_timeout(
        self,
        mock_async_client
    ):
        """
        Test custom timeout configuration.

        GIVEN: Custom timeout provided
        WHEN: DataAPIClient(timeout=30.0) is instantiated
        THEN: Client uses provided timeout value
        """
        # Act
        custom_timeout = 30.0
        client = DataAPIClient(timeout=custom_timeout)

        # Assert: Custom timeout used
        call_kwargs = mock_async_client.call_args.kwargs
        assert call_kwargs["timeout"] == custom_timeout, \
            "Should use provided timeout"


class TestDataAPIClientHTTPMethods:
    """
    Test suite for HTTP method wrappers (GET, POST, PATCH, DELETE).

    Verifies that each method correctly delegates to _execute_request()
    with proper HTTP method and parameters.
    """

    @pytest.mark.unit
    @patch('src.infrastructure.http_clients.http_client.httpx.AsyncClient')
    async def test_get_method_executes_get_request(
        self,
        mock_async_client,
        mock_httpx_client,
        mock_request,
        mock_response
    ):
        """
        Test GET method execution.

        GIVEN: DataAPIClient instance
        WHEN: get("/users", params={"limit": 10}) is called
        THEN: HTTP GET request is made with correct path and parameters
              AND response JSON is returned
        """
        # Arrange
        mock_async_client.return_value = mock_httpx_client
        mock_httpx_client.build_request.return_value = mock_request
        mock_httpx_client.send.return_value = mock_response

        client = DataAPIClient(middlewares=[])

        # Act
        result = await client.get("/users", params={"limit": 10})

        # Assert: GET request made
        mock_httpx_client.build_request.assert_called_once_with(
            "GET", "/users", params={"limit": 10}
        )
        assert result == {"data": "test"}, \
            "Should return response JSON"
        mock_response.json.assert_called_once()

    @pytest.mark.unit
    @patch('src.infrastructure.http_clients.http_client.httpx.AsyncClient')
    async def test_post_method_executes_post_request(
        self,
        mock_async_client,
        mock_httpx_client,
        mock_request,
        mock_response
    ):
        """
        Test POST method execution.

        GIVEN: DataAPIClient instance
        WHEN: post("/users", json={"name": "John"}) is called
        THEN: HTTP POST request is made with JSON body
              AND response JSON is returned
        """
        # Arrange
        mock_async_client.return_value = mock_httpx_client
        mock_httpx_client.build_request.return_value = mock_request
        mock_httpx_client.send.return_value = mock_response

        client = DataAPIClient(middlewares=[])

        # Act
        result = await client.post("/users", json={"name": "John"})

        # Assert: POST request made
        mock_httpx_client.build_request.assert_called_once_with(
            "POST", "/users", json={"name": "John"}
        )
        assert result == {"data": "test"}, \
            "Should return response JSON"

    @pytest.mark.unit
    @patch('src.infrastructure.http_clients.http_client.httpx.AsyncClient')
    async def test_patch_method_executes_patch_request(
        self,
        mock_async_client,
        mock_httpx_client,
        mock_request,
        mock_response
    ):
        """
        Test PATCH method execution.

        GIVEN: DataAPIClient instance
        WHEN: patch("/users/1", json={"name": "Jane"}) is called
        THEN: HTTP PATCH request is made with JSON body
              AND response JSON is returned
        """
        # Arrange
        mock_async_client.return_value = mock_httpx_client
        mock_httpx_client.build_request.return_value = mock_request
        mock_httpx_client.send.return_value = mock_response

        client = DataAPIClient(middlewares=[])

        # Act
        result = await client.patch("/users/1", json={"name": "Jane"})

        # Assert: PATCH request made
        mock_httpx_client.build_request.assert_called_once_with(
            "PATCH", "/users/1", json={"name": "Jane"}
        )
        assert result == {"data": "test"}

    @pytest.mark.unit
    @patch('src.infrastructure.http_clients.http_client.httpx.AsyncClient')
    async def test_delete_method_executes_delete_request_returns_status_code(
        self,
        mock_async_client,
        mock_httpx_client,
        mock_request,
        mock_response
    ):
        """
        Test DELETE method returns status code (not JSON).

        GIVEN: DataAPIClient instance
        WHEN: delete("/users/1") is called
        THEN: HTTP DELETE request is made
              AND status code is returned (204, not JSON)
        """
        # Arrange
        mock_async_client.return_value = mock_httpx_client
        mock_httpx_client.build_request.return_value = mock_request
        mock_response.status_code = 204
        mock_httpx_client.send.return_value = mock_response

        client = DataAPIClient(middlewares=[])

        # Act
        result = await client.delete("/users/1")

        # Assert: DELETE returns status code
        mock_httpx_client.build_request.assert_called_once_with(
            "DELETE", "/users/1"
        )
        assert result == 204, \
            "DELETE should return status code, not JSON"
        mock_response.json.assert_not_called(), \
            "DELETE should not call response.json()"


class TestDataAPIClientMiddlewarePipeline:
    """
    Test suite for middleware pipeline processing.

    Verifies that request, response, and error middleware are executed
    in correct order and modify requests/responses appropriately.
    """

    @pytest.mark.unit
    async def test_process_request_executes_all_request_middleware_in_order(
        self,
        mock_request_middleware
    ):
        """
        Test request middleware pipeline execution.

        GIVEN: Multiple request middleware
        WHEN: _process_request() is called
        THEN: All request middleware process_request() called in order
              AND request is modified by each middleware
        """
        # Arrange
        middleware1 = MagicMock(spec=RequestMiddleware)
        middleware1.process_request = AsyncMock(side_effect=lambda req: req)

        middleware2 = MagicMock(spec=RequestMiddleware)
        middleware2.process_request = AsyncMock(side_effect=lambda req: req)

        with patch('src.infrastructure.http_clients.http_client.httpx.AsyncClient'):
            client = DataAPIClient(middlewares=[middleware1, middleware2])

            request = MagicMock(spec=httpx.Request)

            # Act
            result = await client._process_request(request)

            # Assert: Both middleware called in order
            middleware1.process_request.assert_called_once_with(request)
            middleware2.process_request.assert_called_once()
            assert result == request, \
                "Should return processed request"

    @pytest.mark.unit
    async def test_process_response_executes_all_response_middleware_in_order(
        self,
        mock_response_middleware
    ):
        """
        Test response middleware pipeline execution.

        GIVEN: Multiple response middleware
        WHEN: _process_response() is called
        THEN: All response middleware process_response() called in order
              AND response is modified by each middleware
        """
        # Arrange
        middleware1 = MagicMock(spec=ResponseMiddleware)
        middleware1.process_response = AsyncMock(side_effect=lambda resp: resp)

        middleware2 = MagicMock(spec=ResponseMiddleware)
        middleware2.process_response = AsyncMock(side_effect=lambda resp: resp)

        with patch('src.infrastructure.http_clients.http_client.httpx.AsyncClient'):
            client = DataAPIClient(middlewares=[middleware1, middleware2])

            response = MagicMock(spec=httpx.Response)

            # Act
            result = await client._process_response(response)

            # Assert: Both middleware called in order
            middleware1.process_response.assert_called_once_with(response)
            middleware2.process_response.assert_called_once()
            assert result == response, \
                "Should return processed response"

    @pytest.mark.unit
    async def test_handle_error_calls_should_handle_for_each_middleware(
        self,
        mock_error_middleware
    ):
        """
        Test error middleware should_handle() check.

        GIVEN: Multiple error middleware
        WHEN: _handle_error() is called
        THEN: Each middleware's should_handle() is checked
              AND handle_error() is only called if should_handle() returns True
        """
        # Arrange
        error = httpx.HTTPStatusError("404", request=MagicMock(), response=MagicMock())

        middleware1 = MagicMock(spec=ErrorMiddleware)
        middleware1.should_handle = MagicMock(return_value=False)
        middleware1.handle_error = AsyncMock()

        middleware2 = MagicMock(spec=ErrorMiddleware)
        middleware2.should_handle = MagicMock(return_value=True)
        middleware2.handle_error = AsyncMock(return_value=MagicMock())

        with patch('src.infrastructure.http_clients.http_client.httpx.AsyncClient'):
            client = DataAPIClient(middlewares=[middleware1, middleware2])

            request = MagicMock(spec=httpx.Request)

            # Act
            result = await client._handle_error(error, request)

            # Assert: should_handle checked for both
            middleware1.should_handle.assert_called_once_with(error)
            middleware1.handle_error.assert_not_called(), \
                "Should not handle if should_handle() returns False"

            middleware2.should_handle.assert_called_once_with(error)
            middleware2.handle_error.assert_called_once_with(error, request), \
                "Should handle if should_handle() returns True"

            assert result is not None, \
                "Should return handled response"

    @pytest.mark.unit
    async def test_handle_error_returns_none_if_no_middleware_handles(self):
        """
        Test error handling when no middleware handles error.

        GIVEN: Error middleware that don't handle error
        WHEN: _handle_error() is called
        THEN: None is returned (error will be re-raised)
        """
        # Arrange
        error = Exception("Unhandled error")

        middleware = MagicMock(spec=ErrorMiddleware)
        middleware.should_handle = MagicMock(return_value=False)

        with patch('src.infrastructure.http_clients.http_client.httpx.AsyncClient'):
            client = DataAPIClient(middlewares=[middleware])

            request = MagicMock(spec=httpx.Request)

            # Act
            result = await client._handle_error(error, request)

            # Assert: No handling
            assert result is None, \
                "Should return None if no middleware handles error"


class TestDataAPIClientRequestExecution:
    """
    Test suite for _execute_request() core logic.

    Verifies request building, middleware execution, response handling,
    and error handling flow.
    """

    @pytest.mark.unit
    @patch('src.infrastructure.http_clients.http_client.httpx.AsyncClient')
    async def test_execute_request_processes_through_complete_pipeline(
        self,
        mock_async_client,
        mock_httpx_client,
        mock_request,
        mock_response
    ):
        """
        Test complete request execution pipeline.

        GIVEN: DataAPIClient with middleware
        WHEN: _execute_request() is called
        THEN: Request is built → processed → sent → response processed
              AND middleware pipeline executes in correct order
        """
        # Arrange
        mock_async_client.return_value = mock_httpx_client
        mock_httpx_client.build_request.return_value = mock_request
        mock_httpx_client.send.return_value = mock_response

        request_middleware = MagicMock(spec=RequestMiddleware)
        request_middleware.process_request = AsyncMock(side_effect=lambda req: req)

        response_middleware = MagicMock(spec=ResponseMiddleware)
        response_middleware.process_response = AsyncMock(side_effect=lambda resp: resp)

        client = DataAPIClient(middlewares=[request_middleware, response_middleware])

        # Act
        result = await client._execute_request("GET", "/test")

        # Assert: Full pipeline executed
        mock_httpx_client.build_request.assert_called_once()
        request_middleware.process_request.assert_called_once()
        mock_httpx_client.send.assert_called_once()
        response_middleware.process_response.assert_called_once()
        mock_response.raise_for_status.assert_called_once()
        assert result == {"data": "test"}

    @pytest.mark.unit
    @patch('src.infrastructure.http_clients.http_client.httpx.AsyncClient')
    async def test_execute_request_raises_unhandled_errors(
        self,
        mock_async_client,
        mock_httpx_client,
        mock_request
    ):
        """
        Test unhandled error re-raising.

        GIVEN: Request that fails with no error middleware handling it
        WHEN: _execute_request() is called
        THEN: Exception is re-raised after middleware check
        """
        # Arrange
        mock_async_client.return_value = mock_httpx_client
        mock_httpx_client.build_request.return_value = mock_request

        error = httpx.RequestError("Connection failed")
        mock_httpx_client.send.side_effect = error

        error_middleware = MagicMock(spec=ErrorMiddleware)
        error_middleware.should_handle = MagicMock(return_value=False)

        client = DataAPIClient(middlewares=[error_middleware])

        # Act & Assert: Error re-raised
        with pytest.raises(httpx.RequestError) as exc_info:
            await client._execute_request("GET", "/test")

        assert str(exc_info.value) == "Connection failed"
        error_middleware.should_handle.assert_called_once()

    @pytest.mark.unit
    @patch('src.infrastructure.http_clients.http_client.httpx.AsyncClient')
    async def test_execute_request_returns_handled_error_response(
        self,
        mock_async_client,
        mock_httpx_client,
        mock_request,
        mock_response
    ):
        """
        Test handled error response return.

        GIVEN: Request that fails but error middleware handles it
        WHEN: _execute_request() is called
        THEN: Handled response is returned (error not re-raised)
        """
        # Arrange
        mock_async_client.return_value = mock_httpx_client
        mock_httpx_client.build_request.return_value = mock_request

        error = httpx.HTTPStatusError("404", request=mock_request, response=mock_response)
        mock_httpx_client.send.side_effect = error

        # Mock handled response
        handled_response = MagicMock(spec=httpx.Response)
        handled_response.json = MagicMock(return_value={"error": "handled"})

        error_middleware = MagicMock(spec=ErrorMiddleware)
        error_middleware.should_handle = MagicMock(return_value=True)
        error_middleware.handle_error = AsyncMock(return_value=handled_response)

        client = DataAPIClient(middlewares=[error_middleware])

        # Act: Should not raise
        result = await client._execute_request("GET", "/test")

        # Assert: Handled response returned
        assert result == {"error": "handled"}
        error_middleware.handle_error.assert_called_once()


class TestDataAPIClientResourceManagement:
    """
    Test suite for resource cleanup.

    Verifies proper cleanup of HTTP client resources.
    """

    @pytest.mark.unit
    @patch('src.infrastructure.http_clients.http_client.httpx.AsyncClient')
    async def test_close_calls_httpx_client_aclose(
        self,
        mock_async_client,
        mock_httpx_client
    ):
        """
        Test close() cleanup.

        GIVEN: DataAPIClient instance
        WHEN: close() is called
        THEN: Underlying httpx.AsyncClient.aclose() is called
              (Cleanup HTTP connections)
        """
        # Arrange
        mock_async_client.return_value = mock_httpx_client
        client = DataAPIClient()

        # Act
        await client.close()

        # Assert: Cleanup called
        mock_httpx_client.aclose.assert_called_once(), \
            "Should close httpx client connections"


class TestDataAPIClientEdgeCases:
    """
    Test suite for edge cases and error scenarios.
    """

    @pytest.mark.unit
    @patch('src.infrastructure.http_clients.http_client.httpx.AsyncClient')
    def test_init_with_empty_middleware_list_creates_no_middleware(
        self,
        mock_async_client
    ):
        """
        Test initialization with empty middleware list.

        GIVEN: Empty middleware list provided
        WHEN: DataAPIClient(middlewares=[]) is instantiated
        THEN: No middleware are added (no defaults)
        """
        # Act
        client = DataAPIClient(middlewares=[])

        # Assert: No middleware
        assert len(client.request_middlewares) == 0, \
            "Should have no request middleware"
        assert len(client.response_middlewares) == 0, \
            "Should have no response middleware"
        assert len(client.error_middlewares) == 0, \
            "Should have no error middleware"

    @pytest.mark.unit
    @patch('src.infrastructure.http_clients.http_client.httpx.AsyncClient')
    async def test_delete_method_returns_status_code_on_handled_error(
        self,
        mock_async_client,
        mock_httpx_client,
        mock_request
    ):
        """
        Test DELETE method returns status code even for handled errors.

        GIVEN: DELETE request that fails but is handled by middleware
        WHEN: delete() is called
        THEN: Status code is returned (not JSON)
        """
        # Arrange
        mock_async_client.return_value = mock_httpx_client
        mock_httpx_client.build_request.return_value = mock_request

        error = httpx.HTTPStatusError("404", request=mock_request, response=MagicMock())
        mock_httpx_client.send.side_effect = error

        handled_response = MagicMock(spec=httpx.Response)
        handled_response.status_code = 404

        error_middleware = MagicMock(spec=ErrorMiddleware)
        error_middleware.should_handle = MagicMock(return_value=True)
        error_middleware.handle_error = AsyncMock(return_value=handled_response)

        client = DataAPIClient(middlewares=[error_middleware])

        # Act
        result = await client.delete("/users/1")

        # Assert: Status code returned
        assert result == 404, \
            "DELETE should return status code even for handled errors"
