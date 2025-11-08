# Anti-Patterns

**Purpose**: Common mistakes to AVOID in Activity Tracker Bot.

**For AI**: These are patterns that were tried, failed, and fixed. NEVER repeat these mistakes.

## Table of Contents

1. [Direct Database Access from Bot](#direct-database-access-from-bot)
2. [Duplicate CRUD Code](#duplicate-crud-code)
3. [Business Logic in Routes](#business-logic-in-routes)
4. [Missing FSM State Cleanup](#missing-fsm-state-cleanup)
5. [Unhandled Exceptions](#unhandled-exceptions)
6. [Missing Callback Answers](#missing-callback-answers)
7. [Hardcoded Values](#hardcoded-values)
8. [Missing Type Hints](#missing-type-hints)
9. [Silent Errors](#silent-errors)
10. [Code Without Tests](#code-without-tests)

---

## Direct Database Access from Bot

### ❌ WRONG

```python
# In bot service
from sqlalchemy import select
from src.domain.models.user import User

async def handler(message: Message):
    # NEVER DO THIS!
    async with AsyncSession() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()
```

### ✅ CORRECT

```python
# In bot service
async def handler(message: Message, services: ServiceContainer):
    # ALWAYS use HTTP API
    user = await services.user.get_by_telegram_id(message.from_user.id)
```

**Why Wrong**:
- Violates microservices architecture
- Tight coupling between services
- Can't scale independently
- Bypasses business logic in service layer

**How to Fix**: Always use HTTP client to call Data API

**Files to Check**: Any handler file in `tracker_activity_bot/src/api/handlers/`

---

## Duplicate CRUD Code

### ❌ WRONG

```python
# In each repository
class UserRepository:
    async def get_by_id(self, id: int) -> User | None:
        result = await self.session.execute(
            select(User).where(User.id == id)
        )
        return result.scalar_one_or_none()

    async def create(self, data: UserCreate) -> User:
        user = User(**data.model_dump())
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    # ... 20 more lines of duplicate CRUD


class CategoryRepository:
    # EXACT SAME CODE repeated again!
    async def get_by_id(self, id: int) -> Category | None:
        result = await self.session.execute(
            select(Category).where(Category.id == id)
        )
        return result.scalar_one_or_none()

    async def create(self, data: CategoryCreate) -> Category:
        category = Category(**data.model_dump())
        self.session.add(category)
        await self.session.commit()
        await self.session.refresh(category)
        return category

    # ... 20 more lines of duplicate CRUD
```

### ✅ CORRECT

```python
# Use Generic Repository
from src.infrastructure.repositories.base import BaseRepository

class UserRepository(BaseRepository[User, UserCreate, UserUpdate]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, User)

    # Only add custom methods
    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()


class CategoryRepository(BaseRepository[Category, CategoryCreate, CategoryUpdate]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Category)

    # Only add custom methods
    async def get_by_user_id(self, user_id: int) -> list[Category]:
        result = await self.session.execute(
            select(Category).where(Category.user_id == user_id)
        )
        return list(result.scalars().all())
```

**Why Wrong**:
- Violates DRY principle
- More code to maintain
- Bugs must be fixed in multiple places
- ~100 lines of unnecessary code

**How to Fix**: Use Generic Repository Pattern

**Reference**: `services/data_postgres_api/src/infrastructure/repositories/base.py`

---

## Business Logic in Routes

### ❌ WRONG

```python
# In API route
@router.post("/categories")
async def create_category(
    data: CategoryCreate,
    session: AsyncSession = Depends(get_session)
):
    # Business logic in route - WRONG!
    existing = await session.execute(
        select(Category).where(
            Category.user_id == data.user_id,
            Category.name == data.name
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Category already exists")

    category = Category(**data.model_dump())
    session.add(category)
    await session.commit()
    await session.refresh(category)
    return category
```

### ✅ CORRECT

```python
# In API route - thin controller
@router.post("/categories")
async def create_category(
    data: CategoryCreate,
    service: CategoryService = Depends(get_category_service)
):
    try:
        category = await service.create(data)
        return category
    except ValueError as e:
        raise HTTPException(400, str(e))


# In service - business logic here
class CategoryService:
    async def create(self, data: CategoryCreate) -> Category:
        # Business validation
        existing = await self.repository.get_by_user_and_name(
            data.user_id,
            data.name
        )
        if existing:
            raise ValueError(f"Category '{data.name}' already exists")

        return await self.repository.create(data)
```

**Why Wrong**:
- Routes should be thin controllers
- Business logic can't be reused
- Hard to test
- Violates Single Responsibility Principle

**How to Fix**: Move business logic to Service layer

**Reference**: See `services/data_postgres_api/src/application/services/`

---

## Missing FSM State Cleanup

### ❌ WRONG

```python
@router.message(ActivityStates.waiting_for_category)
async def process_category(message: Message, state: FSMContext):
    data = await state.get_data()

    # Create activity
    await services.activity.create(data)

    # FORGOT to clear state!
    await message.answer("✅ Готово!")
```

**What Happens**:
- User stuck in FSM state forever
- Next message still processed as "waiting_for_category"
- User can't use other commands
- FSM state pollutes Redis

### ✅ CORRECT

```python
@router.message(ActivityStates.waiting_for_category)
async def process_category(message: Message, state: FSMContext):
    data = await state.get_data()

    # Create activity
    await services.activity.create(data)

    # ALWAYS clear state when flow completes!
    await state.clear()

    await message.answer("✅ Готово!")
```

**How to Fix**: ALWAYS call `await state.clear()` when FSM flow completes

**Files to Check**: Any handler using FSM states

---

## Unhandled Exceptions

### ❌ WRONG

```python
@router.callback_query(F.data == "create")
async def handler(callback: CallbackQuery, services: ServiceContainer):
    # No try/except - WRONG!
    user = await services.user.get_by_telegram_id(callback.from_user.id)
    result = await services.your_service.create(user["id"])

    await callback.message.answer(f"Создано: {result}")
    await callback.answer()
```

**What Happens**:
- If API is down → user sees nothing (callback hangs)
- If service raises ValueError → exception propagates to top level
- User has no idea what went wrong
- No error logged

### ✅ CORRECT

```python
@router.callback_query(F.data == "create")
async def handler(callback: CallbackQuery, services: ServiceContainer):
    try:
        user = await services.user.get_by_telegram_id(callback.from_user.id)
        result = await services.your_service.create(user["id"])
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error: {e.response.status_code}")
        await callback.answer("❌ Ошибка сервера. Попробуйте позже.")
        return
    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        await callback.answer(f"❌ {e}")
        return
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка.")
        return

    await callback.message.answer(f"✅ Создано: {result}")
    await callback.answer()
```

**How to Fix**: Wrap service calls in try/except with logging

**Files to Check**: All handlers

---

## Missing Callback Answers

### ❌ WRONG

```python
@router.callback_query(F.data == "action")
async def handler(callback: CallbackQuery):
    await callback.message.answer("Обработано")
    # FORGOT to answer callback!
```

**What Happens**:
- Telegram shows "loading" spinner forever
- Poor user experience
- Telegram may rate-limit your bot

### ✅ CORRECT

```python
@router.callback_query(F.data == "action")
async def handler(callback: CallbackQuery):
    await callback.message.answer("✅ Обработано")

    # ALWAYS answer callback!
    await callback.answer()
```

**How to Fix**: ALWAYS call `await callback.answer()` at the end of callback handlers

**Files to Check**: Any `@router.callback_query` handler

---

## Hardcoded Values

### ❌ WRONG

```python
# Hardcoded values scattered everywhere
async def handler(callback: CallbackQuery):
    # WRONG!
    api_url = "http://localhost:8000"
    timeout = 30
    default_categories = ["Работа", "Учеба", "Спорт"]
```

### ✅ CORRECT

```python
# In config.py
class Settings(BaseSettings):
    data_api_url: str
    http_timeout: int = 30

# In constants.py
DEFAULT_CATEGORIES = [
    {"name": "Работа", "emoji": "💼"},
    {"name": "Учеба", "emoji": "🎯"},
    {"name": "Спорт", "emoji": "🏃"},
]

# In handler
from src.core.config import settings
from src.core.constants import DEFAULT_CATEGORIES

async def handler(callback: CallbackQuery):
    api_url = settings.data_api_url
    categories = DEFAULT_CATEGORIES
```

**Why Wrong**:
- Hard to change
- Hard to test (can't override)
- Different values in different places
- No single source of truth

**How to Fix**: Use `config.py` for settings, `constants.py` for constants

**Reference**: `services/*/src/core/config.py`, `services/*/src/core/constants.py`

---

## Missing Type Hints

### ❌ WRONG

```python
async def get_user(telegram_id):
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()


async def create_activity(data):
    activity = Activity(**data)
    session.add(activity)
    await session.commit()
    return activity
```

**Why Wrong**:
- No IDE autocomplete
- No type checking (mypy can't help)
- Hard to understand what function expects/returns
- Runtime errors instead of compile-time errors

### ✅ CORRECT

```python
from typing import Any

async def get_user(telegram_id: int) -> User | None:
    """
    Get user by Telegram ID.

    Args:
        telegram_id: Telegram user ID

    Returns:
        User or None if not found
    """
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()


async def create_activity(data: dict[str, Any]) -> Activity:
    """
    Create new activity.

    Args:
        data: Activity data

    Returns:
        Created activity
    """
    activity = Activity(**data)
    session.add(activity)
    await session.commit()
    return activity
```

**How to Fix**: Add type hints to ALL function parameters and return values

**Files to Check**: All `.py` files

---

## Silent Errors

### ❌ WRONG (VERY BAD!)

```python
try:
    result = await service.create(data)
except Exception:
    pass  # NEVER DO THIS!!!
```

**Why Wrong**:
- Errors disappear silently
- Impossible to debug
- User has no feedback
- System appears to work but doesn't

### ✅ CORRECT

```python
try:
    result = await service.create(data)
except ValueError as e:
    logger.warning(f"Validation error: {e}")
    await message.answer(f"❌ Ошибка: {e}")
    return
except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
    await message.answer("❌ Произошла ошибка. Попробуйте позже.")
    return
```

**How to Fix**:
- ALWAYS log exceptions
- ALWAYS inform user
- Use specific exception types
- Include context in logs

**Golden Rule**: `except: pass` is FORBIDDEN in this project!

---

## Code Without Tests

### ❌ WRONG

```python
# New service without tests
class NewService:
    async def complex_business_logic(self, data):
        # 50 lines of complex code
        # No tests!
        pass
```

**Why Wrong**:
- Bugs found in production
- Can't refactor safely
- No documentation of expected behavior
- Regressions go unnoticed

### ✅ CORRECT

```python
# Service with tests
class NewService:
    async def complex_business_logic(self, data: DataSchema) -> Result:
        """Complex business logic with clear behavior."""
        # Implementation
        pass


# Test file
@pytest.mark.asyncio
async def test_complex_business_logic_success():
    """Test successful path."""
    # Arrange
    service = NewService()
    data = DataSchema(field="value")

    # Act
    result = await service.complex_business_logic(data)

    # Assert
    assert result.success is True


@pytest.mark.asyncio
async def test_complex_business_logic_validation_error():
    """Test validation error."""
    service = NewService()
    invalid_data = DataSchema(field="")

    with pytest.raises(ValueError):
        await service.complex_business_logic(invalid_data)
```

**How to Fix**: Write tests for all new code (minimum unit tests)

**Reference**: `services/*/tests/unit/`

---

## Summary for AI

### RED FLAGS (STOP immediately if you see these!)

1. ⛔ Bot importing from `src.domain.models` or `sqlalchemy`
2. ⛔ Duplicate `get_by_id`, `create`, `update` methods in repositories
3. ⛔ Business validation in API routes
4. ⛔ FSM handler without `await state.clear()`
5. ⛔ Service call without try/except
6. ⛔ `@router.callback_query` handler without `await callback.answer()`
7. ⛔ Hardcoded URLs, timeouts, or constants
8. ⛔ Function without type hints
9. ⛔ `except: pass` or `except Exception: pass`
10. ⛔ New code without tests

### GREEN FLAGS (Good to see!)

1. ✅ Bot using HTTP clients only
2. ✅ Repositories extending `BaseRepository[T, C, U]`
3. ✅ Business logic in Service layer
4. ✅ `await state.clear()` at end of FSM flows
5. ✅ Try/except with logging in handlers
6. ✅ `await callback.answer()` in all callback handlers
7. ✅ Settings from `config.py`, constants from `constants.py`
8. ✅ Full type hints on all functions
9. ✅ Proper exception handling with user feedback
10. ✅ Tests for new code

**When in doubt**: Look at existing code and copy the pattern!

---

**Last Updated**: 2025-11-08
**Next Update**: When new anti-patterns are discovered and fixed
