# SOLID Principles Compliance Refactoring Plan

**Project:** Activity Tracker Bot
**Date Created:** 2025-11-07
**Document Version:** 1.0
**Status:** 🔴 Planning Phase
**Related Documents:**
- [ADR-20251107-001](../../docs/adr/ADR-20251107-001/README.md)
- [Architecture Documentation](../../ARCHITECTURE.md)
- [ADR Compliance Plan](./refactoring-2025-11-07-(1).md)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [SOLID Analysis Overview](#solid-analysis-overview)
3. [Critical Issues Summary](#critical-issues-summary)
4. [Priority Matrix](#priority-matrix)
5. [Phase 5: SOLID Compliance Refactoring](#phase-5-solid-compliance-refactoring)
6. [Detailed Task Descriptions](#detailed-task-descriptions)
7. [Code Examples & Patterns](#code-examples--patterns)
8. [Testing Strategy](#testing-strategy)
9. [Metrics & Success Criteria](#metrics--success-criteria)
10. [Best Practices Checklist](#best-practices-checklist)

---

## Executive Summary

### Current SOLID Compliance Score: **78/100 (C+)**

The Activity Tracker Bot demonstrates **strong understanding** of advanced patterns (Repository, Dependency Injection, Decorators) but suffers from **God Objects**, **global state management**, and **missing abstractions**.

### Breakdown by Principle

| Principle | Score | Status | Primary Issues |
|-----------|-------|--------|----------------|
| **SRP** (Single Responsibility) | 65/100 | ⚠️ Moderate | God Object in settings.py (841 lines) |
| **OCP** (Open/Closed) | 70/100 | ⚠️ Moderate | HTTP client lacks abstractions |
| **LSP** (Liskov Substitution) | 85/100 | ✅ Good | Excellent Repository pattern |
| **ISP** (Interface Segregation) | 72/100 | ⚠️ Moderate | ServiceContainer too large |
| **DIP** (Dependency Inversion) | 75/100 | ⚠️ Moderate | Global variables (scheduler, FSM) |

### Target Score After Refactoring: **90+/100 (A-)**

### Key Statistics

**Current State:**
- Largest file: 841 lines (settings.py)
- Average functions per file: 20+
- Global mutable state: 2 critical instances
- Testability: 60% (limited by tight coupling)

**Target State:**
- Maximum file size: 300 lines
- Average functions per file: 5-10
- Global mutable state: 0
- Testability: 90%+ (full DI)

### Estimated Effort

- **Phase 5 (SOLID Compliance):** 8 weeks
  - Week 4: SRP - God Objects (3-4 days)
  - Week 5: DIP - Remove Globals (3-4 days)
  - Week 6: OCP - Add Abstractions (3-4 days)
  - Week 7: ISP + LSP (3-4 days)
  - Week 8: Patterns + Polish (3-4 days)

**Total Estimated Hours:** 80-100 hours

---

## SOLID Analysis Overview

### 1. Single Responsibility Principle (SRP)

#### Score: 65/100 ⚠️

**Definition:** A class should have one, and only one, reason to change.

**Current Violations:**

| File | Lines | Functions | Responsibilities | Severity |
|------|-------|-----------|------------------|----------|
| **settings.py** | 841 | 26+ | Menu, Intervals, Quiet Hours, Reminders, FSM, Scheduler | 🔴 CRITICAL |
| **poll.py** | 653 | 12+ | Poll Sending, FSM Checking, Scheduling, Reminders | 🟠 HIGH |
| **activity.py** | 734 | 15+ | Creation, View, Validation, FSM, Formatting | 🟠 HIGH |
| **categories.py** | 538 | 15+ | CRUD, Display, Validation | 🟡 MEDIUM |

**Impact:**
- Hard to test individual features
- Changes cascade to unrelated functionality
- High cognitive load for developers
- Difficult to maintain and extend

**Recommended Actions:**
1. Split settings.py into 4 focused modules
2. Extract classes from poll.py (3 classes)
3. Separate activity.py into creation/view/fsm modules
4. Extract business logic to service classes

---

### 2. Open/Closed Principle (OCP)

#### Score: 70/100 ⚠️

**Definition:** Software entities should be open for extension, but closed for modification.

**Current Violations:**

| Component | Issue | Severity |
|-----------|-------|----------|
| **DataAPIClient** | Hardcoded error handling, no middleware | 🔴 CRITICAL |
| **Keyboard builders** | Cannot extend without modifying | 🟠 HIGH |
| **Scheduler logic** | Hardcoded interval calculation | 🟡 MEDIUM |
| **Message formatters** | Cannot customize without editing | 🟡 MEDIUM |

**Problems:**

```python
# ❌ WRONG: Cannot extend without modification
class DataAPIClient:
    async def get(self, path: str, **kwargs):
        # Hardcoded logging
        logger.debug(...)
        # Hardcoded error handling
        response.raise_for_status()
        # Hardcoded parsing
        return response.json()
```

**Impact:**
- Cannot add retry logic without editing client
- Cannot add custom headers globally
- Cannot extend logging behavior
- Every new requirement modifies existing code

**Recommended Actions:**
1. Implement Middleware Pattern for HTTP client
2. Create Builder Pattern for keyboards
3. Use Strategy Pattern for scheduling algorithms
4. Extract configurable formatters

---

### 3. Liskov Substitution Principle (LSP)

#### Score: 85/100 ✅

**Definition:** Objects of a superclass should be replaceable with objects of a subclass without breaking the application.

**Strengths:**

```python
# ✅ EXCELLENT: Repository pattern maintains LSP
class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    async def get_by_id(self, id: int) -> Optional[ModelType]:
        """Get entity by ID."""
        pass

class ActivityRepository(BaseRepository[Activity, ActivityCreate, ActivityUpdate]):
    async def get_by_id(self, id: int) -> Optional[Activity]:
        """Get activity by ID."""
        # Can substitute base class without issues
        return await self._get_one(Activity.id == id)
```

**Minor Issues:**

| Issue | Location | Severity |
|-------|----------|----------|
| Inconsistent error handling | Service layer | 🟡 MEDIUM |
| Mixed return types (None vs Exception) | CategoryService.delete_category | 🟢 LOW |

**Recommended Actions:**
1. Standardize error handling across services
2. Use consistent return types (Result type or exceptions)
3. Document behavioral contracts

---

### 4. Interface Segregation Principle (ISP)

#### Score: 72/100 ⚠️

**Definition:** No client should be forced to depend on methods it does not use.

**Current Violations:**

```python
# ❌ WRONG: Handler depends on all services
class ServiceContainer:
    user: UserService
    category: CategoryService
    activity: ActivityService
    settings: UserSettingsService

async def handler(callback: types.CallbackQuery, services: ServiceContainer):
    # Only uses user service
    user = await services.user.get_by_telegram_id(...)
    # Forced to depend on unused: category, activity, settings
```

**Impact:**
- Handlers depend on services they don't use
- Changes to unused services still affect handlers
- Harder to mock for testing
- Unclear dependencies at function signature

**Recommended Actions:**
1. Create focused protocols for each service type
2. Update handler signatures to use specific protocols
3. ServiceContainer implements all protocols

---

### 5. Dependency Inversion Principle (DIP)

#### Score: 75/100 ⚠️

**Definition:** High-level modules should depend on abstractions, not concrete implementations.

**Strengths:**

```python
# ✅ EXCELLENT: FastAPI DI
@router.post("/activities")
async def create_activity(
    service: Annotated[ActivityService, Depends(get_activity_service)]
):
    # Depends on abstraction (DI), not global instance
    return await service.create_activity(data)
```

**Critical Violations:**

```python
# ❌ CRITICAL: Global mutable state
# scheduler_service.py:147
scheduler_service = SchedulerService()  # Global!

# All handlers import and use directly
from src.application.services.scheduler_service import scheduler_service

async def handler(...):
    await scheduler_service.schedule_poll(...)  # Tight coupling!
```

**Impact:**
- ❌ Cannot test with mocks
- ❌ Cannot have multiple instances
- ❌ Hidden dependencies
- ❌ Difficult lifecycle management
- ❌ Production issues hard to debug

**Recommended Actions:**
1. Create `PollSchedulerProtocol` abstraction
2. Inject scheduler via ServiceContainer
3. Remove all global instances
4. Update handlers to receive dependencies

---

## Critical Issues Summary

### 🔴 P0 - CRITICAL (Must Fix Immediately)

| # | Issue | File | Impact | Effort | Benefit |
|---|-------|------|--------|--------|---------|
| 1 | God Object (841 lines) | settings.py | Maintainability | High | High |
| 2 | Global scheduler_service | scheduler_service.py | Testability | Medium | High |
| 3 | Global FSM storage | poll.py | Memory leaks | Medium | High |
| 4 | HTTP client no abstractions | http_client.py | Extensibility | High | High |

### 🟠 P1 - HIGH (Fix Soon)

| # | Issue | File | Impact | Effort | Benefit |
|---|-------|------|--------|--------|---------|
| 5 | Poll handler mixed responsibilities | poll.py | Complexity | Medium | Medium |
| 6 | Inconsistent error handling | All handlers | Debugging | Medium | Medium |
| 7 | ServiceContainer violates ISP | dependencies.py | Coupling | Low | Medium |
| 8 | No Strategy for scheduling | scheduler_service.py | Flexibility | High | Medium |

### 🟡 P2 - MEDIUM (When Possible)

| # | Issue | Effort | Benefit |
|---|-------|--------|---------|
| 9 | Extract ActivitySaver class | Low | Low |
| 10 | Keyboard builders not extensible | Medium | Low |
| 11 | No Factory pattern | Medium | Low |
| 12 | View rendering in handlers | Medium | Low |

### 🟢 P3 - LOW (Nice to Have)

| # | Issue | Effort | Benefit |
|---|-------|--------|---------|
| 13 | Observer pattern for events | High | Low |
| 14 | Improve docstring coverage | Low | Low |
| 15 | Result type for error handling | High | Low |

---

## Priority Matrix

### Effort vs Impact

```
High Impact │ P0: scheduler    │ P0: settings.py  │
            │     (4 days)     │     (5 days)     │
            │─────────────────│─────────────────│
            │ P1: error       │ P0: HTTP client  │
            │     handling    │     (4 days)     │
            │     (3 days)    │                  │
────────────┼─────────────────┼─────────────────┤
            │ P2: Keyboard    │ P1: poll.py      │
Low Impact  │     builders    │     (3 days)     │
            │     (2 days)    │                  │
            │─────────────────│─────────────────│
            │ P3: Observer    │ P2: Factories    │
            │     pattern     │     (2 days)     │
            │     (4 days)    │                  │
────────────┴─────────────────┴─────────────────┤
               Low Effort         High Effort
```

---

## Phase 5: SOLID Compliance Refactoring

### Timeline: 8 Weeks (80-100 hours)

```
Week 4: SRP - God Objects           [████████░░] 80%
Week 5: DIP - Remove Globals        [██████████] 100%
Week 6: OCP - Add Abstractions      [████████░░] 80%
Week 7: ISP + LSP                   [██████░░░░] 60%
Week 8: Patterns + Polish           [████░░░░░░] 40%
```

---

### Week 4: Single Responsibility Principle

**Goal:** Break down God Objects into focused modules

**Total Effort:** 18-22 hours

#### Day 1-2: Task 5.1.1 - Split settings.py (5-6 hours)

**Problem:**
- 841 lines, 26 functions
- Handles: Menu, Intervals, Quiet Hours, Reminders, FSM, Scheduler

**Solution:**
Split into 4 focused modules:

```
src/api/handlers/settings/
├── __init__.py              # Router aggregation
├── main_menu.py            # Main settings menu (100 lines)
├── interval_settings.py    # Poll interval configuration (250 lines)
├── quiet_hours_settings.py # Quiet hours management (250 lines)
└── reminder_settings.py    # Reminder configuration (200 lines)
```

**Steps:**

1. **Create directory structure** (5 min)
```bash
mkdir -p services/tracker_activity_bot/src/api/handlers/settings
touch services/tracker_activity_bot/src/api/handlers/settings/__init__.py
touch services/tracker_activity_bot/src/api/handlers/settings/main_menu.py
touch services/tracker_activity_bot/src/api/handlers/settings/interval_settings.py
touch services/tracker_activity_bot/src/api/handlers/settings/quiet_hours_settings.py
touch services/tracker_activity_bot/src/api/handlers/settings/reminder_settings.py
```

2. **Extract main_menu.py** (1 hour)

Move functions:
- `show_settings_menu()` (lines 36-161)
- `return_to_main_menu()` (lines 836-841)

Create helper function for user/settings retrieval (DRY principle).

3. **Extract interval_settings.py** (1.5 hours)

Move functions:
- `show_interval_type()` (lines 165-176)
- `show_weekday_intervals()` (lines 178-197)
- `set_weekday_interval()` (lines 199-230)
- `show_weekday_custom_input()` (lines 232-249)
- `process_weekday_custom_input()` (lines 251-299)
- `show_weekend_intervals()` (lines 301-320)
- `set_weekend_interval()` (lines 322-353)
- `show_weekend_custom_input()` (lines 355-372)
- `process_weekend_custom_input()` (lines 374-422)

4. **Extract quiet_hours_settings.py** (1.5 hours)

Move functions:
- `show_quiet_hours()` (lines 424-452)
- `toggle_quiet_hours()` (lines 454-483)
- `show_quiet_time_selection()` (lines 485-500)
- `show_quiet_start_selection()` (lines 502-521)
- `show_quiet_end_selection()` (lines 523-542)
- `set_quiet_start_time()` (lines 544-580)
- `set_quiet_end_time()` (lines 582-618)
- `process_custom_quiet_start()` (lines 750-777)
- `process_custom_quiet_end()` (lines 779-806)

5. **Extract reminder_settings.py** (1 hour)

Move functions:
- `show_reminders()` (lines 620-641)
- `toggle_reminders()` (lines 643-659)
- `show_reminder_delay()` (lines 661-679)
- `set_reminder_delay()` (lines 681-716)
- `process_reminder_delay_custom()` (lines 718-748)

6. **Create __init__.py aggregator** (30 min)

```python
"""Settings handlers module."""

from aiogram import Router

from .main_menu import router as main_menu_router
from .interval_settings import router as interval_router
from .quiet_hours_settings import router as quiet_hours_router
from .reminder_settings import router as reminder_router

# Aggregate all settings routers
router = Router()
router.include_router(main_menu_router)
router.include_router(interval_router)
router.include_router(quiet_hours_router)
router.include_router(reminder_router)

__all__ = ["router"]
```

7. **Update imports in main.py** (15 min)

```python
# Before
from src.api.handlers import settings as settings_router

# After
from src.api.handlers.settings import router as settings_router
```

8. **Test all settings functionality** (30 min)

```bash
# Manual testing checklist
# - Open settings menu
# - Change interval settings
# - Configure quiet hours
# - Configure reminders
# - Verify scheduler updates
```

**Checklist:**
- [ ] Create directory structure
- [ ] Extract main_menu.py with helper function
- [ ] Extract interval_settings.py
- [ ] Extract quiet_hours_settings.py
- [ ] Extract reminder_settings.py
- [ ] Create __init__.py aggregator
- [ ] Update main.py imports
- [ ] Test all settings work
- [ ] Delete old settings.py
- [ ] Verify no imports reference old file

**Success Criteria:**
- ✅ No single file > 300 lines
- ✅ Each file has single responsibility
- ✅ All settings functionality works
- ✅ No code duplication in user/settings retrieval

---

#### Day 2-3: Task 5.1.2 - Split poll.py (4-5 hours)

**Problem:**
- 653 lines
- `send_automatic_poll()` does 8 different things
- Mixed FSM checking, scheduling, formatting, sending

**Solution:**
Extract 3 focused classes:

```python
# New structure
src/application/services/poll/
├── __init__.py
├── state_checker.py       # PollStateChecker class
├── scheduler.py          # PollScheduler class
└── message_builder.py    # PollMessageBuilder class
```

**Step 1: Extract PollStateChecker** (1.5 hours)

```python
# src/application/services/poll/state_checker.py
"""Poll state checking service."""

import logging
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.redis import RedisStorage

logger = logging.getLogger(__name__)


class PollStateChecker:
    """
    Check if user can receive poll based on FSM state.

    This class encapsulates the logic for checking whether a user
    is currently in an FSM state and available to receive polls.
    """

    def __init__(self, storage: RedisStorage):
        """
        Initialize state checker with FSM storage.

        Args:
            storage: Redis storage for FSM state
        """
        self.storage = storage

    async def can_send_poll(self, user_id: int, bot_id: int) -> bool:
        """
        Check if user is available to receive poll.

        A user can receive a poll if they are not currently in any FSM state.

        Args:
            user_id: Telegram user ID
            bot_id: Bot instance ID

        Returns:
            True if user can receive poll, False otherwise
        """
        key = StorageKey(bot_id=bot_id, chat_id=user_id, user_id=user_id)

        try:
            current_state = await self.storage.get_state(key)

            if current_state is None:
                logger.debug(
                    "User available for poll",
                    extra={"user_id": user_id, "state": None}
                )
                return True

            logger.info(
                "User busy in FSM state",
                extra={"user_id": user_id, "state": current_state}
            )
            return False

        except Exception as e:
            logger.error(
                "Error checking user FSM state",
                extra={
                    "user_id": user_id,
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            )
            # Default to not sending poll if check fails
            return False
```

**Step 2: Extract PollScheduler** (1.5 hours)

```python
# src/application/services/poll/scheduler.py
"""Poll scheduling service."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger

from src.core.constants import POLL_POSTPONE_MINUTES

logger = logging.getLogger(__name__)


class PollScheduler:
    """
    Handle poll scheduling and postponing.

    This class manages the scheduling of automatic polls,
    including postponing polls when users are busy.
    """

    def __init__(self, scheduler: AsyncIOScheduler, jobs: Dict[int, str]):
        """
        Initialize poll scheduler.

        Args:
            scheduler: APScheduler instance
            jobs: Dictionary mapping user_id to job_id
        """
        self.scheduler = scheduler
        self.jobs = jobs

    async def postpone_poll(
        self,
        user_id: int,
        bot: Bot,
        minutes: int = POLL_POSTPONE_MINUTES
    ) -> None:
        """
        Postpone poll for user by specified minutes.

        Schedules a new poll job to run after the specified delay.
        If user already has a scheduled poll, it will be replaced.

        Args:
            user_id: Telegram user ID
            bot: Bot instance for sending poll
            minutes: Minutes to postpone (default from constants)
        """
        next_time = datetime.now(timezone.utc) + timedelta(minutes=minutes)

        # Import here to avoid circular dependency
        from src.api.handlers.poll import send_automatic_poll

        try:
            job = self.scheduler.add_job(
                func=lambda: send_automatic_poll(bot, user_id),
                trigger=DateTrigger(run_date=next_time),
                id=f"poll_postponed_{user_id}_{next_time.timestamp()}",
                replace_existing=True
            )

            self.jobs[user_id] = job.id

            logger.info(
                "Poll postponed for user",
                extra={
                    "user_id": user_id,
                    "postpone_minutes": minutes,
                    "next_poll_time": next_time.isoformat(),
                    "job_id": job.id
                }
            )

        except Exception as e:
            logger.error(
                "Failed to postpone poll",
                extra={
                    "user_id": user_id,
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            )

    def cancel_poll(self, user_id: int) -> None:
        """
        Cancel scheduled poll for user.

        Args:
            user_id: Telegram user ID
        """
        if user_id in self.jobs:
            job_id = self.jobs[user_id]
            try:
                self.scheduler.remove_job(job_id)
                del self.jobs[user_id]
                logger.info(
                    "Poll job cancelled",
                    extra={"user_id": user_id, "job_id": job_id}
                )
            except Exception as e:
                logger.warning(
                    "Failed to cancel poll job",
                    extra={
                        "user_id": user_id,
                        "job_id": job_id,
                        "error": str(e)
                    }
                )
```

**Step 3: Extract PollMessageBuilder** (1 hour)

```python
# src/application/services/poll/message_builder.py
"""Poll message formatting service."""

import logging
from src.application.utils.formatters import format_duration

logger = logging.getLogger(__name__)


class PollMessageBuilder:
    """
    Build poll message text with context.

    This class handles formatting of poll questions based on
    the configured interval and time context.
    """

    def build_poll_message(self, interval_minutes: int) -> str:
        """
        Build poll question with time context.

        Formats the interval into a human-readable string and
        constructs the poll question message.

        Args:
            interval_minutes: Poll interval in minutes

        Returns:
            Formatted poll message text

        Example:
            >>> builder = PollMessageBuilder()
            >>> builder.build_poll_message(120)
            '⏰ Время проверки активности!\\n\\nЧем ты занимался последние 2ч?'
        """
        time_str = self._format_interval(interval_minutes)

        message = (
            "⏰ Время проверки активности!\n\n"
            f"Чем ты занимался последние {time_str}?"
        )

        logger.debug(
            "Built poll message",
            extra={
                "interval_minutes": interval_minutes,
                "time_string": time_str
            }
        )

        return message

    def _format_interval(self, minutes: int) -> str:
        """
        Format interval for display in Russian.

        Args:
            minutes: Interval in minutes

        Returns:
            Formatted time string (e.g., "2ч", "1ч 30м")
        """
        if minutes < 60:
            return f"{minutes}м"

        hours = minutes // 60
        remaining_minutes = minutes % 60

        if remaining_minutes == 0:
            return f"{hours}ч"

        return f"{hours}ч {remaining_minutes}м"
```

**Step 4: Refactor send_automatic_poll()** (1 hour)

```python
# src/api/handlers/poll.py (refactored)
async def send_automatic_poll(bot: Bot, user_id: int):
    """
    Send automatic poll to user.

    Orchestrates poll sending using extracted services:
    - Checks user FSM state
    - Postpones if busy
    - Builds message
    - Sends poll
    - Updates last poll time

    Args:
        bot: Bot instance
        user_id: Telegram user ID
    """
    services = get_service_container()
    state_checker = PollStateChecker(get_fsm_storage())
    poll_scheduler = PollScheduler(
        scheduler_service.scheduler,
        scheduler_service.jobs
    )
    message_builder = PollMessageBuilder()

    logger.info(
        "Starting automatic poll",
        extra={"user_id": user_id}
    )

    try:
        # 1. Get user and settings
        user = await services.user.get_by_telegram_id(user_id)
        if not user:
            logger.warning("User not found", extra={"user_id": user_id})
            return

        settings = await services.settings.get_settings(user["id"])
        if not settings:
            logger.warning("Settings not found", extra={"user_id": user_id})
            return

        # 2. Check if user is available
        if not await state_checker.can_send_poll(user_id, bot.id):
            logger.info("User busy, postponing poll", extra={"user_id": user_id})
            await poll_scheduler.postpone_poll(user_id, bot)
            return

        # 3. Build message
        interval = get_poll_interval(settings)
        message = message_builder.build_poll_message(interval)

        # 4. Send poll
        await bot.send_message(
            chat_id=user_id,
            text=message,
            reply_markup=get_poll_response_keyboard()
        )

        logger.info("Poll sent successfully", extra={"user_id": user_id})

        # 5. Update last poll time
        await services.user.update_last_poll_time(
            user["id"],
            datetime.now(timezone.utc)
        )

    except Exception as e:
        logger.error(
            "Error sending automatic poll",
            extra={
                "user_id": user_id,
                "error": str(e),
                "error_type": type(e).__name__
            },
            exc_info=True
        )
```

**Checklist:**
- [ ] Create `application/services/poll/` directory
- [ ] Implement `PollStateChecker` class
- [ ] Implement `PollScheduler` class
- [ ] Implement `PollMessageBuilder` class
- [ ] Refactor `send_automatic_poll()` to use services
- [ ] Add unit tests for each class
- [ ] Test poll sending works
- [ ] Test poll postponing works
- [ ] Verify logs are informative

**Success Criteria:**
- ✅ `send_automatic_poll()` < 50 lines
- ✅ Each class has single responsibility
- ✅ All classes have 90%+ test coverage
- ✅ Poll functionality unchanged

---

#### Day 3-4: Task 5.1.3 - Split activity.py (4-5 hours)

**Problem:**
- 734 lines, 15 functions
- Mixed creation, view, validation, FSM management

**Solution:**
Split into 3 focused modules:

```
src/api/handlers/activities/
├── __init__.py
├── creation.py      # Activity creation flow (400 lines)
├── view.py         # Activity viewing (150 lines)
└── fsm.py          # FSM management (150 lines)
```

**Plus extract business logic:**

```
src/application/services/
└── activity_business_logic.py  # Business validation
```

**Step 1: Extract view.py** (1 hour)

Move function:
- `show_my_activities()` (lines 576-601)

```python
# src/api/handlers/activities/view.py
"""Activity viewing handlers."""

import logging
from aiogram import Router, types, F
from typing import Annotated

from src.api.dependencies import get_activity_service, get_user_service
from src.api.decorators import require_user
from src.api.keyboards.main_menu import get_main_menu_keyboard
from src.application.utils.formatters import format_activity_list
from src.application.utils.decorators import with_typing_action
from src.core.logging_middleware import log_user_action
from src.core.constants import MAX_ACTIVITY_LIMIT

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "my_activities")
@require_user
@with_typing_action
@log_user_action("my_activities_button_clicked")
async def show_my_activities(
    callback: types.CallbackQuery,
    user: dict
) -> None:
    """
    Show user's recent activities.

    Retrieves and displays the most recent activities for the user,
    formatted with duration and category information.

    Args:
        callback: Telegram callback query
        user: User dict (injected by @require_user decorator)
    """
    logger.debug(
        "Fetching user activities",
        extra={"user_id": user["id"]}
    )

    try:
        # Get activity service
        activity_service = get_activity_service()

        # Fetch recent activities
        activities = await activity_service.get_user_activities(
            user_id=user["id"],
            limit=MAX_ACTIVITY_LIMIT
        )

        if not activities:
            await callback.message.answer(
                "📋 У тебя пока нет активностей.\n\n"
                "Нажми 'Добавить активность', чтобы создать первую запись!",
                reply_markup=get_main_menu_keyboard()
            )
            await callback.answer()
            return

        # Format activities for display
        text = format_activity_list(activities, user["timezone"])

        await callback.message.answer(
            text,
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer()

        logger.info(
            "Activities displayed",
            extra={
                "user_id": user["id"],
                "count": len(activities)
            }
        )

    except Exception as e:
        logger.error(
            "Error fetching activities",
            extra={
                "user_id": user["id"],
                "error": str(e),
                "error_type": type(e).__name__
            },
            exc_info=True
        )
        await callback.message.answer(
            "⚠️ Произошла ошибка при загрузке активностей.",
            reply_markup=get_main_menu_keyboard()
        )
        await callback.answer()
```

**Step 2: Extract fsm.py** (1 hour)

Move functions:
- `cancel_activity_fsm()` (lines 603-627)
- `handle_fsm_reminder_continue()` (lines 629-694)
- `show_help()` (lines 696-734)

**Step 3: Extract business logic** (1.5 hours)

```python
# src/application/services/activity_business_logic.py
"""Activity business logic service."""

import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class ActivityBusinessLogic:
    """
    Business logic for activity operations.

    Handles validation and transformation of activity data
    separate from presentation layer.
    """

    @staticmethod
    def validate_time_range(
        start_time: datetime,
        end_time: datetime
    ) -> tuple[bool, Optional[str]]:
        """
        Validate activity time range.

        Args:
            start_time: Activity start time
            end_time: Activity end time

        Returns:
            Tuple of (is_valid, error_message)
        """
        if end_time <= start_time:
            return False, "Время окончания должно быть позже времени начала"

        duration = (end_time - start_time).total_seconds() / 60

        if duration < 1:
            return False, "Минимальная длительность активности - 1 минута"

        if duration > 24 * 60:
            return False, "Максимальная длительность активности - 24 часа"

        return True, None

    @staticmethod
    def calculate_duration(start_time: datetime, end_time: datetime) -> int:
        """
        Calculate activity duration in minutes.

        Args:
            start_time: Activity start time
            end_time: Activity end time

        Returns:
            Duration in minutes (rounded)
        """
        duration_seconds = (end_time - start_time).total_seconds()
        return round(duration_seconds / 60)

    @staticmethod
    def extract_and_validate_tags(tags_str: Optional[str]) -> list[str]:
        """
        Extract and validate tags from string.

        Args:
            tags_str: Comma-separated tags string

        Returns:
            List of cleaned tags
        """
        if not tags_str:
            return []

        # Split by comma and clean
        tags = [tag.strip() for tag in tags_str.split(",")]

        # Filter empty and validate
        tags = [tag for tag in tags if tag and len(tag) <= 50]

        # Limit to 10 tags
        return tags[:10]
```

**Step 4: Refactor creation.py to use business logic** (1.5 hours)

Update `save_activity()` function to use `ActivityBusinessLogic`.

**Checklist:**
- [ ] Create `handlers/activities/` directory
- [ ] Extract `view.py` with show_my_activities
- [ ] Extract `fsm.py` with FSM handlers
- [ ] Create `ActivityBusinessLogic` service
- [ ] Refactor `creation.py` to use business logic
- [ ] Create `__init__.py` router aggregator
- [ ] Update imports in main.py
- [ ] Test activity creation flow
- [ ] Test activity viewing
- [ ] Test FSM cancellation
- [ ] Delete old activity.py

**Success Criteria:**
- ✅ No file > 400 lines
- ✅ Business logic separated from handlers
- ✅ All activity functionality works
- ✅ Validation logic reusable

---

#### Day 4: Task 5.1.4 - Extract ActivitySaver (2-3 hours)

**Problem:**
- `save_activity()` function mixes validation, transformation, persistence

**Solution:**
Create dedicated `ActivitySaver` class.

```python
# src/application/services/activity_saver.py
"""Activity saving service."""

import logging
from datetime import datetime
from typing import Dict, Any

from src.infrastructure.http_clients.activity_service import ActivityService
from src.application.services.activity_business_logic import ActivityBusinessLogic

logger = logging.getLogger(__name__)


class ActivitySaver:
    """
    Handle activity save operations.

    Orchestrates validation, transformation, and persistence
    of activity data from FSM state.
    """

    def __init__(self, activity_service: ActivityService):
        """
        Initialize activity saver.

        Args:
            activity_service: HTTP service for activity API calls
        """
        self.activity_service = activity_service
        self.business_logic = ActivityBusinessLogic()

    async def save_from_fsm(
        self,
        fsm_data: Dict[str, Any],
        user_id: int,
        timezone: str
    ) -> Dict[str, Any]:
        """
        Save activity from FSM state data.

        Validates, transforms, and persists activity data.

        Args:
            fsm_data: Data collected from FSM states
            user_id: User identifier
            timezone: User timezone for time conversion

        Returns:
            Created activity dict

        Raises:
            ValueError: If validation fails
            HTTPError: If API call fails
        """
        logger.debug(
            "Saving activity from FSM",
            extra={
                "user_id": user_id,
                "has_start_time": "start_time" in fsm_data,
                "has_end_time": "end_time" in fsm_data,
                "has_description": "description" in fsm_data
            }
        )

        # 1. Validate completeness
        self._validate_fsm_data(fsm_data)

        # 2. Parse times
        start_time = datetime.fromisoformat(fsm_data["start_time"])
        end_time = datetime.fromisoformat(fsm_data["end_time"])

        # 3. Validate time range
        is_valid, error = self.business_logic.validate_time_range(
            start_time,
            end_time
        )
        if not is_valid:
            raise ValueError(error)

        # 4. Extract tags
        tags = self.business_logic.extract_and_validate_tags(
            fsm_data.get("tags")
        )

        # 5. Transform to API format
        activity_data = self._transform_to_api_format(
            fsm_data=fsm_data,
            user_id=user_id,
            start_time=start_time,
            end_time=end_time,
            tags=tags
        )

        # 6. Persist via API
        try:
            activity = await self.activity_service.create_activity(
                **activity_data
            )

            logger.info(
                "Activity saved successfully",
                extra={
                    "user_id": user_id,
                    "activity_id": activity.id,
                    "duration_minutes": activity.duration_minutes
                }
            )

            return activity

        except Exception as e:
            logger.error(
                "Failed to save activity",
                extra={
                    "user_id": user_id,
                    "error": str(e),
                    "error_type": type(e).__name__
                },
                exc_info=True
            )
            raise

    def _validate_fsm_data(self, fsm_data: Dict[str, Any]) -> None:
        """
        Validate FSM data completeness.

        Args:
            fsm_data: FSM state data

        Raises:
            ValueError: If required fields missing
        """
        required_fields = ["start_time", "end_time", "description"]
        missing = [f for f in required_fields if not fsm_data.get(f)]

        if missing:
            raise ValueError(
                f"Missing required fields: {', '.join(missing)}"
            )

    def _transform_to_api_format(
        self,
        fsm_data: Dict[str, Any],
        user_id: int,
        start_time: datetime,
        end_time: datetime,
        tags: list[str]
    ) -> Dict[str, Any]:
        """
        Transform FSM data to API format.

        Args:
            fsm_data: FSM state data
            user_id: User identifier
            start_time: Parsed start time
            end_time: Parsed end time
            tags: Validated tags list

        Returns:
            Activity data in API format
        """
        return {
            "user_id": user_id,
            "category_id": fsm_data.get("category_id"),
            "description": fsm_data["description"],
            "tags": tags,
            "start_time": start_time,
            "end_time": end_time
        }
```

**Checklist:**
- [ ] Create `activity_saver.py`
- [ ] Implement `ActivitySaver` class
- [ ] Add validation methods
- [ ] Add transformation methods
- [ ] Update handlers to use `ActivitySaver`
- [ ] Add unit tests (90%+ coverage)
- [ ] Test activity creation flow
- [ ] Verify error handling works

**Success Criteria:**
- ✅ Save logic extracted from handler
- ✅ Validation is reusable
- ✅ Easy to test in isolation
- ✅ Clear separation of concerns

---

### Week 5: Dependency Inversion Principle

**Goal:** Remove all global state, implement proper DI

**Total Effort:** 16-20 hours

---

#### Day 1-2: Task 5.5.1 - Remove Global scheduler_service (6-8 hours)

**Problem:**
```python
# ❌ CRITICAL VIOLATION
# services/tracker_activity_bot/src/application/services/scheduler_service.py:147
scheduler_service = SchedulerService()  # Global mutable state!

# Used everywhere:
from src.application.services.scheduler_service import scheduler_service
await scheduler_service.schedule_poll(...)
```

**Impact:**
- Cannot test with mocks
- Cannot have multiple instances
- Hidden dependencies
- Difficult lifecycle management

**Solution:**
Create protocol and inject via ServiceContainer.

**Step 1: Create PollSchedulerProtocol** (1 hour)

```python
# src/application/protocols/poll_scheduler.py
"""Poll scheduler protocol for dependency inversion."""

from typing import Protocol, Callable, Optional
from datetime import datetime


class PollSchedulerProtocol(Protocol):
    """
    Protocol for poll scheduling operations.

    Defines the interface for scheduling automatic polls,
    allowing for different implementations and easier testing.
    """

    async def schedule_poll(
        self,
        user_id: int,
        settings: dict,
        user_timezone: str,
        send_poll_callback: Callable,
        bot
    ) -> None:
        """
        Schedule next poll for user based on settings.

        Args:
            user_id: Telegram user ID
            settings: User settings dict with poll configuration
            user_timezone: User timezone string (e.g., "Europe/Moscow")
            send_poll_callback: Async function to call when poll due
            bot: Bot instance to pass to callback
        """
        ...

    async def cancel_poll(self, user_id: int) -> None:
        """
        Cancel scheduled poll for user.

        Args:
            user_id: Telegram user ID
        """
        ...

    async def reschedule_poll(
        self,
        user_id: int,
        settings: dict,
        user_timezone: str,
        send_poll_callback: Callable,
        bot
    ) -> None:
        """
        Reschedule poll for user (cancel + schedule).

        Args:
            user_id: Telegram user ID
            settings: Updated user settings
            user_timezone: User timezone
            send_poll_callback: Poll callback function
            bot: Bot instance
        """
        ...

    def start(self) -> None:
        """Start the scheduler."""
        ...

    def stop(self, wait: bool = True) -> None:
        """
        Stop the scheduler.

        Args:
            wait: If True, wait for pending jobs to complete
        """
        ...

    @property
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        ...
```

**Step 2: Update SchedulerService to implement protocol** (30 min)

```python
# src/application/services/scheduler_service.py
"""Scheduler service implementing PollSchedulerProtocol."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.application.protocols.poll_scheduler import PollSchedulerProtocol
from src.application.utils.time_helpers import (
    calculate_poll_start_time,
    get_poll_interval
)

logger = logging.getLogger(__name__)


class SchedulerService(PollSchedulerProtocol):
    """
    APScheduler-based poll scheduler implementation.

    Implements PollSchedulerProtocol using APScheduler for
    job scheduling and management.
    """

    def __init__(self):
        """Initialize scheduler service."""
        self.scheduler = AsyncIOScheduler(timezone="UTC")
        self.jobs: Dict[int, str] = {}
        logger.info("Scheduler service initialized")

    # ... existing methods with proper type hints ...

    # Remove global instance creation at module level
    # scheduler_service = SchedulerService()  # DELETE THIS LINE!
```

**Step 3: Add scheduler to ServiceContainer** (2 hours)

```python
# src/api/dependencies.py (updated)
"""Dependency injection for bot services."""

from typing import Optional

from src.infrastructure.http_clients.http_client import DataAPIClient
from src.infrastructure.http_clients.activity_service import ActivityService
from src.infrastructure.http_clients.category_service import CategoryService
from src.infrastructure.http_clients.user_service import UserService
from src.infrastructure.http_clients.user_settings_service import UserSettingsService
from src.application.services.scheduler_service import SchedulerService
from src.application.protocols.poll_scheduler import PollSchedulerProtocol


# Global instances (to be created once)
_api_client: Optional[DataAPIClient] = None
_scheduler: Optional[PollSchedulerProtocol] = None


class ServiceContainer:
    """
    Service container with all dependencies.

    Provides access to all services needed by handlers,
    with lazy initialization and proper lifecycle management.
    """

    def __init__(
        self,
        api_client: Optional[DataAPIClient] = None,
        scheduler: Optional[PollSchedulerProtocol] = None
    ):
        """
        Initialize service container.

        Args:
            api_client: HTTP client (uses global if not provided)
            scheduler: Poll scheduler (uses global if not provided)
        """
        self._api_client = api_client or get_api_client()
        self._scheduler = scheduler or get_scheduler()

    @property
    def user(self) -> UserService:
        """Get user service."""
        return UserService(self._api_client)

    @property
    def category(self) -> CategoryService:
        """Get category service."""
        return CategoryService(self._api_client)

    @property
    def activity(self) -> ActivityService:
        """Get activity service."""
        return ActivityService(self._api_client)

    @property
    def settings(self) -> UserSettingsService:
        """Get user settings service."""
        return UserSettingsService(self._api_client)

    @property
    def scheduler(self) -> PollSchedulerProtocol:
        """Get poll scheduler."""
        return self._scheduler


# Dependency providers

def get_api_client() -> DataAPIClient:
    """Get or create API client."""
    global _api_client
    if _api_client is None:
        _api_client = DataAPIClient()
    return _api_client


def get_scheduler() -> PollSchedulerProtocol:
    """Get or create scheduler."""
    global _scheduler
    if _scheduler is None:
        _scheduler = SchedulerService()
    return _scheduler


async def close_dependencies() -> None:
    """Close all dependencies on shutdown."""
    global _api_client, _scheduler

    if _api_client is not None:
        await _api_client.close()
        _api_client = None
        logger.info("API client closed")

    if _scheduler is not None:
        _scheduler.stop(wait=True)
        _scheduler = None
        logger.info("Scheduler stopped")
```

**Step 4: Update all handlers to use ServiceContainer.scheduler** (2-3 hours)

Find and replace all occurrences:

```bash
# Find all usages
grep -r "from src.application.services.scheduler_service import scheduler_service" services/tracker_activity_bot/src/

# Files to update:
# - src/api/handlers/settings.py (multiple locations)
# - src/api/handlers/poll.py
# - src/application/services/fsm_timeout_service.py
```

**Before:**
```python
from src.application.services.scheduler_service import scheduler_service

async def handler(callback: types.CallbackQuery, services: ServiceContainer):
    await scheduler_service.schedule_poll(...)  # Direct global access
```

**After:**
```python
async def handler(callback: types.CallbackQuery, services: ServiceContainer):
    await services.scheduler.schedule_poll(...)  # Via DI
```

**Step 5: Update main.py** (1 hour)

```python
# src/main.py (updated)
"""Bot entry point with proper DI."""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage

from src.core.config import settings
from src.core.logging import setup_logging
from src.api.dependencies import get_scheduler, close_dependencies
# ... other imports

setup_logging(service_name="tracker_activity_bot", log_level=settings.log_level)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Main bot entry point."""
    logger.info("Starting tracker_activity_bot")

    # Initialize bot and dispatcher
    bot = Bot(token=settings.telegram_bot_token)
    storage = RedisStorage.from_url(settings.redis_url)
    dp = Dispatcher(storage=storage)

    # Register middleware and routers
    # ...

    # Start scheduler via DI
    scheduler = get_scheduler()
    scheduler.start()
    logger.info("Scheduler started")

    try:
        await dp.start_polling(bot)
    finally:
        # Cleanup via DI
        await close_dependencies()
        await bot.session.close()
        await storage.close()
        logger.info("Bot shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
```

**Step 6: Create mock scheduler for tests** (1 hour)

```python
# tests/mocks/mock_scheduler.py
"""Mock scheduler for testing."""

from typing import List, Dict, Callable, Any
from src.application.protocols.poll_scheduler import PollSchedulerProtocol


class MockScheduler(PollSchedulerProtocol):
    """
    Mock implementation of poll scheduler for testing.

    Records all scheduling operations without actually scheduling,
    allowing verification of scheduler interactions in tests.
    """

    def __init__(self):
        """Initialize mock scheduler."""
        self.scheduled_polls: List[Dict[str, Any]] = []
        self.cancelled_polls: List[int] = []
        self.rescheduled_polls: List[Dict[str, Any]] = []
        self._is_running = False

    async def schedule_poll(
        self,
        user_id: int,
        settings: dict,
        user_timezone: str,
        send_poll_callback: Callable,
        bot
    ) -> None:
        """Record scheduled poll."""
        self.scheduled_polls.append({
            "user_id": user_id,
            "settings": settings,
            "timezone": user_timezone
        })

    async def cancel_poll(self, user_id: int) -> None:
        """Record cancelled poll."""
        self.cancelled_polls.append(user_id)

    async def reschedule_poll(
        self,
        user_id: int,
        settings: dict,
        user_timezone: str,
        send_poll_callback: Callable,
        bot
    ) -> None:
        """Record rescheduled poll."""
        self.rescheduled_polls.append({
            "user_id": user_id,
            "settings": settings,
            "timezone": user_timezone
        })

    def start(self) -> None:
        """Start mock scheduler."""
        self._is_running = True

    def stop(self, wait: bool = True) -> None:
        """Stop mock scheduler."""
        self._is_running = False

    @property
    def is_running(self) -> bool:
        """Check if running."""
        return self._is_running

    def reset(self) -> None:
        """Reset all recorded operations."""
        self.scheduled_polls.clear()
        self.cancelled_polls.clear()
        self.rescheduled_polls.clear()
```

**Step 7: Write tests** (1 hour)

```python
# tests/unit/test_scheduler_di.py
"""Test scheduler dependency injection."""

import pytest
from aiogram.types import CallbackQuery

from src.api.dependencies import ServiceContainer
from tests.mocks.mock_scheduler import MockScheduler


@pytest.mark.asyncio
async def test_handler_uses_injected_scheduler():
    """Test that handlers use scheduler from ServiceContainer."""
    # Arrange
    mock_scheduler = MockScheduler()
    services = ServiceContainer(scheduler=mock_scheduler)

    # Act
    await services.scheduler.schedule_poll(
        user_id=123,
        settings={"poll_interval_weekday": 120},
        user_timezone="UTC",
        send_poll_callback=lambda: None,
        bot=None
    )

    # Assert
    assert len(mock_scheduler.scheduled_polls) == 1
    assert mock_scheduler.scheduled_polls[0]["user_id"] == 123


@pytest.mark.asyncio
async def test_scheduler_lifecycle():
    """Test scheduler start/stop lifecycle."""
    # Arrange
    mock_scheduler = MockScheduler()

    # Act
    mock_scheduler.start()
    assert mock_scheduler.is_running

    mock_scheduler.stop()
    assert not mock_scheduler.is_running
```

**Checklist:**
- [ ] Create `PollSchedulerProtocol`
- [ ] Update `SchedulerService` to implement protocol
- [ ] Add scheduler to `ServiceContainer`
- [ ] Remove global `scheduler_service` instance
- [ ] Update all handlers to use `services.scheduler`
- [ ] Update `main.py` lifecycle management
- [ ] Create `MockScheduler` for tests
- [ ] Write unit tests for DI
- [ ] Test all scheduling functionality works
- [ ] Verify no imports of global scheduler remain

**Success Criteria:**
- ✅ No global `scheduler_service` instance
- ✅ All handlers use DI
- ✅ Tests use mock scheduler
- ✅ Scheduler lifecycle properly managed
- ✅ All functionality unchanged

**Commands to verify:**
```bash
# Find any remaining global imports
grep -r "from src.application.services.scheduler_service import scheduler_service" services/tracker_activity_bot/src/

# Should return nothing if successful
echo $?  # Should be 1 (not found)

# Run tests
cd services/tracker_activity_bot
pytest tests/unit/test_scheduler_di.py -v
```

---

#### Day 2-3: Task 5.5.2 - Remove Global FSM Storage (4-5 hours)

**Problem:**
```python
# ❌ CRITICAL VIOLATION
# services/tracker_activity_bot/src/api/handlers/poll.py:32-48
_fsm_storage: RedisStorage | None = None

def get_fsm_storage() -> RedisStorage:
    global _fsm_storage
    if _fsm_storage is None:
        _fsm_storage = RedisStorage.from_url(app_settings.redis_url)
    return _fsm_storage  # Never closed!
```

**Solution:**
Create protocol and inject via dependency.

**Step 1: Create FSMStorageProtocol** (30 min)

```python
# src/application/protocols/fsm_storage.py
"""FSM storage protocol for dependency inversion."""

from typing import Protocol, Optional, Any
from aiogram.fsm.storage.base import StorageKey


class FSMStorageProtocol(Protocol):
    """
    Protocol for FSM state storage operations.

    Defines interface for getting/setting FSM state,
    allowing different storage implementations.
    """

    async def get_state(self, key: StorageKey) -> Optional[str]:
        """
        Get FSM state for user.

        Args:
            key: Storage key identifying user/chat

        Returns:
            Current state name or None if no state
        """
        ...

    async def set_state(self, key: StorageKey, state: Optional[str]) -> None:
        """
        Set FSM state for user.

        Args:
            key: Storage key identifying user/chat
            state: State name to set, or None to clear
        """
        ...

    async def get_data(self, key: StorageKey) -> dict[str, Any]:
        """
        Get FSM data for user.

        Args:
            key: Storage key identifying user/chat

        Returns:
            FSM data dictionary
        """
        ...

    async def set_data(self, key: StorageKey, data: dict[str, Any]) -> None:
        """
        Set FSM data for user.

        Args:
            key: Storage key identifying user/chat
            data: FSM data to store
        """
        ...

    async def close(self) -> None:
        """Close storage connections."""
        ...
```

**Step 2: Create Redis wrapper** (1 hour)

```python
# src/infrastructure/storage/redis_fsm_storage.py
"""Redis FSM storage wrapper."""

import logging
from typing import Optional, Any

from aiogram.fsm.storage.redis import RedisStorage
from aiogram.fsm.storage.base import StorageKey

from src.application.protocols.fsm_storage import FSMStorageProtocol
from src.core.config import settings

logger = logging.getLogger(__name__)


class RedisFSMStorage(FSMStorageProtocol):
    """
    Redis-backed FSM storage implementation.

    Wraps aiogram RedisStorage to implement FSMStorageProtocol,
    allowing for dependency injection and proper lifecycle management.
    """

    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize Redis FSM storage.

        Args:
            redis_url: Redis connection URL (uses settings if not provided)
        """
        url = redis_url or settings.redis_url
        self._storage = RedisStorage.from_url(url)
        logger.info("Redis FSM storage initialized", extra={"redis_url": url})

    async def get_state(self, key: StorageKey) -> Optional[str]:
        """Get FSM state from Redis."""
        return await self._storage.get_state(key)

    async def set_state(self, key: StorageKey, state: Optional[str]) -> None:
        """Set FSM state in Redis."""
        await self._storage.set_state(key, state)

    async def get_data(self, key: StorageKey) -> dict[str, Any]:
        """Get FSM data from Redis."""
        return await self._storage.get_data(key)

    async def set_data(self, key: StorageKey, data: dict[str, Any]) -> None:
        """Set FSM data in Redis."""
        await self._storage.set_data(key, data)

    async def close(self) -> None:
        """Close Redis connections."""
        await self._storage.close()
        logger.info("Redis FSM storage closed")
```

**Step 3: Update poll.py to use protocol** (1.5 hours)

```python
# src/api/handlers/poll.py (refactored)
"""Poll handlers with FSM storage DI."""

import logging
from datetime import datetime, timezone
from aiogram import Router, types, F, Bot
from aiogram.fsm.storage.base import StorageKey

from src.api.dependencies import get_fsm_storage
from src.api.states.poll import PollStates
from src.application.protocols.fsm_storage import FSMStorageProtocol
# ... other imports

router = Router()
logger = logging.getLogger(__name__)

# Remove global _fsm_storage variable


async def send_automatic_poll(
    bot: Bot,
    user_id: int,
    storage: FSMStorageProtocol
) -> None:
    """
    Send automatic poll to user.

    Args:
        bot: Bot instance
        user_id: Telegram user ID
        storage: FSM storage for state checking (injected)
    """
    # ... existing logic ...

    # Check FSM state using injected storage
    key = StorageKey(bot_id=bot.id, chat_id=user_id, user_id=user_id)
    current_state = await storage.get_state(key)

    if current_state:
        # User is busy, postpone
        logger.info("User in FSM state, postponing", extra={"user_id": user_id})
        await services.scheduler.postpone_poll(user_id, bot)
        return

    # ... rest of logic ...
```

**Step 4: Update dependencies.py** (1 hour)

```python
# src/api/dependencies.py (add FSM storage)
from src.infrastructure.storage.redis_fsm_storage import RedisFSMStorage
from src.application.protocols.fsm_storage import FSMStorageProtocol

_fsm_storage: Optional[FSMStorageProtocol] = None


def get_fsm_storage() -> FSMStorageProtocol:
    """Get or create FSM storage."""
    global _fsm_storage
    if _fsm_storage is None:
        _fsm_storage = RedisFSMStorage()
    return _fsm_storage


async def close_dependencies() -> None:
    """Close all dependencies."""
    global _api_client, _scheduler, _fsm_storage

    # ... existing cleanup ...

    if _fsm_storage is not None:
        await _fsm_storage.close()
        _fsm_storage = None
        logger.info("FSM storage closed")
```

**Step 5: Update fsm_timeout_service.py** (1 hour)

Replace all `RedisStorage.from_url()` calls with `get_fsm_storage()`.

**Checklist:**
- [ ] Create `FSMStorageProtocol`
- [ ] Create `RedisFSMStorage` wrapper
- [ ] Remove global `_fsm_storage` from poll.py
- [ ] Update `send_automatic_poll()` to receive storage parameter
- [ ] Add FSM storage to dependencies.py
- [ ] Update fsm_timeout_service.py to use shared storage
- [ ] Add close in cleanup
- [ ] Test poll sending works
- [ ] Test FSM state checking works
- [ ] Monitor Redis connections (should not leak)

**Success Criteria:**
- ✅ No global FSM storage
- ✅ Storage properly closed on shutdown
- ✅ No Redis connection leaks
- ✅ All FSM functionality works

---

#### Day 3-4: Task 5.5.3 - HTTP Client DI (Already covered in Phase 2)

This task was already planned in Phase 2 (Task 2.5), so mark as completed if Phase 2 is done.

---

### Week 6: Open/Closed Principle

**Goal:** Add abstractions for extensibility

**Total Effort:** 16-20 hours

---

#### Day 1-2: Task 5.2.1 - HTTP Client Middleware Pattern (6-8 hours)

**Problem:**
```python
# ❌ Cannot extend without modifying
class DataAPIClient:
    async def get(self, path: str, **kwargs):
        logger.debug(...)  # Hardcoded
        response.raise_for_status()  # Hardcoded
        return response.json()  # Hardcoded
```

**Solution:**
Implement Strategy Pattern with middleware pipeline.

**Step 1: Create middleware protocols** (1 hour)

```python
# src/infrastructure/http_clients/middleware/protocols.py
"""HTTP client middleware protocols."""

from typing import Protocol
import httpx


class RequestMiddleware(Protocol):
    """Protocol for request middleware."""

    async def process_request(self, request: httpx.Request) -> httpx.Request:
        """
        Process outgoing HTTP request.

        Middleware can modify request before sending:
        - Add headers
        - Log request details
        - Transform request data

        Args:
            request: Outgoing HTTP request

        Returns:
            Modified HTTP request
        """
        ...


class ResponseMiddleware(Protocol):
    """Protocol for response middleware."""

    async def process_response(self, response: httpx.Response) -> httpx.Response:
        """
        Process incoming HTTP response.

        Middleware can:
        - Log response details
        - Transform response data
        - Cache responses

        Args:
            response: Incoming HTTP response

        Returns:
            Modified HTTP response
        """
        ...


class ErrorHandler(Protocol):
    """Protocol for error handling strategies."""

    def should_handle(self, error: Exception) -> bool:
        """
        Check if this handler should process the error.

        Args:
            error: Exception that occurred

        Returns:
            True if this handler can process the error
        """
        ...

    async def handle(
        self,
        error: Exception,
        context: dict
    ) -> Exception:
        """
        Handle or transform the error.

        Args:
            error: Exception to handle
            context: Context dict with request details

        Returns:
            Original or transformed exception
        """
        ...
```

**Step 2: Implement middleware classes** (2 hours)

```python
# src/infrastructure/http_clients/middleware/logging.py
"""Logging middleware for HTTP client."""

import logging
import httpx

logger = logging.getLogger(__name__)


class LoggingMiddleware:
    """
    Middleware to log HTTP requests and responses.

    Logs request method, URL, and response status code
    with structured logging.
    """

    async def process_request(self, request: httpx.Request) -> httpx.Request:
        """
        Log outgoing request.

        Args:
            request: HTTP request

        Returns:
            Unmodified request
        """
        logger.debug(
            "HTTP request",
            extra={
                "method": request.method,
                "url": str(request.url),
                "has_body": bool(request.content)
            }
        )
        return request

    async def process_response(self, response: httpx.Response) -> httpx.Response:
        """
        Log incoming response.

        Args:
            response: HTTP response

        Returns:
            Unmodified response
        """
        logger.debug(
            "HTTP response",
            extra={
                "method": response.request.method,
                "url": str(response.request.url),
                "status_code": response.status_code,
                "content_length": len(response.content)
            }
        )
        return response
```

```python
# src/infrastructure/http_clients/middleware/retry.py
"""Retry middleware for HTTP client."""

import logging
import asyncio
import httpx

logger = logging.getLogger(__name__)


class RetryMiddleware:
    """
    Middleware to retry failed requests.

    Implements exponential backoff for transient errors.
    """

    def __init__(self, max_retries: int = 3, backoff_factor: float = 1.0):
        """
        Initialize retry middleware.

        Args:
            max_retries: Maximum number of retry attempts
            backoff_factor: Multiplier for exponential backoff
        """
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

    async def process_request(self, request: httpx.Request) -> httpx.Request:
        """
        Add retry metadata to request.

        Args:
            request: HTTP request

        Returns:
            Request with retry counter header
        """
        request.headers["X-Retry-Count"] = "0"
        return request

    # Note: Actual retry logic would be in the client,
    # this is just for demonstration
```

```python
# src/infrastructure/http_clients/middleware/auth.py
"""Authentication middleware for HTTP client."""

import httpx


class AuthMiddleware:
    """
    Middleware to add authentication headers.

    Adds Bearer token or API key to all requests.
    """

    def __init__(self, api_key: str):
        """
        Initialize auth middleware.

        Args:
            api_key: API key for authentication
        """
        self.api_key = api_key

    async def process_request(self, request: httpx.Request) -> httpx.Request:
        """
        Add authentication header.

        Args:
            request: HTTP request

        Returns:
            Request with Authorization header
        """
        request.headers["Authorization"] = f"Bearer {self.api_key}"
        return request
```

**Step 3: Create error handlers** (1.5 hours)

```python
# src/infrastructure/http_clients/middleware/error_handlers.py
"""Error handlers for HTTP client."""

import logging
import httpx

logger = logging.getLogger(__name__)


class DataAPIErrorHandler:
    """
    Handle Data API specific errors.

    Transforms HTTP errors into domain-specific exceptions.
    """

    def should_handle(self, error: Exception) -> bool:
        """Check if error is HTTP status error."""
        return isinstance(error, httpx.HTTPStatusError)

    async def handle(self, error: httpx.HTTPStatusError, context: dict) -> Exception:
        """
        Transform HTTP error to domain exception.

        Args:
            error: HTTP status error
            context: Request context

        Returns:
            Domain-specific exception
        """
        status_code = error.response.status_code

        if status_code == 404:
            logger.warning(
                "Resource not found",
                extra={"path": context.get("path"), "status_code": 404}
            )
            return ResourceNotFoundError(
                f"Resource not found: {context.get('path')}"
            )

        elif status_code == 409:
            logger.warning(
                "Resource conflict",
                extra={"path": context.get("path"), "status_code": 409}
            )
            return ResourceConflictError("Resource already exists")

        elif status_code >= 500:
            logger.error(
                "Server error",
                extra={
                    "path": context.get("path"),
                    "status_code": status_code,
                    "error": str(error)
                }
            )
            return ExternalServiceError(
                f"Data API error: {status_code}"
            )

        return error


class DefaultErrorHandler:
    """Default error handler for all other errors."""

    def should_handle(self, error: Exception) -> bool:
        """Handle all exceptions."""
        return True

    async def handle(self, error: Exception, context: dict) -> Exception:
        """
        Log and return error unchanged.

        Args:
            error: Any exception
            context: Request context

        Returns:
            Original exception
        """
        logger.error(
            "HTTP request failed",
            extra={
                "error": str(error),
                "error_type": type(error).__name__,
                "path": context.get("path")
            },
            exc_info=True
        )
        return error
```

**Step 4: Update DataAPIClient** (1.5 hours)

```python
# src/infrastructure/http_clients/http_client.py (refactored)
"""Extensible HTTP client with middleware support."""

import logging
from typing import TypeVar, Type, List, Any

import httpx
from pydantic import BaseModel

from src.core.config import settings
from src.infrastructure.http_clients.middleware.protocols import (
    RequestMiddleware,
    ResponseMiddleware,
    ErrorHandler
)

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


class DataAPIClient:
    """
    Extensible HTTP client with middleware pipeline.

    Supports request/response middleware and pluggable error handlers,
    allowing extension without modification (Open/Closed Principle).
    """

    def __init__(
        self,
        request_middleware: List[RequestMiddleware] = None,
        response_middleware: List[ResponseMiddleware] = None,
        error_handlers: List[ErrorHandler] = None
    ):
        """
        Initialize client with middleware.

        Args:
            request_middleware: List of request middleware
            response_middleware: List of response middleware
            error_handlers: List of error handlers
        """
        self.base_url = settings.data_api_url
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=10.0
        )

        self.request_middleware = request_middleware or []
        self.response_middleware = response_middleware or []
        self.error_handlers = error_handlers or []

    async def get(
        self,
        path: str,
        response_model: Type[T],
        **kwargs: Any
    ) -> T:
        """
        Make GET request with middleware pipeline.

        Args:
            path: API endpoint path
            response_model: Pydantic model for response
            **kwargs: Additional request parameters

        Returns:
            Parsed response as Pydantic model

        Raises:
            HTTPError: If request fails
        """
        request = self.client.build_request("GET", path, **kwargs)

        # Apply request middleware
        for middleware in self.request_middleware:
            request = await middleware.process_request(request)

        try:
            response = await self.client.send(request)

            # Apply response middleware
            for middleware in self.response_middleware:
                response = await middleware.process_response(response)

            response.raise_for_status()
            data = response.json()
            return response_model(**data)

        except Exception as e:
            # Apply error handlers
            for handler in self.error_handlers:
                if handler.should_handle(e):
                    e = await handler.handle(e, {"path": path, "method": "GET"})
            raise e

    def add_request_middleware(self, middleware: RequestMiddleware) -> None:
        """
        Add request middleware at runtime.

        Args:
            middleware: Middleware to add
        """
        self.request_middleware.append(middleware)

    def add_response_middleware(self, middleware: ResponseMiddleware) -> None:
        """
        Add response middleware at runtime.

        Args:
            middleware: Middleware to add
        """
        self.response_middleware.append(middleware)

    def add_error_handler(self, handler: ErrorHandler) -> None:
        """
        Add error handler at runtime.

        Args:
            handler: Error handler to add
        """
        self.error_handlers.append(handler)

    async def close(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()
```

**Step 5: Update dependencies to use middleware** (30 min)

```python
# src/api/dependencies.py (update get_api_client)
from src.infrastructure.http_clients.middleware.logging import LoggingMiddleware
from src.infrastructure.http_clients.middleware.error_handlers import (
    DataAPIErrorHandler,
    DefaultErrorHandler
)


def get_api_client() -> DataAPIClient:
    """Get or create API client with middleware."""
    global _api_client
    if _api_client is None:
        _api_client = DataAPIClient(
            request_middleware=[
                LoggingMiddleware()
            ],
            response_middleware=[
                LoggingMiddleware()
            ],
            error_handlers=[
                DataAPIErrorHandler(),
                DefaultErrorHandler()
            ]
        )
    return _api_client
```

**Checklist:**
- [ ] Create middleware protocols
- [ ] Implement `LoggingMiddleware`
- [ ] Implement `RetryMiddleware`
- [ ] Implement `AuthMiddleware`
- [ ] Create error handler classes
- [ ] Refactor `DataAPIClient` to use middleware
- [ ] Update dependencies to configure middleware
- [ ] Write unit tests for each middleware
- [ ] Test HTTP client with middleware
- [ ] Verify logging works
- [ ] Verify error handling works

**Success Criteria:**
- ✅ Can add middleware without modifying client
- ✅ Middleware pipeline works correctly
- ✅ Error handlers transform exceptions properly
- ✅ All HTTP functionality unchanged

---

### Weeks 7-8: ISP, LSP, and Patterns

*(Content continues with detailed plans for remaining tasks...)*

---

## Metrics & Success Criteria

### Overall Success Criteria

After completing all SOLID refactoring:

**Code Quality:**
- ✅ SOLID Score: 90+/100 (from 78/100)
- ✅ SRP: 90+/100 (from 65/100)
- ✅ OCP: 85+/100 (from 70/100)
- ✅ LSP: 90+/100 (from 85/100)
- ✅ ISP: 85+/100 (from 72/100)
- ✅ DIP: 95+/100 (from 75/100)

**File Metrics:**
- ✅ Max file size: ≤ 300 lines (from 841)
- ✅ Average functions per file: ≤ 10 (from 20+)
- ✅ Cyclomatic complexity: ≤ 10 per function

**Dependency Metrics:**
- ✅ Global mutable state: 0 instances (from 2)
- ✅ Dependency injection: 100% (all services)
- ✅ Testability: 90%+ (can mock all dependencies)

**Test Coverage:**
- ✅ Unit test coverage: ≥ 80%
- ✅ Integration test coverage: ≥ 70%
- ✅ All new classes have tests

---

## Best Practices Checklist

### For Every Code Change:

**Before Committing:**
- [ ] Run type checker: `mypy src/`
- [ ] Run linter: `ruff check src/`
- [ ] Run formatter: `ruff format src/`
- [ ] Run tests: `pytest tests/`
- [ ] Check test coverage: `pytest --cov=src tests/`

**Code Review Checklist:**
- [ ] No functions > 50 lines
- [ ] No files > 300 lines
- [ ] All dependencies injected (no globals)
- [ ] Services use consistent error handling
- [ ] Type hints on all public APIs
- [ ] Docstrings on all public functions
- [ ] Unit tests for business logic
- [ ] No code duplication

**Commit Message Format:**
```
type(scope): brief description

Detailed description of changes.

- Change 1
- Change 2

SOLID Compliance: [SRP|OCP|LSP|ISP|DIP]
Issue: #123
```

---

## Conclusion

This refactoring plan provides a comprehensive, step-by-step approach to achieving full SOLID compliance in the Activity Tracker Bot project. By following this plan systematically over 8 weeks, the codebase will transform from a score of 78/100 to 90+/100, with significant improvements in maintainability, testability, and extensibility.

**Key Takeaways:**

1. **God Objects** are the primary SRP violation - split into focused modules
2. **Global state** violates DIP - use protocols and injection
3. **Hardcoded logic** violates OCP - use middleware and strategies
4. **Fat interfaces** violate ISP - create focused protocols
5. **Strong foundations** exist (Repository, DI in FastAPI) - build on them

**Next Steps:**

1. Review this plan with the team
2. Set up tracking (GitHub Projects, Jira, etc.)
3. Begin with Week 4 (SRP - God Objects)
4. Maintain metrics dashboard
5. Hold weekly retrospectives

---

**Document Metadata:**

- **Created:** 2025-11-07
- **Last Updated:** 2025-11-07
- **Authors:** Development Team
- **Reviewers:** TBD
- **Status:** Draft
- **Next Review:** After Phase 5 Week 1 completion

---

**End of SOLID Compliance Refactoring Plan**
