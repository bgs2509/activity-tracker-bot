"""
Unit tests for UserRepository.

Tests custom user-specific repository methods beyond base CRUD operations.
Verifies telegram_id queries which are critical for bot user lookup.

Test Coverage:
    - get_by_telegram_id(): Found, not found, query correctness, edge cases
    - Inherited base methods: Covered in test_base_repository.py

Coverage Target: 100% of user_repository.py
Execution Time: < 0.3 seconds

Author: Testing Team
Date: 2025-11-07
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.repositories.user_repository import UserRepository
from src.domain.models.user import User
from src.schemas.user import UserCreate, UserUpdate


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
    return session


@pytest.fixture
def user_repository(mock_session):
    """
    Fixture: UserRepository instance for testing.

    Args:
        mock_session: Mocked AsyncSession from fixture

    Returns:
        UserRepository: Repository instance with mocked session
    """
    return UserRepository(mock_session)


@pytest.fixture
def sample_user():
    """
    Fixture: Sample User model instance.

    Returns:
        User: User with typical field values for testing
    """
    return User(
        id=1,
        telegram_id=123456789,
        username="testuser",
        timezone="UTC"
    )


# ============================================================================
# TEST SUITES
# ============================================================================

class TestUserRepositoryGetByTelegramId:
    """
    Test suite for UserRepository.get_by_telegram_id() method.

    This is a critical method used in every bot interaction to identify users.
    Must handle: existing users, new users, edge cases.
    """

    @pytest.mark.unit
    async def test_get_by_telegram_id_when_user_exists_returns_user(
        self,
        user_repository: UserRepository,
        mock_session: AsyncMock,
        sample_user: User
    ):
        """
        Test successful user retrieval by telegram_id.

        GIVEN: User exists in database with telegram_id=123456789
        WHEN: get_by_telegram_id(123456789) is called
        THEN: User object is returned with all fields populated
              AND session.execute() is called once
        """
        # Arrange: Mock database to return user
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_session.execute.return_value = mock_result

        # Act: Query by telegram_id
        result = await user_repository.get_by_telegram_id(123456789)

        # Assert: Verify correct user returned
        assert result is not None, "Expected user to be found"
        assert result == sample_user, "Returned user should match expected"
        assert result.telegram_id == 123456789, "Telegram ID should match query"
        assert result.username == "testuser", "User data should be complete"

        # Verify session interaction
        mock_session.execute.assert_called_once(), \
            "Should query database exactly once"

    @pytest.mark.unit
    async def test_get_by_telegram_id_when_user_not_found_returns_none(
        self,
        user_repository: UserRepository,
        mock_session: AsyncMock
    ):
        """
        Test behavior when user doesn't exist.

        GIVEN: No user with telegram_id=999999999 in database
        WHEN: get_by_telegram_id(999999999) is called
        THEN: None is returned (gracefully handle non-existent user)
              AND no exception is raised
        """
        # Arrange: Mock database to return nothing
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act: Query non-existent user
        result = await user_repository.get_by_telegram_id(999999999)

        # Assert: Graceful None return
        assert result is None, \
            "Should return None for non-existent telegram_id"
        mock_session.execute.assert_called_once()

    @pytest.mark.unit
    async def test_get_by_telegram_id_queries_correct_field(
        self,
        user_repository: UserRepository,
        mock_session: AsyncMock
    ):
        """
        Test that correct SQL query is constructed.

        GIVEN: telegram_id parameter
        WHEN: get_by_telegram_id() is called
        THEN: SQL query filters by User.telegram_id field (not id or other fields)
        """
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act
        await user_repository.get_by_telegram_id(123456789)

        # Assert: Verify SQL query structure
        call_args = mock_session.execute.call_args[0][0]
        query_str = str(call_args).lower()

        # Query should reference telegram_id field
        assert "telegram_id" in query_str, \
            "Query must filter by telegram_id field"
        assert "where" in query_str or "telegram_id =" in query_str, \
            "Query should have WHERE clause with telegram_id"

    @pytest.mark.unit
    async def test_get_by_telegram_id_returns_complete_user_object(
        self,
        user_repository: UserRepository,
        mock_session: AsyncMock
    ):
        """
        Test that all user fields are populated.

        GIVEN: User exists with multiple fields (username, timezone, etc.)
        WHEN: get_by_telegram_id() is called
        THEN: Returned user has all fields populated (not just telegram_id)
        """
        # Arrange: User with multiple fields
        complete_user = User(
            id=1,
            telegram_id=123456789,
            username="john_doe",
            timezone="Europe/Moscow",
            last_poll_time=None
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = complete_user
        mock_session.execute.return_value = mock_result

        # Act
        result = await user_repository.get_by_telegram_id(123456789)

        # Assert: All fields present
        assert result is not None
        assert result.id == 1, "Should have ID"
        assert result.telegram_id == 123456789, "Should have telegram_id"
        assert result.username == "john_doe", "Should have username"
        assert result.timezone == "Europe/Moscow", "Should have timezone"

    @pytest.mark.unit
    @pytest.mark.parametrize("telegram_id", [
        1,  # Minimum valid ID
        123456789,  # Typical Telegram ID
        999999999999,  # Large ID (12 digits)
        5555555555,  # Another typical ID
    ])
    async def test_get_by_telegram_id_handles_various_id_formats(
        self,
        user_repository: UserRepository,
        mock_session: AsyncMock,
        telegram_id: int
    ):
        """
        Test method handles various telegram_id values.

        Telegram IDs are positive integers but vary in length.
        Method should handle all valid Telegram ID formats.
        """
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act: Should not raise exception for any valid telegram_id
        result = await user_repository.get_by_telegram_id(telegram_id)

        # Assert: Handles gracefully (None if not found is OK)
        assert result is None or isinstance(result, User), \
            "Should handle various telegram_id values gracefully"
        mock_session.execute.assert_called_once()

    @pytest.mark.unit
    async def test_get_by_telegram_id_with_zero_returns_none(
        self,
        user_repository: UserRepository,
        mock_session: AsyncMock
    ):
        """
        Test edge case with telegram_id=0.

        GIVEN: telegram_id=0 (technically possible but unlikely in Telegram)
        WHEN: get_by_telegram_id(0) is called
        THEN: Query executes without error (returns None if not found)
        """
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act
        result = await user_repository.get_by_telegram_id(0)

        # Assert: Handles edge case gracefully
        assert result is None, "telegram_id=0 should return None if not found"

    @pytest.mark.unit
    async def test_get_by_telegram_id_uses_correct_sql_function(
        self,
        user_repository: UserRepository,
        mock_session: AsyncMock
    ):
        """
        Test that SELECT query uses scalar_one_or_none() for single result.

        GIVEN: Query for unique telegram_id
        WHEN: get_by_telegram_id() is called
        THEN: Result.scalar_one_or_none() is used (not .all() or .first())
              This ensures we expect 0 or 1 result, never multiple.
        """
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act
        await user_repository.get_by_telegram_id(123456789)

        # Assert: Verify scalar_one_or_none() called
        mock_result.scalar_one_or_none.assert_called_once(), \
            "Should use scalar_one_or_none() for unique telegram_id lookup"


class TestUserRepositoryInheritance:
    """
    Test suite verifying UserRepository inherits base methods correctly.

    These tests ensure the inheritance chain works and base CRUD operations
    are available. Detailed testing of base methods is in test_base_repository.py.
    """

    @pytest.mark.unit
    async def test_user_repository_inherits_get_by_id(
        self,
        user_repository: UserRepository,
        mock_session: AsyncMock,
        sample_user: User
    ):
        """
        Test that inherited get_by_id() method is available and works.

        GIVEN: UserRepository instance
        WHEN: get_by_id() is called (inherited from BaseRepository)
        THEN: Method executes successfully and queries by id field
        """
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_session.execute.return_value = mock_result

        # Act: Call inherited method
        result = await user_repository.get_by_id(1)

        # Assert: Inherited method works
        assert result == sample_user, \
            "Inherited get_by_id() should work correctly"

    @pytest.mark.unit
    async def test_user_repository_inherits_create(
        self,
        user_repository: UserRepository,
        mock_session: AsyncMock
    ):
        """
        Test that inherited create() method is available.

        GIVEN: UserRepository instance
        WHEN: create() is called with UserCreate schema
        THEN: Method executes successfully (inherited from BaseRepository)
        """
        # Arrange
        user_data = UserCreate(telegram_id=123456789, username="newuser")
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()

        # Act: Call inherited method
        from unittest.mock import patch
        with patch.object(User, '__init__', return_value=None):
            try:
                await user_repository.create(user_data)
            except Exception:
                # Expected due to mocking
                pass

        # Assert: Inherited method accessible
        assert mock_session.add.called, \
            "Inherited create() method should be functional"

    @pytest.mark.unit
    async def test_user_repository_inherits_update(
        self,
        user_repository: UserRepository,
        mock_session: AsyncMock,
        sample_user: User
    ):
        """
        Test that inherited update() method is available.

        GIVEN: UserRepository instance
        WHEN: update() is called
        THEN: Method executes successfully (inherited from BaseRepository)
        """
        # Arrange
        update_data = UserUpdate(username="updated_name")

        from unittest.mock import patch
        with patch.object(
            user_repository,
            'get_by_id',
            return_value=sample_user
        ):
            # Act: Call inherited method
            result = await user_repository.update(1, update_data)

            # Assert: Inherited method works
            assert result is not None, \
                "Inherited update() should be functional"

    @pytest.mark.unit
    async def test_user_repository_inherits_delete(
        self,
        user_repository: UserRepository,
        mock_session: AsyncMock
    ):
        """
        Test that inherited delete() method is available.

        GIVEN: UserRepository instance
        WHEN: delete() is called
        THEN: Method executes successfully (inherited from BaseRepository)
        """
        # Arrange
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result
        mock_session.flush = AsyncMock()

        # Act: Call inherited method
        result = await user_repository.delete(1)

        # Assert: Inherited method works
        assert result is True, \
            "Inherited delete() should be functional"


class TestUserRepositoryEdgeCases:
    """
    Test suite for edge cases specific to UserRepository.
    """

    @pytest.mark.unit
    async def test_get_by_telegram_id_with_negative_id(
        self,
        user_repository: UserRepository,
        mock_session: AsyncMock
    ):
        """
        Test behavior with negative telegram_id (invalid but handle gracefully).

        GIVEN: telegram_id=-1 (invalid in Telegram)
        WHEN: get_by_telegram_id(-1) is called
        THEN: Query executes without exception, returns None
        """
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act: Should not crash
        result = await user_repository.get_by_telegram_id(-1)

        # Assert: Graceful handling
        assert result is None, \
            "Negative telegram_id should return None (not found)"

    @pytest.mark.unit
    async def test_repository_initialization_sets_model_correctly(
        self,
        mock_session: AsyncMock
    ):
        """
        Test that UserRepository initializes with correct model.

        GIVEN: UserRepository instantiation
        WHEN: __init__ is called
        THEN: self.model is set to User class
              AND self.session is set to provided session
        """
        # Act: Create repository
        repo = UserRepository(mock_session)

        # Assert: Proper initialization
        assert repo.model == User, \
            "Repository should be initialized with User model"
        assert repo.session == mock_session, \
            "Repository should store the session"

    @pytest.mark.unit
    async def test_get_by_telegram_id_does_not_modify_database(
        self,
        user_repository: UserRepository,
        mock_session: AsyncMock
    ):
        """
        Test that get_by_telegram_id() is read-only.

        GIVEN: Query operation
        WHEN: get_by_telegram_id() is called
        THEN: Only session.execute() is called (no add, flush, commit)
              Read-only operation should not modify database.
        """
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Ensure write methods are not mocked (so we can verify they're not called)
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()

        # Act: Read operation
        await user_repository.get_by_telegram_id(123456789)

        # Assert: No write operations
        mock_session.add.assert_not_called(), \
            "Read operation should not add entities"
        mock_session.flush.assert_not_called(), \
            "Read operation should not flush changes"
        mock_session.commit.assert_not_called(), \
            "Read operation should not commit transaction"


# ============================================================================
# PERFORMANCE & QUERY OPTIMIZATION TESTS
# ============================================================================

class TestUserRepositoryPerformance:
    """
    Test suite for query performance characteristics.

    While unit tests don't measure actual performance, we verify that
    queries are structured efficiently (single query, no N+1 issues, etc.)
    """

    @pytest.mark.unit
    async def test_get_by_telegram_id_executes_single_query(
        self,
        user_repository: UserRepository,
        mock_session: AsyncMock
    ):
        """
        Test that lookup requires only one database query.

        GIVEN: telegram_id lookup
        WHEN: get_by_telegram_id() is called
        THEN: session.execute() is called exactly once (no redundant queries)
        """
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act
        await user_repository.get_by_telegram_id(123456789)

        # Assert: Single query
        assert mock_session.execute.call_count == 1, \
            "Should execute exactly one query (efficient lookup)"

    @pytest.mark.unit
    async def test_get_by_telegram_id_query_has_where_clause(
        self,
        user_repository: UserRepository,
        mock_session: AsyncMock
    ):
        """
        Test that query uses WHERE clause (not fetching all users).

        GIVEN: Query for specific telegram_id
        WHEN: get_by_telegram_id() is called
        THEN: SQL query includes WHERE telegram_id = X
              (Efficient: database filters, not Python filtering)
        """
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act
        await user_repository.get_by_telegram_id(123456789)

        # Assert: Verify WHERE clause in query
        call_args = mock_session.execute.call_args[0][0]
        query_str = str(call_args).lower()

        assert "where" in query_str or "telegram_id =" in query_str, \
            "Query should use WHERE clause for efficient filtering"
