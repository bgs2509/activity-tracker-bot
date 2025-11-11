"""
Level 2 Integration Tests: Category Service.

Test Coverage:
    - Create category stores in database
    - Get category by ID retrieves correct record
    - Update category modifies existing record
    - Delete category removes from database
    - List categories by user
    - Validate category name uniqueness per user
    - Delete category with activities handles gracefully
    - Error handling for invalid operations
"""

import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.integration
@pytest.mark.level2
async def test_create_category_stores_in_database(db_session, test_user):
    """
    GIVEN: Valid category data
    WHEN: Service creates category
    THEN: Category is stored in database with correct attributes

    Mocks: None
    Real: Service, Repository, Database
    Time: ~140ms
    """
    # Arrange
    from services.data_postgres_api.src.application.services.category_service import CategoryService
    from services.data_postgres_api.src.infrastructure.repositories.category_repository import CategoryRepository

    repo = CategoryRepository(db_session)
    service = CategoryService(repo)

    # Act
    created = await service.create_category(
        user_id=test_user.id,
        name="Work",
        emoji="💼"
    )

    # Assert
    assert created.id is not None
    assert created.user_id == test_user.id
    assert created.name == "Work"
    assert created.emoji == "💼"

    # Verify in database
    retrieved = await service.get_category_by_id(created.id)
    assert retrieved is not None
    assert retrieved.id == created.id


@pytest.mark.integration
@pytest.mark.level2
async def test_get_category_by_id_retrieves_correct_record(db_session, test_category):
    """
    GIVEN: Category exists in database
    WHEN: Service retrieves by ID
    THEN: Correct category is returned

    Mocks: None
    Real: Service, Repository, Database
    Time: ~110ms
    """
    # Arrange
    from services.data_postgres_api.src.application.services.category_service import CategoryService
    from services.data_postgres_api.src.infrastructure.repositories.category_repository import CategoryRepository

    repo = CategoryRepository(db_session)
    service = CategoryService(repo)

    # Act
    retrieved = await service.get_category_by_id(test_category.id)

    # Assert
    assert retrieved is not None
    assert retrieved.id == test_category.id
    assert retrieved.user_id == test_category.user_id
    assert retrieved.name == test_category.name


@pytest.mark.integration
@pytest.mark.level2
async def test_get_category_by_id_returns_none_for_nonexistent(db_session):
    """
    GIVEN: Category ID does not exist
    WHEN: Service retrieves by ID
    THEN: None is returned

    Mocks: None
    Real: Service, Repository, Database
    Time: ~90ms
    """
    # Arrange
    from services.data_postgres_api.src.application.services.category_service import CategoryService
    from services.data_postgres_api.src.infrastructure.repositories.category_repository import CategoryRepository

    repo = CategoryRepository(db_session)
    service = CategoryService(repo)

    # Act
    retrieved = await service.get_category_by_id(999999)

    # Assert
    assert retrieved is None


@pytest.mark.integration
@pytest.mark.level2
async def test_update_category_modifies_existing_record(db_session, test_category):
    """
    GIVEN: Category exists in database
    WHEN: Service updates category attributes
    THEN: Database record is modified
          AND updated category is returned

    Mocks: None
    Real: Service, Repository, Database
    Time: ~130ms
    """
    # Arrange
    from services.data_postgres_api.src.application.services.category_service import CategoryService
    from services.data_postgres_api.src.infrastructure.repositories.category_repository import CategoryRepository

    repo = CategoryRepository(db_session)
    service = CategoryService(repo)

    original_name = test_category.name
    new_name = "Updated Category"

    # Act
    updated = await service.update_category(
        test_category.id,
        name=new_name,
        emoji="🎯"
    )

    # Assert
    assert updated is not None
    assert updated.id == test_category.id
    assert updated.name == new_name
    assert updated.emoji == "🎯"
    assert updated.name != original_name

    # Verify persistence
    retrieved = await service.get_category_by_id(test_category.id)
    assert retrieved.name == new_name


@pytest.mark.integration
@pytest.mark.level2
async def test_delete_category_removes_from_database(db_session, test_category):
    """
    GIVEN: Category exists in database
    WHEN: Service deletes category
    THEN: Category is removed from database
          AND subsequent retrieval returns None

    Mocks: None
    Real: Service, Repository, Database
    Time: ~120ms
    """
    # Arrange
    from services.data_postgres_api.src.application.services.category_service import CategoryService
    from services.data_postgres_api.src.infrastructure.repositories.category_repository import CategoryRepository

    repo = CategoryRepository(db_session)
    service = CategoryService(repo)

    category_id = test_category.id

    # Verify exists first
    exists = await service.get_category_by_id(category_id)
    assert exists is not None

    # Act
    result = await service.delete_category(category_id)

    # Assert
    assert result is True

    # Verify deleted
    retrieved = await service.get_category_by_id(category_id)
    assert retrieved is None


@pytest.mark.integration
@pytest.mark.level2
async def test_list_categories_returns_all_user_categories(db_session, test_user):
    """
    GIVEN: Multiple categories exist for user
    WHEN: Service lists categories
    THEN: All user categories are returned

    Mocks: None
    Real: Service, Repository, Database
    Time: ~170ms
    """
    # Arrange
    from services.data_postgres_api.src.application.services.category_service import CategoryService
    from services.data_postgres_api.src.infrastructure.repositories.category_repository import CategoryRepository

    repo = CategoryRepository(db_session)
    service = CategoryService(repo)

    # Create multiple categories
    categories_to_create = [
        ("Work", "💼"),
        ("Sport", "⚽"),
        ("Study", "📚")
    ]

    for name, emoji in categories_to_create:
        await service.create_category(
            user_id=test_user.id,
            name=name,
            emoji=emoji
        )

    # Act
    categories = await service.list_categories(user_id=test_user.id)

    # Assert
    assert len(categories) >= 3
    assert all(c.user_id == test_user.id for c in categories)
    category_names = [c.name for c in categories]
    assert "Work" in category_names
    assert "Sport" in category_names
    assert "Study" in category_names


@pytest.mark.integration
@pytest.mark.level2
async def test_category_name_uniqueness_per_user(db_session, test_user, test_category):
    """
    GIVEN: Category with name exists for user
    WHEN: Service attempts to create duplicate name
    THEN: Error is raised (or duplicate is rejected)

    Mocks: None
    Real: Service, Repository, Database, Unique constraint
    Time: ~140ms
    """
    # Arrange
    from services.data_postgres_api.src.application.services.category_service import CategoryService
    from services.data_postgres_api.src.infrastructure.repositories.category_repository import CategoryRepository

    repo = CategoryRepository(db_session)
    service = CategoryService(repo)

    # Act & Assert
    with pytest.raises(Exception):  # Could be IntegrityError or custom ValidationError
        await service.create_category(
            user_id=test_user.id,
            name=test_category.name,  # Duplicate name
            emoji="🎯"
        )


@pytest.mark.integration
@pytest.mark.level2
async def test_delete_category_with_activities_handles_gracefully(
    db_session, test_user, test_category, test_activity
):
    """
    GIVEN: Category has associated activities
    WHEN: Service attempts to delete category
    THEN: Deletion is handled gracefully
          (either cascades or prevents deletion)

    Mocks: None
    Real: Service, Repository, Database, Foreign key constraints
    Time: ~150ms
    """
    # Arrange
    from services.data_postgres_api.src.application.services.category_service import CategoryService
    from services.data_postgres_api.src.infrastructure.repositories.category_repository import CategoryRepository

    repo = CategoryRepository(db_session)
    service = CategoryService(repo)

    # Verify category has activities
    assert test_activity.category_id == test_category.id

    # Act - Attempt to delete
    # Depending on DB constraints, this should either:
    # 1. Cascade delete (delete activities too)
    # 2. Raise an error (prevent deletion)
    # 3. Set activities.category_id to NULL

    try:
        result = await service.delete_category(test_category.id)
        # If successful, verify what happened to activities
        from services.data_postgres_api.src.application.services.activity_service import ActivityService
        from services.data_postgres_api.src.infrastructure.repositories.activity_repository import ActivityRepository

        activity_repo = ActivityRepository(db_session)
        activity_service = ActivityService(activity_repo)

        activity = await activity_service.get_activity_by_id(test_activity.id)
        # Either activity is deleted or category_id is NULL
        assert activity is None or activity.category_id is None

    except Exception as e:
        # Deletion prevented due to foreign key constraint
        # This is also valid behavior
        assert "foreign key" in str(e).lower() or "constraint" in str(e).lower()
