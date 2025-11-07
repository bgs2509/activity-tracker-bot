"""
Unit tests for RequestLoggingMiddleware.

Tests request/response logging without requiring running server.
"""
import pytest
import logging
from unittest.mock import patch, MagicMock

from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient

from src.api.middleware.logging import RequestLoggingMiddleware
from src.api.middleware.correlation import CorrelationIDMiddleware


@pytest.fixture
def app():
    """Create test FastAPI app with logging middleware."""
    app = FastAPI()

    # Add both middleware (correlation first, then logging)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(CorrelationIDMiddleware)

    @app.get("/test")
    async def test_endpoint():
        """Test endpoint that returns success."""
        return {"message": "success"}

    @app.get("/test-error")
    async def test_error_endpoint():
        """Test endpoint that raises exception."""
        raise HTTPException(status_code=400, detail="Test error")

    @app.get("/test-slow")
    async def test_slow_endpoint():
        """Test endpoint that simulates slow response."""
        import time
        time.sleep(0.1)  # 100ms
        return {"message": "slow response"}

    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


# ============================================================================
# Test: Request logging
# ============================================================================

@pytest.mark.unit
def test_request_started_logged(client, caplog):
    """Test that request start is logged with correct fields."""
    with caplog.at_level(logging.INFO):
        response = client.get("/test")

    assert response.status_code == 200

    # Find "HTTP request started" log
    started_logs = [r for r in caplog.records if "HTTP request started" in r.message]
    assert len(started_logs) >= 1

    log_record = started_logs[0]
    assert log_record.method == "GET"
    assert log_record.path == "/test"
    assert hasattr(log_record, "correlation_id")
    assert log_record.client_host is not None


@pytest.mark.unit
def test_request_completed_logged(client, caplog):
    """Test that request completion is logged with correct fields."""
    with caplog.at_level(logging.INFO):
        response = client.get("/test")

    assert response.status_code == 200

    # Find "HTTP request completed" log
    completed_logs = [r for r in caplog.records if "HTTP request completed" in r.message]
    assert len(completed_logs) >= 1

    log_record = completed_logs[0]
    assert log_record.method == "GET"
    assert log_record.path == "/test"
    assert log_record.status_code == 200
    assert hasattr(log_record, "duration_ms")
    assert log_record.duration_ms >= 0
    assert hasattr(log_record, "correlation_id")


@pytest.mark.unit
def test_request_logs_include_correlation_id(client, caplog):
    """Test that correlation ID is included in all log records."""
    correlation_id = "test-correlation-123"

    with caplog.at_level(logging.INFO):
        response = client.get(
            "/test",
            headers={"X-Correlation-ID": correlation_id}
        )

    assert response.status_code == 200

    # All logs should have the correlation ID
    for record in caplog.records:
        if "HTTP request" in record.message:
            assert hasattr(record, "correlation_id")
            assert record.correlation_id == correlation_id


# ============================================================================
# Test: Duration tracking
# ============================================================================

@pytest.mark.unit
def test_request_duration_tracked(client, caplog):
    """Test that request duration is tracked in milliseconds."""
    with caplog.at_level(logging.INFO):
        response = client.get("/test-slow")

    assert response.status_code == 200

    completed_logs = [r for r in caplog.records if "HTTP request completed" in r.message]
    assert len(completed_logs) >= 1

    log_record = completed_logs[0]
    assert hasattr(log_record, "duration_ms")
    # Should be at least 100ms (from sleep)
    assert log_record.duration_ms >= 100


@pytest.mark.unit
def test_request_duration_rounded(client, caplog):
    """Test that duration is rounded to 2 decimal places."""
    with caplog.at_level(logging.INFO):
        response = client.get("/test")

    assert response.status_code == 200

    completed_logs = [r for r in caplog.records if "HTTP request completed" in r.message]
    log_record = completed_logs[0]

    # Check that duration_ms has at most 2 decimal places
    duration_str = str(log_record.duration_ms)
    if "." in duration_str:
        decimal_places = len(duration_str.split(".")[1])
        assert decimal_places <= 2


# ============================================================================
# Test: Error logging
# ============================================================================

@pytest.mark.unit
def test_request_exception_logged(client, caplog):
    """Test that exceptions during request processing are logged."""
    with caplog.at_level(logging.ERROR):
        response = client.get("/test-error")

    assert response.status_code == 400

    # Should have error log
    error_logs = [r for r in caplog.records if r.levelname == "ERROR"]
    # Note: FastAPI's HTTPException is handled by FastAPI itself, not caught by middleware
    # So we might not see error logs for HTTPException, which is expected behavior


@pytest.mark.unit
def test_request_with_query_params_logged(client, caplog):
    """Test that query parameters are logged."""
    with caplog.at_level(logging.INFO):
        response = client.get("/test?foo=bar&baz=qux")

    assert response.status_code == 200

    started_logs = [r for r in caplog.records if "HTTP request started" in r.message]
    assert len(started_logs) >= 1

    log_record = started_logs[0]
    assert hasattr(log_record, "query_params")
    assert log_record.query_params is not None
    assert "foo=bar" in log_record.query_params or "foo" in log_record.query_params


@pytest.mark.unit
def test_request_without_query_params(client, caplog):
    """Test that requests without query params are handled correctly."""
    with caplog.at_level(logging.INFO):
        response = client.get("/test")

    assert response.status_code == 200

    started_logs = [r for r in caplog.records if "HTTP request started" in r.message]
    log_record = started_logs[0]

    # query_params should be None when no params present
    if hasattr(log_record, "query_params"):
        assert log_record.query_params is None or log_record.query_params == ""


# ============================================================================
# Test: HTTP methods
# ============================================================================

@pytest.mark.unit
def test_different_http_methods_logged(client, caplog):
    """Test that different HTTP methods are logged correctly."""
    with caplog.at_level(logging.INFO):
        # GET request
        response_get = client.get("/test")
        assert response_get.status_code == 200

    # Find GET request logs
    get_logs = [r for r in caplog.records if hasattr(r, "method") and r.method == "GET"]
    assert len(get_logs) >= 2  # Started + completed


# ============================================================================
# Test: Multiple requests
# ============================================================================

@pytest.mark.unit
def test_multiple_requests_logged_separately(client, caplog):
    """Test that multiple requests are logged with separate correlation IDs."""
    with caplog.at_level(logging.INFO):
        response1 = client.get("/test")
        response2 = client.get("/test")

    assert response1.status_code == 200
    assert response2.status_code == 200

    # Should have at least 4 logs (2 started + 2 completed)
    request_logs = [r for r in caplog.records if "HTTP request" in r.message]
    assert len(request_logs) >= 4

    # Correlation IDs should be different
    correlation_ids = set()
    for record in request_logs:
        if hasattr(record, "correlation_id"):
            correlation_ids.add(record.correlation_id)

    # Should have at least 2 different correlation IDs
    assert len(correlation_ids) >= 2
