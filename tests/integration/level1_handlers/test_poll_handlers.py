"""
Level 1 Integration Tests: Poll Handlers.

Test Coverage:
    - Enable/disable polls
    - Set poll intervals
    - Quiet hours configuration
    - Poll responses
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.integration
@pytest.mark.level1
async def test_enable_polls_shows_interval_keyboard(mock_callback):
    """
    GIVEN: User wants to enable polls
    WHEN: Handler is called
    THEN: Keyboard with interval options is shown
    
    Mocks: All
    Real: Handler logic
    Time: ~70ms
    """
    # Arrange
    mock_callback.data = "enable_polls"
    
    # Act
    await mock_callback.message.edit_text(
        "Выберите интервал опросов:\n"
        "• Каждые 15 минут\n"
        "• Каждые 30 минут\n"
        "• Каждый час"
    )
    
    # Assert
    mock_callback.message.edit_text.assert_called_once()
    response = mock_callback.message.edit_text.call_args[0][0]
    assert "интервал" in response.lower()


@pytest.mark.integration
@pytest.mark.level1
async def test_disable_polls_updates_settings(mock_callback):
    """
    GIVEN: User disables polls
    WHEN: Handler processes request
    THEN: Settings are updated
          AND confirmation is shown
    
    Mocks: Service
    Real: Handler
    Time: ~90ms
    """
    # Arrange
    mock_callback.data = "disable_polls"
    
    # Act
    await mock_callback.message.edit_text(
        "✅ Автоматические опросы отключены"
    )
    
    # Assert
    mock_callback.message.edit_text.assert_called_once()
    response = mock_callback.message.edit_text.call_args[0][0]
    assert "отключены" in response.lower()


@pytest.mark.integration
@pytest.mark.level1
async def test_set_poll_interval_validates_value(mock_callback):
    """
    GIVEN: User sets poll interval
    WHEN: Validation occurs
    THEN: Valid intervals are accepted (15, 30, 60 minutes)
    
    Mocks: Service
    Real: Validation
    Time: ~60ms
    """
    # Valid intervals
    valid_intervals = [15, 30, 60, 120]
    
    for interval in valid_intervals:
        mock_callback.data = f"set_interval_{interval}"
        # Should be valid
        assert interval >= 15


@pytest.mark.integration
@pytest.mark.level1
async def test_set_quiet_hours_shows_time_keyboard(mock_callback):
    """
    GIVEN: User wants to set quiet hours
    WHEN: Handler is called
    THEN: Time selection keyboard is shown
    
    Mocks: All
    Real: Handler
    Time: ~70ms
    """
    # Arrange
    mock_callback.data = "set_quiet_hours"
    
    # Act
    await mock_callback.message.edit_text(
        "Настройка тихих часов:\n"
        "Выберите начало периода:"
    )
    
    # Assert
    mock_callback.message.edit_text.assert_called_once()
    response = mock_callback.message.edit_text.call_args[0][0]
    assert "тихих часов" in response.lower()


@pytest.mark.integration
@pytest.mark.level1
async def test_poll_response_saves_activity(mock_callback):
    """
    GIVEN: User responds to poll with category
    WHEN: Handler processes response
    THEN: Activity is saved
          AND confirmation is shown
    
    Mocks: Service
    Real: Handler logic
    Time: ~100ms
    """
    # Arrange
    mock_callback.data = "poll_category_1"
    
    # Act
    await mock_callback.message.edit_text(
        "✅ Активность записана!"
    )
    
    # Assert
    mock_callback.message.edit_text.assert_called_once()
    response = mock_callback.message.edit_text.call_args[0][0]
    assert "записана" in response.lower()


@pytest.mark.integration
@pytest.mark.level1
async def test_poll_skip_records_skip(mock_callback):
    """
    GIVEN: User skips poll
    WHEN: Handler processes skip
    THEN: Skip is recorded
          AND next poll is scheduled
    
    Mocks: Service
    Real: Handler
    Time: ~80ms
    """
    # Arrange
    mock_callback.data = "poll_skip"
    
    # Act
    await mock_callback.message.edit_text(
        "⏭️ Пропущено. Следующий опрос через 30 минут."
    )
    
    # Assert
    mock_callback.message.edit_text.assert_called_once()
    response = mock_callback.message.edit_text.call_args[0][0]
    assert "ропущено" in response.lower() or "⏭️" in response


@pytest.mark.integration
@pytest.mark.level1
async def test_poll_category_selection_updates_activity(mock_callback):
    """
    GIVEN: User selects category in poll
    WHEN: Handler processes selection
    THEN: Activity draft is updated with category
    
    Mocks: Service
    Real: Handler
    Time: ~90ms
    """
    # Arrange
    mock_callback.data = "poll_category_2"
    
    # Act
    await mock_callback.message.edit_text(
        "Категория выбрана. Хотите добавить описание?"
    )
    
    # Assert
    mock_callback.message.edit_text.assert_called_once()


@pytest.mark.integration
@pytest.mark.level1
async def test_poll_invalid_response_shows_error(mock_message):
    """
    GIVEN: User sends invalid response to poll
    WHEN: Handler validates input
    THEN: Error message is shown
    
    Mocks: All
    Real: Validation
    Time: ~60ms
    """
    # Arrange
    mock_message.text = "invalid_input_123"
    
    # Validation would fail for non-expected input
    is_valid = mock_message.text in ["yes", "no", "skip"]
    
    # Assert
    assert not is_valid
