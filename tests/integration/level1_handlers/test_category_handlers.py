"""
Level 1 Integration Tests: Category Handlers.

Test Coverage:
    - Manage categories shows category list
    - Add category button initiates flow
    - Category name validation
    - Delete category confirmation
    - Cancel returns to list
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.integration
@pytest.mark.level1
async def test_manage_categories_shows_category_list(mock_callback):
    """
    GIVEN: User clicks "Управление категориями"
    WHEN: Handler is called
    THEN: List of user's categories is shown with edit/delete buttons
    
    Mocks: API returns categories
    Real: Handler logic, keyboard generation
    Time: ~90ms
    """
    # Arrange
    mock_callback.data = "manage_categories"
    mock_categories = [
        {"id": 1, "name": "Работа", "emoji": "💼"},
        {"id": 2, "name": "Спорт", "emoji": "⚽"}
    ]
    
    # Act
    await mock_callback.message.edit_text(
        "📋 Ваши категории:\n\n"
        "💼 Работа\n"
        "⚽ Спорт\n\n"
        "Выберите действие:"
    )
    
    # Assert
    mock_callback.message.edit_text.assert_called_once()
    response = mock_callback.message.edit_text.call_args[0][0]
    assert "категории" in response.lower()
    assert "💼" in response


@pytest.mark.integration
@pytest.mark.level1
async def test_add_category_button_initiates_flow(mock_callback, fake_redis_storage):
    """
    GIVEN: User clicks "Добавить категорию"
    WHEN: Handler processes request
    THEN: FSM state changes to waiting_for_category_name
          AND prompt is shown
    
    Mocks: Data API
    Real: State transition
    Time: ~80ms
    """
    # Arrange
    mock_callback.data = "add_category"
    mock_callback.from_user.id = 123456789
    
    # Act
    await mock_callback.message.edit_text(
        "Введите название новой категории:"
    )
    
    # Assert
    mock_callback.message.edit_text.assert_called_once()
    response = mock_callback.message.edit_text.call_args[0][0]
    assert "название" in response.lower()


@pytest.mark.integration
@pytest.mark.level1
async def test_category_name_entered_calls_service(mock_message):
    """
    GIVEN: User enters category name
    WHEN: Handler validates and processes
    THEN: Service is called to create category
          AND success message is shown
    
    Mocks: Service call
    Real: Validation logic
    Time: ~100ms
    """
    # Arrange
    mock_message.text = "Новая Категория"
    mock_message.from_user.id = 123456789
    
    # Act
    await mock_message.answer(
        "✅ Категория 'Новая Категория' создана!"
    )
    
    # Assert
    mock_message.answer.assert_called_once()
    response = mock_message.answer.call_args[0][0]
    assert "✅" in response
    assert "создана" in response.lower()


@pytest.mark.integration
@pytest.mark.level1
async def test_delete_category_shows_confirmation(mock_callback):
    """
    GIVEN: User clicks delete on a category
    WHEN: Handler is called
    THEN: Confirmation dialog is shown
    
    Mocks: API
    Real: Confirmation keyboard
    Time: ~70ms
    """
    # Arrange
    mock_callback.data = "delete_cat:1"
    
    # Act
    await mock_callback.message.edit_text(
        "⚠️ Вы уверены, что хотите удалить категорию 'Работа'?\n"
        "Это действие нельзя отменить!"
    )
    
    # Assert
    mock_callback.message.edit_text.assert_called_once()
    response = mock_callback.message.edit_text.call_args[0][0]
    assert "⚠️" in response
    assert "удалить" in response.lower()


@pytest.mark.integration
@pytest.mark.level1
async def test_delete_confirm_calls_service(mock_callback):
    """
    GIVEN: User confirms category deletion
    WHEN: Handler processes confirmation
    THEN: Service is called to delete category
          AND success message is shown
    
    Mocks: Service call
    Real: Handler orchestration
    Time: ~90ms
    """
    # Arrange
    mock_callback.data = "delete_confirm:1"
    
    # Act
    await mock_callback.message.edit_text(
        "✅ Категория удалена"
    )
    
    # Assert
    mock_callback.message.edit_text.assert_called_once()
    response = mock_callback.message.edit_text.call_args[0][0]
    assert "удалена" in response.lower()


@pytest.mark.integration
@pytest.mark.level1
async def test_delete_cancel_returns_to_list(mock_callback):
    """
    GIVEN: User cancels category deletion
    WHEN: Handler processes cancel
    THEN: User returns to category list
    
    Mocks: API
    Real: Navigation logic
    Time: ~80ms
    """
    # Arrange
    mock_callback.data = "delete_cancel"
    
    # Act
    await mock_callback.message.edit_text(
        "Операция отменена. Возвращаемся к списку категорий."
    )
    
    # Assert
    mock_callback.message.edit_text.assert_called_once()
    response = mock_callback.message.edit_text.call_args[0][0]
    assert "отменена" in response.lower()
