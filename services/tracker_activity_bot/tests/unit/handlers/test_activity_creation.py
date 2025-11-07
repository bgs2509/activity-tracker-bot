"""
Unit tests for activity creation handlers.

Tests FSM flow for creating new activities including:
- Start time input (text and quick buttons)
- End time input (text and quick buttons)
- Description input with tag extraction
- Category selection
- Activity saving

Test Coverage:
    - start_add_activity: FSM initiation
    - process_start_time: Text input parsing and validation
    - quick_start_time: Quick time button handlers
    - process_end_time: End time parsing with duration
    - quick_end_time: Quick duration buttons
    - process_description: Description validation and tag extraction
    - process_category_callback: Category selection
    - cancel_category_selection: Cancel flow
    - process_category: Skip category with "0"
    - save_activity: Database save with all validations

Coverage Target: 100% of activity_creation.py
Execution Time: < 1.0 seconds

Author: Testing Team
Date: 2025-11-07
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram import types
from aiogram.fsm.context import FSMContext

from src.api.handlers.activity.activity_creation import (
    start_add_activity,
    process_start_time,
    quick_start_time,
    process_end_time,
    quick_end_time,
    process_description,
    process_category_callback,
    cancel_category_selection,
    process_category,
    save_activity
)
from src.api.states.activity import ActivityStates


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
    callback.message.answer = AsyncMock()
    callback.answer = AsyncMock()
    callback.bot = MagicMock()
    callback.data = ""
    return callback


@pytest.fixture
def mock_message():
    """Fixture: Mock Telegram Message."""
    message = MagicMock(spec=types.Message)
    message.from_user = MagicMock(spec=types.User)
    message.from_user.id = 123456789
    message.answer = AsyncMock()
    message.bot = MagicMock()
    message.text = "Test message"
    return message


@pytest.fixture
def mock_state():
    """Fixture: Mock FSM context."""
    state = AsyncMock(spec=FSMContext)
    state.get_data = AsyncMock(return_value={})
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()
    state.clear = AsyncMock()
    return state


@pytest.fixture
def mock_services():
    """Fixture: Mock ServiceContainer."""
    services = MagicMock()
    services.user = AsyncMock()
    services.activity = AsyncMock()
    services.category = AsyncMock()
    return services


@pytest.fixture
def sample_user():
    """Fixture: Sample user data."""
    return {
        "id": 1,
        "telegram_id": 123456789,
        "username": "testuser",
        "timezone": "Europe/Moscow"
    }


@pytest.fixture
def sample_categories():
    """Fixture: Sample categories."""
    return [
        {"id": 1, "name": "Work", "emoji": "💼"},
        {"id": 2, "name": "Sport", "emoji": "🏃"},
    ]


# ============================================================================
# TEST SUITES
# ============================================================================

class TestStartAddActivity:
    """Test suite for start_add_activity handler."""

    @pytest.mark.unit
    async def test_start_add_activity_sets_state_and_shows_instructions(
        self,
        mock_callback,
        mock_state
    ):
        """
        Test activity creation initiation.

        GIVEN: User starts activity creation
        WHEN: start_add_activity is called
        THEN: FSM state is set to waiting_for_start_time
              AND instructions are shown
        """
        # Arrange
        with patch('src.api.handlers.activity.activity_creation.schedule_fsm_timeout') as mock_timeout:
            # Act
            await start_add_activity(mock_callback, mock_state)

        # Assert: State set
        mock_state.set_state.assert_called_once_with(ActivityStates.waiting_for_start_time)

        # Assert: Timeout scheduled
        mock_timeout.assert_called_once()

        # Assert: Instructions shown
        mock_callback.message.answer.assert_called_once()
        message_text = mock_callback.message.answer.call_args[0][0]
        assert "время НАЧАЛА" in message_text
        assert "14:30" in message_text  # Example format

        # Assert: Callback answered
        mock_callback.answer.assert_called_once()


class TestProcessStartTime:
    """Test suite for process_start_time handler."""

    @pytest.mark.unit
    async def test_process_start_time_with_valid_time_saves_to_state(
        self,
        mock_message,
        mock_state
    ):
        """
        Test valid start time parsing.

        GIVEN: User inputs valid time "14:30"
        WHEN: process_start_time is called
        THEN: Time is parsed and saved to state
              AND FSM state changes to waiting_for_end_time
        """
        # Arrange
        mock_message.text = "14:30"

        with patch('src.api.handlers.activity.activity_creation.parse_time_input') as mock_parse:
            parsed_time = datetime(2025, 11, 7, 14, 30, tzinfo=timezone.utc)
            mock_parse.return_value = parsed_time

            with patch('src.api.handlers.activity.activity_creation.fsm_timeout_module'):
                with patch('src.api.handlers.activity.activity_creation.format_time') as mock_format:
                    mock_format.return_value = "14:30"

                    # Act
                    await process_start_time(mock_message, mock_state)

        # Assert: Time saved
        mock_state.update_data.assert_called_once()
        assert "start_time" in mock_state.update_data.call_args.kwargs

        # Assert: State changed
        mock_state.set_state.assert_called_once_with(ActivityStates.waiting_for_end_time)

        # Assert: End time prompt shown
        mock_message.answer.assert_called_once()
        message_text = mock_message.answer.call_args[0][0]
        assert "ОКОНЧАНИЯ" in message_text

    @pytest.mark.unit
    async def test_process_start_time_with_future_time_shows_error(
        self,
        mock_message,
        mock_state
    ):
        """
        Test future time validation.

        GIVEN: User inputs future time
        WHEN: process_start_time is called
        THEN: Error is shown
              AND state is not changed
        """
        # Arrange
        mock_message.text = "25:00"  # Future time

        with patch('src.api.handlers.activity.activity_creation.parse_time_input') as mock_parse:
            # Return future time
            future_time = datetime.now(timezone.utc).replace(hour=23, minute=59) + \
                         __import__('datetime').timedelta(days=1)
            mock_parse.return_value = future_time

            # Act
            await process_start_time(mock_message, mock_state)

        # Assert: Error shown
        mock_message.answer.assert_called_once()
        message_text = mock_message.answer.call_args[0][0]
        assert "не может быть в будущем" in message_text

        # Assert: State not changed
        mock_state.set_state.assert_not_called()

    @pytest.mark.unit
    async def test_process_start_time_with_invalid_format_shows_error(
        self,
        mock_message,
        mock_state
    ):
        """
        Test invalid time format handling.

        GIVEN: User inputs invalid time format
        WHEN: process_start_time is called
        THEN: Parsing error is shown
        """
        # Arrange
        mock_message.text = "invalid"

        with patch('src.api.handlers.activity.activity_creation.parse_time_input') as mock_parse:
            mock_parse.side_effect = ValueError("Invalid time format")

            # Act
            await process_start_time(mock_message, mock_state)

        # Assert: Error shown
        mock_message.answer.assert_called_once()
        message_text = mock_message.answer.call_args[0][0]
        assert "Не могу распознать время" in message_text


class TestQuickStartTime:
    """Test suite for quick_start_time handler."""

    @pytest.mark.unit
    async def test_quick_start_time_with_30m_button_sets_time(
        self,
        mock_callback,
        mock_state
    ):
        """
        Test quick time button "30м".

        GIVEN: User clicks "30м" button
        WHEN: quick_start_time is called
        THEN: Start time is calculated as 30 minutes ago
              AND state changes to waiting_for_end_time
        """
        # Arrange
        mock_callback.data = "time_start_30m"

        with patch('src.api.handlers.activity.activity_creation.parse_time_input') as mock_parse:
            parsed_time = datetime(2025, 11, 7, 14, 0, tzinfo=timezone.utc)
            mock_parse.return_value = parsed_time

            with patch('src.api.handlers.activity.activity_creation.fsm_timeout_module'):
                with patch('src.api.handlers.activity.activity_creation.format_time') as mock_format:
                    mock_format.return_value = "14:00"

                    # Act
                    await quick_start_time(mock_callback, mock_state)

        # Assert: parse_time_input called with "30м"
        mock_parse.assert_called_once_with("30м")

        # Assert: Time saved to state
        mock_state.update_data.assert_called_once()

        # Assert: State changed
        mock_state.set_state.assert_called_once_with(ActivityStates.waiting_for_end_time)

        # Assert: Callback answered
        mock_callback.answer.assert_called_once()


class TestProcessEndTime:
    """Test suite for process_end_time handler."""

    @pytest.mark.unit
    async def test_process_end_time_with_valid_duration_calculates_end(
        self,
        mock_message,
        mock_state
    ):
        """
        Test end time calculation from duration.

        GIVEN: Start time in state, user inputs "30м"
        WHEN: process_end_time is called
        THEN: End time is calculated as start_time + 30 minutes
        """
        # Arrange
        mock_message.text = "30м"
        start_time = datetime(2025, 11, 7, 14, 0, tzinfo=timezone.utc)
        mock_state.get_data.return_value = {"start_time": start_time.isoformat()}

        with patch('src.api.handlers.activity.activity_creation.parse_duration') as mock_parse:
            end_time = datetime(2025, 11, 7, 14, 30, tzinfo=timezone.utc)
            mock_parse.return_value = end_time

            with patch('src.api.handlers.activity.activity_creation.fsm_timeout_module'):
                with patch('src.api.handlers.activity.activity_creation.format_time') as mock_format_time:
                    mock_format_time.return_value = "14:30"
                    with patch('src.api.handlers.activity.activity_creation.format_duration') as mock_format_dur:
                        mock_format_dur.return_value = "30 минут"

                        # Act
                        await process_end_time(mock_message, mock_state)

        # Assert: Duration parsed
        mock_parse.assert_called_once_with("30м", start_time)

        # Assert: End time saved
        mock_state.update_data.assert_called_once()

        # Assert: State changed to description
        mock_state.set_state.assert_called_once_with(ActivityStates.waiting_for_description)

    @pytest.mark.unit
    async def test_process_end_time_with_end_before_start_shows_error(
        self,
        mock_message,
        mock_state
    ):
        """
        Test end time validation.

        GIVEN: Start time in state, end time before start
        WHEN: process_end_time is called
        THEN: Validation error is shown
        """
        # Arrange
        mock_message.text = "13:00"
        start_time = datetime(2025, 11, 7, 14, 0, tzinfo=timezone.utc)
        end_time = datetime(2025, 11, 7, 13, 0, tzinfo=timezone.utc)  # Before start
        mock_state.get_data.return_value = {"start_time": start_time.isoformat()}

        with patch('src.api.handlers.activity.activity_creation.parse_duration') as mock_parse:
            mock_parse.return_value = end_time

            # Act
            await process_end_time(mock_message, mock_state)

        # Assert: Error shown
        mock_message.answer.assert_called_once()
        message_text = mock_message.answer.call_args[0][0]
        assert "должно быть позже" in message_text

        # Assert: State not changed
        mock_state.set_state.assert_not_called()

    @pytest.mark.unit
    async def test_process_end_time_without_start_time_clears_state(
        self,
        mock_message,
        mock_state
    ):
        """
        Test missing start time handling.

        GIVEN: No start time in state
        WHEN: process_end_time is called
        THEN: Error is shown and state is cleared
        """
        # Arrange
        mock_message.text = "16:00"
        mock_state.get_data.return_value = {}  # No start_time

        with patch('src.api.handlers.activity.activity_creation.fsm_timeout_module'):
            # Act
            await process_end_time(mock_message, mock_state)

        # Assert: Error shown
        mock_message.answer.assert_called_once()
        message_text = mock_message.answer.call_args[0][0]
        assert "не найдено" in message_text

        # Assert: State cleared
        mock_state.clear.assert_called_once()


class TestQuickEndTime:
    """Test suite for quick_end_time handler."""

    @pytest.mark.unit
    async def test_quick_end_time_with_now_button_uses_current_time(
        self,
        mock_callback,
        mock_state
    ):
        """
        Test "Сейчас" quick button.

        GIVEN: User clicks "Сейчас" button
        WHEN: quick_end_time is called
        THEN: End time is set to current time
        """
        # Arrange
        mock_callback.data = "time_end_now"
        start_time = datetime(2025, 11, 7, 14, 0, tzinfo=timezone.utc)
        mock_state.get_data.return_value = {"start_time": start_time.isoformat()}

        with patch('src.api.handlers.activity.activity_creation.datetime') as mock_dt:
            now = datetime(2025, 11, 7, 15, 0, tzinfo=timezone.utc)
            mock_dt.now.return_value = now
            mock_dt.fromisoformat = datetime.fromisoformat
            mock_dt.timezone = timezone

            with patch('src.api.handlers.activity.activity_creation.fsm_timeout_module'):
                with patch('src.api.handlers.activity.activity_creation.format_time') as mock_format_time:
                    mock_format_time.return_value = "15:00"
                    with patch('src.api.handlers.activity.activity_creation.format_duration') as mock_format_dur:
                        mock_format_dur.return_value = "1 час"

                        # Act
                        await quick_end_time(mock_callback, mock_state)

        # Assert: Current time used
        mock_state.update_data.assert_called_once()

        # Assert: State changed
        mock_state.set_state.assert_called_once_with(ActivityStates.waiting_for_description)

    @pytest.mark.unit
    async def test_quick_end_time_with_1h_button_calculates_duration(
        self,
        mock_callback,
        mock_state
    ):
        """
        Test "1ч" duration button.

        GIVEN: User clicks "1ч длилось" button
        WHEN: quick_end_time is called
        THEN: End time is start_time + 1 hour
        """
        # Arrange
        mock_callback.data = "time_end_1h"
        start_time = datetime(2025, 11, 7, 14, 0, tzinfo=timezone.utc)
        mock_state.get_data.return_value = {"start_time": start_time.isoformat()}

        with patch('src.api.handlers.activity.activity_creation.parse_duration') as mock_parse:
            end_time = datetime(2025, 11, 7, 15, 0, tzinfo=timezone.utc)
            mock_parse.return_value = end_time

            with patch('src.api.handlers.activity.activity_creation.fsm_timeout_module'):
                with patch('src.api.handlers.activity.activity_creation.format_time') as mock_format_time:
                    mock_format_time.return_value = "15:00"
                    with patch('src.api.handlers.activity.activity_creation.format_duration') as mock_format_dur:
                        mock_format_dur.return_value = "1 час"

                        # Act
                        await quick_end_time(mock_callback, mock_state)

        # Assert: Duration parsed with "1ч"
        mock_parse.assert_called_once()


class TestProcessDescription:
    """Test suite for process_description handler."""

    @pytest.mark.unit
    async def test_process_description_with_valid_text_extracts_tags(
        self,
        mock_message,
        mock_state,
        mock_services,
        sample_user,
        sample_categories
    ):
        """
        Test description processing with tags.

        GIVEN: User inputs description with #tags
        WHEN: process_description is called
        THEN: Tags are extracted
              AND state changes to waiting_for_category
        """
        # Arrange
        mock_message.text = "Working on project #work #coding"
        mock_services.user.get_by_telegram_id.return_value = sample_user
        mock_services.category.get_user_categories.return_value = sample_categories

        with patch('src.api.handlers.activity.activity_creation.extract_tags') as mock_extract:
            mock_extract.return_value = ["work", "coding"]

            with patch('src.api.handlers.activity.activity_creation.fsm_timeout_module'):
                # Act
                await process_description(mock_message, mock_state, mock_services)

        # Assert: Tags extracted
        mock_extract.assert_called_once_with("Working on project #work #coding")

        # Assert: Data saved to state
        mock_state.update_data.assert_called()
        call_kwargs = mock_state.update_data.call_args.kwargs
        assert call_kwargs["description"] == "Working on project #work #coding"
        assert call_kwargs["tags"] == ["work", "coding"]

        # Assert: State changed
        mock_state.set_state.assert_called_once_with(ActivityStates.waiting_for_category)

    @pytest.mark.unit
    async def test_process_description_with_short_text_shows_error(
        self,
        mock_message,
        mock_state,
        mock_services
    ):
        """
        Test description length validation.

        GIVEN: User inputs description < 3 chars
        WHEN: process_description is called
        THEN: Validation error is shown
        """
        # Arrange
        mock_message.text = "ab"  # Too short

        # Act
        await process_description(mock_message, mock_state, mock_services)

        # Assert: Error shown
        mock_message.answer.assert_called_once()
        message_text = mock_message.answer.call_args[0][0]
        assert "минимум 3 символа" in message_text

        # Assert: State not changed
        mock_state.set_state.assert_not_called()

    @pytest.mark.unit
    async def test_process_description_with_no_categories_saves_without_category(
        self,
        mock_message,
        mock_state,
        mock_services,
        sample_user
    ):
        """
        Test automatic save when no categories exist.

        GIVEN: User has no categories
        WHEN: process_description is called
        THEN: Activity is saved without category
        """
        # Arrange
        mock_message.text = "Test activity"
        mock_services.user.get_by_telegram_id.return_value = sample_user
        mock_services.category.get_user_categories.return_value = []  # No categories

        with patch('src.api.handlers.activity.activity_creation.extract_tags', return_value=[]):
            with patch('src.api.handlers.activity.activity_creation.save_activity') as mock_save:
                # Act
                await process_description(mock_message, mock_state, mock_services)

        # Assert: save_activity called with category_id=None
        mock_save.assert_called_once()
        assert mock_save.call_args[0][3] is None  # category_id is None


class TestProcessCategoryCallback:
    """Test suite for process_category_callback handler."""

    @pytest.mark.unit
    async def test_process_category_callback_with_valid_category_saves_activity(
        self,
        mock_callback,
        mock_state,
        mock_services,
        sample_categories
    ):
        """
        Test category selection via button.

        GIVEN: User selects category from buttons
        WHEN: process_category_callback is called
        THEN: Activity is saved with selected category
        """
        # Arrange
        mock_callback.data = "poll_category_1"
        mock_state.get_data.return_value = {
            "categories": sample_categories,
            "user_id": 1
        }

        with patch('src.api.handlers.activity.activity_creation.save_activity') as mock_save:
            # Act
            await process_category_callback(mock_callback, mock_state, mock_services)

        # Assert: save_activity called with category_id=1
        mock_save.assert_called_once()
        assert mock_save.call_args[0][3] == 1  # category_id

        # Assert: Callback answered
        mock_callback.answer.assert_called_once()


class TestCancelCategorySelection:
    """Test suite for cancel_category_selection handler."""

    @pytest.mark.unit
    async def test_cancel_category_selection_clears_state(
        self,
        mock_callback,
        mock_state
    ):
        """
        Test cancellation of category selection.

        GIVEN: User clicks cancel button
        WHEN: cancel_category_selection is called
        THEN: State is cleared and message shown
        """
        # Act
        await cancel_category_selection(mock_callback, mock_state)

        # Assert: State cleared
        mock_state.clear.assert_called_once()

        # Assert: Cancellation message
        mock_callback.message.answer.assert_called_once()
        message_text = mock_callback.message.answer.call_args[0][0]
        assert "отменена" in message_text


class TestProcessCategory:
    """Test suite for process_category (text input) handler."""

    @pytest.mark.unit
    async def test_process_category_with_zero_skips_category(
        self,
        mock_message,
        mock_state,
        mock_services,
        sample_user
    ):
        """
        Test skipping category with "0".

        GIVEN: User sends "0" to skip category
        WHEN: process_category is called
        THEN: Activity is saved without category
        """
        # Arrange
        mock_message.text = "0"
        mock_services.user.get_by_telegram_id.return_value = sample_user

        with patch('src.api.handlers.activity.activity_creation.save_activity') as mock_save:
            # Act
            await process_category(mock_message, mock_state, mock_services)

        # Assert: save_activity called with category_id=None
        mock_save.assert_called_once()
        assert mock_save.call_args[0][3] is None

    @pytest.mark.unit
    async def test_process_category_with_other_text_shows_button_reminder(
        self,
        mock_message,
        mock_state,
        mock_services
    ):
        """
        Test non-zero text input handling.

        GIVEN: User sends text other than "0"
        WHEN: process_category is called
        THEN: Reminder to use buttons is shown
        """
        # Arrange
        mock_message.text = "Work"  # Should use buttons instead

        # Act
        await process_category(mock_message, mock_state, mock_services)

        # Assert: Reminder message
        mock_message.answer.assert_called_once()
        message_text = mock_message.answer.call_args[0][0]
        assert "используй кнопки" in message_text


class TestSaveActivity:
    """Test suite for save_activity helper function."""

    @pytest.mark.unit
    async def test_save_activity_with_all_data_creates_activity(
        self,
        mock_message,
        mock_state,
        mock_services
    ):
        """
        Test successful activity save.

        GIVEN: All required data in state
        WHEN: save_activity is called
        THEN: Activity is created in database
              AND success message shown
        """
        # Arrange
        start_time = datetime(2025, 11, 7, 14, 0, tzinfo=timezone.utc)
        end_time = datetime(2025, 11, 7, 15, 30, tzinfo=timezone.utc)
        mock_state.get_data.return_value = {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "description": "Working on project",
            "tags": ["work", "coding"]
        }

        with patch('src.api.handlers.activity.activity_creation.fsm_timeout_module'):
            with patch('src.api.handlers.activity.activity_creation.format_duration') as mock_format:
                mock_format.return_value = "1 час 30 минут"

                # Act
                await save_activity(
                    mock_message,
                    mock_state,
                    user_id=1,
                    category_id=1,
                    telegram_user_id=123456789,
                    services=mock_services
                )

        # Assert: Activity created
        mock_services.activity.create_activity.assert_called_once()
        call_kwargs = mock_services.activity.create_activity.call_args.kwargs
        assert call_kwargs["user_id"] == 1
        assert call_kwargs["category_id"] == 1
        assert call_kwargs["description"] == "Working on project"
        assert call_kwargs["tags"] == ["work", "coding"]

        # Assert: Success message
        mock_message.answer.assert_called_once()
        message_text = mock_message.answer.call_args[0][0]
        assert "сохранена" in message_text

        # Assert: State cleared
        mock_state.clear.assert_called_once()

    @pytest.mark.unit
    async def test_save_activity_with_missing_data_shows_error(
        self,
        mock_message,
        mock_state,
        mock_services
    ):
        """
        Test save with incomplete data.

        GIVEN: Missing required fields in state
        WHEN: save_activity is called
        THEN: Error is shown and state is cleared
        """
        # Arrange
        mock_state.get_data.return_value = {
            "start_time": "2025-11-07T14:00:00+00:00"
            # Missing end_time and description
        }

        # Act
        await save_activity(
            mock_message,
            mock_state,
            user_id=1,
            category_id=1,
            telegram_user_id=123456789,
            services=mock_services
        )

        # Assert: Error shown
        mock_message.answer.assert_called_once()
        message_text = mock_message.answer.call_args[0][0]
        assert "Недостаточно данных" in message_text

        # Assert: Activity not created
        mock_services.activity.create_activity.assert_not_called()

    @pytest.mark.unit
    async def test_save_activity_with_service_error_handles_gracefully(
        self,
        mock_message,
        mock_state,
        mock_services
    ):
        """
        Test error handling during save.

        GIVEN: Service raises exception
        WHEN: save_activity is called
        THEN: Error is caught and error message shown
        """
        # Arrange
        start_time = datetime(2025, 11, 7, 14, 0, tzinfo=timezone.utc)
        end_time = datetime(2025, 11, 7, 15, 0, tzinfo=timezone.utc)
        mock_state.get_data.return_value = {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "description": "Test",
            "tags": []
        }
        mock_services.activity.create_activity.side_effect = Exception("Database error")

        with patch('src.api.handlers.activity.activity_creation.fsm_timeout_module'):
            # Act
            await save_activity(
                mock_message,
                mock_state,
                user_id=1,
                category_id=1,
                telegram_user_id=123456789,
                services=mock_services
            )

        # Assert: Error message shown
        mock_message.answer.assert_called()
        message_text = mock_message.answer.call_args[0][0]
        assert "Ошибка при сохранении" in message_text

        # Assert: State cleared
        mock_state.clear.assert_called_once()
