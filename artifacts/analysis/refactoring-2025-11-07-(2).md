# Refactoring Plan: DRY, KISS, YAGNI Principles
**Date**: 2025-11-07
**Status**: Planning
**Priority**: High

---

## Executive Summary

Analysis identified **31 violations** across DRY, KISS, and YAGNI principles:
- **DRY Violations**: 12 (4 Critical, 2 High, 6 Medium)
- **KISS Violations**: 8 (3 High, 4 Medium, 1 Low)
- **YAGNI Violations**: 11 (3 High, 5 Medium, 3 Low)

**Estimated Impact**:
- Reduce code duplication by ~40%
- Improve maintainability score
- Decrease cyclomatic complexity
- Remove ~500-800 lines of redundant code

---

## Phase 1: Critical DRY Violations (Priority: CRITICAL)

### Task 1.1: Implement Dependency Injection Pattern
**Issue**: Service instantiation repeated 45+ times across all handlers
**Files Affected**:
- `services/tracker_activity_bot/src/api/handlers/activity.py`
- `services/tracker_activity_bot/src/api/handlers/poll.py`
- `services/tracker_activity_bot/src/api/handlers/categories.py`
- `services/tracker_activity_bot/src/api/handlers/settings.py`

**Current Pattern** (repeated everywhere):
```python
user_service = UserService(api_client)
category_service = CategoryService(api_client)
activity_service = ActivityService(api_client)
settings_service = UserSettingsService(api_client)
```

**Solution**:
```python
# Create: src/api/dependencies.py
from typing import Annotated
from aiogram import types
from .services.api_client import APIClient

class ServiceContainer:
    def __init__(self, api_client: APIClient):
        self._user_service = None
        self._category_service = None
        self._activity_service = None
        self._settings_service = None
        self.api_client = api_client

    @property
    def user(self) -> UserService:
        if not self._user_service:
            self._user_service = UserService(self.api_client)
        return self._user_service

    # ... repeat for other services

# Usage in handlers:
async def handler(callback: types.CallbackQuery, services: ServiceContainer):
    user = await services.user.get_by_telegram_id(callback.from_user.id)
```

**Steps**:
- [ ] Create `src/api/dependencies.py` with `ServiceContainer` class
- [ ] Add lazy initialization for all services
- [ ] Update main.py to inject `ServiceContainer` into router context
- [ ] Refactor activity.py handlers to use container (10 handlers)
- [ ] Refactor poll.py handlers to use container (8 handlers)
- [ ] Refactor categories.py handlers to use container (7 handlers)
- [ ] Refactor settings.py handlers to use container (11 handlers)
- [ ] Remove local service instantiations
- [ ] Test all handlers

**Expected Outcome**: Remove ~90 lines of duplicated service creation

---

### Task 1.2: Consolidate Duration Formatting
**Issue**: Duration formatting logic duplicated in 6+ locations
**Files Affected**:
- `services/tracker_activity_bot/src/api/handlers/settings.py` (lines 64-86, 77-86, 314-321, 455-462)
- `services/tracker_activity_bot/src/api/keyboards/settings.py` (lines 31-33, 52-54)
- `services/tracker_activity_bot/src/application/utils/formatters.py` (lines 6-24)

**Current Duplication**:
```python
# Pattern repeated in 6 places with slight variations:
if minutes < 60:
    result = f"{minutes}м"
else:
    hours = minutes // 60
    remaining = minutes % 60
    if remaining == 0:
        result = f"{hours}ч"
    else:
        result = f"{hours}ч {remaining}м"
```

**Solution**: Use existing `format_duration()` from formatters.py everywhere

**Steps**:
- [ ] Review `formatters.py::format_duration()` function
- [ ] Add unit tests for edge cases (0, 30, 60, 90, 1440 minutes)
- [ ] Replace duration formatting in `settings.py` line 64-86
- [ ] Replace duration formatting in `settings.py` line 314-321
- [ ] Replace duration formatting in `settings.py` line 455-462
- [ ] Replace duration formatting in `keyboards/settings.py` line 31-33
- [ ] Replace duration formatting in `keyboards/settings.py` line 52-54
- [ ] Run integration tests
- [ ] Verify UI displays correctly

**Expected Outcome**: Remove ~50 lines, single source of truth for formatting

---

### Task 1.3: Create User Retrieval Decorator
**Issue**: User retrieval pattern repeated 40+ times
**Files Affected**: All handler files

**Current Pattern**:
```python
user_service = UserService(api_client)
telegram_id = callback.from_user.id
user = await user_service.get_by_telegram_id(telegram_id)
if not user:
    await callback.message.answer("⚠️ Пользователь не найден.")
    await callback.answer()
    return
```

**Solution**:
```python
# Create: src/api/decorators.py
from functools import wraps
from typing import Callable

def require_user(handler: Callable):
    @wraps(handler)
    async def wrapper(
        callback: types.CallbackQuery,
        services: ServiceContainer,
        **kwargs
    ):
        user = await services.user.get_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.message.answer("⚠️ Пользователь не найден.")
            await callback.answer()
            return
        return await handler(callback, services, user=user, **kwargs)
    return wrapper

# Usage:
@router.callback_query(F.data == "some_action")
@require_user
async def handler(callback: types.CallbackQuery, services: ServiceContainer, user: User):
    # user is already retrieved and validated
    pass
```

**Steps**:
- [ ] Create `src/api/decorators.py` with `require_user` decorator
- [ ] Add support for both `CallbackQuery` and `Message` events
- [ ] Add unit tests for decorator
- [ ] Apply decorator to activity.py handlers (12 handlers)
- [ ] Apply decorator to poll.py handlers (9 handlers)
- [ ] Apply decorator to categories.py handlers (8 handlers)
- [ ] Apply decorator to settings.py handlers (13 handlers)
- [ ] Remove manual user retrieval code
- [ ] Test all decorated handlers

**Expected Outcome**: Remove ~160 lines of repeated user retrieval logic

---

### Task 1.4: Simplify FSM Timeout Management
**Issue**: FSM timeout scheduling/canceling repeated 37+ times
**Files Affected**: All handler files

**Current Pattern**:
```python
if fsm_timeout_module.fsm_timeout_service:
    fsm_timeout_module.fsm_timeout_service.schedule_timeout(
        user_id=callback.from_user.id,
        state=SomeStates.some_state,
        bot=callback.bot
    )

# Later...
if fsm_timeout_module.fsm_timeout_service:
    fsm_timeout_module.fsm_timeout_service.cancel_timeout(user_id)
```

**Solution Option A** (Simple): Helper functions
```python
# src/api/utils/fsm_helpers.py
async def schedule_fsm_timeout(user_id: int, state: str, bot):
    if fsm_timeout_module.fsm_timeout_service:
        fsm_timeout_module.fsm_timeout_service.schedule_timeout(user_id, state, bot)

async def cancel_fsm_timeout(user_id: int):
    if fsm_timeout_module.fsm_timeout_service:
        fsm_timeout_module.fsm_timeout_service.cancel_timeout(user_id)
```

**Solution Option B** (Better): State transition decorator
```python
@auto_timeout(NewCategoryStates.waiting_name)
async def handler(callback: types.CallbackQuery, state: FSMContext):
    # Timeout automatically scheduled on state entry
    # Automatically cancelled on state exit
    pass
```

**Steps**:
- [ ] Choose solution approach (A or B)
- [ ] Implement helper functions or decorator
- [ ] Add unit tests
- [ ] Refactor activity.py (17 schedule/cancel calls)
- [ ] Refactor categories.py (8 calls)
- [ ] Refactor settings.py (10 calls)
- [ ] Refactor poll.py (4 calls)
- [ ] Test FSM timeout behavior
- [ ] Verify cleanup works correctly

**Expected Outcome**: Remove ~74 lines, centralize timeout logic

---

## Phase 2: High Priority DRY & KISS Violations

### Task 2.1: Create Base Repository Class
**Issue**: Common CRUD methods duplicated across all repositories
**Files Affected**:
- `services/data_postgres_api/src/infrastructure/repositories/user_repository.py`
- `services/data_postgres_api/src/infrastructure/repositories/category_repository.py`
- `services/data_postgres_api/src/infrastructure/repositories/activity_repository.py`
- `services/data_postgres_api/src/infrastructure/repositories/user_settings_repository.py`

**Solution**:
```python
# Create: src/infrastructure/repositories/base.py
from typing import TypeVar, Generic, Type
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

T = TypeVar('T')

class BaseRepository(Generic[T]):
    def __init__(self, session: AsyncSession, model: Type[T]):
        self.session = session
        self.model = model

    async def get_by_id(self, id: int) -> T | None:
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def create(self, data: dict) -> T:
        instance = self.model(**data)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def delete(self, id: int) -> bool:
        instance = await self.get_by_id(id)
        if instance:
            await self.session.delete(instance)
            await self.session.flush()
            return True
        return False

# Usage:
class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, User)

    # Only custom methods here
    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        ...
```

**Steps**:
- [ ] Create `base.py` with `BaseRepository[T]` class
- [ ] Implement common CRUD: `get_by_id`, `create`, `delete`
- [ ] Add unit tests for base repository
- [ ] Refactor UserRepository to inherit from BaseRepository
- [ ] Refactor CategoryRepository to inherit from BaseRepository
- [ ] Refactor ActivityRepository to inherit from BaseRepository
- [ ] Refactor UserSettingsRepository to inherit from BaseRepository
- [ ] Remove duplicated methods
- [ ] Test all repository operations

**Expected Outcome**: Remove ~80 lines of duplicated CRUD code

---

### Task 2.2: Consolidate Error Handling in API Routes
**Issue**: Try-except-ValueError-HTTPException pattern repeated in every endpoint
**Files Affected**: `services/data_postgres_api/src/api/routes/*.py`

**Solution**:
```python
# Create: src/api/middleware/error_handler.py
from functools import wraps
from fastapi import HTTPException, status

def handle_service_errors(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            # Log unexpected errors
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )
    return wrapper

# Usage:
@router.post("/activities/", response_model=ActivityResponse)
@handle_service_errors
async def create_activity(data: ActivityCreate, service: ActivityService = Depends()):
    result = await service.create(data.model_dump())
    return ActivityResponse.model_validate(result)
```

**Steps**:
- [ ] Create error handling decorator
- [ ] Add logging for errors
- [ ] Apply to activities.py routes (4 routes)
- [ ] Apply to categories.py routes (4 routes)
- [ ] Apply to users.py routes (3 routes)
- [ ] Apply to user_settings.py routes (3 routes)
- [ ] Remove local try-except blocks
- [ ] Test error responses

**Expected Outcome**: Remove ~60 lines, centralized error handling

---

### Task 2.3: Consolidate Keyboard Building Logic
**Issue**: Duplicate keyboard creation in settings.py
**Location**: `services/tracker_activity_bot/src/api/keyboards/settings.py`

**Solution**:
```python
def build_interval_keyboard(
    intervals: list[int],
    current: int,
    callback_prefix: str
) -> InlineKeyboardMarkup:
    """
    Build interval selection keyboard.

    Args:
        intervals: List of interval values in minutes
        current: Currently selected interval
        callback_prefix: Prefix for callback data (e.g., "set_weekday")

    Returns:
        InlineKeyboardMarkup with interval buttons
    """
    buttons = []
    for interval in intervals:
        label = format_duration(interval)  # Use existing formatter!
        if interval == current:
            label = f"✓ {label}"
        buttons.append([
            InlineKeyboardButton(
                text=label,
                callback_data=f"{callback_prefix}_{interval}"
            )
        ])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="settings")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Usage:
def get_weekday_interval_keyboard(current: int) -> InlineKeyboardMarkup:
    return build_interval_keyboard(WEEKDAY_INTERVALS, current, "set_weekday")

def get_weekend_interval_keyboard(current: int) -> InlineKeyboardMarkup:
    return build_interval_keyboard(WEEKEND_INTERVALS, current, "set_weekend")
```

**Steps**:
- [ ] Create `build_interval_keyboard()` helper function
- [ ] Refactor `get_weekday_interval_keyboard()` to use helper
- [ ] Refactor `get_weekend_interval_keyboard()` to use helper
- [ ] Test both keyboards display correctly
- [ ] Test callback data is correct

**Expected Outcome**: Remove ~30 lines of duplicated keyboard logic

---

### Task 2.4: Extract State Clearing Helper
**Issue**: State clear + timeout cancel pattern repeated 20+ times
**Files Affected**: All handler files

**Solution**:
```python
# Add to: src/api/utils/fsm_helpers.py
async def clear_state_and_timeout(state: FSMContext, user_id: int):
    """
    Clear FSM state and cancel associated timeout.

    Args:
        state: FSM context to clear
        user_id: User ID for timeout cancellation
    """
    await state.clear()
    if fsm_timeout_module.fsm_timeout_service:
        fsm_timeout_module.fsm_timeout_service.cancel_timeout(user_id)

# Usage in handlers:
await clear_state_and_timeout(state, callback.from_user.id)
```

**Steps**:
- [ ] Create helper function
- [ ] Add to existing `fsm_helpers.py` module
- [ ] Replace in activity.py (7 occurrences)
- [ ] Replace in categories.py (5 occurrences)
- [ ] Replace in settings.py (6 occurrences)
- [ ] Replace in poll.py (3 occurrences)
- [ ] Test state clearing works

**Expected Outcome**: Remove ~40 lines, single cleanup function

---

### Task 2.5: Simplify FSM Timeout System (KISS)
**Issue**: Over-engineered timeout system with multiple tracking dictionaries
**Files Affected**:
- `services/tracker_activity_bot/src/application/services/fsm_timeout_service.py`
- All handlers using timeout system

**Analysis**: Current system has:
- Separate APScheduler jobs
- Cleanup timers
- Multiple job tracking dictionaries
- Conditional checks everywhere

**Proposed Solution**: Use Redis TTL for state expiration
```python
# Instead of manual timeout management, use Redis storage with TTL:
# In main.py
storage = RedisStorage(
    redis=redis,
    state_ttl=300,  # 5 minutes - states auto-expire
    data_ttl=300
)

# No manual timeout management needed!
# States automatically expire after 5 minutes of inactivity
```

**Alternative Solution**: If must keep manual timeouts, simplify:
```python
# Single timeout task per user, stored in Redis
# No separate scheduler, use asyncio.create_task
class SimpleFSMTimeout:
    def __init__(self, bot):
        self.bot = bot
        self.timeouts: dict[int, asyncio.Task] = {}

    def schedule(self, user_id: int, minutes: int):
        self.cancel(user_id)  # Cancel existing
        self.timeouts[user_id] = asyncio.create_task(
            self._timeout_task(user_id, minutes)
        )

    def cancel(self, user_id: int):
        if user_id in self.timeouts:
            self.timeouts[user_id].cancel()
            del self.timeouts[user_id]

    async def _timeout_task(self, user_id: int, minutes: int):
        await asyncio.sleep(minutes * 60)
        # Clear state and notify user
```

**Steps**:
- [ ] **Decision**: Choose Redis TTL or simplified manual timeout
- [ ] **If Redis TTL**:
  - [ ] Configure Redis storage with state_ttl
  - [ ] Remove fsm_timeout_service.py completely
  - [ ] Remove all schedule/cancel calls from handlers
  - [ ] Test state expiration works
- [ ] **If Simplified Manual**:
  - [ ] Implement SimpleFSMTimeout class
  - [ ] Replace existing timeout service
  - [ ] Update all handler calls
  - [ ] Test timeout behavior
- [ ] Remove cleanup tasks and job tracking
- [ ] Update documentation

**Expected Outcome**: Remove 100-200 lines of timeout management code

---

## Phase 3: High Priority YAGNI Violations

### Task 3.1: Remove or Simplify last_poll_time Infrastructure
**Issue**: Over-engineered for minimal usage
**Files Affected**:
- `services/data_postgres_api/src/domain/models/user.py` (field)
- `services/data_postgres_api/src/infrastructure/repositories/user_repository.py` (method)
- `services/data_postgres_api/src/application/services/user_service.py` (method)
- `services/data_postgres_api/src/api/routes/users.py` (dedicated endpoint)
- `services/tracker_activity_bot/src/api/handlers/poll.py` (usage)

**Analysis**:
- Used only once for sleep duration calculation
- Has dedicated API endpoint
- Most poll logic uses settings intervals

**Decision Required**: Keep or remove?

**Option A: Remove Completely**
```python
# Use settings-based intervals only, no tracking
# Calculate next poll based on current time + interval
```

**Option B: Simplify to In-Memory**
```python
# Store in Redis with TTL, no database persistence
# Sufficient for sleep calculation
```

**Steps**:
- [ ] **Decision**: Keep or remove last_poll_time
- [ ] **If Remove**:
  - [ ] Remove field from User model
  - [ ] Create migration to drop column
  - [ ] Remove update_last_poll_time from repository
  - [ ] Remove update_last_poll_time from service
  - [ ] Remove API endpoint
  - [ ] Refactor poll.py sleep calculation
  - [ ] Test poll scheduling works
- [ ] **If Simplify**:
  - [ ] Implement Redis-based tracking
  - [ ] Remove database field and migration
  - [ ] Remove API endpoint
  - [ ] Keep service method, change to Redis
  - [ ] Test poll tracking

**Expected Outcome**: Remove 50-100 lines of infrastructure code

---

### Task 3.2: Remove Statistics Placeholder
**Issue**: Complete handler showing only "under development" message
**Location**: `services/tracker_activity_bot/src/api/handlers/activity.py` (lines 628-643)

**Steps**:
- [ ] Remove statistics handler function
- [ ] Remove statistics callback query route
- [ ] Remove "📊 Статистика" button from main menu
- [ ] Test main menu displays correctly
- [ ] Update TODO/roadmap to track feature for future

**Expected Outcome**: Remove 15 lines, cleaner main menu

---

### Task 3.3: Simplify Activity Pagination
**Issue**: Full pagination infrastructure for hardcoded limit
**Files Affected**:
- `services/data_postgres_api/src/infrastructure/repositories/activity_repository.py`
- `services/data_postgres_api/src/application/services/activity_service.py`

**Current**:
```python
# Complex pagination with limit/offset validation
async def get_by_user_id(
    self,
    user_id: int,
    limit: int = 10,
    offset: int = 0
) -> tuple[list[Activity], int]:
    # Validation, count query, offset/limit logic
    ...
```

**Simplified**:
```python
# Just get last N activities
async def get_recent_by_user_id(
    self,
    user_id: int,
    limit: int = 10
) -> list[Activity]:
    result = await self.session.execute(
        select(Activity)
        .where(Activity.user_id == user_id)
        .order_by(Activity.start_time.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
```

**Steps**:
- [ ] Replace `get_by_user_id` with `get_recent_by_user_id`
- [ ] Remove offset parameter
- [ ] Remove total count calculation
- [ ] Remove validation logic
- [ ] Update service layer method
- [ ] Update API route
- [ ] Update bot handler calls
- [ ] Test activity list displays correctly

**Expected Outcome**: Remove ~40 lines of pagination complexity

---

### Task 3.4: Remove Bulk Category Creation
**Issue**: Complex bulk creation not used
**Files Affected**:
- `services/data_postgres_api/src/application/services/category_service.py` (lines 56-83)
- `services/data_postgres_api/src/api/routes/categories.py` (bulk endpoint)

**Steps**:
- [ ] Remove `create_bulk()` method from CategoryService
- [ ] Remove bulk creation API endpoint
- [ ] Remove related Pydantic schemas if any
- [ ] Test single category creation still works
- [ ] Update API documentation

**Expected Outcome**: Remove ~50 lines of unused code

---

### Task 3.5: Remove Unused Repository Methods
**Issue**: Multiple unused methods across repositories
**Files Affected**: All repository files

**Methods to Remove**:
- `UserSettingsRepository.get_by_id()` - settings retrieved by user_id only
- `UserSettingsRepository.delete()` - settings never deleted
- `UserRepository.update()` generic method - only used for one field

**Steps**:
- [ ] Remove `UserSettingsRepository.get_by_id()`
- [ ] Remove `UserSettingsRepository.delete()`
- [ ] Analyze `UserRepository.update()` usage
- [ ] Either remove or keep only specific field updates
- [ ] Test affected services still work
- [ ] Update service layer to use specific methods

**Expected Outcome**: Remove ~40 lines of unused code

---

## Phase 4: Medium Priority Violations

### Task 4.1: Simplify Quiet Hours Validation
**Issue**: Over-complex time validation with regex
**Location**: `services/data_postgres_api/src/application/services/user_settings_service.py`

**Current** (lines 147-177):
```python
# 30 lines of regex parsing and manual validation
time_pattern = re.compile(r'^([0-1]?[0-9]|2[0-3]):([0-5][0-9])$')
# Manual hour/minute validation...
```

**Simplified**:
```python
# Rely on Pydantic and database validation
# Remove custom validation entirely
```

**Steps**:
- [ ] Verify Pydantic schema validates time format
- [ ] Verify database time field validates correctly
- [ ] Remove regex pattern and manual validation
- [ ] Test invalid time inputs are rejected
- [ ] Test valid times are accepted

**Expected Outcome**: Remove ~30 lines, rely on schema validation

---

### Task 4.2: Simplify Emoji Keyboard
**Issue**: 94 lines of hardcoded emojis
**Location**: `services/tracker_activity_bot/src/api/handlers/categories.py` (lines 140-233)

**Current**: 60+ emojis manually categorized in code

**Proposed**:
```python
# Move to config file: config/category_emojis.json
COMMON_EMOJIS = [
    "💼", "🏃", "🍽️", "😴", "📚", "🎮", "💻", "🏋️",
    "🎵", "🎨", "🚗", "✈️", "🏠", "👨‍👩‍👧‍👦", "🛒"
]

# Allow text input as primary method
# Show only 15-20 most common emojis
```

**Steps**:
- [ ] Create `config/category_emojis.json` with top 15-20 emojis
- [ ] Load emojis from config
- [ ] Simplify keyboard generation
- [ ] Emphasize text input option
- [ ] Test emoji selection works
- [ ] Test custom emoji input works

**Expected Outcome**: Remove ~70 lines, move config to file

---

### Task 4.3: Extract Poll Time Calculation Helper
**Issue**: Time calculation logic duplicated
**Location**: `poll.py` and `activity.py`

**Solution**:
```python
# Create: src/application/utils/time_helpers.py
def calculate_poll_start_time(
    end_time: datetime,
    settings: dict
) -> datetime:
    """
    Calculate poll start time based on end time and user settings.

    Args:
        end_time: End time of the period
        settings: User settings with poll intervals

    Returns:
        Calculated start time
    """
    is_weekend = end_time.weekday() >= 5
    interval_minutes = (
        settings["poll_interval_weekend"]
        if is_weekend
        else settings["poll_interval_weekday"]
    )
    return end_time - timedelta(minutes=interval_minutes)
```

**Steps**:
- [ ] Create helper function
- [ ] Add unit tests for weekday/weekend logic
- [ ] Replace in poll.py (lines 286-299, 509-520)
- [ ] Replace in activity.py (lines 254, 322, 544)
- [ ] Test poll time calculations are correct

**Expected Outcome**: Remove ~30 lines, centralized logic

---

### Task 4.4: Standardize UserSettingsRepository
**Issue**: Inconsistent signature compared to other repositories
**Location**: `services/data_postgres_api/src/infrastructure/repositories/user_settings_repository.py`

**Current Issues**:
- Takes UserSettings object instead of schema
- Uses commit() instead of flush() pattern
- Different from other repositories

**Solution**: Align with BaseRepository pattern (from Task 2.1)

**Steps**:
- [ ] Wait for Task 2.1 completion
- [ ] Refactor to inherit from BaseRepository
- [ ] Change to accept dict/schema instead of model object
- [ ] Change commit() to flush() for consistency
- [ ] Update service layer calls
- [ ] Test settings CRUD operations

**Expected Outcome**: Consistent repository pattern

---

### Task 4.5: Simplify Settings Display Logic
**Issue**: 76 lines of complex logic for next poll time display
**Location**: `services/tracker_activity_bot/src/api/handlers/settings.py` (lines 94-170)

**Analysis**:
- Multiple try-except blocks
- Nested conditionals
- Duplicate formatting
- Fallback scheduling mixed with display

**Solution**:
```python
# Pre-calculate next poll in scheduler service
# Simple lookup for display
next_poll = await poll_scheduler.get_next_poll_time(user.id)
if next_poll:
    next_poll_str = next_poll.strftime("%H:%M")
else:
    next_poll_str = "не запланирован"
```

**Steps**:
- [ ] Add `get_next_poll_time()` to scheduler service
- [ ] Simplify display logic to single lookup
- [ ] Remove try-except complexity
- [ ] Remove fallback scheduling from display
- [ ] Test settings display shows correct time
- [ ] Test when no poll scheduled

**Expected Outcome**: Reduce from 76 to ~10 lines

---

### Task 4.6: Simplify Dependency Chain for Simple Operations
**Issue**: 4-layer dependency chain for CRUD
**Location**: `services/data_postgres_api/src/api/dependencies.py`

**Current**: get_db → get_repository → get_service → endpoint

**Analysis**: Service layer should have business logic, not just pass-through

**Review Required**:
- Which services have actual business logic?
- Which services are just CRUD wrappers?

**Steps**:
- [ ] Audit each service for business logic
- [ ] Keep service layer where business logic exists
- [ ] Consider direct repository access for pure CRUD
- [ ] Update dependency injection
- [ ] Update API routes
- [ ] Test all endpoints

**Expected Outcome**: Simplified dependency chain where appropriate

---

## Phase 5: Low Priority & Cleanup

### Task 5.1: Optimize Documentation
**Issue**: Excessive docstrings repeating obvious code
**Files Affected**: All service files

**Steps**:
- [ ] Review all docstrings in services/
- [ ] Remove docstrings that just repeat method signature
- [ ] Keep docstrings for complex business logic
- [ ] Keep docstrings for public APIs
- [ ] Update documentation guidelines

**Expected Outcome**: Cleaner code, less maintenance

---

### Task 5.2: Tags Feature - Complete or Remove
**Issue**: Tags infrastructure built but not fully utilized
**Location**: Activity model, extract tags function

**Decision Required**: Complete feature or simplify to description-only?

**If Complete**:
- [ ] Add tag filtering to activity queries
- [ ] Add tag display in activity list UI
- [ ] Add tag search in bot commands
- [ ] Add tag autocomplete

**If Remove**:
- [ ] Remove tags field from Activity model
- [ ] Remove extract_tags() function
- [ ] Migration to drop tags column
- [ ] Simplify to description-only

**Expected Outcome**: Either complete feature or remove unused code

---

### Task 5.3: Remove Unused FSM Storage in Poll Handler
**Issue**: Separate FSM storage instance just for state checking
**Location**: `services/tracker_activity_bot/src/api/handlers/poll.py` (lines 36-67)

**Steps**:
- [ ] Analyze if storage check is necessary
- [ ] Use main dispatcher's storage instead
- [ ] Remove global variable
- [ ] Remove cleanup function
- [ ] Simplify state checking
- [ ] Test poll functionality

**Expected Outcome**: Remove ~30 lines, simpler state management

---

## Testing Strategy

### Unit Tests Required
- [ ] ServiceContainer lazy initialization
- [ ] User retrieval decorator edge cases
- [ ] FSM timeout helpers
- [ ] Duration formatting edge cases
- [ ] Keyboard building helper
- [ ] State clearing helper
- [ ] Base repository CRUD operations
- [ ] Error handling decorator
- [ ] Time calculation helper

### Integration Tests Required
- [ ] All refactored handlers work correctly
- [ ] Service injection flows through properly
- [ ] FSM state transitions with timeouts
- [ ] User authentication flow
- [ ] Settings display and updates
- [ ] Category CRUD operations
- [ ] Activity tracking flow
- [ ] Poll scheduling

### Regression Tests
- [ ] All existing tests still pass
- [ ] UI displays correctly in Russian
- [ ] All keyboards render properly
- [ ] Error messages display correctly
- [ ] Poll scheduling works as before
- [ ] Activity logging unchanged
- [ ] Settings updates persist

---

## Rollout Plan

### Phase 1: Critical DRY (Week 1)
- Tasks 1.1-1.4 (Dependency injection, formatters, decorators, FSM)
- High impact, foundational changes
- **Risk**: Medium - touches many files
- **Testing**: Extensive integration tests required

### Phase 2: High Priority DRY & KISS (Week 2)
- Tasks 2.1-2.5 (Base repository, error handling, keyboards, helpers)
- Builds on Phase 1
- **Risk**: Low-Medium
- **Testing**: Unit tests + integration tests

### Phase 3: YAGNI Cleanup (Week 3)
- Tasks 3.1-3.5 (Remove unused code, simplify pagination)
- Simplifies codebase
- **Risk**: Low - mostly removal
- **Testing**: Regression tests to ensure nothing breaks

### Phase 4: Medium Priority (Week 4)
- Tasks 4.1-4.6 (Validation, emojis, time helpers, standardization)
- Polish and optimization
- **Risk**: Low
- **Testing**: Targeted unit tests

### Phase 5: Low Priority (Ongoing)
- Tasks 5.1-5.3 (Documentation, tags, cleanup)
- Can be done incrementally
- **Risk**: Very low

---

## Success Metrics

### Code Quality
- [ ] Cyclomatic complexity reduced by 30%
- [ ] Code duplication reduced by 40%
- [ ] Lines of code reduced by 500-800
- [ ] Test coverage maintained at 80%+

### Maintainability
- [ ] New handler can be added in <20 lines
- [ ] Service changes don't require handler updates
- [ ] Single source of truth for formatting/validation
- [ ] Consistent patterns across all handlers

### Performance
- [ ] No performance degradation
- [ ] Response times maintained
- [ ] Memory usage not increased

---

## Risk Assessment

### High Risk Tasks
1. **Task 1.1** (Dependency Injection) - Touches all handlers
   - Mitigation: Incremental rollout, one handler file at a time
   - Rollback: Keep old service creation pattern in git history

2. **Task 2.5** (FSM Timeout Simplification) - Core functionality
   - Mitigation: Feature flag to switch between old/new system
   - Rollback: Can revert to old timeout service

### Medium Risk Tasks
1. **Task 1.3** (User Decorator) - Authentication flow
   - Mitigation: Extensive testing of error cases
   - Rollback: Decorator is optional, can remove

2. **Task 3.1** (last_poll_time) - Poll scheduling
   - Mitigation: Test poll timing extensively
   - Rollback: Database migration can be reverted

### Low Risk Tasks
- All removal tasks (statistics, bulk creation, etc.)
- Helper function extractions
- Documentation cleanup

---

## Notes

### Best Practices Applied
✅ Single Responsibility Principle
✅ DRY - Don't Repeat Yourself
✅ KISS - Keep It Simple, Stupid
✅ YAGNI - You Aren't Gonna Need It
✅ Dependency Injection
✅ Consistent Error Handling
✅ Decorator Pattern for Cross-Cutting Concerns

### Documentation Standards
- All documentation in English ✅
- All user-facing text in Russian ✅
- Doc-strings for public APIs and complex logic only
- Inline comments for non-obvious code only

### Code Review Checklist
- [ ] No duplicated code
- [ ] Simple, readable solutions
- [ ] No premature optimization
- [ ] No unused code
- [ ] Consistent patterns
- [ ] Proper error handling
- [ ] Unit tests included
- [ ] Integration tests pass

---

**End of Refactoring Plan**
