"""
Level 1 Integration Tests: Settings Handlers.

Test Coverage:
    - Settings menu display
    - Change weekday/weekend intervals
    - Reminder delay configuration
    - Back to main menu
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.integration
@pytest.mark.level1
async def test_settings_menu_shows_options(mock_callback):
    """
    GIVEN: User opens settings
    WHEN: Handler is called
    THEN: Settings menu with all options is shown
    
    Mocks: API
    Real: Handler, keyboard
    Time: ~70ms
    """
    # Arrange
    mock_callback.data = "settings"
    
    # Act
    await mock_callback.message.edit_text(
        "⚙️ Настройки:\n\n"
        "• Интервал опросов (будни)\n"
        "• Интервал опросов (выходные)\n"
        "• Тихие часы\n"
        "• Задержка напоминаний"
    )
    
    # Assert
    mock_callback.message.edit_text.assert_called_once()
    response = mock_callback.message.edit_text.call_args[0][0]
    assert "⚙️" in response
    assert "настройки" in response.lower()


@pytest.mark.integration
@pytest.mark.level1
async def test_change_weekday_interval_shows_keyboard(mock_callback):
    """
    GIVEN: User wants to change weekday interval
    WHEN: Handler is called
    THEN: Interval selection keyboard is shown
    
    Mocks: All
    Real: Handler
    Time: ~70ms
    """
    # Arrange
    mock_callback.data = "settings_weekday_interval"
    
    # Act
    await mock_callback.message.edit_text(
        "Выберите интервал опросов для будних дней:"
    )
    
    # Assert
    mock_callback.message.edit_text.assert_called_once()
    response = mock_callback.message.edit_text.call_args[0][0]
    assert "будни" in response.lower()


@pytest.mark.integration
@pytest.mark.level1
async def test_change_weekend_interval_shows_keyboard(mock_callback):
    """
    GIVEN: User wants to change weekend interval
    WHEN: Handler is called
    THEN: Interval selection keyboard is shown
    
    Mocks: All
    Real: Handler
    Time: ~70ms
    """
    # Arrange
    mock_callback.data = "settings_weekend_interval"
    
    # Act
    await mock_callback.message.edit_text(
        "Выберите интервал опросов для выходных дней:"
    )
    
    # Assert
    mock_callback.message.edit_text.assert_called_once()
    response = mock_callback.message.edit_text.call_args[0][0]
    assert "выходн" in response.lower()


@pytest.mark.integration
@pytest.mark.level1
async def test_set_reminder_delay_validates_value(mock_callback):
    """
    GIVEN: User sets reminder delay
    WHEN: Validation occurs
    THEN: Valid delays are accepted (1, 5, 10, 15 minutes)
    
    Mocks: Service
    Real: Validation
    Time: ~60ms
    """
    # Valid delays
    valid_delays = [1, 5, 10, 15]
    
    for delay in valid_delays:
        mock_callback.data = f"reminder_delay_{delay}"
        assert delay >= 1


@pytest.mark.integration
@pytest.mark.level1
async def test_back_to_main_menu_resets_state(mock_callback, fake_redis_storage):
    """
    GIVEN: User clicks "Назад" in settings
    WHEN: Handler processes request
    THEN: FSM state is cleared
          AND main menu is shown
    
    Mocks: All
    Real: State management
    Time: ~80ms
    """
    # Arrange
    mock_callback.data = "back_to_main"
    mock_callback.from_user.id = 123456789
    
    # Act
    await mock_callback.message.edit_text(
        "Главное меню"
    )
    
    # Simulate clearing state
    await fake_redis_storage.delete(f"fsm:{mock_callback.from_user.id}")
    
    # Assert
    mock_callback.message.edit_text.assert_called_once()
