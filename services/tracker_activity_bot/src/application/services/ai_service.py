"""AI service for natural language activity parsing using OpenRouter.

This service integrates with OpenRouter API to provide intelligent parsing
of user text input into structured activity data (category, description, time).

Architecture:
- Uses OpenAI-compatible API via openai library
- Implements automatic model failover via AIModelSelector
- Analyzes user's activity history for context-aware parsing
- Returns structured JSON with confidence levels and alternatives

Key Features:
- 1-second timeout per model attempt
- Automatic fallback to alternative models
- Context-aware parsing based on user's past activities
- Confidence scoring (high/medium/low)
- Generation of 3 alternative interpretations
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any

from openai import AsyncOpenAI, APITimeoutError, APIError

from src.core.config import settings
from src.application.services.ai_model_selector import AIModelSelector

logger = logging.getLogger(__name__)


class AIParsingResult:
    """Structured result from AI activity parsing.

    Attributes:
        confidence: Parsing confidence level ("high", "medium", "low")
        category_name: Detected category name
        description: Activity description
        start_time: ISO timestamp for activity start (or None)
        end_time: ISO timestamp for activity end (or None)
        alternatives: List of 2 alternative interpretations
        raw_response: Raw JSON response from AI
    """

    def __init__(self, data: Dict[str, Any]):
        """Initialize parsing result from AI response.

        Args:
            data: Dictionary with AI response data
        """
        self.confidence = data.get("confidence", "low")
        self.category_name = data.get("category")
        self.description = data.get("description")
        self.start_time = data.get("start_time")
        self.end_time = data.get("end_time")
        self.alternatives = data.get("alternatives", [])
        self.raw_response = data

    def is_complete(self) -> bool:
        """Check if parsing result has all required data.

        Returns:
            True if category, description, and both time fields are present
        """
        return all([
            self.category_name,
            self.description,
            self.start_time,
            self.end_time
        ])

    def __repr__(self) -> str:
        return (
            f"AIParsingResult(confidence={self.confidence}, "
            f"category={self.category_name}, complete={self.is_complete()})"
        )


class AIService:
    """Service for AI-powered activity parsing using OpenRouter.

    This service provides intelligent natural language understanding for
    activity tracking. It analyzes user input in context of their history
    and available categories to extract structured activity data.

    Usage:
        service = AIService()
        result = await service.parse_activity_text(
            user_input="читал книгу с 14:00 до 15:30",
            categories=[...],
            recent_activities=[...]
        )
    """

    def __init__(self):
        """Initialize AI service with OpenRouter configuration."""
        self.api_key = settings.openrouter_api_key
        self.model_selector = AIModelSelector()

        if not self.api_key:
            logger.warning(
                "OpenRouter API key not configured, AI parsing will be disabled"
            )
            self.enabled = False
        else:
            self.enabled = True
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url="https://openrouter.ai/api/v1"
            )
            logger.info("AI service initialized with OpenRouter")

    async def parse_activity_text(
        self,
        user_input: str,
        categories: List[Dict[str, Any]],
        recent_activities: List[Dict[str, Any]] | None = None,
        max_retries: int = 3
    ) -> AIParsingResult | None:
        """Parse user text input into structured activity data.

        This method attempts to extract activity information from natural
        language input using AI. It tries multiple models with automatic
        failover if the primary model is unavailable.

        Args:
            user_input: Raw text from user (e.g., "читал книгу 2 часа")
            categories: List of user's available categories
            recent_activities: User's recent activities for context
            max_retries: Maximum number of model attempts

        Returns:
            AIParsingResult with parsed data, or None if all models fail

        Example:
            >>> result = await ai_service.parse_activity_text(
            ...     "читал книгу с 14:00 до 15:30",
            ...     categories=[{"name": "Образование", "emoji": "📚"}],
            ...     recent_activities=[...]
            ... )
            >>> if result and result.is_complete():
            ...     # Save activity directly
            >>> else:
            ...     # Show suggestions to user
        """
        if not self.enabled:
            logger.warning("AI service is disabled, skipping parsing")
            return None

        # Build prompt with context
        prompt = self._build_prompt(user_input, categories, recent_activities)

        # Try models with automatic failover
        current_model = self.model_selector.get_best_model()
        attempts = 0

        while current_model and attempts < max_retries:
            attempts += 1

            try:
                logger.info(
                    "Attempting AI parsing",
                    extra={
                        "model": current_model,
                        "attempt": attempts,
                        "max_retries": max_retries,
                        "input_length": len(user_input)
                    }
                )

                # Call AI with 1-second timeout
                result = await self._call_ai_with_timeout(
                    prompt=prompt,
                    model=current_model,
                    timeout=1.0
                )

                if result:
                    # Success! Increase model rating
                    self.model_selector.increase_rating(current_model)

                    logger.info(
                        "AI parsing successful",
                        extra={
                            "model": current_model,
                            "confidence": result.confidence,
                            "complete": result.is_complete()
                        }
                    )
                    return result

            except (APITimeoutError, asyncio.TimeoutError) as e:
                logger.warning(
                    "AI model timeout, switching to next model",
                    extra={
                        "model": current_model,
                        "attempt": attempts,
                        "error": str(e)
                    }
                )
                current_model = self.model_selector.get_next_model(current_model)

            except APIError as e:
                logger.error(
                    "AI API error, switching to next model",
                    extra={
                        "model": current_model,
                        "attempt": attempts,
                        "error": str(e),
                        "error_type": type(e).__name__
                    },
                    exc_info=True
                )
                current_model = self.model_selector.get_next_model(current_model)

            except Exception as e:
                logger.error(
                    "Unexpected error during AI parsing",
                    extra={
                        "model": current_model,
                        "attempt": attempts,
                        "error": str(e)
                    },
                    exc_info=True
                )
                # Try next model for any unexpected error
                current_model = self.model_selector.get_next_model(current_model)

        logger.error(
            "All AI models failed or timed out",
            extra={"attempts": attempts, "max_retries": max_retries}
        )
        return None

    async def _call_ai_with_timeout(
        self,
        prompt: str,
        model: str,
        timeout: float
    ) -> AIParsingResult | None:
        """Call AI API with timeout protection.

        Args:
            prompt: System prompt with parsing instructions
            model: Model identifier
            timeout: Timeout in seconds

        Returns:
            Parsed result or None on failure
        """
        try:
            # Wrap API call in asyncio timeout
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "system",
                            "content": prompt
                        }
                    ],
                    temperature=0.3,
                    max_tokens=500,
                    response_format={"type": "json_object"}
                ),
                timeout=timeout
            )

            # Parse response
            content = response.choices[0].message.content
            if not content:
                logger.warning("AI returned empty response")
                return None

            data = json.loads(content)
            return AIParsingResult(data)

        except asyncio.TimeoutError:
            logger.warning(
                "AI request timed out",
                extra={"model": model, "timeout": timeout}
            )
            raise
        except json.JSONDecodeError as e:
            logger.error(
                "Failed to parse AI JSON response",
                extra={"error": str(e), "model": model},
                exc_info=True
            )
            return None

    def _build_prompt(
        self,
        user_input: str,
        categories: List[Dict[str, Any]],
        recent_activities: List[Dict[str, Any]] | None
    ) -> str:
        """Build AI prompt with user context.

        Constructs a detailed prompt that includes:
        - Available categories
        - Recent activity history
        - Current date/time
        - Expected JSON format

        Args:
            user_input: User's text input
            categories: Available categories
            recent_activities: Recent activities for context

        Returns:
            Complete prompt string
        """
        now = datetime.now(timezone.utc)
        current_date = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%H:%M")

        # Format categories
        categories_text = "\n".join([
            f"- {cat['name']}" + (f" {cat['emoji']}" if cat.get('emoji') else "")
            for cat in categories
        ])

        # Format recent activities (last 10 for context)
        activities_text = "Нет данных"
        if recent_activities:
            activities_list = []
            for act in recent_activities[:10]:
                cat_name = act.get('category_name', 'Без категории')
                desc = act.get('description', '')
                activities_list.append(f"- {cat_name}: {desc}")
            activities_text = "\n".join(activities_list)

        # Build comprehensive prompt
        prompt = f"""Ты — помощник для парсинга активностей пользователя.

ТЕКУЩАЯ ДАТА И ВРЕМЯ:
Дата: {current_date}
Время: {current_time}

ДОСТУПНЫЕ КАТЕГОРИИ:
{categories_text}

ПОСЛЕДНИЕ АКТИВНОСТИ ПОЛЬЗОВАТЕЛЯ (для контекста):
{activities_text}

ТЕКСТ ОТ ПОЛЬЗОВАТЕЛЯ:
"{user_input}"

ЗАДАЧА:
Проанализируй текст и определи:
1. Категорию (из доступных выше)
2. Описание активности
3. Время начала (в формате ISO 8601 с UTC timezone)
4. Время окончания (в формате ISO 8601 с UTC timezone)

ПРАВИЛА ПАРСИНГА ВРЕМЕНИ:
- "с 14:00 до 15:30" → конкретные времена сегодня
- "2 часа" / "2ч" → период от текущего времени минус 2 часа до текущего времени
- "30 минут" / "30м" → период от текущего времени минус 30 минут
- "вчера с 18:00 до 19:00" → времена вчерашнего дня
- Если время не указано явно → null для обоих полей

УРОВЕНЬ УВЕРЕННОСТИ:
- "high": категория определена точно, описание понятно, время указано явно
- "medium": категория вероятна, время частично определено
- "low": категория неясна или время не указано

АЛЬТЕРНАТИВЫ:
Предложи 2 альтернативных варианта интерпретации (другие категории, другое время).

ФОРМАТ ОТВЕТА (строго JSON):
{{
  "confidence": "high|medium|low",
  "category": "название категории из списка выше",
  "description": "краткое описание активности",
  "start_time": "2025-01-15T14:00:00+00:00 или null",
  "end_time": "2025-01-15T15:30:00+00:00 или null",
  "alternatives": [
    {{
      "category": "другая категория",
      "description": "альтернативное описание",
      "start_time": "ISO или null",
      "end_time": "ISO или null"
    }},
    {{
      "category": "ещё категория",
      "description": "ещё описание",
      "start_time": "ISO или null",
      "end_time": "ISO или null"
    }}
  ]
}}

Верни ТОЛЬКО валидный JSON, без дополнительного текста."""

        return prompt
