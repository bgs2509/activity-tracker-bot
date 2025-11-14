"""
Unit tests for /start command handler.

Tests user onboarding flow including user creation, default categories,
settings initialization, and poll scheduling.

Test Coverage:
    - New user: creation, categories, settings, scheduling
    - Existing user: welcome back message
    - Existing user without settings: backward compatibility
    - Error handling: service failures
    - Message formatting: correct keyboard, text

Coverage Target: 100% of start.py
Execution Time: < 0.5 seconds

Author: Testing Team
Date: 2025-11-07
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram import types

from src.api.handlers.start import cmd_start
from src.api.dependencies import ServiceContainer


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def mock_message():
    """
    Fixture: Mock Telegram Message.

    Returns:
        MagicMock: Mocked message with typical fields
    """
    message = MagicMock(spec=types.Message)
    message.from_user = MagicMock(spec=types.User)
    message.from_user.id = 123456789
    message.from_user.username = "testuser"
    message.from_user.first_name = "Тест"
    message.answer = AsyncMock()
    message.bot = MagicMock()
    return message


@pytest.fixture
def mock_services():
    """
    Fixture: Mock ServiceContainer.

    Returns:
        MagicMock: Mocked service container with all services
    """
    services = MagicMock(spec=ServiceContainer)
    services.user = AsyncMock()
    services.category = AsyncMock()
    services.settings = AsyncMock()
    services.scheduler = AsyncMock()
    return services


@pytest.fixture
def sample_user():
    """
    Fixture: Sample user data.

    Returns:
        dict: User data returned from service
    """
    return {
        "id": 1,
        "telegram_id": 123456789,
        "username": "testuser",
        "first_name": "Тест",
        "timezone": "Europe/Moscow"
    }


@pytest.fixture
def sample_settings():
    """
    Fixture: Sample settings data.

    Returns:
        dict: Settings data returned from service
    """
    return {
        "id": 1,
        "user_id": 1,
        "weekday_interval_minutes": 120,
        "weekend_interval_minutes": 180,
        "is_reminder_enabled": True
    }


# ============================================================================
# TEST SUITES
# ============================================================================

class TestStartHandlerNewUser:
    """
    Test suite for /start command with new user.

    Tests complete onboarding flow.
    """

    @pytest.mark.unit
    async def test_start_command_with_new_user_creates_user_and_defaults(
        self,
        mock_message,
        mock_services,
        sample_user,
        sample_settings
    ):
        """
        Test new user onboarding.

        GIVEN: User does not exist in database
        WHEN: /start command is called
        THEN: User is created, categories, settings, poll scheduled
              AND welcome message is sent with keyboard
        """
        # Arrange: User does not exist
        mock_services.user.get_by_telegram_id.return_value = None
        mock_services.user.create_user.return_value = sample_user
        mock_services.settings.create_settings.return_value = sample_settings

        # Act
        with patch('src.api.handlers.start.send_automatic_poll'):
            await cmd_start(mock_message, mock_services)

        # Assert: User created
        mock_services.user.get_by_telegram_id.assert_called_once_with(123456789)
        mock_services.user.create_user.assert_called_once_with(
            123456789,
            "testuser",
            "Тест"
        )

        # Assert: Default categories created
        mock_services.category.bulk_create_categories.assert_called_once()
        call_args = mock_services.category.bulk_create_categories.call_args
        user_id = call_args[0][0]
        categories = call_args[0][1]

        assert user_id == 1
        assert len(categories) == 6
        assert any(cat["name"] == "Работа" and cat["emoji"] == "💼" for cat in categories)
        assert any(cat["name"] == "Спорт" and cat["emoji"] == "🏃" for cat in categories)
        assert any(cat["name"] == "Отдых" and cat["emoji"] == "🎮" for cat in categories)
        assert any(cat["name"] == "Обучение" and cat["emoji"] == "📚" for cat in categories)
        assert any(cat["name"] == "Сон" and cat["emoji"] == "😴" for cat in categories)
        assert any(cat["name"] == "Еда" and cat["emoji"] == "🍽️" for cat in categories)

        # Assert: Settings created
        mock_services.settings.create_settings.assert_called_once_with(1)

        # Assert: Poll scheduled
        mock_services.scheduler.schedule_poll.assert_called_once()
        schedule_call = mock_services.scheduler.schedule_poll.call_args
        assert schedule_call.kwargs["user_id"] == 123456789
        assert schedule_call.kwargs["settings"] == sample_settings
        assert schedule_call.kwargs["user_timezone"] == "Europe/Moscow"

    @pytest.mark.unit
    async def test_start_command_new_user_sends_welcome_message_with_instructions(
        self,
        mock_message,
        mock_services,
        sample_user,
        sample_settings
    ):
        """
        Test welcome message for new user.

        GIVEN: New user onboarding
        WHEN: /start completes
        THEN: Detailed welcome message with instructions sent
              AND main menu keyboard attached
        """
        # Arrange
        mock_services.user.get_by_telegram_id.return_value = None
        mock_services.user.create_user.return_value = sample_user
        mock_services.settings.create_settings.return_value = sample_settings

        # Act
        with patch('src.api.handlers.start.send_automatic_poll'):
            await cmd_start(mock_message, mock_services)

        # Assert: Two messages sent (welcome + menu)
        assert mock_message.answer.call_count == 2

        # Check first message (welcome with instructions)
        first_call = mock_message.answer.call_args_list[0]
        message_text = first_call[0][0]
        assert "Привет, Тест!" in message_text
        assert "отслеживать твою активность" in message_text
        assert "базовые категории" in message_text
        assert "💼 Работа" in message_text
        assert "автоматические опросы" in message_text
        assert "Будни: каждые 2 часа" in message_text
        assert "Тихие часы: 23:00 — 07:00" in message_text

        # Check first message has reply keyboard
        assert "reply_markup" in first_call[1]

        # Check second message (main menu)
        second_call = mock_message.answer.call_args_list[1]
        second_message_text = second_call[0][0]
        assert "🏠 Главное меню" in second_message_text

    @pytest.mark.unit
    async def test_start_command_new_user_uses_telegram_user_data(
        self,
        mock_message,
        mock_services,
        sample_user,
        sample_settings
    ):
        """
        Test user data extraction from Telegram.

        GIVEN: Telegram message with user info
        WHEN: User is created
        THEN: Telegram ID, username, first_name are used
        """
        # Arrange
        mock_message.from_user.id = 987654321
        mock_message.from_user.username = "john_doe"
        mock_message.from_user.first_name = "John"

        mock_services.user.get_by_telegram_id.return_value = None
        mock_services.user.create_user.return_value = sample_user
        mock_services.settings.create_settings.return_value = sample_settings

        # Act
        with patch('src.api.handlers.start.send_automatic_poll'):
            await cmd_start(mock_message, mock_services)

        # Assert: Correct data passed
        mock_services.user.create_user.assert_called_once_with(
            987654321,
            "john_doe",
            "John"
        )


class TestStartHandlerExistingUser:
    """
    Test suite for /start command with existing user.

    Tests returning user flow.
    """

    @pytest.mark.unit
    async def test_start_command_with_existing_user_sends_welcome_back_message(
        self,
        mock_message,
        mock_services,
        sample_user,
        sample_settings
    ):
        """
        Test welcome back message.

        GIVEN: User already exists with settings
        WHEN: /start command is called
        THEN: Short welcome back message sent
              AND no user/category creation
        """
        # Arrange: User exists
        mock_services.user.get_by_telegram_id.return_value = sample_user
        mock_services.settings.get_settings.return_value = sample_settings

        # Act
        with patch('src.api.handlers.start.get_main_menu_keyboard') as mock_keyboard:
            mock_keyboard.return_value = MagicMock()
            await cmd_start(mock_message, mock_services)

        # Assert: No user creation
        mock_services.user.create_user.assert_not_called()
        mock_services.category.bulk_create_categories.assert_not_called()

        # Assert: Welcome back message
        # Note: First call is welcome message, second call is main menu
        assert mock_message.answer.call_count == 2

        # Check first message (welcome)
        first_call_text = mock_message.answer.call_args_list[0][0][0]
        assert "С возвращением, Тест!" in first_call_text

        # Check second message (main menu)
        second_call_text = mock_message.answer.call_args_list[1][0][0]
        assert "🏠 Главное меню" in second_call_text

        # Should be shorter message (no detailed instructions)
        assert "отслеживать твою активность" not in first_call_text

    @pytest.mark.unit
    async def test_start_command_existing_user_does_not_create_settings(
        self,
        mock_message,
        mock_services,
        sample_user,
        sample_settings
    ):
        """
        Test existing user with settings.

        GIVEN: User has existing settings
        WHEN: /start is called
        THEN: Settings creation is skipped
              AND no poll scheduling
        """
        # Arrange
        mock_services.user.get_by_telegram_id.return_value = sample_user
        mock_services.settings.get_settings.return_value = sample_settings

        # Act
        with patch('src.api.handlers.start.get_main_menu_keyboard'):
            await cmd_start(mock_message, mock_services)

        # Assert: No settings creation
        mock_services.settings.create_settings.assert_not_called()
        mock_services.scheduler.schedule_poll.assert_not_called()

    @pytest.mark.unit
    async def test_start_command_existing_user_without_settings_creates_them(
        self,
        mock_message,
        mock_services,
        sample_user,
        sample_settings
    ):
        """
        Test backward compatibility.

        GIVEN: Existing user without settings (old user)
        WHEN: /start is called
        THEN: Settings are created and poll scheduled
              (Backward compatibility for users created before settings feature)
        """
        # Arrange: User exists but no settings
        mock_services.user.get_by_telegram_id.return_value = sample_user
        mock_services.settings.get_settings.return_value = None
        mock_services.settings.create_settings.return_value = sample_settings

        # Act
        with patch('src.api.handlers.start.send_automatic_poll'):
            with patch('src.api.handlers.start.get_main_menu_keyboard'):
                await cmd_start(mock_message, mock_services)

        # Assert: Settings created for existing user
        mock_services.settings.create_settings.assert_called_once_with(1)

        # Assert: Poll scheduled
        mock_services.scheduler.schedule_poll.assert_called_once()


class TestStartHandlerEdgeCases:
    """
    Test suite for edge cases and error scenarios.
    """

    @pytest.mark.unit
    async def test_start_command_with_user_without_username(
        self,
        mock_message,
        mock_services,
        sample_user,
        sample_settings
    ):
        """
        Test user without Telegram username.

        GIVEN: Telegram user without username (None)
        WHEN: /start is called
        THEN: User created with username=None
        """
        # Arrange: User without username
        mock_message.from_user.username = None

        mock_services.user.get_by_telegram_id.return_value = None
        mock_services.user.create_user.return_value = sample_user
        mock_services.settings.create_settings.return_value = sample_settings

        # Act
        with patch('src.api.handlers.start.send_automatic_poll'):
            await cmd_start(mock_message, mock_services)

        # Assert: None passed for username
        mock_services.user.create_user.assert_called_once_with(
            123456789,
            None,  # No username
            "Тест"
        )

    @pytest.mark.unit
    async def test_start_command_with_user_without_first_name(
        self,
        mock_message,
        mock_services,
        sample_user,
        sample_settings
    ):
        """
        Test user without first name.

        GIVEN: Telegram user without first_name
        WHEN: /start is called
        THEN: User created with first_name=None
        """
        # Arrange
        mock_message.from_user.first_name = None

        mock_services.user.get_by_telegram_id.return_value = None
        mock_services.user.create_user.return_value = sample_user
        mock_services.settings.create_settings.return_value = sample_settings

        # Act
        with patch('src.api.handlers.start.send_automatic_poll'):
            await cmd_start(mock_message, mock_services)

        # Assert
        mock_services.user.create_user.assert_called_once_with(
            123456789,
            "testuser",
            None  # No first name
        )

    @pytest.mark.unit
    async def test_start_command_uses_default_timezone_if_missing(
        self,
        mock_message,
        mock_services,
        sample_settings
    ):
        """
        Test default timezone handling.

        GIVEN: User data without timezone field
        WHEN: Poll is scheduled
        THEN: Default "Europe/Moscow" is used
        """
        # Arrange: User without timezone
        user_without_tz = {
            "id": 1,
            "telegram_id": 123456789,
            "username": "testuser"
            # No "timezone" field
        }

        mock_services.user.get_by_telegram_id.return_value = None
        mock_services.user.create_user.return_value = user_without_tz
        mock_services.settings.create_settings.return_value = sample_settings

        # Act
        with patch('src.api.handlers.start.send_automatic_poll'):
            await cmd_start(mock_message, mock_services)

        # Assert: Default timezone used
        schedule_call = mock_services.scheduler.schedule_poll.call_args
        assert schedule_call.kwargs["user_timezone"] == "Europe/Moscow"

    @pytest.mark.unit
    async def test_start_command_all_default_categories_marked_as_default(
        self,
        mock_message,
        mock_services,
        sample_user,
        sample_settings
    ):
        """
        Test default category flag.

        GIVEN: New user creation
        WHEN: Default categories are created
        THEN: All have is_default=True flag
        """
        # Arrange
        mock_services.user.get_by_telegram_id.return_value = None
        mock_services.user.create_user.return_value = sample_user
        mock_services.settings.create_settings.return_value = sample_settings

        # Act
        with patch('src.api.handlers.start.send_automatic_poll'):
            await cmd_start(mock_message, mock_services)

        # Assert: All categories have is_default=True
        call_args = mock_services.category.bulk_create_categories.call_args
        categories = call_args[0][1]

        for cat in categories:
            assert cat.get("is_default") is True, \
                f"Category {cat['name']} should have is_default=True"
