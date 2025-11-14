"""
Unit tests for AIService and AIParsingResult.

Tests AI-powered natural language parsing service that converts user text
into structured activity data using OpenRouter API with automatic failover.

Test Coverage:
    - AIParsingResult: Initialization, completeness checking, representation
    - AIService initialization: With/without API key
    - parse_activity_text(): Success, failover, timeout, errors
    - _call_ai_with_timeout(): Response parsing, timeouts, JSON errors
    - _build_prompt(): Context construction with categories and history
    - Model failover: Rating updates, automatic switching

Coverage Target: 90%+
Execution Time: < 0.5 seconds

Author: Testing Team
Date: 2025-11-14
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch, mock_open
from datetime import datetime, timezone
import json
import asyncio

from openai import APITimeoutError, APIError

from src.application.services.ai_service import AIService, AIParsingResult


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def mock_openai_client():
    """
    Fixture: Mock AsyncOpenAI client.

    Returns:
        AsyncMock: Mocked OpenAI client for testing without API calls
    """
    client = AsyncMock()
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = json.dumps({
        "confidence": "high",
        "category": "Работа",
        "description": "Coding",
        "start_time": "2025-11-14T10:00:00+00:00",
        "end_time": "2025-11-14T12:00:00+00:00",
        "alternatives": [
            {"category": "Образование", "description": "Learning", "start_time": None, "end_time": None},
            {"category": "Хобби", "description": "Side project", "start_time": None, "end_time": None}
        ]
    })
    client.chat.completions.create = AsyncMock(return_value=response)
    return client


@pytest.fixture
def mock_model_selector():
    """
    Fixture: Mock AIModelSelector.

    Returns:
        MagicMock: Mocked model selector for testing failover
    """
    selector = MagicMock()
    selector.get_best_model.return_value = "meta-llama/llama-3.2-3b-instruct:free"
    selector.get_next_model.return_value = "google/gemma-2-9b-it:free"
    selector.increase_rating = MagicMock()
    selector.decrease_rating = MagicMock()
    return selector


@pytest.fixture
def sample_categories():
    """
    Fixture: Sample user categories.

    Returns:
        list: List of category dictionaries
    """
    return [
        {"name": "Работа", "emoji": "💼"},
        {"name": "Образование", "emoji": "📚"},
        {"name": "Спорт", "emoji": "⚽"}
    ]


@pytest.fixture
def sample_recent_activities():
    """
    Fixture: Sample recent activities for context.

    Returns:
        list: List of recent activity dictionaries
    """
    return [
        {"category_name": "Работа", "description": "Coding task"},
        {"category_name": "Спорт", "description": "Running"}
    ]


@pytest.fixture
def sample_ai_response_data():
    """
    Fixture: Sample AI response data.

    Returns:
        dict: Parsed AI response
    """
    return {
        "confidence": "high",
        "category": "Работа",
        "description": "Coding session",
        "start_time": "2025-11-14T10:00:00+00:00",
        "end_time": "2025-11-14T12:00:00+00:00",
        "alternatives": []
    }


# ============================================================================
# TEST SUITES - AIParsingResult
# ============================================================================

class TestAIParsingResult:
    """
    Test suite for AIParsingResult class.
    """

    @pytest.mark.unit
    def test_init_stores_all_fields_from_data(self, sample_ai_response_data):
        """
        Test initialization stores all response fields.

        GIVEN: AI response data dictionary
        WHEN: AIParsingResult is instantiated
        THEN: All fields are correctly stored
        """
        # Act
        result = AIParsingResult(sample_ai_response_data)

        # Assert
        assert result.confidence == "high"
        assert result.category_name == "Работа"
        assert result.description == "Coding session"
        assert result.start_time == "2025-11-14T10:00:00+00:00"
        assert result.end_time == "2025-11-14T12:00:00+00:00"
        assert result.alternatives == []
        assert result.raw_response == sample_ai_response_data

    @pytest.mark.unit
    def test_init_with_missing_fields_uses_defaults(self):
        """
        Test initialization with incomplete data.

        GIVEN: Response with missing fields
        WHEN: AIParsingResult is instantiated
        THEN: Default values are used (None or "low")
        """
        # Arrange
        incomplete_data = {
            "category": "Работа"
        }

        # Act
        result = AIParsingResult(incomplete_data)

        # Assert
        assert result.confidence == "low"  # Default
        assert result.category_name == "Работа"
        assert result.description is None
        assert result.start_time is None
        assert result.end_time is None
        assert result.alternatives == []

    @pytest.mark.unit
    def test_is_complete_returns_true_when_all_required_fields_present(
        self,
        sample_ai_response_data
    ):
        """
        Test completeness check with all fields.

        GIVEN: Response with all required fields (category, description, times)
        WHEN: is_complete() is called
        THEN: Returns True
        """
        # Arrange
        result = AIParsingResult(sample_ai_response_data)

        # Act & Assert
        assert result.is_complete() is True

    @pytest.mark.unit
    @pytest.mark.parametrize("missing_field", [
        "category",
        "description",
        "start_time",
        "end_time"
    ])
    def test_is_complete_returns_false_when_required_field_missing(
        self,
        sample_ai_response_data,
        missing_field
    ):
        """
        Test completeness check with missing required field.

        GIVEN: Response missing one required field
        WHEN: is_complete() is called
        THEN: Returns False
        """
        # Arrange
        data = sample_ai_response_data.copy()
        data[missing_field] = None
        result = AIParsingResult(data)

        # Act & Assert
        assert result.is_complete() is False

    @pytest.mark.unit
    def test_repr_contains_key_information(self, sample_ai_response_data):
        """
        Test string representation.

        GIVEN: AIParsingResult instance
        WHEN: repr() is called
        THEN: Returns string with confidence, category, and completeness
        """
        # Arrange
        result = AIParsingResult(sample_ai_response_data)

        # Act
        repr_str = repr(result)

        # Assert
        assert "AIParsingResult" in repr_str
        assert "confidence=high" in repr_str
        assert "category=Работа" in repr_str
        assert "complete=True" in repr_str


# ============================================================================
# TEST SUITES - AIService Initialization
# ============================================================================

class TestAIServiceInitialization:
    """
    Test suite for AIService initialization.
    """

    @pytest.mark.unit
    @patch('src.application.services.ai_service.settings')
    @patch('src.application.services.ai_service.AIModelSelector')
    @patch('src.application.services.ai_service.AsyncOpenAI')
    def test_init_with_api_key_enables_service(
        self,
        mock_async_openai,
        mock_model_selector_class,
        mock_settings
    ):
        """
        Test initialization with valid API key.

        GIVEN: OpenRouter API key is configured
        WHEN: AIService is instantiated
        THEN: Service is enabled
              AND OpenAI client is created
              AND model selector is initialized
        """
        # Arrange
        mock_settings.openrouter_api_key = "test_api_key"

        # Act
        service = AIService()

        # Assert
        assert service.enabled is True
        assert service.api_key == "test_api_key"
        mock_async_openai.assert_called_once_with(
            api_key="test_api_key",
            base_url="https://openrouter.ai/api/v1"
        )
        mock_model_selector_class.assert_called_once()

    @pytest.mark.unit
    @patch('src.application.services.ai_service.settings')
    @patch('src.application.services.ai_service.AIModelSelector')
    def test_init_without_api_key_disables_service(
        self,
        mock_model_selector_class,
        mock_settings
    ):
        """
        Test initialization without API key.

        GIVEN: OpenRouter API key is not configured (None)
        WHEN: AIService is instantiated
        THEN: Service is disabled
              AND client is not created
        """
        # Arrange
        mock_settings.openrouter_api_key = None

        # Act
        service = AIService()

        # Assert
        assert service.enabled is False
        assert service.api_key is None
        assert not hasattr(service, 'client')


# ============================================================================
# TEST SUITES - parse_activity_text()
# ============================================================================

class TestAIServiceParseActivityText:
    """
    Test suite for parse_activity_text() method.
    """

    @pytest.mark.unit
    @patch('src.application.services.ai_service.settings')
    @patch('src.application.services.ai_service.AsyncOpenAI')
    async def test_parse_with_disabled_service_returns_none(
        self,
        mock_async_openai,
        mock_settings,
        sample_categories
    ):
        """
        Test parsing when service is disabled.

        GIVEN: AI service is disabled (no API key)
        WHEN: parse_activity_text() is called
        THEN: Returns None without making API calls
        """
        # Arrange
        mock_settings.openrouter_api_key = None
        service = AIService()

        # Act
        result = await service.parse_activity_text(
            user_input="читал книгу 2 часа",
            categories=sample_categories
        )

        # Assert
        assert result is None

    @pytest.mark.unit
    @patch('src.application.services.ai_service.settings')
    @patch('src.application.services.ai_service.AsyncOpenAI')
    async def test_parse_with_successful_first_attempt_returns_result(
        self,
        mock_async_openai_class,
        mock_settings,
        mock_openai_client,
        mock_model_selector,
        sample_categories
    ):
        """
        Test successful parsing on first attempt.

        GIVEN: AI service is enabled
              AND first model responds successfully
        WHEN: parse_activity_text() is called
        THEN: Returns AIParsingResult
              AND model rating is increased
        """
        # Arrange
        mock_settings.openrouter_api_key = "test_key"
        mock_async_openai_class.return_value = mock_openai_client

        service = AIService()
        service.model_selector = mock_model_selector

        # Act
        result = await service.parse_activity_text(
            user_input="работал над проектом с 10:00 до 12:00",
            categories=sample_categories
        )

        # Assert
        assert result is not None
        assert isinstance(result, AIParsingResult)
        assert result.confidence == "high"
        assert result.category_name == "Работа"

        # Model rating increased
        mock_model_selector.increase_rating.assert_called_once_with(
            "meta-llama/llama-3.2-3b-instruct:free"
        )

    @pytest.mark.unit
    @patch('src.application.services.ai_service.settings')
    @patch('src.application.services.ai_service.AsyncOpenAI')
    async def test_parse_with_timeout_switches_to_next_model(
        self,
        mock_async_openai_class,
        mock_settings,
        mock_model_selector,
        sample_categories
    ):
        """
        Test model failover on timeout.

        GIVEN: First model times out
              AND second model succeeds
        WHEN: parse_activity_text() is called
        THEN: Switches to second model
              AND returns result from second model
        """
        # Arrange
        mock_settings.openrouter_api_key = "test_key"

        # First model timeouts, second succeeds
        mock_client = AsyncMock()
        first_call = AsyncMock(side_effect=asyncio.TimeoutError())
        second_response = MagicMock()
        second_response.choices = [MagicMock()]
        second_response.choices[0].message.content = json.dumps({
            "confidence": "medium",
            "category": "Работа",
            "description": "Task",
            "start_time": None,
            "end_time": None,
            "alternatives": []
        })
        second_call = AsyncMock(return_value=second_response)

        mock_client.chat.completions.create.side_effect = [first_call(), second_call()]
        mock_async_openai_class.return_value = mock_client

        # Model selector returns different models
        mock_model_selector.get_best_model.return_value = "model1"
        mock_model_selector.get_next_model.return_value = "model2"

        service = AIService()
        service.model_selector = mock_model_selector

        # Act
        with patch('src.application.services.ai_service.asyncio.wait_for') as mock_wait_for:
            # First call times out, second succeeds
            mock_wait_for.side_effect = [
                asyncio.TimeoutError(),
                second_response
            ]

            result = await service.parse_activity_text(
                user_input="test",
                categories=sample_categories
            )

        # Assert
        assert result is not None
        assert result.confidence == "medium"

        # get_next_model was called after timeout
        mock_model_selector.get_next_model.assert_called_once_with("model1")

    @pytest.mark.unit
    @patch('src.application.services.ai_service.settings')
    @patch('src.application.services.ai_service.AsyncOpenAI')
    async def test_parse_with_all_models_failing_returns_none(
        self,
        mock_async_openai_class,
        mock_settings,
        mock_model_selector,
        sample_categories
    ):
        """
        Test behavior when all models fail.

        GIVEN: All 3 model attempts timeout
        WHEN: parse_activity_text() is called with max_retries=3
        THEN: Returns None after exhausting retries
        """
        # Arrange
        mock_settings.openrouter_api_key = "test_key"

        mock_client = AsyncMock()
        mock_async_openai_class.return_value = mock_client

        mock_model_selector.get_best_model.return_value = "model1"
        mock_model_selector.get_next_model.side_effect = ["model2", "model3", None]

        service = AIService()
        service.model_selector = mock_model_selector

        # Act
        with patch('src.application.services.ai_service.asyncio.wait_for') as mock_wait_for:
            mock_wait_for.side_effect = asyncio.TimeoutError()

            result = await service.parse_activity_text(
                user_input="test",
                categories=sample_categories,
                max_retries=3
            )

        # Assert
        assert result is None
        assert mock_model_selector.get_next_model.call_count == 3

    @pytest.mark.unit
    @patch('src.application.services.ai_service.settings')
    @patch('src.application.services.ai_service.AsyncOpenAI')
    async def test_parse_with_api_error_switches_to_next_model(
        self,
        mock_async_openai_class,
        mock_settings,
        mock_model_selector,
        sample_categories
    ):
        """
        Test model failover on API error.

        GIVEN: First model raises APIError
              AND second model succeeds
        WHEN: parse_activity_text() is called
        THEN: Switches to second model automatically
        """
        # Arrange
        mock_settings.openrouter_api_key = "test_key"

        mock_client = AsyncMock()
        mock_async_openai_class.return_value = mock_client

        mock_model_selector.get_best_model.return_value = "model1"
        mock_model_selector.get_next_model.return_value = "model2"

        service = AIService()
        service.model_selector = mock_model_selector

        # First attempt raises APIError, second succeeds
        success_response = MagicMock()
        success_response.choices = [MagicMock()]
        success_response.choices[0].message.content = json.dumps({
            "confidence": "high",
            "category": "Test",
            "description": "Test",
            "start_time": None,
            "end_time": None,
            "alternatives": []
        })

        # Act
        with patch('src.application.services.ai_service.asyncio.wait_for') as mock_wait_for:
            mock_wait_for.side_effect = [
                APIError("API Error"),
                success_response
            ]

            result = await service.parse_activity_text(
                user_input="test",
                categories=sample_categories
            )

        # Assert
        assert result is not None
        mock_model_selector.get_next_model.assert_called_once()

    @pytest.mark.unit
    @patch('src.application.services.ai_service.settings')
    @patch('src.application.services.ai_service.AsyncOpenAI')
    async def test_parse_includes_recent_activities_in_context(
        self,
        mock_async_openai_class,
        mock_settings,
        mock_openai_client,
        mock_model_selector,
        sample_categories,
        sample_recent_activities
    ):
        """
        Test that recent activities are included in prompt.

        GIVEN: Recent activities are provided
        WHEN: parse_activity_text() is called
        THEN: Prompt includes activity history for context
        """
        # Arrange
        mock_settings.openrouter_api_key = "test_key"
        mock_async_openai_class.return_value = mock_openai_client

        service = AIService()
        service.model_selector = mock_model_selector

        # Act
        with patch.object(service, '_build_prompt', return_value="test_prompt") as mock_build:
            await service.parse_activity_text(
                user_input="test",
                categories=sample_categories,
                recent_activities=sample_recent_activities
            )

            # Assert: _build_prompt was called with activities
            mock_build.assert_called_once_with(
                "test",
                sample_categories,
                sample_recent_activities
            )


# ============================================================================
# TEST SUITES - _call_ai_with_timeout()
# ============================================================================

class TestAIServiceCallAIWithTimeout:
    """
    Test suite for _call_ai_with_timeout() method.
    """

    @pytest.mark.unit
    @patch('src.application.services.ai_service.settings')
    @patch('src.application.services.ai_service.AsyncOpenAI')
    async def test_call_ai_with_valid_response_returns_result(
        self,
        mock_async_openai_class,
        mock_settings,
        mock_openai_client
    ):
        """
        Test successful AI call.

        GIVEN: AI returns valid JSON response
        WHEN: _call_ai_with_timeout() is called
        THEN: Returns AIParsingResult with parsed data
        """
        # Arrange
        mock_settings.openrouter_api_key = "test_key"
        mock_async_openai_class.return_value = mock_openai_client

        service = AIService()

        # Act
        with patch('src.application.services.ai_service.asyncio.wait_for') as mock_wait_for:
            mock_wait_for.return_value = mock_openai_client.chat.completions.create.return_value

            result = await service._call_ai_with_timeout(
                prompt="test prompt",
                model="test-model",
                timeout=1.0
            )

        # Assert
        assert result is not None
        assert isinstance(result, AIParsingResult)
        assert result.confidence == "high"

    @pytest.mark.unit
    @patch('src.application.services.ai_service.settings')
    @patch('src.application.services.ai_service.AsyncOpenAI')
    async def test_call_ai_with_timeout_raises_timeout_error(
        self,
        mock_async_openai_class,
        mock_settings
    ):
        """
        Test timeout handling.

        GIVEN: AI call exceeds timeout
        WHEN: _call_ai_with_timeout() is called
        THEN: Raises asyncio.TimeoutError
        """
        # Arrange
        mock_settings.openrouter_api_key = "test_key"
        mock_client = AsyncMock()
        mock_async_openai_class.return_value = mock_client

        service = AIService()

        # Act & Assert
        with patch('src.application.services.ai_service.asyncio.wait_for') as mock_wait_for:
            mock_wait_for.side_effect = asyncio.TimeoutError()

            with pytest.raises(asyncio.TimeoutError):
                await service._call_ai_with_timeout(
                    prompt="test",
                    model="test-model",
                    timeout=1.0
                )

    @pytest.mark.unit
    @patch('src.application.services.ai_service.settings')
    @patch('src.application.services.ai_service.AsyncOpenAI')
    async def test_call_ai_with_empty_response_returns_none(
        self,
        mock_async_openai_class,
        mock_settings
    ):
        """
        Test handling of empty AI response.

        GIVEN: AI returns response with empty content
        WHEN: _call_ai_with_timeout() is called
        THEN: Returns None (gracefully handles empty response)
        """
        # Arrange
        mock_settings.openrouter_api_key = "test_key"

        mock_client = AsyncMock()
        empty_response = MagicMock()
        empty_response.choices = [MagicMock()]
        empty_response.choices[0].message.content = None  # Empty

        mock_async_openai_class.return_value = mock_client

        service = AIService()

        # Act
        with patch('src.application.services.ai_service.asyncio.wait_for') as mock_wait_for:
            mock_wait_for.return_value = empty_response

            result = await service._call_ai_with_timeout(
                prompt="test",
                model="test-model",
                timeout=1.0
            )

        # Assert
        assert result is None

    @pytest.mark.unit
    @patch('src.application.services.ai_service.settings')
    @patch('src.application.services.ai_service.AsyncOpenAI')
    async def test_call_ai_with_invalid_json_returns_none(
        self,
        mock_async_openai_class,
        mock_settings
    ):
        """
        Test handling of invalid JSON response.

        GIVEN: AI returns non-JSON content
        WHEN: _call_ai_with_timeout() is called
        THEN: Returns None (handles JSONDecodeError gracefully)
        """
        # Arrange
        mock_settings.openrouter_api_key = "test_key"

        mock_client = AsyncMock()
        invalid_response = MagicMock()
        invalid_response.choices = [MagicMock()]
        invalid_response.choices[0].message.content = "Not JSON!"

        mock_async_openai_class.return_value = mock_client

        service = AIService()

        # Act
        with patch('src.application.services.ai_service.asyncio.wait_for') as mock_wait_for:
            mock_wait_for.return_value = invalid_response

            result = await service._call_ai_with_timeout(
                prompt="test",
                model="test-model",
                timeout=1.0
            )

        # Assert
        assert result is None


# ============================================================================
# TEST SUITES - _build_prompt()
# ============================================================================

class TestAIServiceBuildPrompt:
    """
    Test suite for _build_prompt() method.
    """

    @pytest.mark.unit
    @patch('src.application.services.ai_service.settings')
    @patch('src.application.services.ai_service.AsyncOpenAI')
    @patch('src.application.services.ai_service.datetime')
    def test_build_prompt_includes_categories(
        self,
        mock_datetime,
        mock_async_openai,
        mock_settings,
        sample_categories
    ):
        """
        Test prompt includes all user categories.

        GIVEN: User has 3 categories
        WHEN: _build_prompt() is called
        THEN: All categories with emojis are in prompt
        """
        # Arrange
        mock_settings.openrouter_api_key = "test_key"
        mock_now = datetime(2025, 11, 14, 10, 30, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now

        service = AIService()

        # Act
        prompt = service._build_prompt(
            user_input="работал 2 часа",
            categories=sample_categories,
            recent_activities=None
        )

        # Assert
        assert "Работа 💼" in prompt
        assert "Образование 📚" in prompt
        assert "Спорт ⚽" in prompt

    @pytest.mark.unit
    @patch('src.application.services.ai_service.settings')
    @patch('src.application.services.ai_service.AsyncOpenAI')
    @patch('src.application.services.ai_service.datetime')
    def test_build_prompt_includes_recent_activities(
        self,
        mock_datetime,
        mock_async_openai,
        mock_settings,
        sample_categories,
        sample_recent_activities
    ):
        """
        Test prompt includes recent activity history.

        GIVEN: User has 2 recent activities
        WHEN: _build_prompt() is called with recent_activities
        THEN: Activity history is included for context
        """
        # Arrange
        mock_settings.openrouter_api_key = "test_key"
        mock_now = datetime(2025, 11, 14, 10, 30, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now

        service = AIService()

        # Act
        prompt = service._build_prompt(
            user_input="test",
            categories=sample_categories,
            recent_activities=sample_recent_activities
        )

        # Assert
        assert "Работа: Coding task" in prompt
        assert "Спорт: Running" in prompt

    @pytest.mark.unit
    @patch('src.application.services.ai_service.settings')
    @patch('src.application.services.ai_service.AsyncOpenAI')
    @patch('src.application.services.ai_service.datetime')
    def test_build_prompt_without_recent_activities_shows_placeholder(
        self,
        mock_datetime,
        mock_async_openai,
        mock_settings,
        sample_categories
    ):
        """
        Test prompt handles missing recent activities.

        GIVEN: No recent activities provided
        WHEN: _build_prompt() is called
        THEN: Placeholder text is shown
        """
        # Arrange
        mock_settings.openrouter_api_key = "test_key"
        mock_now = datetime(2025, 11, 14, 10, 30, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now

        service = AIService()

        # Act
        prompt = service._build_prompt(
            user_input="test",
            categories=sample_categories,
            recent_activities=None
        )

        # Assert
        assert "Нет данных" in prompt

    @pytest.mark.unit
    @patch('src.application.services.ai_service.settings')
    @patch('src.application.services.ai_service.AsyncOpenAI')
    @patch('src.application.services.ai_service.datetime')
    def test_build_prompt_includes_current_date_and_time(
        self,
        mock_datetime,
        mock_async_openai,
        mock_settings,
        sample_categories
    ):
        """
        Test prompt includes current date/time for context.

        GIVEN: Current time is 2025-11-14 10:30
        WHEN: _build_prompt() is called
        THEN: Date and time are included in prompt
        """
        # Arrange
        mock_settings.openrouter_api_key = "test_key"
        mock_now = datetime(2025, 11, 14, 10, 30, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now

        service = AIService()

        # Act
        prompt = service._build_prompt(
            user_input="test",
            categories=sample_categories,
            recent_activities=None
        )

        # Assert
        assert "2025-11-14" in prompt
        assert "10:30" in prompt

    @pytest.mark.unit
    @patch('src.application.services.ai_service.settings')
    @patch('src.application.services.ai_service.AsyncOpenAI')
    @patch('src.application.services.ai_service.datetime')
    def test_build_prompt_includes_user_input(
        self,
        mock_datetime,
        mock_async_openai,
        mock_settings,
        sample_categories
    ):
        """
        Test prompt includes user's input text.

        GIVEN: User input is "работал над проектом 2 часа"
        WHEN: _build_prompt() is called
        THEN: User input is included verbatim
        """
        # Arrange
        mock_settings.openrouter_api_key = "test_key"
        mock_now = datetime(2025, 11, 14, 10, 30, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now

        service = AIService()
        user_text = "работал над проектом 2 часа"

        # Act
        prompt = service._build_prompt(
            user_input=user_text,
            categories=sample_categories,
            recent_activities=None
        )

        # Assert
        assert user_text in prompt

    @pytest.mark.unit
    @patch('src.application.services.ai_service.settings')
    @patch('src.application.services.ai_service.AsyncOpenAI')
    def test_build_prompt_limits_recent_activities_to_10(
        self,
        mock_async_openai,
        mock_settings,
        sample_categories
    ):
        """
        Test prompt limits activity history to 10 items.

        GIVEN: User has 15 recent activities
        WHEN: _build_prompt() is called
        THEN: Only first 10 activities are included
        """
        # Arrange
        mock_settings.openrouter_api_key = "test_key"

        service = AIService()

        many_activities = [
            {"category_name": f"Category{i}", "description": f"Activity {i}"}
            for i in range(15)
        ]

        # Act
        prompt = service._build_prompt(
            user_input="test",
            categories=sample_categories,
            recent_activities=many_activities
        )

        # Assert: First 10 are present
        for i in range(10):
            assert f"Activity {i}" in prompt

        # 11th and beyond should not be present
        assert "Activity 10" not in prompt
        assert "Activity 14" not in prompt
