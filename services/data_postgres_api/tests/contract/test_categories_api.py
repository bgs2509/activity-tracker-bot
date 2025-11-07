"""
Contract tests for Categories API endpoints.

Tests request/response schemas, duplicate handling, and error handling
for /api/v1/categories endpoints using FastAPI TestClient.

Test Coverage:
    - POST /categories: Create category with duplicate check
    - GET /categories: List user categories
    - DELETE /categories/{id}: Delete category with validation
    - Schema validation: name uniqueness, required fields
    - Error cases: 404, 409 conflict, 422 validation

Coverage Target: 100% of categories.py endpoints
Execution Time: < 0.4 seconds

Author: Testing Team
Date: 2025-11-07
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from src.main import app
from src.domain.models.category import Category


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def client():
    """Fixture: FastAPI TestClient."""
    return TestClient(app)


@pytest.fixture
def mock_category_service():
    """Fixture: Mock CategoryService."""
    return AsyncMock()


@pytest.fixture
def sample_category():
    """Fixture: Sample Category model."""
    return Category(
        id=1,
        user_id=1,
        name="Work",
        emoji="💼",
        created_at=datetime(2025, 11, 7, 12, 0, 0, tzinfo=timezone.utc)
    )


# ============================================================================
# TEST SUITES
# ============================================================================

class TestCreateCategoryEndpoint:
    """Test suite for POST /api/v1/categories endpoint."""

    @pytest.mark.contract
    def test_create_category_with_valid_data_returns_201(
        self,
        client,
        mock_category_service,
        sample_category
    ):
        """
        Test successful category creation.

        GIVEN: Valid category data
        WHEN: POST /api/v1/categories is called
        THEN: 201 status with created category
        """
        # Arrange
        request_data = {
            "user_id": 1,
            "name": "Work",
            "emoji": "💼"
        }
        mock_category_service.create_category.return_value = sample_category

        # Act
        with patch('src.api.dependencies.get_category_service', return_value=mock_category_service):
            response = client.post("/api/v1/categories", json=request_data)

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == 1
        assert data["name"] == "Work"
        assert data["emoji"] == "💼"

    @pytest.mark.contract
    def test_create_category_with_missing_name_returns_422(self, client):
        """
        Test validation: missing required name.

        GIVEN: Request missing name field
        WHEN: POST request is made
        THEN: 422 validation error
        """
        # Arrange
        request_data = {"user_id": 1, "emoji": "💼"}

        # Act
        response = client.post("/api/v1/categories", json=request_data)

        # Assert
        assert response.status_code == 422
        data = response.json()
        errors = data["detail"]
        assert any("name" in str(e.get("loc", [])) for e in errors)

    @pytest.mark.contract
    def test_create_category_with_duplicate_name_returns_409(
        self,
        client,
        mock_category_service
    ):
        """
        Test duplicate category handling.

        GIVEN: Category with same name already exists
        WHEN: POST request is made
        THEN: 409 Conflict (handled by middleware)
        """
        # Arrange: Service raises ValueError for duplicate
        mock_category_service.create_category.side_effect = ValueError(
            "Category with this name already exists"
        )

        request_data = {"user_id": 1, "name": "Work"}

        # Act
        with patch('src.api.dependencies.get_category_service', return_value=mock_category_service):
            response = client.post("/api/v1/categories", json=request_data)

        # Assert: Middleware converts to 409
        assert response.status_code == 409


class TestGetCategoriesEndpoint:
    """Test suite for GET /api/v1/categories endpoint."""

    @pytest.mark.contract
    def test_get_categories_with_user_id_returns_200_with_list(
        self,
        client,
        mock_category_service,
        sample_category
    ):
        """
        Test successful category listing.

        GIVEN: user_id query parameter
        WHEN: GET /api/v1/categories is called
        THEN: 200 with list of categories
        """
        # Arrange
        mock_category_service.get_user_categories.return_value = [sample_category]

        # Act
        with patch('src.api.dependencies.get_category_service', return_value=mock_category_service):
            response = client.get("/api/v1/categories?user_id=1")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["name"] == "Work"

    @pytest.mark.contract
    def test_get_categories_without_user_id_returns_422(self, client):
        """
        Test missing required query parameter.

        GIVEN: user_id not provided
        WHEN: GET request is made
        THEN: 422 validation error
        """
        # Act
        response = client.get("/api/v1/categories")

        # Assert
        assert response.status_code == 422

    @pytest.mark.contract
    def test_get_categories_returns_empty_list_for_new_user(
        self,
        client,
        mock_category_service
    ):
        """
        Test empty result set.

        GIVEN: User has no categories
        WHEN: GET request is made
        THEN: 200 with empty list
        """
        # Arrange
        mock_category_service.get_user_categories.return_value = []

        # Act
        with patch('src.api.dependencies.get_category_service', return_value=mock_category_service):
            response = client.get("/api/v1/categories?user_id=999")

        # Assert
        assert response.status_code == 200
        assert response.json() == []


class TestDeleteCategoryEndpoint:
    """Test suite for DELETE /api/v1/categories/{id} endpoint."""

    @pytest.mark.contract
    def test_delete_category_when_exists_returns_204(
        self,
        client,
        mock_category_service
    ):
        """
        Test successful category deletion.

        GIVEN: Category exists
        WHEN: DELETE /api/v1/categories/{id} is called
        THEN: 204 No Content
        """
        # Arrange
        mock_category_service.delete_category.return_value = None

        # Act
        with patch('src.api.dependencies.get_category_service', return_value=mock_category_service):
            response = client.delete("/api/v1/categories/1")

        # Assert
        assert response.status_code == 204
        assert response.content == b''

    @pytest.mark.contract
    def test_delete_category_when_not_found_returns_404(
        self,
        client,
        mock_category_service
    ):
        """
        Test deletion of non-existent category.

        GIVEN: Category does not exist
        WHEN: DELETE request is made
        THEN: 404 Not Found
        """
        # Arrange: Service raises ValueError with "not found"
        mock_category_service.delete_category.side_effect = ValueError(
            "Category not found"
        )

        # Act
        with patch('src.api.dependencies.get_category_service', return_value=mock_category_service):
            response = client.delete("/api/v1/categories/999")

        # Assert
        assert response.status_code == 404

    @pytest.mark.contract
    def test_delete_category_with_validation_error_returns_400(
        self,
        client,
        mock_category_service
    ):
        """
        Test deletion with business rule violation.

        GIVEN: Category cannot be deleted (business rule)
        WHEN: DELETE request is made
        THEN: 400 Bad Request
        """
        # Arrange: Service raises ValueError (non-404 case)
        mock_category_service.delete_category.side_effect = ValueError(
            "Cannot delete default category"
        )

        # Act
        with patch('src.api.dependencies.get_category_service', return_value=mock_category_service):
            response = client.delete("/api/v1/categories/1")

        # Assert
        assert response.status_code == 400
        data = response.json()
        assert "Cannot delete" in data["detail"]
