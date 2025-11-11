"""
Unit tests for shared activity handler functions.

This module tests the shared functions used by both manual and automatic
activity recording flows, ensuring DRY principle compliance and proper
error handling.

Test Coverage:
    - validate_description: Input validation with various edge cases
    - fetch_and_build_description_prompt: Prompt building with/without recent activities
    - create_and_save_activity: Activity saving with optional post-save callbacks

Coverage Target: 100% of shared.py
Execution Time: < 0.5 seconds

Author: Testing Team
Date: 2025-11-11
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, call
from aiogram import types
from aiogram.fsm.context import FSMContext

from src.api.handlers.activity.shared import (
    validate_description,
    fetch_and_build_description_prompt,
    create_and_save_activity
)


# ============================================================================
# TEST FIXTURES
# ============================================================================

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
def sample_activities():
    """Fixture: Sample recent activities."""
    return [
        {
            "id": 1,
            "description": "Работа над проектом #работа",
            "start_time": "2025-11-11T10:00:00+00:00",
            "end_time": "2025-11-11T12:00:00+00:00",
            "duration_minutes": 120
        },
        {
            "id": 2,
            "description": "Встреча с командой",
            "start_time": "2025-11-11T14:00:00+00:00",
            "end_time": "2025-11-11T15:00:00+00:00",
            "duration_minutes": 60
        }
    ]


# ============================================================================
# TEST SUITES
# ============================================================================

class TestValidateDescription:
    """Test suite for validate_description function."""

    @pytest.mark.unit
    def test_validate_description_valid_input_returns_true_and_none(self):
        """
        Test that valid description passes validation.

        GIVEN: Description with >= 3 characters
        WHEN: validate_description is called
        THEN: Returns (True, None)
        """
        # Arrange
        description = "Работа над проектом"

        # Act
        is_valid, error_msg = validate_description(description)

        # Assert
        assert is_valid is True
        assert error_msg is None

    @pytest.mark.unit
    def test_validate_description_too_short_returns_false_and_error(self):
        """
        Test that too short description fails validation.

        GIVEN: Description with < 3 characters
        WHEN: validate_description is called
        THEN: Returns (False, error_message)
        """
        # Arrange
        description = "ab"

        # Act
        is_valid, error_msg = validate_description(description)

        # Assert
        assert is_valid is False
        assert error_msg is not None
        assert "минимум 3 символа" in error_msg

    @pytest.mark.unit
    def test_validate_description_empty_string_returns_false(self):
        """
        Test that empty string fails validation.

        GIVEN: Empty description string
        WHEN: validate_description is called
        THEN: Returns (False, error_message)
        """
        # Arrange
        description = ""

        # Act
        is_valid, error_msg = validate_description(description)

        # Assert
        assert is_valid is False
        assert error_msg is not None

    @pytest.mark.unit
    def test_validate_description_only_whitespace_returns_false(self):
        """
        Test that whitespace-only string fails validation.

        GIVEN: Description with only whitespace
        WHEN: validate_description is called
        THEN: Returns (False, error_message)
              AND whitespace is stripped before checking
        """
        # Arrange
        description = "   \t\n  "

        # Act
        is_valid, error_msg = validate_description(description)

        # Assert
        assert is_valid is False
        assert error_msg is not None

    @pytest.mark.unit
    def test_validate_description_exact_min_length_returns_true(self):
        """
        Test that description with exact minimum length passes.

        GIVEN: Description with exactly 3 characters
        WHEN: validate_description is called
        THEN: Returns (True, None)
        """
        # Arrange
        description = "abc"

        # Act
        is_valid, error_msg = validate_description(description)

        # Assert
        assert is_valid is True
        assert error_msg is None

    @pytest.mark.unit
    def test_validate_description_custom_min_length_works(self):
        """
        Test that custom min_length parameter is respected.

        GIVEN: Description of 5 characters and min_length=5
        WHEN: validate_description is called
        THEN: Returns (True, None)
        """
        # Arrange
        description = "12345"

        # Act
        is_valid, error_msg = validate_description(description, min_length=5)

        # Assert
        assert is_valid is True
        assert error_msg is None

    @pytest.mark.unit
    def test_validate_description_unicode_and_emoji_works(self):
        """
        Test that Unicode and emoji characters are supported.

        GIVEN: Description with Cyrillic and emoji
        WHEN: validate_description is called
        THEN: Returns (True, None)
              AND counts characters correctly
        """
        # Arrange
        description = "🎉 Успех"

        # Act
        is_valid, error_msg = validate_description(description)

        # Assert
        assert is_valid is True
        assert error_msg is None


class TestFetchAndBuildDescriptionPrompt:
    """Test suite for fetch_and_build_description_prompt function."""

    @pytest.mark.unit
    async def test_fetch_with_recent_activities_returns_text_and_keyboard(
        self,
        mock_services,
        sample_activities
    ):
        """
        Test that recent activities result in keyboard with suggestions.

        GIVEN: Recent activities exist for category
        WHEN: fetch_and_build_description_prompt is called
        THEN: Returns (text, keyboard)
              AND keyboard is not None
              AND text mentions "Выбери из последних"
        """
        # Arrange
        mock_services.activity.get_user_activities_by_category.return_value = {
            "activities": sample_activities
        }
        start_time = datetime(2025, 11, 11, 10, 0, tzinfo=timezone.utc)
        end_time = datetime(2025, 11, 11, 12, 0, tzinfo=timezone.utc)

        # Act
        text, keyboard = await fetch_and_build_description_prompt(
            services=mock_services,
            user_id=1,
            category_id=5,
            start_time=start_time,
            end_time=end_time,
            limit=20
        )

        # Assert
        assert isinstance(text, str)
        assert keyboard is not None
        assert "Выбери из последних" in text
        assert "10:00 — 12:00" in text
        assert "2ч" in text
        mock_services.activity.get_user_activities_by_category.assert_called_once_with(
            user_id=1,
            category_id=5,
            limit=20
        )

    @pytest.mark.unit
    async def test_fetch_without_activities_returns_text_and_none(
        self,
        mock_services
    ):
        """
        Test that no recent activities results in None keyboard.

        GIVEN: No recent activities for category
        WHEN: fetch_and_build_description_prompt is called
        THEN: Returns (text, None)
              AND text mentions "Напиши, чем ты занимался"
        """
        # Arrange
        mock_services.activity.get_user_activities_by_category.return_value = {
            "activities": []
        }
        start_time = datetime(2025, 11, 11, 10, 0, tzinfo=timezone.utc)
        end_time = datetime(2025, 11, 11, 12, 0, tzinfo=timezone.utc)

        # Act
        text, keyboard = await fetch_and_build_description_prompt(
            services=mock_services,
            user_id=1,
            category_id=5,
            start_time=start_time,
            end_time=end_time
        )

        # Assert
        assert isinstance(text, str)
        assert keyboard is None
        assert "Напиши, чем ты занимался" in text

    @pytest.mark.unit
    async def test_fetch_formats_time_correctly(
        self,
        mock_services,
        sample_activities
    ):
        """
        Test that time is formatted correctly in prompt.

        GIVEN: Specific start and end times
        WHEN: fetch_and_build_description_prompt is called
        THEN: Text contains formatted time range
        """
        # Arrange
        mock_services.activity.get_user_activities_by_category.return_value = {
            "activities": sample_activities
        }
        start_time = datetime(2025, 11, 11, 14, 30, tzinfo=timezone.utc)
        end_time = datetime(2025, 11, 11, 16, 45, tzinfo=timezone.utc)

        # Act
        text, _ = await fetch_and_build_description_prompt(
            services=mock_services,
            user_id=1,
            category_id=5,
            start_time=start_time,
            end_time=end_time
        )

        # Assert
        assert "14:30" in text
        assert "16:45" in text

    @pytest.mark.unit
    async def test_fetch_calculates_duration_correctly(
        self,
        mock_services,
        sample_activities
    ):
        """
        Test that duration is calculated and formatted correctly.

        GIVEN: Start and end times with 2h 15m difference
        WHEN: fetch_and_build_description_prompt is called
        THEN: Text contains "2ч 15м"
        """
        # Arrange
        mock_services.activity.get_user_activities_by_category.return_value = {
            "activities": sample_activities
        }
        start_time = datetime(2025, 11, 11, 10, 0, tzinfo=timezone.utc)
        end_time = datetime(2025, 11, 11, 12, 15, tzinfo=timezone.utc)

        # Act
        text, _ = await fetch_and_build_description_prompt(
            services=mock_services,
            user_id=1,
            category_id=5,
            start_time=start_time,
            end_time=end_time
        )

        # Assert
        assert "2ч 15м" in text or "2ч15м" in text or "135м" in text

    @pytest.mark.unit
    async def test_fetch_service_error_returns_empty_activities(
        self,
        mock_services
    ):
        """
        Test that service error is handled gracefully.

        GIVEN: Service raises exception
        WHEN: fetch_and_build_description_prompt is called
        THEN: Returns (text, None)
              AND no exception is raised
        """
        # Arrange
        mock_services.activity.get_user_activities_by_category.side_effect = Exception("DB error")
        start_time = datetime(2025, 11, 11, 10, 0, tzinfo=timezone.utc)
        end_time = datetime(2025, 11, 11, 12, 0, tzinfo=timezone.utc)

        # Act
        text, keyboard = await fetch_and_build_description_prompt(
            services=mock_services,
            user_id=1,
            category_id=5,
            start_time=start_time,
            end_time=end_time
        )

        # Assert
        assert isinstance(text, str)
        assert keyboard is None

    @pytest.mark.unit
    async def test_fetch_limit_parameter_controls_activities_count(
        self,
        mock_services,
        sample_activities
    ):
        """
        Test that limit parameter is passed to service correctly.

        GIVEN: limit=5 is specified
        WHEN: fetch_and_build_description_prompt is called
        THEN: Service is called with limit=5
        """
        # Arrange
        mock_services.activity.get_user_activities_by_category.return_value = {
            "activities": sample_activities
        }
        start_time = datetime(2025, 11, 11, 10, 0, tzinfo=timezone.utc)
        end_time = datetime(2025, 11, 11, 12, 0, tzinfo=timezone.utc)

        # Act
        await fetch_and_build_description_prompt(
            services=mock_services,
            user_id=1,
            category_id=5,
            start_time=start_time,
            end_time=end_time,
            limit=5
        )

        # Assert
        mock_services.activity.get_user_activities_by_category.assert_called_once_with(
            user_id=1,
            category_id=5,
            limit=5
        )


class TestCreateAndSaveActivity:
    """Test suite for create_and_save_activity function."""

    @pytest.mark.unit
    async def test_create_successful_save_without_callback(
        self,
        mock_message,
        mock_state,
        mock_services
    ):
        """
        Test successful activity save without post_save_callback.

        GIVEN: Valid state data and no callback
        WHEN: create_and_save_activity is called
        THEN: Activity is created
              AND success message is sent
              AND FSM state is cleared
              AND function returns True
        """
        # Arrange
        mock_state.get_data.return_value = {
            "user_id": 1,
            "category_id": 5,
            "start_time": "2025-11-11T10:00:00+00:00",
            "end_time": "2025-11-11T12:00:00+00:00"
        }
        mock_services.activity.create_activity.return_value = None

        # Act
        with patch('src.api.handlers.activity.shared.fsm_timeout_module') as mock_timeout:
            mock_timeout.fsm_timeout_service = MagicMock()
            result = await create_and_save_activity(
                message=mock_message,
                state=mock_state,
                services=mock_services,
                telegram_user_id=123456789,
                description="Работа над проектом",
                tags=["работа"],
                post_save_callback=None
            )

        # Assert
        assert result is True
        mock_services.activity.create_activity.assert_called_once()
        mock_message.answer.assert_called_once()
        mock_state.clear.assert_called_once()

    @pytest.mark.unit
    async def test_create_successful_save_with_callback(
        self,
        mock_message,
        mock_state,
        mock_services
    ):
        """
        Test successful save with post_save_callback execution.

        GIVEN: Valid state data and async callback
        WHEN: create_and_save_activity is called
        THEN: Activity is created
              AND callback is called with state_data
              AND function returns True
        """
        # Arrange
        state_data = {
            "user_id": 1,
            "category_id": 5,
            "start_time": "2025-11-11T10:00:00+00:00",
            "end_time": "2025-11-11T12:00:00+00:00",
            "settings": {"poll_interval": 120},
            "user_timezone": "Europe/Moscow"
        }
        mock_state.get_data.return_value = state_data
        mock_callback = AsyncMock()

        # Act
        with patch('src.api.handlers.activity.shared.fsm_timeout_module') as mock_timeout:
            mock_timeout.fsm_timeout_service = MagicMock()
            result = await create_and_save_activity(
                message=mock_message,
                state=mock_state,
                services=mock_services,
                telegram_user_id=123456789,
                description="Встреча",
                tags=[],
                post_save_callback=mock_callback
            )

        # Assert
        assert result is True
        mock_callback.assert_called_once_with(state_data)

    @pytest.mark.unit
    async def test_create_missing_user_id_returns_false(
        self,
        mock_message,
        mock_state,
        mock_services
    ):
        """
        Test that missing user_id returns False.

        GIVEN: State data without user_id
        WHEN: create_and_save_activity is called
        THEN: Returns False
              AND error message is sent
              AND state is cleared
        """
        # Arrange
        mock_state.get_data.return_value = {
            "category_id": 5,
            "start_time": "2025-11-11T10:00:00+00:00",
            "end_time": "2025-11-11T12:00:00+00:00"
        }

        # Act
        result = await create_and_save_activity(
            message=mock_message,
            state=mock_state,
            services=mock_services,
            telegram_user_id=123456789,
            description="Test",
            tags=[]
        )

        # Assert
        assert result is False
        mock_message.answer.assert_called_once()
        assert "Недостаточно данных" in mock_message.answer.call_args[0][0]
        mock_state.clear.assert_called_once()

    @pytest.mark.unit
    async def test_create_missing_required_data_returns_false(
        self,
        mock_message,
        mock_state,
        mock_services
    ):
        """
        Test that missing required fields returns False.

        GIVEN: State data missing start_time
        WHEN: create_and_save_activity is called
        THEN: Returns False
              AND error message is sent
        """
        # Arrange
        mock_state.get_data.return_value = {
            "user_id": 1,
            "category_id": 5,
            "end_time": "2025-11-11T12:00:00+00:00"
        }

        # Act
        result = await create_and_save_activity(
            message=mock_message,
            state=mock_state,
            services=mock_services,
            telegram_user_id=123456789,
            description="Test",
            tags=[]
        )

        # Assert
        assert result is False

    @pytest.mark.unit
    async def test_create_invalid_time_format_returns_false(
        self,
        mock_message,
        mock_state,
        mock_services
    ):
        """
        Test that invalid time format is handled gracefully.

        GIVEN: State data with invalid ISO format time
        WHEN: create_and_save_activity is called
        THEN: Returns False
              AND error message is sent
        """
        # Arrange
        mock_state.get_data.return_value = {
            "user_id": 1,
            "category_id": 5,
            "start_time": "invalid-time",
            "end_time": "2025-11-11T12:00:00+00:00"
        }

        # Act
        with patch('src.api.handlers.activity.shared.fsm_timeout_module') as mock_timeout:
            mock_timeout.fsm_timeout_service = MagicMock()
            result = await create_and_save_activity(
                message=mock_message,
                state=mock_state,
                services=mock_services,
                telegram_user_id=123456789,
                description="Test",
                tags=[]
            )

        # Assert
        assert result is False
        mock_message.answer.assert_called()
        assert "Ошибка" in mock_message.answer.call_args[0][0]

    @pytest.mark.unit
    async def test_create_service_error_returns_false(
        self,
        mock_message,
        mock_state,
        mock_services
    ):
        """
        Test that service error during create is handled.

        GIVEN: Service raises exception during create_activity
        WHEN: create_and_save_activity is called
        THEN: Returns False
              AND error message is sent
              AND state is cleared
        """
        # Arrange
        mock_state.get_data.return_value = {
            "user_id": 1,
            "category_id": 5,
            "start_time": "2025-11-11T10:00:00+00:00",
            "end_time": "2025-11-11T12:00:00+00:00"
        }
        mock_services.activity.create_activity.side_effect = Exception("DB error")

        # Act
        with patch('src.api.handlers.activity.shared.fsm_timeout_module') as mock_timeout:
            mock_timeout.fsm_timeout_service = MagicMock()
            result = await create_and_save_activity(
                message=mock_message,
                state=mock_state,
                services=mock_services,
                telegram_user_id=123456789,
                description="Test",
                tags=[]
            )

        # Assert
        assert result is False
        mock_state.clear.assert_called_once()

    @pytest.mark.unit
    async def test_create_clears_fsm_state_after_save(
        self,
        mock_message,
        mock_state,
        mock_services
    ):
        """
        Test that FSM state is cleared after successful save.

        GIVEN: Successful activity creation
        WHEN: create_and_save_activity completes
        THEN: state.clear() is called
        """
        # Arrange
        mock_state.get_data.return_value = {
            "user_id": 1,
            "category_id": 5,
            "start_time": "2025-11-11T10:00:00+00:00",
            "end_time": "2025-11-11T12:00:00+00:00"
        }

        # Act
        with patch('src.api.handlers.activity.shared.fsm_timeout_module') as mock_timeout:
            mock_timeout.fsm_timeout_service = MagicMock()
            await create_and_save_activity(
                message=mock_message,
                state=mock_state,
                services=mock_services,
                telegram_user_id=123456789,
                description="Test",
                tags=[]
            )

        # Assert
        mock_state.clear.assert_called_once()

    @pytest.mark.unit
    async def test_create_cancels_fsm_timeout(
        self,
        mock_message,
        mock_state,
        mock_services
    ):
        """
        Test that FSM timeout is cancelled after save.

        GIVEN: Successful activity creation
        WHEN: create_and_save_activity completes
        THEN: fsm_timeout_service.cancel_timeout() is called
        """
        # Arrange
        mock_state.get_data.return_value = {
            "user_id": 1,
            "category_id": 5,
            "start_time": "2025-11-11T10:00:00+00:00",
            "end_time": "2025-11-11T12:00:00+00:00"
        }

        # Act
        with patch('src.api.handlers.activity.shared.fsm_timeout_module') as mock_timeout:
            mock_timeout_service = MagicMock()
            mock_timeout.fsm_timeout_service = mock_timeout_service
            await create_and_save_activity(
                message=mock_message,
                state=mock_state,
                services=mock_services,
                telegram_user_id=123456789,
                description="Test",
                tags=[]
            )

        # Assert
        mock_timeout_service.cancel_timeout.assert_called_once_with(123456789)

    @pytest.mark.unit
    async def test_create_callback_error_does_not_fail_save(
        self,
        mock_message,
        mock_state,
        mock_services
    ):
        """
        Test that callback error doesn't fail the save operation.

        GIVEN: post_save_callback raises exception
        WHEN: create_and_save_activity is called
        THEN: Activity is still saved
              AND function returns True
              AND error is logged but not raised
        """
        # Arrange
        mock_state.get_data.return_value = {
            "user_id": 1,
            "category_id": 5,
            "start_time": "2025-11-11T10:00:00+00:00",
            "end_time": "2025-11-11T12:00:00+00:00"
        }
        mock_callback = AsyncMock(side_effect=Exception("Callback failed"))

        # Act
        with patch('src.api.handlers.activity.shared.fsm_timeout_module') as mock_timeout:
            mock_timeout.fsm_timeout_service = MagicMock()
            result = await create_and_save_activity(
                message=mock_message,
                state=mock_state,
                services=mock_services,
                telegram_user_id=123456789,
                description="Test",
                tags=[],
                post_save_callback=mock_callback
            )

        # Assert
        assert result is True
        mock_services.activity.create_activity.assert_called_once()

    @pytest.mark.unit
    async def test_create_success_message_includes_duration(
        self,
        mock_message,
        mock_state,
        mock_services
    ):
        """
        Test that success message includes formatted duration.

        GIVEN: Activity with 2h duration
        WHEN: create_and_save_activity succeeds
        THEN: Success message contains "2ч"
        """
        # Arrange
        mock_state.get_data.return_value = {
            "user_id": 1,
            "category_id": 5,
            "start_time": "2025-11-11T10:00:00+00:00",
            "end_time": "2025-11-11T12:00:00+00:00"
        }

        # Act
        with patch('src.api.handlers.activity.shared.fsm_timeout_module') as mock_timeout:
            mock_timeout.fsm_timeout_service = MagicMock()
            await create_and_save_activity(
                message=mock_message,
                state=mock_state,
                services=mock_services,
                telegram_user_id=123456789,
                description="Работа",
                tags=[]
            )

        # Assert
        success_msg = mock_message.answer.call_args[0][0]
        assert "Активность сохранена" in success_msg
        assert "2ч" in success_msg
