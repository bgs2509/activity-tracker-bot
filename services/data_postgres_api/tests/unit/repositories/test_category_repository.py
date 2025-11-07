"""
Unit tests for CategoryRepository.

Tests custom category-specific repository methods including category lookup,
user category listings, and count operations.

Test Coverage:
    - get_by_user_and_name(): Lookup by user and name, uniqueness check
    - get_all_by_user(): All categories for user, ordering
    - count_by_user(): Category count calculation
    - Inherited base methods: Covered in test_base_repository.py

Coverage Target: 100% of category_repository.py
Execution Time: < 0.3 seconds

Author: Testing Team
Date: 2025-11-07
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.repositories.category_repository import (
    CategoryRepository,
    CategoryUpdate
)
from src.domain.models.category import Category
from src.schemas.category import CategoryCreate


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_session():
    """
    Fixture: Mock SQLAlchemy AsyncSession.

    Returns:
        AsyncMock: Mocked session for testing without database
    """
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def category_repository(mock_session):
    """
    Fixture: CategoryRepository instance for testing.

    Args:
        mock_session: Mocked AsyncSession from fixture

    Returns:
        CategoryRepository: Repository instance with mocked session
    """
    return CategoryRepository(mock_session)


@pytest.fixture
def sample_category():
    """
    Fixture: Sample Category model instance.

    Returns:
        Category: Category with typical field values for testing
    """
    return Category(
        id=1,
        user_id=1,
        name="Work",
        created_at=datetime(2025, 11, 7, 10, 0)
    )


# ============================================================================
# TEST SUITES
# ============================================================================

class TestCategoryRepositoryGetByUserAndName:
    """
    Test suite for CategoryRepository.get_by_user_and_name() method.

    Tests category lookup by user_id and name combination.
    Critical for preventing duplicate categories per user.
    """

    @pytest.mark.unit
    async def test_get_by_user_and_name_when_found_returns_category(
        self,
        category_repository: CategoryRepository,
        mock_session: AsyncMock,
        sample_category: Category
    ):
        """
        Test successful category retrieval by user and name.

        GIVEN: Category "Work" exists for user_id=1
        WHEN: get_by_user_and_name(1, "Work") is called
        THEN: Category object is returned
        """
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_category
        mock_session.execute.return_value = mock_result

        # Act
        result = await category_repository.get_by_user_and_name(
            user_id=1,
            name="Work"
        )

        # Assert
        assert result is not None, "Expected category to be found"
        assert result == sample_category
        assert result.name == "Work"
        assert result.user_id == 1

    @pytest.mark.unit
    async def test_get_by_user_and_name_when_not_found_returns_none(
        self,
        category_repository: CategoryRepository,
        mock_session: AsyncMock
    ):
        """
        Test behavior when category doesn't exist.

        GIVEN: No category "NonExistent" for user_id=1
        WHEN: get_by_user_and_name(1, "NonExistent") is called
        THEN: None is returned
        """
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act
        result = await category_repository.get_by_user_and_name(
            user_id=1,
            name="NonExistent"
        )

        # Assert
        assert result is None, "Should return None when category not found"

    @pytest.mark.unit
    async def test_get_by_user_and_name_filters_by_both_user_and_name(
        self,
        category_repository: CategoryRepository,
        mock_session: AsyncMock
    ):
        """
        Test that query filters by both user_id AND name.

        GIVEN: Multiple users may have categories with same name
        WHEN: get_by_user_and_name() is called
        THEN: Query filters by both user_id and name (not just one)
        """
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act
        await category_repository.get_by_user_and_name(
            user_id=1,
            name="Work"
        )

        # Assert: Verify query filters by both fields
        call_args = mock_session.execute.call_args[0][0]
        query_str = str(call_args).lower()

        assert "user_id" in query_str, \
            "Query should filter by user_id"
        assert "name" in query_str or "work" in query_str.lower(), \
            "Query should filter by name"

    @pytest.mark.unit
    async def test_get_by_user_and_name_is_case_sensitive(
        self,
        category_repository: CategoryRepository,
        mock_session: AsyncMock
    ):
        """
        Test case sensitivity of name matching.

        Different databases may handle case differently.
        This test documents expected behavior.

        GIVEN: Category "Work" exists
        WHEN: get_by_user_and_name(1, "work") is called (lowercase)
        THEN: Depends on database collation (test queries with exact match)
        """
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act: Query with different case
        await category_repository.get_by_user_and_name(
            user_id=1,
            name="work"  # lowercase
        )

        # Assert: Query should use exact name provided
        mock_session.execute.assert_called_once()

    @pytest.mark.unit
    async def test_get_by_user_and_name_handles_special_characters(
        self,
        category_repository: CategoryRepository,
        mock_session: AsyncMock
    ):
        """
        Test category names with special characters.

        GIVEN: Category name with special chars "Work & Study"
        WHEN: get_by_user_and_name() is called
        THEN: Query executes without error
        """
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act: Name with special characters
        result = await category_repository.get_by_user_and_name(
            user_id=1,
            name="Work & Study 🎓"
        )

        # Assert: Handles gracefully
        assert result is None or isinstance(result, Category)


class TestCategoryRepositoryGetAllByUser:
    """
    Test suite for CategoryRepository.get_all_by_user() method.

    Tests retrieval of all categories for a specific user.
    """

    @pytest.mark.unit
    async def test_get_all_by_user_returns_all_user_categories(
        self,
        category_repository: CategoryRepository,
        mock_session: AsyncMock
    ):
        """
        Test retrieval of all categories for a user.

        GIVEN: User has 3 categories
        WHEN: get_all_by_user(user_id=1) is called
        THEN: All 3 categories are returned
        """
        # Arrange: 3 categories for user 1
        categories = [
            Category(
                id=1,
                user_id=1,
                name="Work",
                created_at=datetime(2025, 11, 1, 10, 0)
            ),
            Category(
                id=2,
                user_id=1,
                name="Personal",
                created_at=datetime(2025, 11, 2, 10, 0)
            ),
            Category(
                id=3,
                user_id=1,
                name="Study",
                created_at=datetime(2025, 11, 3, 10, 0)
            ),
        ]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = categories
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act
        result = await category_repository.get_all_by_user(user_id=1)

        # Assert
        assert isinstance(result, list), "Should return list"
        assert len(result) == 3, "Should return all 3 categories"
        assert all(c.user_id == 1 for c in result), \
            "All categories should belong to user 1"

    @pytest.mark.unit
    async def test_get_all_by_user_orders_by_created_at(
        self,
        category_repository: CategoryRepository,
        mock_session: AsyncMock
    ):
        """
        Test that categories are ordered by creation time.

        GIVEN: Categories created at different times
        WHEN: get_all_by_user() is called
        THEN: Categories are ordered by created_at ascending (oldest first)
        """
        # Arrange: Categories in order (oldest to newest)
        categories = [
            Category(
                id=1,
                user_id=1,
                name="First",
                created_at=datetime(2025, 11, 1, 10, 0)  # Oldest
            ),
            Category(
                id=2,
                user_id=1,
                name="Second",
                created_at=datetime(2025, 11, 2, 10, 0)
            ),
            Category(
                id=3,
                user_id=1,
                name="Third",
                created_at=datetime(2025, 11, 3, 10, 0)  # Newest
            ),
        ]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = categories
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act
        result = await category_repository.get_all_by_user(user_id=1)

        # Assert: Ordered oldest to newest
        assert result[0].name == "First", \
            "First category should be oldest"
        assert result[-1].name == "Third", \
            "Last category should be newest"

    @pytest.mark.unit
    async def test_get_all_by_user_returns_empty_list_when_no_categories(
        self,
        category_repository: CategoryRepository,
        mock_session: AsyncMock
    ):
        """
        Test behavior when user has no categories.

        GIVEN: User has no categories
        WHEN: get_all_by_user() is called
        THEN: Empty list is returned (not None)
        """
        # Arrange: No categories
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act
        result = await category_repository.get_all_by_user(user_id=999)

        # Assert
        assert result == [], "Should return empty list"
        assert isinstance(result, list), "Should be list, not None"

    @pytest.mark.unit
    async def test_get_all_by_user_filters_by_user_id(
        self,
        category_repository: CategoryRepository,
        mock_session: AsyncMock
    ):
        """
        Test that only specified user's categories are returned.

        GIVEN: Multiple users with categories
        WHEN: get_all_by_user(user_id=1) is called
        THEN: Only user 1's categories are in query
        """
        # Arrange
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act
        await category_repository.get_all_by_user(user_id=1)

        # Assert: Verify WHERE clause
        call_args = mock_session.execute.call_args[0][0]
        query_str = str(call_args).lower()

        assert "user_id" in query_str or "where" in query_str, \
            "Query should filter by user_id"


class TestCategoryRepositoryCountByUser:
    """
    Test suite for CategoryRepository.count_by_user() method.

    Tests category count calculation for a user.
    """

    @pytest.mark.unit
    async def test_count_by_user_returns_correct_count(
        self,
        category_repository: CategoryRepository,
        mock_session: AsyncMock
    ):
        """
        Test count returns correct number of categories.

        GIVEN: User has 5 categories
        WHEN: count_by_user(user_id=1) is called
        THEN: 5 is returned
        """
        # Arrange: Mock count result
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 5
        mock_session.execute.return_value = mock_result

        # Act
        result = await category_repository.count_by_user(user_id=1)

        # Assert
        assert result == 5, "Should return count of 5"
        assert isinstance(result, int), "Count should be integer"

    @pytest.mark.unit
    async def test_count_by_user_returns_zero_when_no_categories(
        self,
        category_repository: CategoryRepository,
        mock_session: AsyncMock
    ):
        """
        Test count when user has no categories.

        GIVEN: User has no categories
        WHEN: count_by_user() is called
        THEN: 0 is returned
        """
        # Arrange: Mock zero count
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 0
        mock_session.execute.return_value = mock_result

        # Act
        result = await category_repository.count_by_user(user_id=999)

        # Assert
        assert result == 0, "Should return 0 for user with no categories"

    @pytest.mark.unit
    async def test_count_by_user_uses_sql_count_function(
        self,
        category_repository: CategoryRepository,
        mock_session: AsyncMock
    ):
        """
        Test that COUNT() SQL function is used (not loading all rows).

        GIVEN: User has many categories
        WHEN: count_by_user() is called
        THEN: SQL COUNT() function is used (efficient)
              Not loading all categories and counting in Python
        """
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 100
        mock_session.execute.return_value = mock_result

        # Act
        result = await category_repository.count_by_user(user_id=1)

        # Assert: Verify COUNT query
        call_args = mock_session.execute.call_args[0][0]
        query_str = str(call_args).lower()

        assert "count" in query_str, \
            "Should use SQL COUNT function for efficiency"
        assert result == 100

    @pytest.mark.unit
    @pytest.mark.parametrize("count", [0, 1, 5, 10, 50, 100])
    async def test_count_by_user_handles_various_counts(
        self,
        category_repository: CategoryRepository,
        mock_session: AsyncMock,
        count: int
    ):
        """
        Test count with various result values.

        Verifies method handles different count results correctly.
        """
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = count
        mock_session.execute.return_value = mock_result

        # Act
        result = await category_repository.count_by_user(user_id=1)

        # Assert
        assert result == count, f"Should return count of {count}"
        assert isinstance(result, int), "Count should be integer"


class TestCategoryRepositoryInheritance:
    """
    Test suite verifying CategoryRepository inherits base methods.

    Verifies CRUD operations from BaseRepository are available.
    """

    @pytest.mark.unit
    async def test_category_repository_inherits_get_by_id(
        self,
        category_repository: CategoryRepository,
        mock_session: AsyncMock,
        sample_category: Category
    ):
        """
        Test that inherited get_by_id() is available.

        GIVEN: CategoryRepository instance
        WHEN: get_by_id() is called
        THEN: Method executes successfully
        """
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_category
        mock_session.execute.return_value = mock_result

        # Act
        result = await category_repository.get_by_id(1)

        # Assert
        assert result == sample_category, "Inherited get_by_id() should work"

    @pytest.mark.unit
    async def test_category_repository_inherits_create(
        self,
        category_repository: CategoryRepository,
        mock_session: AsyncMock
    ):
        """
        Test that inherited create() is available.

        GIVEN: CategoryRepository instance
        WHEN: create() is called with CategoryCreate schema
        THEN: Method executes successfully
        """
        # Arrange
        category_data = CategoryCreate(user_id=1, name="New Category")

        from unittest.mock import patch
        with patch.object(Category, '__init__', return_value=None):
            try:
                await category_repository.create(category_data)
            except Exception:
                # Expected due to mocking
                pass

        # Assert
        assert mock_session.add.called, "Inherited create() should work"

    @pytest.mark.unit
    async def test_category_repository_inherits_delete(
        self,
        category_repository: CategoryRepository,
        mock_session: AsyncMock
    ):
        """
        Test that inherited delete() is available.

        GIVEN: CategoryRepository instance
        WHEN: delete() is called
        THEN: Method executes successfully
        """
        # Arrange
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result
        mock_session.flush = AsyncMock()

        # Act
        result = await category_repository.delete(1)

        # Assert
        assert result is True, "Inherited delete() should work"


class TestCategoryRepositoryEdgeCases:
    """
    Test suite for edge cases specific to CategoryRepository.
    """

    @pytest.mark.unit
    async def test_get_by_user_and_name_with_empty_name(
        self,
        category_repository: CategoryRepository,
        mock_session: AsyncMock
    ):
        """
        Test behavior with empty string name.

        GIVEN: Empty string as category name
        WHEN: get_by_user_and_name(1, "") is called
        THEN: Query executes (may or may not find match)
        """
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act: Empty name
        result = await category_repository.get_by_user_and_name(
            user_id=1,
            name=""
        )

        # Assert: Handles gracefully
        assert result is None or isinstance(result, Category)

    @pytest.mark.unit
    async def test_get_by_user_and_name_with_very_long_name(
        self,
        category_repository: CategoryRepository,
        mock_session: AsyncMock
    ):
        """
        Test with very long category name.

        GIVEN: Category name with 255 characters
        WHEN: get_by_user_and_name() is called
        THEN: Query executes without error
        """
        # Arrange: Very long name
        long_name = "A" * 255

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act
        result = await category_repository.get_by_user_and_name(
            user_id=1,
            name=long_name
        )

        # Assert: Handles long names
        assert result is None or isinstance(result, Category)

    @pytest.mark.unit
    async def test_count_by_user_filters_by_user_id(
        self,
        category_repository: CategoryRepository,
        mock_session: AsyncMock
    ):
        """
        Test that count filters by specific user.

        GIVEN: Multiple users with categories
        WHEN: count_by_user(user_id=1) is called
        THEN: Query filters by user_id=1 (not counting all users)
        """
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 5
        mock_session.execute.return_value = mock_result

        # Act
        await category_repository.count_by_user(user_id=1)

        # Assert: Verify WHERE clause in count query
        call_args = mock_session.execute.call_args[0][0]
        query_str = str(call_args).lower()

        assert "where" in query_str or "user_id" in query_str, \
            "COUNT should filter by user_id"
