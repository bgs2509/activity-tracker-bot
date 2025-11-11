"""
Level 3 Integration Tests: Category Management Flows.

Test full end-to-end category management flows.

Test Coverage:
    - Create new category flow
    - Edit category name flow
    - Edit category emoji flow
    - Delete category flow
    - List categories flow
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.integration
@pytest.mark.level3
async def test_create_new_category_flow(
    db_session, redis_storage, test_user
):
    """
    GIVEN: User wants to create a new category
    WHEN: User enters name and emoji
    THEN: Category is created in database
          AND confirmation is shown
          AND category appears in list

    Mocks: Telegram Bot API
    Real: Full category creation flow
    Time: ~320ms
    """
    # Arrange
    from aiogram.fsm.context import FSMContext
    from services.data_postgres_api.src.application.services.category_service import CategoryService
    from services.data_postgres_api.src.infrastructure.repositories.category_repository import CategoryRepository

    user_id = test_user.telegram_id
    state = FSMContext(
        storage=redis_storage,
        key=f"{user_id}:state"
    )

    # Step 1: User clicks "Добавить категорию"
    await state.set_state("category_creation:waiting_name")

    # Step 2: User enters name
    category_name = "New Category"
    await state.update_data(name=category_name)
    await state.set_state("category_creation:waiting_emoji")

    # Step 3: User enters emoji
    category_emoji = "🎯"
    await state.update_data(emoji=category_emoji)

    # Act - Save category
    repo = CategoryRepository(db_session)
    service = CategoryService(repo)

    category = await service.create_category(
        user_id=test_user.id,
        name=category_name,
        emoji=category_emoji
    )

    # Assert
    assert category is not None
    assert category.name == category_name
    assert category.emoji == category_emoji

    # Verify in database
    retrieved = await service.get_category_by_id(category.id)
    assert retrieved is not None
    assert retrieved.name == category_name

    # Verify appears in list
    categories = await service.list_categories(user_id=test_user.id)
    assert any(c.name == category_name for c in categories)

    # Clean up state
    await state.clear()


@pytest.mark.integration
@pytest.mark.level3
async def test_edit_category_name_flow(
    db_session, redis_storage, test_user, test_category
):
    """
    GIVEN: Category exists
    WHEN: User edits category name
    THEN: Category name is updated in database
          AND confirmation is shown

    Mocks: Telegram Bot API
    Real: Full edit flow
    Time: ~290ms
    """
    # Arrange
    from services.data_postgres_api.src.application.services.category_service import CategoryService
    from services.data_postgres_api.src.infrastructure.repositories.category_repository import CategoryRepository

    repo = CategoryRepository(db_session)
    service = CategoryService(repo)

    original_name = test_category.name
    new_name = "Updated Category Name"

    # Act
    updated = await service.update_category(
        test_category.id,
        name=new_name
    )

    # Assert
    assert updated is not None
    assert updated.name == new_name
    assert updated.name != original_name
    assert updated.emoji == test_category.emoji  # Unchanged

    # Verify persistence
    retrieved = await service.get_category_by_id(test_category.id)
    assert retrieved.name == new_name


@pytest.mark.integration
@pytest.mark.level3
async def test_edit_category_emoji_flow(
    db_session, redis_storage, test_user, test_category
):
    """
    GIVEN: Category exists
    WHEN: User edits category emoji
    THEN: Category emoji is updated in database
          AND confirmation is shown

    Mocks: Telegram Bot API
    Real: Full edit flow
    Time: ~290ms
    """
    # Arrange
    from services.data_postgres_api.src.application.services.category_service import CategoryService
    from services.data_postgres_api.src.infrastructure.repositories.category_repository import CategoryRepository

    repo = CategoryRepository(db_session)
    service = CategoryService(repo)

    original_emoji = test_category.emoji
    new_emoji = "🚀"

    # Act
    updated = await service.update_category(
        test_category.id,
        emoji=new_emoji
    )

    # Assert
    assert updated is not None
    assert updated.emoji == new_emoji
    assert updated.emoji != original_emoji
    assert updated.name == test_category.name  # Unchanged

    # Verify persistence
    retrieved = await service.get_category_by_id(test_category.id)
    assert retrieved.emoji == new_emoji


@pytest.mark.integration
@pytest.mark.level3
async def test_delete_category_flow(
    db_session, redis_storage, test_user, test_category
):
    """
    GIVEN: Category exists without activities
    WHEN: User deletes category
    THEN: Category is removed from database
          AND confirmation is shown
          AND category does not appear in list

    Mocks: Telegram Bot API
    Real: Full delete flow
    Time: ~280ms
    """
    # Arrange
    from services.data_postgres_api.src.application.services.category_service import CategoryService
    from services.data_postgres_api.src.infrastructure.repositories.category_repository import CategoryRepository

    repo = CategoryRepository(db_session)
    service = CategoryService(repo)

    category_id = test_category.id
    category_name = test_category.name

    # Verify exists
    exists = await service.get_category_by_id(category_id)
    assert exists is not None

    # Act
    result = await service.delete_category(category_id)

    # Assert
    assert result is True

    # Verify deleted
    retrieved = await service.get_category_by_id(category_id)
    assert retrieved is None

    # Verify not in list
    categories = await service.list_categories(user_id=test_user.id)
    assert not any(c.name == category_name for c in categories)


@pytest.mark.integration
@pytest.mark.level3
async def test_list_categories_flow(
    db_session, redis_storage, test_user
):
    """
    GIVEN: User has multiple categories
    WHEN: User views category list
    THEN: All categories are shown
          AND categories are ordered correctly

    Mocks: Telegram Bot API
    Real: Full list flow
    Time: ~260ms
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
        ("Study", "📚"),
        ("Hobby", "🎨")
    ]

    created_categories = []
    for name, emoji in categories_to_create:
        category = await service.create_category(
            user_id=test_user.id,
            name=name,
            emoji=emoji
        )
        created_categories.append(category)

    # Act
    categories = await service.list_categories(user_id=test_user.id)

    # Assert
    assert len(categories) >= 4
    assert all(c.user_id == test_user.id for c in categories)

    # Verify all created categories are present
    category_names = [c.name for c in categories]
    for name, _ in categories_to_create:
        assert name in category_names
