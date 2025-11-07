"""
Unit tests for health check endpoints.

Tests /health/live and /health/ready endpoints without requiring a running server.
"""
import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy.exc import OperationalError

from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client."""
    from src.main import app
    return TestClient(app)


# ============================================================================
# Test: /health/live (Liveness probe)
# ============================================================================

@pytest.mark.unit
def test_liveness_endpoint_returns_200(client):
    """Test that liveness endpoint returns 200 status code."""
    response = client.get("/health/live")

    assert response.status_code == 200


@pytest.mark.unit
def test_liveness_endpoint_returns_json(client):
    """Test that liveness endpoint returns valid JSON."""
    response = client.get("/health/live")

    assert response.headers["content-type"] == "application/json"
    data = response.json()
    assert "status" in data


@pytest.mark.unit
def test_liveness_endpoint_status_alive(client):
    """Test that liveness endpoint returns 'alive' status."""
    response = client.get("/health/live")

    data = response.json()
    assert data["status"] == "alive"


@pytest.mark.unit
def test_liveness_endpoint_fast_response(client):
    """Test that liveness endpoint responds quickly (no external dependencies)."""
    import time
    start = time.time()
    response = client.get("/health/live")
    duration = time.time() - start

    assert response.status_code == 200
    # Should be very fast (< 100ms) since it doesn't check database
    assert duration < 0.1


@pytest.mark.unit
def test_liveness_endpoint_no_database_check(client):
    """Test that liveness probe does NOT check database connectivity."""
    # Liveness should succeed even if DB is down
    # This is by design - liveness only checks if process is alive
    response = client.get("/health/live")

    assert response.status_code == 200
    data = response.json()
    # Should NOT have database field
    assert "database" not in data


# ============================================================================
# Test: /health/ready (Readiness probe)
# ============================================================================

@pytest.mark.unit
def test_readiness_endpoint_returns_200_when_db_healthy(client):
    """Test that readiness endpoint returns 200 when database is connected."""
    response = client.get("/health/ready")

    # Note: This test will fail if DB is not available
    # In unit tests, we'd normally mock the DB connection
    # For now, assuming DB is available during test run
    assert response.status_code == 200


@pytest.mark.unit
def test_readiness_endpoint_returns_json(client):
    """Test that readiness endpoint returns valid JSON."""
    response = client.get("/health/ready")

    assert response.headers["content-type"] == "application/json"


@pytest.mark.unit
def test_readiness_endpoint_includes_database_status(client):
    """Test that readiness response includes database connection status."""
    response = client.get("/health/ready")

    if response.status_code == 200:
        data = response.json()
        assert "status" in data
        assert "database" in data
        assert data["status"] == "ready"
        assert data["database"] == "connected"


@pytest.mark.unit
@patch("src.infrastructure.database.connection.get_db")
async def test_readiness_endpoint_returns_503_when_db_unavailable(mock_get_db, client):
    """Test that readiness endpoint returns 503 when database is unavailable."""
    # Mock database connection failure
    async def mock_db_session():
        mock_session = AsyncMock()
        # Simulate database connection error
        mock_session.execute = AsyncMock(side_effect=OperationalError("", "", ""))
        yield mock_session

    mock_get_db.return_value = mock_db_session()

    response = client.get("/health/ready")

    # Should return 503 Service Unavailable
    assert response.status_code == 503
    data = response.json()
    assert "detail" in data
    assert "Database connection failed" in data["detail"]


# ============================================================================
# Test: Health check separation (liveness vs readiness)
# ============================================================================

@pytest.mark.unit
def test_liveness_and_readiness_are_separate_endpoints(client):
    """Test that liveness and readiness are different endpoints with different purposes."""
    liveness_response = client.get("/health/live")
    readiness_response = client.get("/health/ready")

    # Both should be valid endpoints
    assert liveness_response.status_code == 200
    assert readiness_response.status_code in [200, 503]

    # Liveness should NOT have database field
    liveness_data = liveness_response.json()
    assert "database" not in liveness_data

    # Readiness should have database field (when successful)
    if readiness_response.status_code == 200:
        readiness_data = readiness_response.json()
        assert "database" in readiness_data


# ============================================================================
# Test: Legacy endpoint (deprecated)
# ============================================================================

@pytest.mark.unit
def test_root_endpoint_returns_service_info(client):
    """Test that root endpoint returns service information."""
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert "status" in data
    assert "version" in data
    assert data["status"] == "running"


# ============================================================================
# Test: Edge cases
# ============================================================================

@pytest.mark.unit
def test_liveness_endpoint_multiple_calls(client):
    """Test that liveness endpoint is idempotent and stable."""
    responses = [client.get("/health/live") for _ in range(5)]

    for response in responses:
        assert response.status_code == 200
        assert response.json()["status"] == "alive"


@pytest.mark.unit
def test_health_endpoints_with_correlation_id(client):
    """Test that health endpoints work with correlation ID middleware."""
    correlation_id = "health-check-123"

    liveness_response = client.get(
        "/health/live",
        headers={"X-Correlation-ID": correlation_id}
    )
    readiness_response = client.get(
        "/health/ready",
        headers={"X-Correlation-ID": correlation_id}
    )

    # Should preserve correlation ID in responses
    assert liveness_response.headers.get("X-Correlation-ID") == correlation_id
    assert readiness_response.headers.get("X-Correlation-ID") == correlation_id
