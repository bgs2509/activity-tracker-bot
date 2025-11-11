"""
Unit tests for category handlers.

Tests category management including list view, creation FSM flow,
and deletion FSM flow.

Test Coverage:
    - show_categories_list: Display user's categories
    - add_category_start: Start creation FSM
    - add_category_name: Name validation and saving
    - add_category_emoji_button: Emoji selection via buttons
    - add_category_emoji_text: Emoji input via text
    - create_category_final: Database save with duplicate handling
    - cancel_category_fsm: Cancel creation flow
    - delete_category_select: Category selection for deletion
    - delete_category_confirm: Deletion confirmation
    - delete_category_execute: Execute deletion with validation

Coverage Target: 100% of category handlers
Execution Time: < 0.6 seconds

Author: Testing Team
Date: 2025-11-07
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram import types
from aiogram.fsm.context import FSMContext
import httpx

from src.api.handlers.categories.category_list import (
    show_categories_list
)
# Note: main_menu handler is in src.api.handlers.settings.main_menu, not here
from src.api.handlers.categories.category_creation import (
    add_category_start,
    add_category_name,
    add_category_emoji_button,
    add_category_emoji_text,
    create_category_final,
    cancel_category_fsm
)
from src.api.handlers.categories.category_deletion import (
    delete_category_select,
    delete_category_confirm,
    delete_category_execute
)
from src.api.states.category import CategoryStates


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def mock_callback():
    """Fixture: Mock Telegram CallbackQuery."""
    callback = MagicMock(spec=types.CallbackQuery)
    callback.from_user = MagicMock(spec=types.User)
    callback.from_user.id = 123456789
    callback.from_user.username = "testuser"
    callback.message = MagicMock(spec=types.Message)
    callback.message.chat = MagicMock()
    callback.message.chat.id = 123456789
    callback.message.answer = AsyncMock()
    callback.message.edit_text = AsyncMock()
    callback.answer = AsyncMock()
    callback.bot = MagicMock()
    callback.bot.send_chat_action = AsyncMock()
    callback.data = ""
    return callback


@pytest.fixture
def mock_message():
    """Fixture: Mock Telegram Message."""
    message = MagicMock(spec=types.Message)
    message.from_user = MagicMock(spec=types.User)
    message.from_user.id = 123456789
    message.from_user.username = "testuser"
    message.answer = AsyncMock()
    message.bot = MagicMock()
    message.text = "Test category"
    return message


@pytest.fixture
def mock_state():
    """Fixture: Mock FSM context."""
    state = AsyncMock(spec=FSMContext)
    state.get_data = AsyncMock(return_value={})
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()
    state.clear = AsyncMock()
    state.get_state = AsyncMock(return_value=None)
    return state


@pytest.fixture
def mock_services():
    """Fixture: Mock ServiceContainer."""
    services = MagicMock()
    services.user = AsyncMock()
    services.category = AsyncMock()
    return services


@pytest.fixture
def sample_user():
    """Fixture: Sample user data."""
    return {
        "id": 1,
        "telegram_id": 123456789,
        "username": "testuser"
    }


@pytest.fixture
def sample_categories():
    """Fixture: Sample categories list."""
    return [
        {"id": 1, "name": "Work", "emoji": "💼"},
        {"id": 2, "name": "Sport", "emoji": "🏃"},
        {"id": 3, "name": "Hobby", "emoji": "🎨"}
    ]


# ============================================================================
# TEST SUITES: CATEGORY LIST
# ============================================================================

class TestShowCategoriesList:
    """Test suite for show_categories_list handler."""

    @pytest.mark.unit
    async def test_show_categories_list_with_categories_displays_list(
        self,
        mock_callback,
        mock_services,
        sample_user,
        sample_categories
    ):
        """
        Test category list display.

        GIVEN: User has categories
        WHEN: show_categories_list is called
        THEN: Categories are listed with emojis
        """
        # Arrange
        mock_services.user.get_by_telegram_id.return_value = sample_user
        mock_services.category.get_user_categories.return_value = sample_categories

        # Act - pass services as keyword argument for @require_user decorator
        await show_categories_list(mock_callback, services=mock_services)

        # Assert: Categories fetched
        mock_services.category.get_user_categories.assert_called_once_with(1)

        # Assert: Message edited with list
        mock_callback.message.edit_text.assert_called_once()
        message_text = mock_callback.message.edit_text.call_args[0][0]
        assert "Твои категории" in message_text
        assert "💼 Work" in message_text
        assert "🏃 Sport" in message_text
        assert "🎨 Hobby" in message_text

        # Assert: Callback answered
        mock_callback.answer.assert_called_once()

    @pytest.mark.unit
    async def test_show_categories_list_with_empty_list_shows_header(
        self,
        mock_callback,
        mock_services,
        sample_user
    ):
        """
        Test empty category list.

        GIVEN: User has no categories
        WHEN: show_categories_list is called
        THEN: Only header is shown
        """
        # Arrange
        mock_services.user.get_by_telegram_id.return_value = sample_user
        mock_services.category.get_user_categories.return_value = []

        # Act - pass services as keyword argument for @require_user decorator
        await show_categories_list(mock_callback, services=mock_services)

        # Assert: Message edited
        mock_callback.message.edit_text.assert_called_once()
        message_text = mock_callback.message.edit_text.call_args[0][0]
        assert "Твои категории" in message_text


# Commented out: main_menu handler moved to src.api.handlers.settings.main_menu
# and is tested in test_settings_handlers.py
#
# class TestShowMainMenu:
#     """Test suite for show_main_menu handler."""
#
#     @pytest.mark.unit
#     async def test_show_main_menu_returns_to_menu(
#         self,
#         mock_callback
#     ):
#         """
#         Test main menu navigation.
#
#         GIVEN: User clicks main menu button
#         WHEN: show_main_menu is called
#         THEN: Main menu is shown
#         """
#         # Act
#         await show_main_menu(mock_callback)
#
#         # Assert: Main menu shown
#         mock_callback.message.edit_text.assert_called_once()
#         message_text = mock_callback.message.edit_text.call_args[0][0]
#         assert "Выбери действие" in message_text


# ============================================================================
# TEST SUITES: CATEGORY CREATION
# ============================================================================

class TestAddCategoryStart:
    """Test suite for add_category_start handler."""

    @pytest.mark.unit
    async def test_add_category_start_sets_state_and_prompts_for_name(
        self,
        mock_callback,
        mock_state
    ):
        """
        Test category creation initiation.

        GIVEN: User starts category creation
        WHEN: add_category_start is called
        THEN: FSM state is set to waiting_for_name
              AND name prompt is shown
        """
        # Arrange
        with patch('src.api.handlers.categories.category_creation.fsm_timeout_module'):
            # Act
            await add_category_start(mock_callback, mock_state)

        # Assert: State set
        mock_state.set_state.assert_called_once_with(CategoryStates.waiting_for_name)

        # Assert: Prompt shown
        mock_callback.message.edit_text.assert_called_once()
        message_text = mock_callback.message.edit_text.call_args[0][0]
        assert "название новой категории" in message_text
        assert "Минимум 2 символа" in message_text

        # Assert: Callback answered
        mock_callback.answer.assert_called_once()


class TestAddCategoryName:
    """Test suite for add_category_name handler."""

    @pytest.mark.unit
    async def test_add_category_name_with_valid_name_saves_and_prompts_emoji(
        self,
        mock_message,
        mock_state
    ):
        """
        Test valid category name processing.

        GIVEN: User inputs valid category name
        WHEN: add_category_name is called
        THEN: Name is saved to state
              AND emoji selection prompt shown
        """
        # Arrange
        mock_message.text = "Hobby"

        with patch('src.api.handlers.categories.category_creation.validate_category_name') as mock_validate:
            mock_validate.return_value = None  # No error

            with patch('src.api.handlers.categories.category_creation.fsm_timeout_module'):
                # Act
                await add_category_name(mock_message, mock_state)

        # Assert: Name saved
        mock_state.update_data.assert_called_once_with(category_name="Hobby")

        # Assert: State changed to emoji
        mock_state.set_state.assert_called_once_with(CategoryStates.waiting_for_emoji)

        # Assert: Emoji prompt shown
        mock_message.answer.assert_called_once()
        message_text = mock_message.answer.call_args[0][0]
        assert "Выбери эмодзи" in message_text
        assert "Hobby" in message_text

    @pytest.mark.unit
    async def test_add_category_name_with_invalid_name_shows_error(
        self,
        mock_message,
        mock_state
    ):
        """
        Test invalid category name validation.

        GIVEN: User inputs invalid name (e.g., too short)
        WHEN: add_category_name is called
        THEN: Error message shown
              AND state not changed
        """
        # Arrange
        mock_message.text = "A"  # Too short

        with patch('src.api.handlers.categories.category_creation.validate_category_name') as mock_validate:
            mock_validate.return_value = "⚠️ Название должно быть от 2 до 50 символов"

            # Act
            await add_category_name(mock_message, mock_state)

        # Assert: Error shown
        mock_message.answer.assert_called_once()
        message_text = mock_message.answer.call_args[0][0]
        assert "должно быть от 2 до 50 символов" in message_text

        # Assert: State not changed
        mock_state.set_state.assert_not_called()


class TestAddCategoryEmojiButton:
    """Test suite for add_category_emoji_button handler."""

    @pytest.mark.unit
    async def test_add_category_emoji_button_with_emoji_creates_category(
        self,
        mock_callback,
        mock_state,
        mock_services
    ):
        """
        Test emoji selection via button.

        GIVEN: User selects emoji from keyboard
        WHEN: add_category_emoji_button is called
        THEN: Category is created with selected emoji
        """
        # Arrange
        mock_callback.data = "emoji:🎨"
        mock_state.get_data.return_value = {"category_name": "Hobby"}

        with patch('src.api.handlers.categories.category_creation.validate_emoji') as mock_validate:
            mock_validate.return_value = None  # No error

            with patch('src.api.handlers.categories.category_creation.create_category_final') as mock_create:
                with patch('src.api.handlers.categories.category_creation.fsm_timeout_module'):
                    # Act
                    await add_category_emoji_button(mock_callback, mock_state, mock_services)

        # Assert: Category creation initiated
        mock_create.assert_called_once()
        assert mock_create.call_args[0][2] == "🎨"  # emoji argument

        # Assert: State cleared
        mock_state.clear.assert_called_once()

    @pytest.mark.unit
    async def test_add_category_emoji_button_with_no_emoji_creates_category_without_emoji(
        self,
        mock_callback,
        mock_state,
        mock_services
    ):
        """
        Test "No emoji" option.

        GIVEN: User selects "No emoji" button
        WHEN: add_category_emoji_button is called
        THEN: Category is created without emoji
        """
        # Arrange
        mock_callback.data = "emoji:none"

        with patch('src.api.handlers.categories.category_creation.validate_emoji') as mock_validate:
            mock_validate.return_value = None

            with patch('src.api.handlers.categories.category_creation.create_category_final') as mock_create:
                with patch('src.api.handlers.categories.category_creation.fsm_timeout_module'):
                    # Act
                    await add_category_emoji_button(mock_callback, mock_state, mock_services)

        # Assert: Category created with None emoji
        mock_create.assert_called_once()
        assert mock_create.call_args[0][2] is None


class TestAddCategoryEmojiText:
    """Test suite for add_category_emoji_text handler."""

    @pytest.mark.unit
    async def test_add_category_emoji_text_with_valid_emoji_creates_category(
        self,
        mock_message,
        mock_state,
        mock_services
    ):
        """
        Test emoji input via text.

        GIVEN: User sends emoji as text message
        WHEN: add_category_emoji_text is called
        THEN: Category is created with emoji
        """
        # Arrange
        mock_message.text = "🚀"

        with patch('src.api.handlers.categories.category_creation.validate_emoji') as mock_validate:
            mock_validate.return_value = None

            with patch('src.api.handlers.categories.category_creation.create_category_final') as mock_create:
                with patch('src.api.handlers.categories.category_creation.fsm_timeout_module'):
                    # Act
                    await add_category_emoji_text(mock_message, mock_state, mock_services)

        # Assert: Category creation initiated
        mock_create.assert_called_once()
        assert mock_create.call_args[0][2] == "🚀"

    @pytest.mark.unit
    async def test_add_category_emoji_text_with_invalid_emoji_shows_error(
        self,
        mock_message,
        mock_state,
        mock_services
    ):
        """
        Test emoji validation.

        GIVEN: User sends text too long for emoji
        WHEN: add_category_emoji_text is called
        THEN: Validation error is shown
        """
        # Arrange
        mock_message.text = "a" * 20  # Too long

        with patch('src.api.handlers.categories.category_creation.validate_emoji') as mock_validate:
            mock_validate.return_value = "⚠️ Эмодзи не может быть длиннее 10 символов"

            # Act
            await add_category_emoji_text(mock_message, mock_state, mock_services)

        # Assert: Error shown
        mock_message.answer.assert_called_once()
        message_text = mock_message.answer.call_args[0][0]
        assert "длиннее 10 символов" in message_text


class TestCreateCategoryFinal:
    """Test suite for create_category_final helper function."""

    @pytest.mark.unit
    async def test_create_category_final_with_valid_data_creates_category(
        self,
        mock_message,
        mock_state,
        mock_services,
        sample_user
    ):
        """
        Test successful category creation.

        GIVEN: Valid name and emoji in state
        WHEN: create_category_final is called
        THEN: Category is created in database
              AND success message shown
        """
        # Arrange
        mock_state.get_data.return_value = {"category_name": "Hobby"}
        mock_services.user.get_by_telegram_id.return_value = sample_user
        mock_services.category.create_category.return_value = {
            "id": 10,
            "name": "Hobby",
            "emoji": "🎨"
        }

        # Act
        await create_category_final(
            123456789,
            mock_state,
            "🎨",
            mock_message,
            mock_services
        )

        # Assert: Category created
        mock_services.category.create_category.assert_called_once()
        call_kwargs = mock_services.category.create_category.call_args.kwargs
        assert call_kwargs["user_id"] == 1
        assert call_kwargs["name"] == "Hobby"
        assert call_kwargs["emoji"] == "🎨"
        assert call_kwargs["is_default"] is False

        # Assert: Success message
        mock_message.answer.assert_called_once()
        message_text = mock_message.answer.call_args[0][0]
        assert "успешно добавлена" in message_text
        assert "Hobby" in message_text

    @pytest.mark.unit
    async def test_create_category_final_with_duplicate_name_shows_error(
        self,
        mock_message,
        mock_state,
        mock_services,
        sample_user
    ):
        """
        Test duplicate category handling.

        GIVEN: Category with same name exists
        WHEN: create_category_final is called
        THEN: 409 conflict error is handled
              AND user is prompted to enter different name
        """
        # Arrange
        mock_state.get_data.return_value = {"category_name": "Work"}
        mock_services.user.get_by_telegram_id.return_value = sample_user

        # Create HTTPStatusError for 409
        response = MagicMock()
        response.status_code = 409
        error = httpx.HTTPStatusError("Conflict", request=MagicMock(), response=response)
        mock_services.category.create_category.side_effect = error

        with patch('src.api.handlers.categories.category_creation.fsm_timeout_module'):
            # Act
            await create_category_final(
                123456789,
                mock_state,
                "💼",
                mock_message,
                mock_services
            )

        # Assert: Error message shown
        mock_message.answer.assert_called_once()
        message_text = mock_message.answer.call_args[0][0]
        assert "уже существует" in message_text

        # Assert: State reset to name input
        mock_state.set_state.assert_called_once_with(CategoryStates.waiting_for_name)

    @pytest.mark.unit
    async def test_create_category_final_with_user_not_found_shows_error(
        self,
        mock_message,
        mock_state,
        mock_services
    ):
        """
        Test user not found handling.

        GIVEN: User does not exist
        WHEN: create_category_final is called
        THEN: Error message shown
        """
        # Arrange
        mock_services.user.get_by_telegram_id.return_value = None

        # Act
        await create_category_final(
            123456789,
            mock_state,
            "🎨",
            mock_message,
            mock_services
        )

        # Assert: Error message
        mock_message.answer.assert_called_once()
        message_text = mock_message.answer.call_args[0][0]
        assert "не найден" in message_text


class TestCancelCategoryFsm:
    """Test suite for cancel_category_fsm handler."""

    @pytest.mark.unit
    async def test_cancel_category_fsm_with_active_state_cancels(
        self,
        mock_message,
        mock_state
    ):
        """
        Test /cancel command with active category FSM.

        GIVEN: User is in CategoryStates
        WHEN: /cancel command is issued
        THEN: State is cleared and message shown
        """
        # Arrange
        mock_state.get_state.return_value = "CategoryStates:waiting_for_name"

        with patch('src.api.handlers.categories.category_creation.fsm_timeout_module'):
            # Act
            await cancel_category_fsm(mock_message, mock_state)

        # Assert: State cleared
        mock_state.clear.assert_called_once()

        # Assert: Cancellation message
        mock_message.answer.assert_called_once()
        message_text = mock_message.answer.call_args[0][0]
        assert "отменено" in message_text

    @pytest.mark.unit
    async def test_cancel_category_fsm_without_state_shows_nothing_to_cancel(
        self,
        mock_message,
        mock_state
    ):
        """
        Test /cancel without active FSM.

        GIVEN: User is not in category FSM
        WHEN: /cancel is issued
        THEN: "Nothing to cancel" message shown
        """
        # Arrange
        mock_state.get_state.return_value = None

        # Act
        await cancel_category_fsm(mock_message, mock_state)

        # Assert: Nothing to cancel message
        mock_message.answer.assert_called_once()
        message_text = mock_message.answer.call_args[0][0]
        assert "Нечего отменять" in message_text


# ============================================================================
# TEST SUITES: CATEGORY DELETION
# ============================================================================

class TestDeleteCategorySelect:
    """Test suite for delete_category_select handler."""

    @pytest.mark.unit
    async def test_delete_category_select_shows_category_list(
        self,
        mock_callback,
        mock_services,
        sample_user,
        sample_categories
    ):
        """
        Test category deletion selection.

        GIVEN: User has categories
        WHEN: delete_category_select is called
        THEN: Category list with delete buttons shown
        """
        # Arrange
        mock_services.user.get_by_telegram_id.return_value = sample_user
        mock_services.category.get_user_categories.return_value = sample_categories

        # Act
        await delete_category_select(mock_callback, mock_services)

        # Assert: Categories fetched
        mock_services.category.get_user_categories.assert_called_once_with(1)

        # Assert: Selection message shown
        mock_callback.message.edit_text.assert_called_once()
        message_text = mock_callback.message.edit_text.call_args[0][0]
        assert "Выбери категорию для удаления" in message_text


class TestDeleteCategoryConfirm:
    """Test suite for delete_category_confirm handler."""

    @pytest.mark.unit
    async def test_delete_category_confirm_shows_confirmation_dialog(
        self,
        mock_callback,
        mock_services,
        sample_user,
        sample_categories
    ):
        """
        Test deletion confirmation.

        GIVEN: User selects category to delete
        WHEN: delete_category_confirm is called
        THEN: Confirmation dialog shown with warning
        """
        # Arrange
        mock_callback.data = "delete_cat:1"
        mock_services.user.get_by_telegram_id.return_value = sample_user
        mock_services.category.get_user_categories.return_value = sample_categories

        # Act
        await delete_category_confirm(mock_callback, mock_services)

        # Assert: Confirmation shown
        mock_callback.message.edit_text.assert_called_once()
        message_text = mock_callback.message.edit_text.call_args[0][0]
        assert "уверен" in message_text
        assert "Work" in message_text
        assert "💼" in message_text


class TestDeleteCategoryExecute:
    """Test suite for delete_category_execute handler."""

    @pytest.mark.unit
    async def test_delete_category_execute_with_valid_category_deletes(
        self,
        mock_callback,
        mock_services,
        sample_user,
        sample_categories
    ):
        """
        Test successful category deletion.

        GIVEN: User confirms deletion
        WHEN: delete_category_execute is called
        THEN: Category is deleted
              AND success message shown
        """
        # Arrange
        mock_callback.data = "delete_confirm:1"
        mock_services.user.get_by_telegram_id.return_value = sample_user
        mock_services.category.get_user_categories.return_value = sample_categories
        mock_services.category.delete_category.return_value = None

        # Act
        await delete_category_execute(mock_callback, mock_services)

        # Assert: Category deleted
        mock_services.category.delete_category.assert_called_once_with(1)

        # Assert: Success message
        mock_callback.message.edit_text.assert_called_once()
        message_text = mock_callback.message.edit_text.call_args[0][0]
        assert "удалена" in message_text
        assert "Work" in message_text

    @pytest.mark.unit
    async def test_delete_category_execute_with_last_category_shows_error(
        self,
        mock_callback,
        mock_services,
        sample_user,
        sample_categories
    ):
        """
        Test deleting last category protection.

        GIVEN: Attempting to delete last category
        WHEN: delete_category_execute is called
        THEN: ValueError is caught
              AND warning message shown
        """
        # Arrange
        mock_callback.data = "delete_confirm:1"
        mock_services.user.get_by_telegram_id.return_value = sample_user
        mock_services.category.get_user_categories.return_value = sample_categories
        mock_services.category.delete_category.side_effect = ValueError("Cannot delete last category")

        # Act
        await delete_category_execute(mock_callback, mock_services)

        # Assert: Warning message
        mock_callback.message.edit_text.assert_called_once()
        message_text = mock_callback.message.edit_text.call_args[0][0]
        assert "Нельзя удалить последнюю категорию" in message_text

    @pytest.mark.unit
    async def test_delete_category_execute_with_http_error_shows_alert(
        self,
        mock_callback,
        mock_services,
        sample_user,
        sample_categories
    ):
        """
        Test HTTP error handling.

        GIVEN: Service raises HTTPStatusError
        WHEN: delete_category_execute is called
        THEN: Error alert is shown
        """
        # Arrange
        mock_callback.data = "delete_confirm:1"
        mock_services.user.get_by_telegram_id.return_value = sample_user
        mock_services.category.get_user_categories.return_value = sample_categories

        response = MagicMock()
        response.status_code = 500
        error = httpx.HTTPStatusError("Server error", request=MagicMock(), response=response)
        mock_services.category.delete_category.side_effect = error

        # Act
        await delete_category_execute(mock_callback, mock_services)

        # Assert: Error alert shown
        mock_callback.answer.assert_called()
        call_kwargs = mock_callback.answer.call_args.kwargs
        assert "show_alert" in call_kwargs
