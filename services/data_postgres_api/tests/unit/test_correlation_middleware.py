"""
Unit tests for CorrelationIDMiddleware.

Tests correlation ID generation and propagation without requiring running server.
"""
import pytest
from unittest.mock import AsyncMock, Mock
from uuid import UUID

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from src.api.middleware.correlation import CorrelationIDMiddleware, CORRELATION_ID_HEADER


@pytest.fixture
def app():
    """Create test FastAPI app with correlation middleware."""
    app = FastAPI()
    app.add_middleware(CorrelationIDMiddleware)

    @app.get("/test")
    async def test_endpoint(request: Request):
        """Test endpoint that returns correlation ID from request state."""
        return {
            "correlation_id": getattr(request.state, "correlation_id", None)
        }

    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


# ============================================================================
# Test: Correlation ID generation
# ============================================================================

@pytest.mark.unit
def test_correlation_id_generated_when_not_provided(client):
    """Test that correlation ID is auto-generated when not in request headers."""
    response = client.get("/test")

    assert response.status_code == 200
    assert CORRELATION_ID_HEADER in response.headers

    # Verify it's a valid UUID
    correlation_id = response.headers[CORRELATION_ID_HEADER]
    try:
        UUID(correlation_id)
        is_valid_uuid = True
    except ValueError:
        is_valid_uuid = False

    assert is_valid_uuid


@pytest.mark.unit
def test_correlation_id_added_to_request_state(client):
    """Test that correlation ID is added to request.state for handlers."""
    response = client.get("/test")

    assert response.status_code == 200
    data = response.json()
    assert data["correlation_id"] is not None

    # Should match response header
    assert data["correlation_id"] == response.headers[CORRELATION_ID_HEADER]


# ============================================================================
# Test: Correlation ID extraction
# ============================================================================

@pytest.mark.unit
def test_correlation_id_extracted_from_request_header(client):
    """Test that existing correlation ID is extracted from request headers."""
    custom_correlation_id = "test-correlation-123"

    response = client.get("/test", headers={CORRELATION_ID_HEADER: custom_correlation_id})

    assert response.status_code == 200
    assert response.headers[CORRELATION_ID_HEADER] == custom_correlation_id

    # Verify it's available in request state
    data = response.json()
    assert data["correlation_id"] == custom_correlation_id


@pytest.mark.unit
def test_correlation_id_propagated_to_response(client):
    """Test that correlation ID from request is propagated to response."""
    custom_correlation_id = "client-provided-id"

    response = client.get("/test", headers={CORRELATION_ID_HEADER: custom_correlation_id})

    assert response.status_code == 200
    assert response.headers[CORRELATION_ID_HEADER] == custom_correlation_id


# ============================================================================
# Test: Multiple requests
# ============================================================================

@pytest.mark.unit
def test_correlation_id_unique_per_request(client):
    """Test that each request without correlation ID gets unique ID."""
    response1 = client.get("/test")
    response2 = client.get("/test")

    correlation_id1 = response1.headers[CORRELATION_ID_HEADER]
    correlation_id2 = response2.headers[CORRELATION_ID_HEADER]

    assert correlation_id1 != correlation_id2


@pytest.mark.unit
def test_correlation_id_consistent_within_request(client):
    """Test that correlation ID is consistent throughout request lifecycle."""
    custom_id = "consistent-id-test"

    response = client.get("/test", headers={CORRELATION_ID_HEADER: custom_id})

    # ID in response header should match what's in request state
    assert response.headers[CORRELATION_ID_HEADER] == custom_id
    assert response.json()["correlation_id"] == custom_id


# ============================================================================
# Test: Edge cases
# ============================================================================

@pytest.mark.unit
def test_correlation_id_with_empty_string(client):
    """Test that empty string correlation ID is replaced with generated UUID."""
    response = client.get("/test", headers={CORRELATION_ID_HEADER: ""})

    assert response.status_code == 200
    correlation_id = response.headers[CORRELATION_ID_HEADER]
    assert correlation_id != ""

    # Should be valid UUID
    try:
        UUID(correlation_id)
        is_valid_uuid = True
    except ValueError:
        is_valid_uuid = False

    assert is_valid_uuid


@pytest.mark.unit
def test_correlation_id_with_whitespace(client):
    """Test that whitespace-only correlation ID is accepted (FastAPI behavior)."""
    whitespace_id = "   "

    response = client.get("/test", headers={CORRELATION_ID_HEADER: whitespace_id})

    assert response.status_code == 200
    # FastAPI/Starlette will preserve the whitespace value
    assert response.headers[CORRELATION_ID_HEADER] == whitespace_id


@pytest.mark.unit
def test_correlation_id_with_special_characters(client):
    """Test that correlation ID with special characters is preserved."""
    special_id = "test-123_abc@xyz.com"

    response = client.get("/test", headers={CORRELATION_ID_HEADER: special_id})

    assert response.status_code == 200
    assert response.headers[CORRELATION_ID_HEADER] == special_id


@pytest.mark.unit
def test_correlation_id_with_uuid_format(client):
    """Test that valid UUID format correlation IDs are preserved."""
    uuid_id = "550e8400-e29b-41d4-a716-446655440000"

    response = client.get("/test", headers={CORRELATION_ID_HEADER: uuid_id})

    assert response.status_code == 200
    assert response.headers[CORRELATION_ID_HEADER] == uuid_id

    # Verify it's valid UUID
    try:
        UUID(uuid_id)
        is_valid_uuid = True
    except ValueError:
        is_valid_uuid = False

    assert is_valid_uuid
