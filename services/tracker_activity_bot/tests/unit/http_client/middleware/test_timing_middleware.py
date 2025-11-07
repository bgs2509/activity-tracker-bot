"""
Unit tests for TimingMiddleware.

Tests timing middleware that measures HTTP request/response duration.
Verifies start time storage, duration calculation, and logging behavior.

Test Coverage:
    - process_request(): Start time recording
    - process_response(): Duration calculation and logging
    - Edge cases: Missing start time, multiple concurrent requests

Coverage Target: 100% of timing_middleware.py
Execution Time: < 0.2 seconds

Author: Testing Team
Date: 2025-11-07
"""

import pytest
from unittest.mock import MagicMock, patch
import time
import httpx

from src.infrastructure.http_clients.middleware.timing_middleware import (
    TimingMiddleware
)


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def timing_middleware():
    """
    Fixture: TimingMiddleware instance.

    Returns:
        TimingMiddleware: Fresh middleware instance with empty timings
    """
    return TimingMiddleware()


@pytest.fixture
def mock_request():
    """
    Fixture: Mock httpx.Request.

    Returns:
        MagicMock: Mocked HTTP request with id()
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
    Fixture: Mock httpx.Response with associated request.

    Returns:
        MagicMock: Mocked HTTP response
    """
    response = MagicMock(spec=httpx.Response)
    response.status_code = 200
    response.request = MagicMock(spec=httpx.Request)
    response.request.method = "GET"
    response.request.url = MagicMock()
    response.request.url.path = "/api/users"
    response.request.url.__str__ = lambda self: "http://api.test.com/api/users"
    return response


# ============================================================================
# TEST SUITES
# ============================================================================

class TestTimingMiddlewareProcessRequest:
    """
    Test suite for process_request() method.

    Verifies start time recording for duration calculation.
    """

    @pytest.mark.unit
    async def test_process_request_stores_start_time(
        self,
        timing_middleware: TimingMiddleware,
        mock_request
    ):
        """
        Test start time recording.

        GIVEN: Incoming HTTP request
        WHEN: process_request() is called
        THEN: Start time is stored keyed by request ID
              AND request is returned unmodified
        """
        # Act
        result = await timing_middleware.process_request(mock_request)

        # Assert: Start time stored
        request_id = id(mock_request)
        assert request_id in timing_middleware._timings, \
            "Should store start time for request"

        start_time = timing_middleware._timings[request_id]
        assert isinstance(start_time, float), \
            "Start time should be float (time.time())"
        assert start_time <= time.time(), \
            "Start time should not be in future"

        # Request unmodified
        assert result is mock_request, \
            "Should return unmodified request"

    @pytest.mark.unit
    async def test_process_request_stores_unique_times_for_concurrent_requests(
        self,
        timing_middleware: TimingMiddleware
    ):
        """
        Test concurrent request handling.

        GIVEN: Multiple concurrent requests
        WHEN: process_request() is called for each
        THEN: Each request has separate start time entry
              (No timing data collision)
        """
        # Arrange: Multiple requests
        request1 = MagicMock(spec=httpx.Request)
        request2 = MagicMock(spec=httpx.Request)
        request3 = MagicMock(spec=httpx.Request)

        # Act: Process concurrently
        await timing_middleware.process_request(request1)
        await timing_middleware.process_request(request2)
        await timing_middleware.process_request(request3)

        # Assert: Each has unique timing entry
        assert id(request1) in timing_middleware._timings
        assert id(request2) in timing_middleware._timings
        assert id(request3) in timing_middleware._timings

        assert len(timing_middleware._timings) == 3, \
            "Should track 3 concurrent requests separately"

    @pytest.mark.unit
    async def test_process_request_uses_current_time(
        self,
        timing_middleware: TimingMiddleware,
        mock_request
    ):
        """
        Test start time uses current timestamp.

        GIVEN: process_request() call
        WHEN: Start time is recorded
        THEN: time.time() is used (current timestamp)
        """
        # Act
        with patch('time.time', return_value=1234567890.123):
            await timing_middleware.process_request(mock_request)

        # Assert: Stored time matches time.time()
        request_id = id(mock_request)
        assert timing_middleware._timings[request_id] == 1234567890.123, \
            "Should use time.time() for start timestamp"


class TestTimingMiddlewareProcessResponse:
    """
    Test suite for process_response() method.

    Verifies duration calculation, logging, and cleanup of timing data.
    """

    @pytest.mark.unit
    @patch('src.infrastructure.http_clients.middleware.timing_middleware.logger')
    async def test_process_response_calculates_duration_and_logs(
        self,
        mock_logger,
        timing_middleware: TimingMiddleware,
        mock_response
    ):
        """
        Test duration calculation and logging.

        GIVEN: Request processed earlier with start time stored
        WHEN: process_response() is called
        THEN: Duration is calculated (end - start) in milliseconds
              AND timing details are logged
              AND response is returned unmodified
        """
        # Arrange: Simulate request processed earlier
        request_id = id(mock_response.request)
        start_time = time.time() - 0.245  # 245ms ago
        timing_middleware._timings[request_id] = start_time

        # Act
        with patch('time.time', return_value=start_time + 0.245):
            result = await timing_middleware.process_response(mock_response)

        # Assert: Duration logged
        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args

        assert call_args[0][0] == "HTTP timing", \
            "Should log timing message"

        # Check logged details
        extra = call_args[1]["extra"]
        assert extra["method"] == "GET"
        assert extra["url"] == "http://api.test.com/api/users"
        assert extra["path"] == "/api/users"
        assert extra["status_code"] == 200
        assert extra["duration_ms"] == 245.0, \
            "Should calculate duration in milliseconds"

        # Response unmodified
        assert result is mock_response, \
            "Should return unmodified response"

    @pytest.mark.unit
    @patch('src.infrastructure.http_clients.middleware.timing_middleware.logger')
    async def test_process_response_removes_timing_entry_after_calculation(
        self,
        mock_logger,
        timing_middleware: TimingMiddleware,
        mock_response
    ):
        """
        Test timing data cleanup.

        GIVEN: Request with stored start time
        WHEN: process_response() is called
        THEN: Timing entry is removed from storage
              (Prevent memory leak for long-running applications)
        """
        # Arrange
        request_id = id(mock_response.request)
        timing_middleware._timings[request_id] = time.time()

        # Act
        await timing_middleware.process_response(mock_response)

        # Assert: Entry removed
        assert request_id not in timing_middleware._timings, \
            "Should remove timing entry after calculating duration"

    @pytest.mark.unit
    @patch('src.infrastructure.http_clients.middleware.timing_middleware.logger')
    async def test_process_response_with_missing_start_time_does_not_log(
        self,
        mock_logger,
        timing_middleware: TimingMiddleware,
        mock_response
    ):
        """
        Test graceful handling of missing start time.

        GIVEN: Response for request without start time recorded
        WHEN: process_response() is called
        THEN: No logging occurs (graceful degradation)
              AND no exception is raised
              AND response is returned unmodified
        """
        # Arrange: No start time stored
        assert id(mock_response.request) not in timing_middleware._timings

        # Act: Should not raise exception
        result = await timing_middleware.process_response(mock_response)

        # Assert: No logging
        mock_logger.debug.assert_not_called(), \
            "Should not log if start time is missing"

        # Response unmodified
        assert result is mock_response

    @pytest.mark.unit
    @patch('src.infrastructure.http_clients.middleware.timing_middleware.logger')
    async def test_process_response_rounds_duration_to_two_decimals(
        self,
        mock_logger,
        timing_middleware: TimingMiddleware,
        mock_response
    ):
        """
        Test duration rounding for readability.

        GIVEN: Duration with many decimal places (245.6789ms)
        WHEN: process_response() logs duration
        THEN: Duration is rounded to 2 decimal places (245.68ms)
        """
        # Arrange: Request started earlier
        request_id = id(mock_response.request)
        start_time = 1000.0
        timing_middleware._timings[request_id] = start_time

        # Act: End time creates precise duration
        with patch('time.time', return_value=1000.2456789):
            await timing_middleware.process_response(mock_response)

        # Assert: Duration rounded
        extra = mock_logger.debug.call_args[1]["extra"]
        duration = extra["duration_ms"]

        assert duration == 245.68, \
            "Should round duration to 2 decimal places"
        assert isinstance(duration, float)

    @pytest.mark.unit
    @patch('src.infrastructure.http_clients.middleware.timing_middleware.logger')
    async def test_process_response_logs_zero_duration_for_instant_response(
        self,
        mock_logger,
        timing_middleware: TimingMiddleware,
        mock_response
    ):
        """
        Test logging of very fast requests (0ms).

        GIVEN: Request and response at same time (instant)
        WHEN: process_response() is called
        THEN: Duration of 0.0ms is logged (no error)
        """
        # Arrange: Same start and end time
        request_id = id(mock_response.request)
        current_time = time.time()
        timing_middleware._timings[request_id] = current_time

        # Act
        with patch('time.time', return_value=current_time):
            await timing_middleware.process_response(mock_response)

        # Assert: Zero duration logged
        extra = mock_logger.debug.call_args[1]["extra"]
        assert extra["duration_ms"] == 0.0, \
            "Should handle 0ms duration (instant response)"


class TestTimingMiddlewareIntegration:
    """
    Test suite for full request-response timing flow.

    Verifies correct integration of process_request() and process_response().
    """

    @pytest.mark.unit
    @patch('src.infrastructure.http_clients.middleware.timing_middleware.logger')
    async def test_full_request_response_timing_flow(
        self,
        mock_logger,
        timing_middleware: TimingMiddleware,
        mock_request,
        mock_response
    ):
        """
        Test complete timing workflow.

        GIVEN: HTTP request → response flow
        WHEN: process_request() then process_response() called
        THEN: Duration is calculated from request start to response end
        """
        # Arrange: Link response to request
        mock_response.request = mock_request

        # Act: Simulate request → response flow
        await timing_middleware.process_request(mock_request)

        # Simulate network delay
        await timing_middleware.process_response(mock_response)

        # Assert: Timing logged
        mock_logger.debug.assert_called_once()
        extra = mock_logger.debug.call_args[1]["extra"]

        assert "duration_ms" in extra
        assert extra["duration_ms"] >= 0, \
            "Duration should be non-negative"

    @pytest.mark.unit
    @patch('src.infrastructure.http_clients.middleware.timing_middleware.logger')
    async def test_multiple_sequential_requests_tracked_independently(
        self,
        mock_logger,
        timing_middleware: TimingMiddleware
    ):
        """
        Test multiple sequential request timings.

        GIVEN: Multiple requests processed sequentially
        WHEN: Each request → response pair completes
        THEN: Each has independent timing (no interference)
        """
        # Arrange: Create 3 request-response pairs
        pairs = []
        for i in range(3):
            request = MagicMock(spec=httpx.Request)
            response = MagicMock(spec=httpx.Response)
            response.request = request
            response.status_code = 200
            response.request.method = "GET"
            response.request.url = MagicMock()
            response.request.url.path = f"/api/resource{i}"
            response.request.url.__str__ = lambda self, i=i: f"http://api.test/resource{i}"
            pairs.append((request, response))

        # Act: Process sequentially
        for request, response in pairs:
            await timing_middleware.process_request(request)
            await timing_middleware.process_response(response)

        # Assert: All 3 logged
        assert mock_logger.debug.call_count == 3, \
            "Should log timing for each request"

        # Timing storage should be empty (cleaned up)
        assert len(timing_middleware._timings) == 0, \
            "Should clean up all timing entries after responses"


class TestTimingMiddlewareEdgeCases:
    """
    Test suite for edge cases in timing measurement.
    """

    @pytest.mark.unit
    def test_middleware_initialization_creates_empty_timings_dict(
        self,
        timing_middleware: TimingMiddleware
    ):
        """
        Test initial state.

        GIVEN: TimingMiddleware instantiation
        WHEN: Middleware is created
        THEN: Empty _timings dict is initialized
        """
        # Assert
        assert hasattr(timing_middleware, '_timings'), \
            "Should have _timings attribute"
        assert timing_middleware._timings == {}, \
            "Should initialize with empty timings dict"
        assert isinstance(timing_middleware._timings, dict)

    @pytest.mark.unit
    @patch('src.infrastructure.http_clients.middleware.timing_middleware.logger')
    async def test_process_response_with_none_start_time_does_not_crash(
        self,
        mock_logger,
        timing_middleware: TimingMiddleware,
        mock_response
    ):
        """
        Test handling of None start time (defensive programming).

        GIVEN: Timing entry exists but value is None
        WHEN: process_response() is called
        THEN: No exception raised, no logging occurs
        """
        # Arrange: Set start time to None
        request_id = id(mock_response.request)
        timing_middleware._timings[request_id] = None

        # Act: Should not crash
        result = await timing_middleware.process_response(mock_response)

        # Assert: Graceful handling
        mock_logger.debug.assert_not_called()
        assert result is mock_response

        # Entry removed
        assert request_id not in timing_middleware._timings

    @pytest.mark.unit
    @patch('src.infrastructure.http_clients.middleware.timing_middleware.logger')
    async def test_process_response_uses_pop_for_atomic_retrieval(
        self,
        mock_logger,
        timing_middleware: TimingMiddleware,
        mock_response
    ):
        """
        Test atomic get-and-remove using pop().

        GIVEN: Start time stored
        WHEN: process_response() is called
        THEN: dict.pop() is used (atomic get and remove)
              (Thread-safe for concurrent requests)
        """
        # Arrange
        request_id = id(mock_response.request)
        timing_middleware._timings[request_id] = time.time()

        # Act
        await timing_middleware.process_response(mock_response)

        # Assert: Entry removed (via pop)
        assert request_id not in timing_middleware._timings, \
            "Should use pop() to atomically retrieve and remove"
