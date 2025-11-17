"""AI service for natural language activity parsing using OpenRouter.

This service integrates with OpenRouter API to provide intelligent parsing
of user text input into structured activity data (category, description, time).

Architecture:
- Uses OpenAI-compatible API via openai library
- Implements automatic model failover via AIModelSelector
- Analyzes user's activity history for context-aware parsing
- Returns structured JSON with confidence levels and alternatives

Key Features:
- 10-second timeout per model attempt
- Automatic fallback to alternative models
- Context-aware parsing based on user's past activities
- Confidence scoring (high/medium/low)
- Generation of 3 alternative interpretations
"""

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
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

        # Temporary disable mechanism to prevent overload
        self.consecutive_failures = 0
        self.temporarily_disabled_until = None
        self.max_consecutive_failures = 5
        self.disable_duration_minutes = 5

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
        user_timezone: str = "UTC",
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
            user_timezone: User's timezone (e.g., "Europe/Moscow")
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

        # Check if temporarily disabled due to consecutive failures
        if self.temporarily_disabled_until:
            now = datetime.now(timezone.utc)
            if now < self.temporarily_disabled_until:
                remaining_seconds = (self.temporarily_disabled_until - now).total_seconds()
                logger.warning(
                    "AI service temporarily disabled due to consecutive failures",
                    extra={
                        "remaining_seconds": int(remaining_seconds),
                        "consecutive_failures": self.consecutive_failures
                    }
                )
                return None
            else:
                # Re-enable after cooldown period
                logger.info(
                    "AI service re-enabled after cooldown period",
                    extra={"consecutive_failures": self.consecutive_failures}
                )
                self.temporarily_disabled_until = None
                self.consecutive_failures = 0

        # Build prompt with context
        prompt = self._build_prompt(user_input, categories, recent_activities, user_timezone)

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

                # Call AI with 10-second timeout
                result = await self._call_ai_with_timeout(
                    prompt=prompt,
                    model=current_model,
                    timeout=10.0
                )

                if result:
                    # Success! Reset failure counter and increase model rating
                    self.consecutive_failures = 0
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

        # All models failed - increment failure counter
        self.consecutive_failures += 1

        logger.error(
            "All AI models failed or timed out",
            extra={
                "attempts": attempts,
                "max_retries": max_retries,
                "consecutive_failures": self.consecutive_failures
            }
        )

        # Check if we should temporarily disable AI service
        if self.consecutive_failures >= self.max_consecutive_failures:
            self.temporarily_disabled_until = (
                datetime.now(timezone.utc) +
                timedelta(minutes=self.disable_duration_minutes)
            )
            logger.warning(
                "AI service temporarily disabled due to consecutive failures",
                extra={
                    "consecutive_failures": self.consecutive_failures,
                    "disable_duration_minutes": self.disable_duration_minutes,
                    "disabled_until": self.temporarily_disabled_until.isoformat()
                }
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
        recent_activities: List[Dict[str, Any]] | None,
        user_timezone: str
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
            user_timezone: User's timezone for accurate time parsing

        Returns:
            Complete prompt string
        """
        # Import zoneinfo for timezone handling
        from zoneinfo import ZoneInfo

        # Get current time in user's timezone
        now_utc = datetime.now(timezone.utc)
        try:
            user_tz = ZoneInfo(user_timezone)
            now_local = now_utc.astimezone(user_tz)
        except Exception:
            # Fallback to UTC if timezone is invalid
            logger.warning(f"Invalid timezone: {user_timezone}, falling back to UTC")
            now_local = now_utc
            user_timezone = "UTC"

        current_date = now_local.strftime("%Y-%m-%d")
        current_time = now_local.strftime("%H:%M")

        # Format categories
        categories_text = "\n".join([
            f"- {cat['name']}" + (f" {cat['emoji']}" if cat.get('emoji') else "")
            for cat in categories
        ])

        # Format recent activities (last 10 for context)
        activities_text = "Нет данных"
        last_activity_info = "Нет данных"
        if recent_activities:
            activities_list = []
            for act in recent_activities[:10]:
                cat_name = act.get('category_name', 'Без категории')
                desc = act.get('description', '')
                activities_list.append(f"- {cat_name}: {desc}")
            activities_text = "\n".join(activities_list)

            # Extract last activity timing info for context
            last_activity = recent_activities[0]
            try:
                end_time_str = last_activity.get('end_time')
                duration_minutes = last_activity.get('duration_minutes')

                if end_time_str:
                    # Parse end_time (could be string or datetime)
                    if isinstance(end_time_str, str):
                        last_end_utc = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
                    else:
                        # Already datetime object
                        last_end_utc = end_time_str

                    # Convert to user's local timezone
                    last_end_local = last_end_utc.astimezone(user_tz)
                    last_activity_info = (
                        f"Закончилась в: {last_end_local.strftime('%H:%M')} "
                        f"(продолжительность: {duration_minutes} мин)"
                    )
            except Exception as e:
                logger.warning(
                    f"Failed to parse last activity timing: {e}",
                    extra={"last_activity": last_activity}
                )

        # Build comprehensive prompt
        prompt = f"""Ты — помощник для парсинга активностей пользователя.

ТЕКУЩАЯ ДАТА И ВРЕМЯ (в часовом поясе пользователя {user_timezone}):
Дата: {current_date}
Время: {current_time}

ДОСТУПНЫЕ КАТЕГОРИИ:
{categories_text}

ПОСЛЕДНИЕ АКТИВНОСТИ ПОЛЬЗОВАТЕЛЯ (для контекста):
{activities_text}

ПОСЛЕДНЯЯ АКТИВНОСТЬ:
{last_activity_info}

ТЕКСТ ОТ ПОЛЬЗОВАТЕЛЯ:
"{user_input}"

ЗАДАЧА:
Проанализируй текст и определи:
1. Категорию (из доступных выше)
2. Описание активности
3. Время начала (в формате ISO 8601 с UTC timezone)
4. Время окончания (в формате ISO 8601 с UTC timezone)

ВАЖНО ПРО ЧАСОВОЙ ПОЯС:
- Пользователь находится в часовом поясе: {user_timezone}
- Все времена в тексте пользователя интерпретируй как локальные для этого часового пояса
- В ответе конвертируй времена СТРОГО в UTC формат (ISO 8601 ТОЛЬКО с +00:00)
- ⚠️ ЗАПРЕЩЕНО использовать любые другие timezone offset (+01:00, +02:00, +03:00 и т.д.)
- Текущее время показано выше уже в часовом поясе пользователя

⚠️ КРИТИЧЕСКИ ВАЖНО - ВАЛИДАЦИЯ ВРЕМЕНИ С ЗАПАСОМ ДЛЯ API:

1. ОБЯЗАТЕЛЬНОЕ ПРАВИЛО ДЛЯ end_time (с учётом задержек валидации):
   - Если активность "до сейчас" или end_time близок к текущему моменту:
     → end_time = ТЕКУЩЕЕ ВРЕМЯ МИНУС 60 СЕКУНД (в UTC формате)
   - Это компенсирует задержки HTTP-запросов и гарантирует прохождение валидации API
   - Пример: текущее время 10:17:30 → end_time должен быть 10:16:30 или раньше
   - Если пользователь указал будущее время (например, "до 11:17" в 10:17):
     → Также ставь end_time = текущее время минус 60 секунд

2. ОБЯЗАТЕЛЬНОЕ ПРАВИЛО ДЛЯ start_time:
   - start_time ВСЕГДА должен быть СТРОГО МЕНЬШЕ end_time
   - Минимальная продолжительность: 1 минута
   - start_time < end_time < (текущее_время - 60 секунд)
   - Пример: если end_time = 10:16:30, то start_time максимум 10:15:30

3. ЗАПРЕЩЕНО:
   ❌ Ставить end_time = текущее время без вычета 60 секунд
   ❌ Ставить end_time в будущее
   ❌ Ставить start_time >= end_time
   ❌ Делать продолжительность меньше 1 минуты

ПРАВИЛА ПАРСИНГА ВРЕМЕНИ:
- "с 14:00 до 15:30" → конкретные времена сегодня в timezone пользователя, конвертируй в UTC
- "2 часа" / "2ч" → период от (текущее время - 2 часа - 60 сек) до (текущее время - 60 сек)
- "30 минут" / "30м" → период от (текущее время - 30 минут - 60 сек) до (текущее время - 60 сек)
- "до сейчас" → end_time = текущее время минус 60 секунд
- "вчера с 18:00 до 19:00" → времена вчерашнего дня в timezone пользователя, конвертируй в UTC
- "до полуночи" / "до 00:00" → полночь следующего дня в timezone пользователя

⚠️ КРИТИЧЕСКИ ВАЖНО - ВАЛИДАЦИЯ И ИСПРАВЛЕНИЕ ВРЕМЕНИ:

1. ОБЯЗАТЕЛЬНОЕ ТРЕБОВАНИЕ: end_time ВСЕГДА должен быть СТРОГО БОЛЬШЕ start_time
   - Минимальная продолжительность: 1 минута
   - НИКОГДА не возвращай одинаковые start_time и end_time
   - Если получается 0 минут или отрицательная продолжительность — это ОШИБКА, исправь её

2. ИСПРАВЛЕНИЕ ОШИБОК В ТЕКСТЕ ПОЛЬЗОВАТЕЛЯ:
   - "читал 0 минут" / "работал 0 минут" → пользователь ОШИБСЯ, определи реальную продолжительность
   - Используй контекст последней активности: если она закончилась недавно, начни новую от того момента
   - Если время вообще не ясно: используй разумный период (обычно 30-60 минут до текущего момента)
   - "работал до сейчас" → от времени конца последней активности до текущего момента

3. ЛОГИКА ОПРЕДЕЛЕНИЯ ВРЕМЕНИ КОГДА НЕ УКАЗАНО:
   - Если есть последняя активность И она закончилась недавно (< 2 часов назад):
     → start_time = время окончания последней активности
     → end_time = текущее время минус 60 секунд
   - Если последняя активность была давно ИЛИ нет данных:
     → Оцени разумную продолжительность (30-60 мин) и отсчитай от текущего момента
     → end_time = текущее время минус 60 секунд
     → start_time = end_time - разумная продолжительность
   - Если указана только продолжительность без времени:
     → end_time = текущее время минус 60 секунд
     → start_time = end_time - указанная продолжительность

4. ПРИОРИТЕТ ИСПРАВЛЕНИЯ НАД ТОЧНОСТЬЮ:
   - Лучше сделать разумное предположение, чем вернуть невалидные данные
   - Если пользователь явно ошибся — исправь тихо, сохрани confidence "high"
   - Цель: ВСЕГДА возвращать валидные start_time и end_time если категория определена

5. ЗАПРЕЩЕНО:
   ❌ Возвращать null для времени если категория определена
   ❌ Возвращать одинаковые start_time и end_time
   ❌ Возвращать end_time раньше start_time
   ❌ Игнорировать контекст последней активности

УРОВЕНЬ УВЕРЕННОСТИ:
- "high": категория определена точно, описание понятно, время валидно (явно или вычислено)
- "medium": категория вероятна, время определено на основе контекста
- "low": категория неясна (время все равно должно быть валидным)

АЛЬТЕРНАТИВЫ:
Предложи 2 альтернативных варианта интерпретации (другие категории, другое время).
Альтернативы тоже должны иметь валидное время:
- end_time > start_time (минимум 1 минута разницы)
- Если end_time близок к "сейчас" → применяй правило минус 60 секунд

ФОРМАТ ОТВЕТА (строго JSON):
{{
  "confidence": "high|medium|low",
  "category": "название категории из списка выше",
  "description": "краткое описание активности",
  "start_time": "2025-01-15T14:00:00+00:00",
  "end_time": "2025-01-15T15:30:00+00:00",
  "alternatives": [
    {{
      "category": "другая категория",
      "description": "альтернативное описание",
      "start_time": "2025-01-15T14:00:00+00:00",
      "end_time": "2025-01-15T15:30:00+00:00"
    }},
    {{
      "category": "ещё категория",
      "description": "ещё описание",
      "start_time": "2025-01-15T14:00:00+00:00",
      "end_time": "2025-01-15T15:30:00+00:00"
    }}
  ]
}}

ВАЖНО:
- Все поля времени (start_time, end_time) ОБЯЗАТЕЛЬНЫ и должны быть валидными ISO 8601 строками в UTC
- ВСЕГДА применяй правило: end_time = текущее время минус 60 секунд (если активность до "сейчас")
- start_time < end_time (минимум 1 минута разницы)
Верни ТОЛЬКО валидный JSON, без дополнительного текста."""

        return prompt
