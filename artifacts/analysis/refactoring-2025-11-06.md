
## 🔧 REFACTORING PLAN: Code Quality & Architecture

**Приоритет:** СРЕДНИЙ (после критических UI задач)
**Дата добавления:** 2025-11-05
**Цель:** Улучшить качество кода, устранить дублирование, следовать best practices

---

### 📊 АНАЛИЗ ТЕКУЩЕГО СОСТОЯНИЯ

#### Статистика кодовой базы:
```
services/tracker_activity_bot/src/api/handlers/
  └─ settings.py          893 строк ⚠️ (требует декомпозиции)
  └─ activity.py          568 строк ⚠️
  └─ categories.py        519 строк ⚠️
  └─ poll.py              461 строк ⚠️
```

#### Основные Code Smells:

1. **Code Duplication (DRY violation)**
   - Получение `user`/`settings` повторяется ~20 раз
   - Форматирование duration дублируется в handlers
   - Reschedule poll logic копируется в 5+ местах
   - Форматирование "следующий опрос" дублируется

2. **Long Methods**
   - `show_settings_menu()` - 136 строк активного кода
   - Множество handlers > 50 строк

3. **Magic Numbers**
   - Validation пределы: 30, 480, 600, 120, 5, 8
   - Postpone delay: 10 минут
   - Нет централизации констант

4. **Poor Error Handling**
   - Общий `except Exception as e` везде
   - Нет специфичных exception types
   - Отсутствует retry logic для API

5. **Missing Abstractions**
   - Нет service layer для business logic
   - Нет typing action decorator
   - Нет error handling middleware

---

### 🎯 ЗАДАЧА R1: Создать Service Layer для Business Logic

**Приоритет:** ВЫСОКИЙ
**Файлы:**
- Создать: `src/application/services/settings_service.py`
- Создать: `src/application/services/activity_service.py`
- Создать: `src/application/services/poll_service.py`

**Проблема:**
Handlers содержат бизнес-логику, что нарушает принцип Single Responsibility. Handlers должны только маршрутизировать запросы и форматировать ответы.

**Шаги:**

#### R1.1: Создать Settings Business Service
```python
# Файл: src/application/services/settings_business_service.py

"""Business logic for settings management.

This service encapsulates all business rules and validations
for user settings, separate from presentation layer (handlers).
"""
from datetime import datetime, timezone
from typing import Tuple, Optional
import logging

from src.infrastructure.http_clients.http_client import DataAPIClient
from src.infrastructure.http_clients.user_service import UserService
from src.infrastructure.http_clients.user_settings_service import UserSettingsService
from src.application.services.scheduler_service import scheduler_service
from src.core.constants import (
    MIN_POLL_INTERVAL_MINUTES,
    MAX_POLL_INTERVAL_WEEKDAY_MINUTES,
    MAX_POLL_INTERVAL_WEEKEND_MINUTES,
    MIN_REMINDER_DELAY_MINUTES,
    MAX_REMINDER_DELAY_MINUTES,
)

logger = logging.getLogger(__name__)


class SettingsBusinessService:
    """Service for settings business logic."""

    def __init__(self, api_client: DataAPIClient):
        self.api_client = api_client
        self.user_service = UserService(api_client)
        self.settings_service = UserSettingsService(api_client)

    async def get_user_and_settings(self, telegram_id: int) -> Tuple[Optional[dict], Optional[dict]]:
        """Get user and their settings.

        Args:
            telegram_id: Telegram user ID

        Returns:
            Tuple of (user, settings) or (None, None) if not found
        """
        user = await self.user_service.get_by_telegram_id(telegram_id)
        if not user:
            return None, None

        settings = await self.settings_service.get_settings(user["id"])
        return user, settings

    def validate_poll_interval(self, interval_minutes: int, is_weekend: bool = False) -> bool:
        """Validate poll interval value.

        Args:
            interval_minutes: Interval in minutes
            is_weekend: Whether this is for weekend

        Returns:
            True if valid

        Raises:
            ValueError: If invalid with descriptive message
        """
        max_interval = (
            MAX_POLL_INTERVAL_WEEKEND_MINUTES
            if is_weekend
            else MAX_POLL_INTERVAL_WEEKDAY_MINUTES
        )

        if interval_minutes < MIN_POLL_INTERVAL_MINUTES:
            raise ValueError(
                f"⚠️ Интервал должен быть не менее {MIN_POLL_INTERVAL_MINUTES} минут."
            )

        if interval_minutes > max_interval:
            hours = max_interval // 60
            raise ValueError(
                f"⚠️ Интервал должен быть не более {max_interval} минут ({hours}ч)."
            )

        return True

    def validate_reminder_delay(self, delay_minutes: int) -> bool:
        """Validate reminder delay value.

        Args:
            delay_minutes: Delay in minutes

        Returns:
            True if valid

        Raises:
            ValueError: If invalid with descriptive message
        """
        if delay_minutes < MIN_REMINDER_DELAY_MINUTES:
            raise ValueError(
                f"⚠️ Задержка должна быть не менее {MIN_REMINDER_DELAY_MINUTES} минут."
            )

        if delay_minutes > MAX_REMINDER_DELAY_MINUTES:
            raise ValueError(
                f"⚠️ Задержка должна быть не более {MAX_REMINDER_DELAY_MINUTES} минут."
            )

        return True

    async def update_poll_interval_and_reschedule(
        self,
        telegram_id: int,
        interval_minutes: int,
        is_weekend: bool,
        send_poll_callback
    ) -> dict:
        """Update poll interval and reschedule job.

        Args:
            telegram_id: Telegram user ID
            interval_minutes: New interval in minutes
            is_weekend: Whether updating weekend interval
            send_poll_callback: Callback for sending poll

        Returns:
            Updated settings dict

        Raises:
            ValueError: If validation fails
        """
        # Validate
        self.validate_poll_interval(interval_minutes, is_weekend)

        # Get user and settings
        user, settings = await self.get_user_and_settings(telegram_id)
        if not user or not settings:
            raise ValueError("User or settings not found")

        # Update settings
        field_name = "poll_interval_weekend" if is_weekend else "poll_interval_weekday"
        await self.settings_service.update_settings(
            settings["id"],
            **{field_name: interval_minutes}
        )

        # Fetch updated settings
        updated_settings = await self.settings_service.get_settings(user["id"])

        # Reschedule poll
        await scheduler_service.schedule_poll(
            user_id=telegram_id,
            settings=updated_settings,
            user_timezone=user.get("timezone", "Europe/Moscow"),
            send_poll_callback=send_poll_callback
        )

        logger.info(
            f"Updated {field_name} to {interval_minutes}m and rescheduled poll "
            f"for user {telegram_id}"
        )

        return updated_settings
```

#### R1.2: Создать Poll Business Service
```python
# Файл: src/application/services/poll_business_service.py

"""Business logic for poll management."""
from datetime import datetime, timedelta, timezone
from typing import Optional
import logging

from src.infrastructure.http_clients.http_client import DataAPIClient
from src.infrastructure.http_clients.user_service import UserService
from src.infrastructure.http_clients.user_settings_service import UserSettingsService
from src.infrastructure.http_clients.category_service import CategoryService
from src.infrastructure.http_clients.activity_service import ActivityService
from src.application.services.scheduler_service import scheduler_service
from src.core.constants import DEFAULT_SLEEP_DURATION_HOURS

logger = logging.getLogger(__name__)


class PollBusinessService:
    """Service for poll-related business logic."""

    def __init__(self, api_client: DataAPIClient):
        self.api_client = api_client
        self.user_service = UserService(api_client)
        self.settings_service = UserSettingsService(api_client)
        self.category_service = CategoryService(api_client)
        self.activity_service = ActivityService(api_client)

    async def create_sleep_activity(
        self,
        telegram_id: int
    ) -> Tuple[dict, float]:
        """Create sleep activity.

        Args:
            telegram_id: Telegram user ID

        Returns:
            Tuple of (activity, duration_hours)

        Raises:
            ValueError: If user not found
        """
        # Get user and settings
        user = await self.user_service.get_by_telegram_id(telegram_id)
        if not user:
            raise ValueError("User not found")

        settings = await self.settings_service.get_settings(user["id"])
        if not settings:
            raise ValueError("Settings not found")

        # Find or create sleep category
        categories = await self.category_service.get_user_categories(user["id"])
        sleep_category = next(
            (cat for cat in categories if cat["name"].lower() == "сон"),
            None
        )

        if not sleep_category:
            sleep_category = await self.category_service.create_category(
                user_id=user["id"],
                name="Сон",
                emoji="😴"
            )

        # Calculate sleep duration
        end_time = datetime.now(timezone.utc)
        start_time = self._calculate_activity_start_time(user, settings, end_time)

        # Create activity
        activity = await self.activity_service.create_activity(
            user_id=user["id"],
            category_id=sleep_category["id"],
            description="Сон",
            tags=["сон"],
            start_time=start_time,
            end_time=end_time
        )

        duration_hours = (end_time - start_time).total_seconds() / 3600

        return activity, duration_hours

    async def create_poll_activity(
        self,
        telegram_id: int,
        category_id: int
    ) -> Tuple[dict, int]:
        """Create activity from poll response.

        Args:
            telegram_id: Telegram user ID
            category_id: Selected category ID

        Returns:
            Tuple of (activity, duration_minutes)

        Raises:
            ValueError: If user not found
        """
        user = await self.user_service.get_by_telegram_id(telegram_id)
        if not user:
            raise ValueError("User not found")

        settings = await self.settings_service.get_settings(user["id"])
        if not settings:
            raise ValueError("Settings not found")

        # Calculate time range
        end_time = datetime.now(timezone.utc)
        start_time = self._calculate_activity_start_time(user, settings, end_time)

        # Create activity
        activity = await self.activity_service.create_activity(
            user_id=user["id"],
            category_id=category_id,
            description="Активность",
            tags=[],
            start_time=start_time,
            end_time=end_time
        )

        duration_minutes = int((end_time - start_time).total_seconds() / 60)

        return activity, duration_minutes

    def _calculate_activity_start_time(
        self,
        user: dict,
        settings: dict,
        end_time: datetime
    ) -> datetime:
        """Calculate activity start time based on last poll or interval.

        Args:
            user: User dict
            settings: Settings dict
            end_time: Activity end time

        Returns:
            Calculated start time
        """
        last_poll = user.get("last_poll_time")
        if last_poll:
            # Use actual last poll time
            return datetime.fromisoformat(last_poll.replace('Z', '+00:00'))

        # Fallback: use poll interval
        is_weekend = end_time.weekday() >= 5
        interval_minutes = (
            settings["poll_interval_weekend"]
            if is_weekend
            else settings["poll_interval_weekday"]
        )

        return end_time - timedelta(minutes=interval_minutes)
```

**Ожидаемый результат:**
- ✅ Handlers становятся тонкими (thin controllers)
- ✅ Бизнес-логика изолирована и переиспользуема
- ✅ Легче тестировать
- ✅ Централизованная валидация

---

### 🎯 ЗАДАЧА R2: Создать Helper Decorators и Middleware

**Приоритет:** ВЫСОКИЙ
**Файлы:**
- Создать: `src/application/utils/decorators.py`
- Создать: `src/application/utils/error_handlers.py`

**Проблема:**
Отсутствуют переиспользуемые декораторы для частых задач (typing action, error handling, logging).

**Шаги:**

#### R2.1: Создать Typing Action Decorator
```python
# Файл: src/application/utils/decorators.py

"""Useful decorators for handlers."""
from functools import wraps
from typing import Callable, TypeVar, ParamSpec
from aiogram import types
from aiogram.enums import ChatAction
import logging

P = ParamSpec('P')
T = TypeVar('T')

logger = logging.getLogger(__name__)


def with_typing_action(func: Callable[P, T]) -> Callable[P, T]:
    """Decorator to show typing action before handler execution.

    Automatically shows "typing..." indicator when user clicks inline button
    or sends a message. Improves UX by providing immediate feedback.

    Usage:
        @router.callback_query(F.data == "something")
        @with_typing_action
        async def handler(callback: CallbackQuery, ...):
            # Typing action is automatically shown
            ...
    """
    @wraps(func)
    async def wrapper(event: types.CallbackQuery | types.Message, *args, **kwargs):
        # Determine chat_id and bot based on event type
        if isinstance(event, types.CallbackQuery):
            chat_id = event.message.chat.id
            bot = event.bot
        else:  # Message
            chat_id = event.chat.id
            bot = event.bot

        try:
            # Show typing action
            await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        except Exception as e:
            # Don't fail if typing action fails
            logger.debug(f"Could not send typing action: {e}")

        # Execute original handler
        return await func(event, *args, **kwargs)

    return wrapper


def with_error_handling(func: Callable[P, T]) -> Callable[P, T]:
    """Decorator for graceful error handling in handlers.

    Catches exceptions and sends user-friendly error messages.

    Usage:
        @router.callback_query(F.data == "something")
        @with_error_handling
        async def handler(callback: CallbackQuery, ...):
            # Errors are automatically caught and handled
            ...
    """
    @wraps(func)
    async def wrapper(event: types.CallbackQuery | types.Message, *args, **kwargs):
        try:
            return await func(event, *args, **kwargs)
        except ValueError as e:
            # User input validation errors
            message = str(e)
            if isinstance(event, types.CallbackQuery):
                await event.message.answer(message)
                await event.answer()
            else:
                await event.answer(message)
        except Exception as e:
            # Unexpected errors
            logger.error(
                f"Error in handler {func.__name__}: {e}",
                exc_info=True,
                extra={"handler": func.__name__}
            )
            error_message = "⚠️ Произошла ошибка. Попробуй позже."
            if isinstance(event, types.CallbackQuery):
                await event.message.answer(error_message)
                await event.answer()
            else:
                await event.answer(error_message)

    return wrapper


def with_user_context(func: Callable) -> Callable:
    """Decorator to inject user and settings into handler.

    Automatically fetches user and settings, handles not found cases.

    Usage:
        @router.callback_query(F.data == "something")
        @with_user_context
        async def handler(callback: CallbackQuery, user: dict, settings: dict, ...):
            # user and settings are automatically injected
            ...
    """
    @wraps(func)
    async def wrapper(event: types.CallbackQuery | types.Message, *args, **kwargs):
        from src.infrastructure.http_clients.http_client import DataAPIClient
        from src.application.services.settings_business_service import SettingsBusinessService

        api_client = DataAPIClient()
        service = SettingsBusinessService(api_client)

        telegram_id = event.from_user.id
        user, settings = await service.get_user_and_settings(telegram_id)

        if not user:
            message = event.message if isinstance(event, types.CallbackQuery) else event
            from src.api.keyboards.main_menu import get_main_menu_keyboard
            await message.answer(
                "⚠️ Пользователь не найден. Отправь /start для регистрации.",
                reply_markup=get_main_menu_keyboard()
            )
            if isinstance(event, types.CallbackQuery):
                await event.answer()
            return

        if not settings:
            message = event.message if isinstance(event, types.CallbackQuery) else event
            from src.api.keyboards.main_menu import get_main_menu_keyboard
            await message.answer(
                "⚠️ Настройки не найдены.",
                reply_markup=get_main_menu_keyboard()
            )
            if isinstance(event, types.CallbackQuery):
                await event.answer()
            return

        # Inject user and settings
        kwargs['user'] = user
        kwargs['settings'] = settings
        return await func(event, *args, **kwargs)

    return wrapper
```

**Ожидаемый результат:**
- ✅ Typing action в одну строку
- ✅ Централизованная обработка ошибок
- ✅ Автоматическая инжекция user/settings

---

### 🎯 ЗАДАЧА R3: Централизовать Constants и Validation Rules

**Приоритет:** СРЕДНИЙ
**Файлы:**
- Создать: `src/core/constants.py`
- Создать: `src/core/validation.py`

**Проблема:**
Magic numbers разбросаны по коду. Validation logic дублируется.

**Шаги:**

#### R3.1: Создать Constants файл
```python
# Файл: src/core/constants.py

"""Application-wide constants.

All magic numbers and configuration values should be defined here
to ensure consistency and ease of maintenance.
"""

# ============================================================================
# POLL SETTINGS
# ============================================================================

DEFAULT_SLEEP_DURATION_HOURS = 8
"""Default sleep duration when last_poll_time is unknown"""

POLL_POSTPONE_MINUTES = 10
"""Minutes to postpone poll if user is busy in FSM dialog"""

# ============================================================================
# VALIDATION LIMITS
# ============================================================================

# Poll intervals
MIN_POLL_INTERVAL_MINUTES = 30
"""Minimum poll interval (30 minutes = 0.5 hours)"""

MAX_POLL_INTERVAL_WEEKDAY_MINUTES = 480
"""Maximum weekday poll interval (480 minutes = 8 hours)"""

MAX_POLL_INTERVAL_WEEKEND_MINUTES = 600
"""Maximum weekend poll interval (600 minutes = 10 hours)"""

# Reminders
MIN_REMINDER_DELAY_MINUTES = 5
"""Minimum reminder delay (5 minutes)"""

MAX_REMINDER_DELAY_MINUTES = 120
"""Maximum reminder delay (120 minutes = 2 hours)"""

# Categories
MIN_CATEGORY_NAME_LENGTH = 2
"""Minimum category name length"""

MAX_CATEGORY_NAME_LENGTH = 50
"""Maximum category name length"""

# Activities
MIN_ACTIVITY_DURATION_MINUTES = 1
"""Minimum activity duration in minutes"""

MAX_ACTIVITY_LIST_LIMIT = 10
"""Maximum number of activities to show in list"""

# ============================================================================
# UI CONSTANTS
# ============================================================================

QUIET_HOURS_DEFAULT_START = "23:00:00"
"""Default quiet hours start time"""

QUIET_HOURS_DEFAULT_END = "07:00:00"
"""Default quiet hours end time"""

DEFAULT_TIMEZONE = "Europe/Moscow"
"""Default timezone for users"""
```

#### R3.2: Применить константы в коде
```python
# Пример использования в handlers:

from src.core.constants import (
    MIN_POLL_INTERVAL_MINUTES,
    MAX_POLL_INTERVAL_WEEKDAY_MINUTES,
    POLL_POSTPONE_MINUTES,
    DEFAULT_TIMEZONE,
)

# Вместо:
if interval < 30 or interval > 480:
    ...

# Использовать:
if interval < MIN_POLL_INTERVAL_MINUTES or interval > MAX_POLL_INTERVAL_WEEKDAY_MINUTES:
    ...
```

**Файлы для обновления:**
- `src/api/handlers/settings.py` - все validation checks
- `src/api/handlers/poll.py` - postpone delay, sleep duration
- `src/api/handlers/categories.py` - name length validation
- `src/api/handlers/activity.py` - activity limits

**Ожидаемый результат:**
- ✅ Нет magic numbers в коде
- ✅ Централизованное управление limits
- ✅ Легко изменить значения
- ✅ Самодокументирующийся код

---

### 🎯 ЗАДАЧА R4: Извлечь Helper Functions в Utils

**Приоритет:** СРЕДНИЙ
**Файлы:**
- Обновить: `src/application/utils/formatters.py`
- Создать: `src/application/utils/time_helpers.py`

**Проблема:**
Форматирование duration, времени следующего опроса дублируется.

**Шаги:**

#### R4.1: Расширить formatters.py
```python
# Файл: src/application/utils/formatters.py
# ДОБАВИТЬ в конец файла:

def format_next_poll_time(minutes_until: int) -> str:
    """Format time until next poll in human-readable format.

    Args:
        minutes_until: Minutes until next poll

    Returns:
        Formatted string like "через 30 минут" or "через 2 часа"

    Examples:
        45 → "через 45 минут"
        90 → "через 1ч 30м"
        120 → "через 2 часа"
    """
    if minutes_until < 0:
        return "просрочен"

    if minutes_until < 60:
        return f"через {minutes_until} минут"

    hours = minutes_until // 60
    remaining_minutes = minutes_until % 60

    if remaining_minutes == 0:
        # Правильное склонение часов
        if hours == 1:
            hours_word = "час"
        elif 1 < hours < 5:
            hours_word = "часа"
        else:
            hours_word = "часов"
        return f"через {hours} {hours_word}"
    else:
        return f"через {hours}ч {remaining_minutes}м"


def format_interval_setting(minutes: int) -> str:
    """Format poll interval for display in settings.

    Args:
        minutes: Interval in minutes

    Returns:
        Formatted string

    Examples:
        45 → "45м"
        90 → "1ч 30м"
        120 → "2ч"
    """
    # Same logic as format_duration, but extracted for clarity
    return format_duration(minutes)


def format_time_range(start: datetime, end: datetime, timezone: str = "Europe/Moscow") -> str:
    """Format time range as "HH:MM — HH:MM (duration)".

    Args:
        start: Start datetime
        end: End datetime
        timezone: Timezone string

    Returns:
        Formatted string like "14:30 — 16:00 (1ч 30м)"
    """
    start_str = format_time(start, timezone)
    end_str = format_time(end, timezone)
    duration_minutes = int((end - start).total_seconds() / 60)
    duration_str = format_duration(duration_minutes)

    return f"{start_str} — {end_str} ({duration_str})"
```

#### R4.2: Применить helpers в handlers
```python
# В settings.py заменить все дублирование:

# БЫЛО:
weekday_minutes = settings["poll_interval_weekday"]
if weekday_minutes < 60:
    weekday_str = f"{weekday_minutes}м"
else:
    weekday_h = weekday_minutes // 60
    weekday_m = weekday_minutes % 60
    if weekday_m == 0:
        weekday_str = f"{weekday_h}ч"
    else:
        weekday_str = f"{weekday_h}ч {weekday_m}м"

# СТАЛО:
from src.application.utils.formatters import format_interval_setting
weekday_str = format_interval_setting(settings["poll_interval_weekday"])
```

**Ожидаемый результат:**
- ✅ Нет дублирования форматирования
- ✅ Единообразный формат везде
- ✅ Легко изменить формат глобально

---

### 🎯 ЗАДАЧА R5: Применить Decorators к Handlers

**Приоритет:** НИЗКИЙ (после R1, R2)
**Файлы:**
- Все handler файлы

**Проблема:**
После создания decorators нужно применить их ко всем handlers.

**Шаги:**

#### R5.1: Применить @with_typing_action
```python
# Применить ко ВСЕМ callback_query handlers:

# Файл: src/api/handlers/settings.py
from src.application.utils.decorators import with_typing_action, with_error_handling

@router.callback_query(F.data == "settings")
@with_typing_action
@with_error_handling
async def show_settings_menu(callback: types.CallbackQuery):
    """Show main settings menu."""
    # ... код без изменений
```

**Всего handlers для обновления:** ~40

#### R5.2: Применить @with_user_context где возможно
```python
# Для handlers, которым нужен user/settings:

@router.callback_query(F.data == "settings")
@with_typing_action
@with_user_context
async def show_settings_menu(callback: types.CallbackQuery, user: dict, settings: dict):
    """Show main settings menu."""
    # Больше не нужно:
    # user_service = UserService(api_client)
    # user = await user_service.get_by_telegram_id(...)

    # Сразу используем инжектированные user и settings
    weekday_str = format_interval_setting(settings["poll_interval_weekday"])
    ...
```

**Ожидаемый результат:**
- ✅ Все handlers показывают typing indicator
- ✅ Централизованная обработка ошибок
- ✅ Устранено дублирование получения user/settings

---

### 🎯 ЗАДАЧА R6: Разбить Длинные Handlers

**Приоритет:** НИЗКИЙ
**Файлы:**
- `src/api/handlers/settings.py`

**Проблема:**
`show_settings_menu()` - 136 строк активного кода, слишком длинная функция.

**Шаги:**

#### R6.1: Извлечь подфункции
```python
# Файл: src/api/handlers/settings.py

def _format_settings_display(settings: dict) -> str:
    """Format settings for display in menu.

    Args:
        settings: User settings dict

    Returns:
        Formatted text with current settings
    """
    from src.application.utils.formatters import format_interval_setting

    weekday_str = format_interval_setting(settings["poll_interval_weekday"])
    weekend_str = format_interval_setting(settings["poll_interval_weekend"])

    quiet_enabled = settings["quiet_hours_start"] is not None
    quiet_text = (
        f"С {settings['quiet_hours_start'][:5]} до {settings['quiet_hours_end'][:5]}"
        if quiet_enabled
        else "Выключены"
    )

    reminder_status = "Включены ✅" if settings["reminder_enabled"] else "Выключены ❌"

    text = (
        f"⚙️ Настройки бота\n\n"
        f"Текущие настройки:\n\n"
        f"📅 Интервалы опросов:\n"
        f"• Будни: каждые {weekday_str}\n"
        f"• Выходные: каждые {weekend_str}\n"
    )

    # Add next poll text separately
    return text


def _get_next_poll_info(telegram_id: int) -> Optional[str]:
    """Get formatted next poll time info.

    Args:
        telegram_id: Telegram user ID

    Returns:
        Formatted string or None if no poll scheduled
    """
    from src.application.utils.formatters import format_next_poll_time
    from datetime import datetime, timezone

    if telegram_id not in scheduler_service.jobs:
        return None

    job_id = scheduler_service.jobs[telegram_id]
    try:
        job = scheduler_service.scheduler.get_job(job_id)
        if job and job.next_run_time:
            now = datetime.now(timezone.utc)
            time_until = job.next_run_time - now
            minutes = int(time_until.total_seconds() / 60)

            return f"⏰ Следующий опрос {format_next_poll_time(minutes)}"
    except Exception as e:
        logger.warning(f"Could not get next poll time: {e}")

    return None


@router.callback_query(F.data == "settings")
@with_typing_action
@with_user_context
async def show_settings_menu(callback: types.CallbackQuery, user: dict, settings: dict):
    """Show main settings menu."""
    # Build settings text
    text = _format_settings_display(settings)

    # Add next poll info
    next_poll_text = _get_next_poll_info(callback.from_user.id)
    if next_poll_text:
        text += f"• {next_poll_text}\n"
    else:
        # Schedule poll if missing
        from src.api.handlers.poll import send_automatic_poll
        try:
            await scheduler_service.schedule_poll(
                user_id=callback.from_user.id,
                settings=settings,
                user_timezone=user.get("timezone", DEFAULT_TIMEZONE),
                send_poll_callback=lambda uid: send_automatic_poll(callback.bot, uid)
            )
            next_poll_text = _get_next_poll_info(callback.from_user.id)
            if next_poll_text:
                text += f"• {next_poll_text}\n"
        except Exception as e:
            logger.error(f"Failed to schedule poll: {e}")

    # Add quiet hours and reminders
    text += (
        f"\n🌙 Тихие часы:\n"
        f"• {_format_quiet_hours(settings)}\n"
        f"(Бот не будет беспокоить в это время)\n\n"
        f"🔔 Напоминания:\n"
        f"• {_format_reminder_status(settings)}\n"
        f"• Задержка: {settings['reminder_delay_minutes']} минут"
    )

    await callback.message.answer(text, reply_markup=get_main_settings_keyboard())
    await callback.answer()
```

**Ожидаемый результат:**
- ✅ Функция < 30 строк
- ✅ Каждая подфункция делает одно
- ✅ Легче читать и тестировать

---

### 📊 METRICS & TRACKING

#### Метрики качества до рефакторинга:
```
Code Duplication:        ~30% (оценка)
Average Handler Length:  ~80 строк
Magic Numbers:           ~25 locations
Error Handling:          Generic (except Exception)
Test Coverage:           Minimal
```

#### Целевые метрики после рефакторинга:
```
Code Duplication:        < 5%
Average Handler Length:  < 40 строк
Magic Numbers:           0 (все в constants)
Error Handling:          Специфичная (по типам)
Test Coverage:           > 60%
```

---

### 🎯 EXECUTION PLAN

#### Phase 1: Foundation (Week 1)
- ✅ R3: Создать constants.py и применить
- ✅ R2: Создать decorators.py
- ✅ R4: Расширить formatters.py

#### Phase 2: Services (Week 2)
- ✅ R1.1: Создать SettingsBusinessService
- ✅ R1.2: Создать PollBusinessService

#### Phase 3: Application (Week 3)
- ✅ R5.1: Применить @with_typing_action ко всем handlers
- ✅ R5.2: Применить @with_user_context где нужно
- ✅ R6: Разбить длинные функции

#### Phase 4: Testing & Validation (Week 4)
- ✅ Написать unit tests для services
- ✅ Integration tests для основных flow
- ✅ Проверить metrics

---

### ✅ ACCEPTANCE CRITERIA

Рефакторинг считается завершённым когда:

1. **No Code Duplication**
   - [ ] Получение user/settings вынесено в decorator/service
   - [ ] Форматирование использует общие функции
   - [ ] Reschedule logic в одном месте

2. **Clean Architecture**
   - [ ] Business logic в services, не в handlers
   - [ ] Handlers < 40 строк в среднем
   - [ ] Нет прямых API calls в handlers

3. **Constants & Configuration**
   - [ ] Все magic numbers в constants.py
   - [ ] Validation rules централизованы

4. **Error Handling**
   - [ ] Специфичные exception types
   - [ ] Централизованная обработка через decorators
   - [ ] User-friendly error messages

5. **Code Quality**
   - [ ] Typing hints везде
   - [ ] Docstrings в Google style
   - [ ] No linter warnings

6. **Testing**
   - [ ] Unit tests для всех services
   - [ ] Integration tests для критических flow
   - [ ] > 60% coverage

---

### 📚 BEST PRACTICES REFERENCE

**Применённые принципы:**
- ✅ DRY (Don't Repeat Yourself)
- ✅ SOLID (особенно SRP)
- ✅ Clean Architecture (layers separation)
- ✅ Dependency Injection
- ✅ Error Handling patterns
- ✅ Decorator pattern
- ✅ Service Layer pattern

**Code Style:**
- ✅ PEP 8
- ✅ Type hints (PEP 484)
- ✅ Docstrings (Google style)
- ✅ Константы в UPPER_CASE
- ✅ Private functions с _ prefix

---

**Конец TODO файла**

Готов к выполнению! 🚀

---
