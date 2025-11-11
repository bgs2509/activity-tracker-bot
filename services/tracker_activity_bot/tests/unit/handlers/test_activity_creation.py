"""
Unit tests for activity creation handlers.

Tests FSM flow for creating new activities including:
- Period selection (auto-calculate or quick buttons)
- Category selection
- Description input with tag extraction
- Activity saving with callbacks

Test Coverage:
    - start_add_activity: FSM initiation with period keyboard
    - handle_noop: Visual divider click handler
    - auto_calculate_period: Auto-calculate period from last activity
    - quick_period_selection: Quick period button handlers
    - process_period_input: Manual period text input
    - process_category_callback: Category selection callback
    - select_recent_activity: Recent activity quick selection
    - process_description: Description validation using shared functions
    - handle_cancel: Cancel flow handler
    - save_activity: Activity save wrapper
    - _create_poll_scheduling_callback: Poll scheduling callback factory

Coverage Target: 100% of activity_creation.py
Execution Time: < 2.0 seconds

Author: Testing Team
Date: 2025-11-11 (Updated for Phase 4-6 refactoring)
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram import types
from aiogram.fsm.context import FSMContext

from src.api.handlers.activity.activity_creation import (
    start_add_activity,
    handle_noop,
    auto_calculate_period,
    quick_period_selection,
    process_period_input,
    process_category_callback,
    select_recent_activity,
    process_description,
    handle_cancel,
    save_activity,
    _create_poll_scheduling_callback
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
    callback.message.edit_text = AsyncMock()
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
    services.settings = AsyncMock()
    services.scheduler = MagicMock()
    services.scheduler.scheduler = MagicMock()
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


@pytest.fixture
def sample_settings():
    """Fixture: Sample user settings."""
    return {
        "poll_interval_minutes": 60,
        "enable_polling": True
    }


@pytest.fixture
def sample_activities():
    """Fixture: Sample recent activities."""
    return [
        {
            "id": 1,
            "description": "Работал над проектом",
            "start_time": datetime(2025, 11, 11, 10, 0, tzinfo=timezone.utc),
            "end_time": datetime(2025, 11, 11, 12, 0, tzinfo=timezone.utc),
        },
        {
            "id": 2,
            "description": "Читал книгу",
            "start_time": datetime(2025, 11, 11, 8, 0, tzinfo=timezone.utc),
            "end_time": datetime(2025, 11, 11, 9, 0, tzinfo=timezone.utc),
        }
    ]


# ============================================================================
# TEST SUITES
# ============================================================================

class TestStartAddActivity:
    """Test suite for start_add_activity handler."""

    @pytest.mark.unit
    async def test_start_shows_period_keyboard_with_auto_option(
        self,
        mock_callback,
        mock_state
    ):
        """
        Test activity creation initiation with auto-calculate option.

        GIVEN: User starts manual activity creation
        WHEN: start_add_activity is called
        THEN: Period keyboard with auto-calculate button is shown
              AND FSM state is set to waiting_for_period
              AND timeout is scheduled
        """
        # Arrange
        with patch('src.api.handlers.activity.activity_creation.schedule_fsm_timeout') as mock_timeout:
            with patch('src.api.handlers.activity.activity_creation.get_period_keyboard_with_auto') as mock_kb:
                mock_kb.return_value = MagicMock()

                # Act
                await start_add_activity(mock_callback, mock_state)

        # Assert: State set to waiting_for_period
        mock_state.set_state.assert_called_once_with(ActivityStates.waiting_for_period)

        # Assert: Trigger source marked as manual
        mock_state.update_data.assert_called_once()
        assert mock_state.update_data.call_args.kwargs["trigger_source"] == "manual"

        # Assert: Timeout scheduled
        mock_timeout.assert_called_once()

        # Assert: Message sent with keyboard
        mock_callback.message.answer.assert_called_once()
        message_text = mock_callback.message.answer.call_args[0][0]
        assert "период активности" in message_text.lower()

        # Assert: Callback answered
        mock_callback.answer.assert_called_once()


class TestHandleNoop:
    """Test suite for handle_noop (visual divider) handler."""

    @pytest.mark.unit
    async def test_handle_noop_answers_callback_without_action(
        self,
        mock_callback
    ):
        """
        Test visual divider click handling.

        GIVEN: User clicks on visual divider button
        WHEN: handle_noop is called
        THEN: Callback is answered silently
              AND no state changes occur
        """
        # Act
        await handle_noop(mock_callback)

        # Assert: Callback answered
        mock_callback.answer.assert_called_once()

        # Assert: No message sent
        mock_callback.message.answer.assert_not_called()


class TestAutoCalculatePeriod:
    """Test suite for auto_calculate_period handler."""

    @pytest.mark.unit
    async def test_auto_calculate_with_last_activity_calculates_period(
        self,
        mock_callback,
        mock_state,
        mock_services,
        sample_user,
        sample_settings,
        sample_categories
    ):
        """
        Test auto-calculate period from last activity.

        GIVEN: User has last activity and settings
        WHEN: auto_calculate_period is called
        THEN: Period is calculated from last activity end time
              AND state changes to waiting_for_category
              AND category keyboard is shown
        """
        # Arrange
        mock_services.user.get_by_telegram_id.return_value = sample_user
        mock_services.settings.get_settings.return_value = sample_settings
        mock_services.category.get_user_categories.return_value = sample_categories

        with patch('src.api.handlers.activity.activity_creation.calculate_poll_period') as mock_calc:
            start_time = datetime(2025, 11, 11, 10, 0, tzinfo=timezone.utc)
            end_time = datetime(2025, 11, 11, 11, 0, tzinfo=timezone.utc)
            mock_calc.return_value = (start_time, end_time)

            with patch('src.api.handlers.activity.activity_creation.schedule_fsm_timeout'):
                with patch('src.api.handlers.activity.activity_creation.format_time') as mock_format_time:
                    mock_format_time.side_effect = ["10:00", "11:00"]
                    with patch('src.api.handlers.activity.activity_creation.format_duration') as mock_format_dur:
                        mock_format_dur.return_value = "1 час"

                        # Act
                        await auto_calculate_period(mock_callback, mock_state, mock_services)

        # Assert: calculate_poll_period called
        mock_calc.assert_called_once()

        # Assert: Period saved to state
        mock_state.update_data.assert_called()
        call_kwargs = mock_state.update_data.call_args.kwargs
        assert "start_time" in call_kwargs
        assert "end_time" in call_kwargs

        # Assert: State changed to waiting_for_category
        mock_state.set_state.assert_called_once_with(ActivityStates.waiting_for_category)

        # Assert: Category keyboard shown
        mock_callback.message.edit_text.assert_called_once()

    @pytest.mark.unit
    async def test_auto_calculate_without_categories_saves_without_category(
        self,
        mock_callback,
        mock_state,
        mock_services,
        sample_user,
        sample_settings
    ):
        """
        Test auto-calculate when user has no categories.

        GIVEN: User has no categories
        WHEN: auto_calculate_period is called
        THEN: Activity is saved without category selection
        """
        # Arrange
        mock_services.user.get_by_telegram_id.return_value = sample_user
        mock_services.settings.get_settings.return_value = sample_settings
        mock_services.category.get_user_categories.return_value = []

        with patch('src.api.handlers.activity.activity_creation.calculate_poll_period') as mock_calc:
            start_time = datetime(2025, 11, 11, 10, 0, tzinfo=timezone.utc)
            end_time = datetime(2025, 11, 11, 11, 0, tzinfo=timezone.utc)
            mock_calc.return_value = (start_time, end_time)

            with patch('src.api.handlers.activity.activity_creation.fetch_and_build_description_prompt') as mock_fetch:
                mock_fetch.return_value = ("Test prompt", None)

                with patch('src.api.handlers.activity.activity_creation.schedule_fsm_timeout'):
                    # Act
                    await auto_calculate_period(mock_callback, mock_state, mock_services)

        # Assert: State changed to waiting_for_description
        mock_state.set_state.assert_called_once_with(ActivityStates.waiting_for_description)

        # Assert: Description prompt shown
        mock_callback.message.edit_text.assert_called_once()

    @pytest.mark.unit
    async def test_auto_calculate_handles_service_error_gracefully(
        self,
        mock_callback,
        mock_state,
        mock_services
    ):
        """
        Test error handling in auto-calculate.

        GIVEN: Service raises exception
        WHEN: auto_calculate_period is called
        THEN: Error is caught and error message shown
              AND state is cleared
        """
        # Arrange
        mock_services.user.get_by_telegram_id.side_effect = Exception("Database error")

        with patch('src.api.handlers.activity.activity_creation.cancel_fsm_timeout'):
            # Act
            await auto_calculate_period(mock_callback, mock_state, mock_services)

        # Assert: Error message shown
        mock_callback.message.edit_text.assert_called_once()
        message_text = mock_callback.message.edit_text.call_args[0][0]
        assert "Ошибка" in message_text

        # Assert: State cleared
        mock_state.clear.assert_called_once()


class TestQuickPeriodSelection:
    """Test suite for quick_period_selection handler."""

    @pytest.mark.unit
    async def test_quick_period_15m_sets_15_minute_period(
        self,
        mock_callback,
        mock_state,
        mock_services,
        sample_user,
        sample_categories
    ):
        """
        Test 15-minute quick period button.

        GIVEN: User clicks "15 минут" button
        WHEN: quick_period_selection is called
        THEN: Period of 15 minutes ending now is set
              AND state changes to waiting_for_category
        """
        # Arrange
        mock_callback.data = "period_15m"
        mock_services.user.get_by_telegram_id.return_value = sample_user
        mock_services.category.get_user_categories.return_value = sample_categories

        with patch('src.api.handlers.activity.activity_creation.datetime') as mock_dt:
            now = datetime(2025, 11, 11, 12, 0, tzinfo=timezone.utc)
            mock_dt.now.return_value = now
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

            with patch('src.api.handlers.activity.activity_creation.schedule_fsm_timeout'):
                with patch('src.api.handlers.activity.activity_creation.format_time') as mock_format_time:
                    mock_format_time.side_effect = ["11:45", "12:00"]
                    with patch('src.api.handlers.activity.activity_creation.format_duration') as mock_format_dur:
                        mock_format_dur.return_value = "15 минут"

                        # Act
                        await quick_period_selection(mock_callback, mock_state, mock_services)

        # Assert: Period saved
        mock_state.update_data.assert_called()
        call_kwargs = mock_state.update_data.call_args.kwargs
        assert "start_time" in call_kwargs
        assert "end_time" in call_kwargs

        # Assert: State changed to waiting_for_category
        mock_state.set_state.assert_called_once_with(ActivityStates.waiting_for_category)

    @pytest.mark.unit
    async def test_quick_period_3h_sets_3_hour_period(
        self,
        mock_callback,
        mock_state,
        mock_services,
        sample_user,
        sample_categories
    ):
        """
        Test 3-hour quick period button.

        GIVEN: User clicks "3 часа" button
        WHEN: quick_period_selection is called
        THEN: Period of 3 hours ending now is set
        """
        # Arrange
        mock_callback.data = "period_3h"
        mock_services.user.get_by_telegram_id.return_value = sample_user
        mock_services.category.get_user_categories.return_value = sample_categories

        with patch('src.api.handlers.activity.activity_creation.datetime') as mock_dt:
            now = datetime(2025, 11, 11, 15, 0, tzinfo=timezone.utc)
            mock_dt.now.return_value = now
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

            with patch('src.api.handlers.activity.activity_creation.schedule_fsm_timeout'):
                with patch('src.api.handlers.activity.activity_creation.format_time') as mock_format_time:
                    mock_format_time.side_effect = ["12:00", "15:00"]
                    with patch('src.api.handlers.activity.activity_creation.format_duration') as mock_format_dur:
                        mock_format_dur.return_value = "3 часа"

                        # Act
                        await quick_period_selection(mock_callback, mock_state, mock_services)

        # Assert: State changed to waiting_for_category
        mock_state.set_state.assert_called_once_with(ActivityStates.waiting_for_category)

    @pytest.mark.unit
    async def test_quick_period_validates_trigger_source_is_manual(
        self,
        mock_callback,
        mock_state,
        mock_services
    ):
        """
        Test trigger_source validation.

        GIVEN: State has trigger_source != "manual"
        WHEN: quick_period_selection is called
        THEN: Error is shown and operation rejected
        """
        # Arrange
        mock_callback.data = "period_1h"
        mock_state.get_data.return_value = {"trigger_source": "automatic"}

        # Act
        await quick_period_selection(mock_callback, mock_state, mock_services)

        # Assert: Error message
        mock_callback.answer.assert_called_once()
        assert "доступно только в ручном режиме" in mock_callback.answer.call_args.kwargs.get("text", "")

        # Assert: State not changed
        mock_state.set_state.assert_not_called()


class TestProcessPeriodInput:
    """Test suite for process_period_input handler (manual text input)."""

    @pytest.mark.unit
    async def test_process_period_input_parses_custom_duration(
        self,
        mock_message,
        mock_state,
        mock_services,
        sample_user,
        sample_categories
    ):
        """
        Test custom period text input.

        GIVEN: User enters custom duration like "45m"
        WHEN: process_period_input is called
        THEN: Duration is parsed and period is set
        """
        # Arrange
        mock_message.text = "45м"
        mock_services.user.get_by_telegram_id.return_value = sample_user
        mock_services.category.get_user_categories.return_value = sample_categories

        with patch('src.api.handlers.activity.activity_creation.parse_duration') as mock_parse:
            start_time = datetime(2025, 11, 11, 10, 15, tzinfo=timezone.utc)
            end_time = datetime(2025, 11, 11, 11, 0, tzinfo=timezone.utc)
            mock_parse.return_value = start_time  # parse_duration returns start_time when given duration from now

            with patch('src.api.handlers.activity.activity_creation.datetime') as mock_dt:
                now = datetime(2025, 11, 11, 11, 0, tzinfo=timezone.utc)
                mock_dt.now.return_value = now
                mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

                with patch('src.api.handlers.activity.activity_creation.schedule_fsm_timeout'):
                    with patch('src.api.handlers.activity.activity_creation.format_time') as mock_format_time:
                        mock_format_time.side_effect = ["10:15", "11:00"]
                        with patch('src.api.handlers.activity.activity_creation.format_duration') as mock_format_dur:
                            mock_format_dur.return_value = "45 минут"

                            # Act
                            await process_period_input(mock_message, mock_state, mock_services)

        # Assert: Duration parsed
        mock_parse.assert_called_once()

        # Assert: State changed to waiting_for_category
        mock_state.set_state.assert_called_once_with(ActivityStates.waiting_for_category)

    @pytest.mark.unit
    async def test_process_period_input_with_invalid_format_shows_error(
        self,
        mock_message,
        mock_state,
        mock_services
    ):
        """
        Test invalid duration format handling.

        GIVEN: User enters unparseable text
        WHEN: process_period_input is called
        THEN: Parse error is shown
        """
        # Arrange
        mock_message.text = "invalid"

        with patch('src.api.handlers.activity.activity_creation.parse_duration') as mock_parse:
            mock_parse.side_effect = ValueError("Cannot parse duration")

            # Act
            await process_period_input(mock_message, mock_state, mock_services)

        # Assert: Error message shown
        mock_message.answer.assert_called_once()
        message_text = mock_message.answer.call_args[0][0]
        assert "Не могу распознать" in message_text


class TestProcessCategoryCallback:
    """Test suite for process_category_callback handler."""

    @pytest.mark.unit
    async def test_category_callback_uses_shared_save_function(
        self,
        mock_callback,
        mock_state,
        mock_services,
        sample_categories
    ):
        """
        Test category selection saves activity using shared function.

        GIVEN: User selects category
        WHEN: process_category_callback is called
        THEN: create_and_save_activity from shared module is called
              AND post_save_callback is used for automatic flow
        """
        # Arrange
        mock_callback.data = "poll_category_1"
        mock_state.get_data.return_value = {
            "trigger_source": "automatic",
            "categories": sample_categories,
            "user_id": 1,
            "start_time": "2025-11-11T10:00:00+00:00",
            "end_time": "2025-11-11T11:00:00+00:00"
        }

        with patch('src.api.handlers.activity.activity_creation.create_and_save_activity') as mock_create:
            mock_create.return_value = True

            # Act
            await process_category_callback(mock_callback, mock_state, mock_services)

        # Assert: create_and_save_activity called
        mock_create.assert_called_once()
        call_args = mock_create.call_args

        # Assert: category_id set correctly
        assert call_args.kwargs["category_id"] == 1

        # Assert: post_save_callback provided for automatic flow
        assert call_args.kwargs.get("post_save_callback") is not None

    @pytest.mark.unit
    async def test_category_callback_skip_option_sets_none(
        self,
        mock_callback,
        mock_state,
        mock_services
    ):
        """
        Test skip category option.

        GIVEN: User clicks "Пропустить" button
        WHEN: process_category_callback is called
        THEN: Activity is saved with category_id=None
        """
        # Arrange
        mock_callback.data = "poll_category_skip"
        mock_state.get_data.return_value = {
            "trigger_source": "manual",
            "user_id": 1,
            "start_time": "2025-11-11T10:00:00+00:00",
            "end_time": "2025-11-11T11:00:00+00:00"
        }

        with patch('src.api.handlers.activity.activity_creation.create_and_save_activity') as mock_create:
            mock_create.return_value = True

            # Act
            await process_category_callback(mock_callback, mock_state, mock_services)

        # Assert: category_id is None
        assert mock_create.call_args.kwargs["category_id"] is None

    @pytest.mark.unit
    async def test_category_callback_transitions_to_description_on_failure(
        self,
        mock_callback,
        mock_state,
        mock_services
    ):
        """
        Test transition to description state when save fails.

        GIVEN: create_and_save_activity returns False
        WHEN: process_category_callback is called
        THEN: State transitions to waiting_for_description
        """
        # Arrange
        mock_callback.data = "poll_category_1"
        mock_state.get_data.return_value = {
            "trigger_source": "manual",
            "user_id": 1,
            "start_time": "2025-11-11T10:00:00+00:00",
            "end_time": "2025-11-11T11:00:00+00:00"
        }

        with patch('src.api.handlers.activity.activity_creation.create_and_save_activity') as mock_create:
            mock_create.return_value = False  # Save failed (missing description)

            with patch('src.api.handlers.activity.activity_creation.fetch_and_build_description_prompt') as mock_fetch:
                mock_fetch.return_value = ("Enter description", None)

                with patch('src.api.handlers.activity.activity_creation.schedule_fsm_timeout'):
                    # Act
                    await process_category_callback(mock_callback, mock_state, mock_services)

        # Assert: State changed to waiting_for_description
        mock_state.set_state.assert_called_once_with(ActivityStates.waiting_for_description)


class TestSelectRecentActivity:
    """Test suite for select_recent_activity handler."""

    @pytest.mark.unit
    async def test_select_recent_activity_uses_shared_save_function(
        self,
        mock_callback,
        mock_state,
        mock_services,
        sample_activities
    ):
        """
        Test recent activity selection uses shared save function.

        GIVEN: User selects recent activity
        WHEN: select_recent_activity is called
        THEN: Description is populated from selected activity
              AND create_and_save_activity is called
        """
        # Arrange
        mock_callback.data = "recent_activity_1"
        mock_state.get_data.return_value = {
            "trigger_source": "manual",
            "user_id": 1,
            "recent_activities": sample_activities,
            "start_time": "2025-11-11T13:00:00+00:00",
            "end_time": "2025-11-11T14:00:00+00:00"
        }

        with patch('src.api.handlers.activity.activity_creation.create_and_save_activity') as mock_create:
            mock_create.return_value = True

            # Act
            await select_recent_activity(mock_callback, mock_state, mock_services)

        # Assert: Description set from activity
        mock_state.update_data.assert_called()
        assert "description" in mock_state.update_data.call_args.kwargs
        assert mock_state.update_data.call_args.kwargs["description"] == "Работал над проектом"

        # Assert: create_and_save_activity called
        mock_create.assert_called_once()

    @pytest.mark.unit
    async def test_select_recent_activity_with_invalid_index_shows_error(
        self,
        mock_callback,
        mock_state,
        mock_services
    ):
        """
        Test invalid activity index handling.

        GIVEN: Callback data has out-of-range index
        WHEN: select_recent_activity is called
        THEN: Error is shown
        """
        # Arrange
        mock_callback.data = "recent_activity_999"
        mock_state.get_data.return_value = {
            "trigger_source": "manual",
            "user_id": 1,
            "recent_activities": [],
            "start_time": "2025-11-11T13:00:00+00:00",
            "end_time": "2025-11-11T14:00:00+00:00"
        }

        with patch('src.api.handlers.activity.activity_creation.cancel_fsm_timeout'):
            # Act
            await select_recent_activity(mock_callback, mock_state, mock_services)

        # Assert: Error message
        mock_callback.message.answer.assert_called_once()
        message_text = mock_callback.message.answer.call_args[0][0]
        assert "Ошибка" in message_text


class TestProcessDescription:
    """Test suite for process_description handler."""

    @pytest.mark.unit
    async def test_process_description_uses_shared_validation(
        self,
        mock_message,
        mock_state,
        mock_services
    ):
        """
        Test description processing uses shared validation.

        GIVEN: User enters valid description
        WHEN: process_description is called
        THEN: validate_description from shared module is used
              AND create_and_save_activity is called
        """
        # Arrange
        mock_message.text = "Test activity description"
        mock_state.get_data.return_value = {
            "trigger_source": "manual",
            "user_id": 1,
            "category_id": 1,
            "start_time": "2025-11-11T10:00:00+00:00",
            "end_time": "2025-11-11T11:00:00+00:00"
        }

        with patch('src.api.handlers.activity.activity_creation.validate_description') as mock_validate:
            mock_validate.return_value = (True, None)

            with patch('src.api.handlers.activity.activity_creation.extract_tags') as mock_extract:
                mock_extract.return_value = []

                with patch('src.api.handlers.activity.activity_creation.create_and_save_activity') as mock_create:
                    mock_create.return_value = True

                    # Act
                    await process_description(mock_message, mock_state, mock_services)

        # Assert: validate_description called
        mock_validate.assert_called_once_with("Test activity description")

        # Assert: Tags extracted
        mock_extract.assert_called_once()

        # Assert: Description saved
        mock_state.update_data.assert_called()

        # Assert: Activity saved
        mock_create.assert_called_once()

    @pytest.mark.unit
    async def test_process_description_with_invalid_shows_error(
        self,
        mock_message,
        mock_state,
        mock_services
    ):
        """
        Test invalid description handling.

        GIVEN: Description fails validation
        WHEN: process_description is called
        THEN: Validation error is shown
        """
        # Arrange
        mock_message.text = "ab"  # Too short

        with patch('src.api.handlers.activity.activity_creation.validate_description') as mock_validate:
            mock_validate.return_value = (False, "Описание должно содержать минимум 3 символа")

            # Act
            await process_description(mock_message, mock_state, mock_services)

        # Assert: Error shown
        mock_message.answer.assert_called_once()
        message_text = mock_message.answer.call_args[0][0]
        assert "минимум 3 символа" in message_text

    @pytest.mark.unit
    async def test_process_description_extracts_tags(
        self,
        mock_message,
        mock_state,
        mock_services
    ):
        """
        Test tag extraction from description.

        GIVEN: Description contains #tags
        WHEN: process_description is called
        THEN: Tags are extracted and saved
        """
        # Arrange
        mock_message.text = "Working on project #work #coding"
        mock_state.get_data.return_value = {
            "trigger_source": "manual",
            "user_id": 1,
            "category_id": 1,
            "start_time": "2025-11-11T10:00:00+00:00",
            "end_time": "2025-11-11T11:00:00+00:00"
        }

        with patch('src.api.handlers.activity.activity_creation.validate_description') as mock_validate:
            mock_validate.return_value = (True, None)

            with patch('src.api.handlers.activity.activity_creation.extract_tags') as mock_extract:
                mock_extract.return_value = ["work", "coding"]

                with patch('src.api.handlers.activity.activity_creation.create_and_save_activity') as mock_create:
                    mock_create.return_value = True

                    # Act
                    await process_description(mock_message, mock_state, mock_services)

        # Assert: Tags extracted
        mock_extract.assert_called_once_with("Working on project #work #coding")

        # Assert: Tags saved
        call_kwargs = mock_state.update_data.call_args.kwargs
        assert call_kwargs["tags"] == ["work", "coding"]


class TestHandleCancel:
    """Test suite for handle_cancel handler."""

    @pytest.mark.unit
    async def test_handle_cancel_clears_state_and_shows_message(
        self,
        mock_callback,
        mock_state
    ):
        """
        Test cancel operation.

        GIVEN: User clicks cancel button
        WHEN: handle_cancel is called
        THEN: FSM state is cleared
              AND timeout is cancelled
              AND confirmation message shown
        """
        # Arrange
        with patch('src.api.handlers.activity.activity_creation.cancel_fsm_timeout') as mock_cancel_timeout:
            # Act
            await handle_cancel(mock_callback, mock_state)

        # Assert: State cleared
        mock_state.clear.assert_called_once()

        # Assert: Timeout cancelled
        mock_cancel_timeout.assert_called_once()

        # Assert: Confirmation message
        mock_callback.message.answer.assert_called_once()
        message_text = mock_callback.message.answer.call_args[0][0]
        assert "отменена" in message_text.lower()

        # Assert: Callback answered
        mock_callback.answer.assert_called_once()


class TestSaveActivity:
    """Test suite for save_activity wrapper function."""

    @pytest.mark.unit
    async def test_save_activity_delegates_to_shared_function(
        self,
        mock_message,
        mock_state,
        mock_services
    ):
        """
        Test save_activity delegates to shared create_and_save_activity.

        GIVEN: Valid state data
        WHEN: save_activity is called
        THEN: create_and_save_activity from shared module is called
        """
        # Arrange
        mock_state.get_data.return_value = {
            "user_id": 1,
            "category_id": 1,
            "start_time": "2025-11-11T10:00:00+00:00",
            "end_time": "2025-11-11T11:00:00+00:00",
            "description": "Test activity"
        }

        with patch('src.api.handlers.activity.activity_creation.create_and_save_activity') as mock_create:
            mock_create.return_value = True

            # Act
            await save_activity(
                mock_message,
                mock_state,
                user_id=1,
                category_id=1,
                telegram_user_id=123456789,
                services=mock_services
            )

        # Assert: Shared function called
        mock_create.assert_called_once()

        # Assert: Correct parameters passed
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs["user_id"] == 1
        assert call_kwargs["category_id"] == 1


class TestCreatePollSchedulingCallback:
    """Test suite for _create_poll_scheduling_callback helper."""

    @pytest.mark.unit
    async def test_callback_schedules_next_poll(
        self,
        mock_services,
        sample_user,
        sample_settings
    ):
        """
        Test poll scheduling callback creation.

        GIVEN: User, settings, and bot instance
        WHEN: Callback is executed
        THEN: Next poll is scheduled via scheduler service
        """
        # Arrange
        bot = MagicMock()
        activity_data = {"id": 1}

        # Create callback
        callback = _create_poll_scheduling_callback(
            bot=bot,
            user=sample_user,
            settings=sample_settings,
            services=mock_services,
            telegram_user_id=123456789
        )

        with patch('src.api.handlers.activity.activity_creation.schedule_next_poll') as mock_schedule:
            # Act
            await callback(activity_data)

        # Assert: schedule_next_poll called
        mock_schedule.assert_called_once()
        call_args = mock_schedule.call_args.kwargs
        assert call_args["bot"] == bot
        assert call_args["user_id"] == 123456789
        assert call_args["services"] == mock_services

    @pytest.mark.unit
    async def test_callback_handles_scheduling_error_gracefully(
        self,
        mock_services,
        sample_user,
        sample_settings
    ):
        """
        Test error handling in callback.

        GIVEN: schedule_next_poll raises exception
        WHEN: Callback is executed
        THEN: Error is caught and logged (doesn't propagate)
        """
        # Arrange
        bot = MagicMock()
        activity_data = {"id": 1}

        callback = _create_poll_scheduling_callback(
            bot=bot,
            user=sample_user,
            settings=sample_settings,
            services=mock_services,
            telegram_user_id=123456789
        )

        with patch('src.api.handlers.activity.activity_creation.schedule_next_poll') as mock_schedule:
            mock_schedule.side_effect = Exception("Scheduler error")

            # Act - should not raise
            await callback(activity_data)

        # Assert: Exception was caught (no assertion needed - test passes if no exception)
