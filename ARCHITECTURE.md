# Architecture Documentation

This document describes the architectural patterns and design decisions used in the Activity Tracker Bot project.

## Table of Contents

- [Overview](#overview)
- [Design Principles](#design-principles)
- [Architecture Patterns](#architecture-patterns)
  - [Dependency Injection](#dependency-injection)
  - [Generic Repository Pattern](#generic-repository-pattern)
  - [Service Layer Pattern](#service-layer-pattern)
  - [Decorator Pattern](#decorator-pattern)
  - [Helper Functions](#helper-functions)
- [Error Handling Strategy](#error-handling-strategy)
- [Code Organization](#code-organization)
- [Best Practices](#best-practices)

---

## Overview

The Activity Tracker Bot follows a **microservices architecture** with clear separation of concerns:

```
┌─────────────────────────┐
│  Telegram Users         │
└───────────┬─────────────┘
            │
┌───────────▼─────────────┐
│  tracker_activity_bot   │  ← Bot Service (Aiogram 3.x)
│  - Handlers             │
│  - FSM States           │
│  - HTTP Client          │
└───────────┬─────────────┘
            │ HTTP
┌───────────▼─────────────┐
│  data_postgres_api      │  ← Data Access Service (FastAPI)
│  - REST API             │
│  - Service Layer        │
│  - Repository Layer     │
└───────────┬─────────────┘
            │
┌───────────▼─────────────┐
│  PostgreSQL Database    │
└─────────────────────────┘
```

**Key Principles**:
- **DRY** (Don't Repeat Yourself) - Eliminated ~450 lines of duplicated code
- **KISS** (Keep It Simple, Stupid) - Simplified over-engineered components
- **YAGNI** (You Aren't Gonna Need It) - Removed unused features
- **Separation of Concerns** - Clear layer boundaries
- **Type Safety** - Leveraged Python typing and generics

---

## Design Principles

### 1. Single Responsibility Principle (SRP)

Each class/function has one clear purpose:
- **Handlers** - Process user input and orchestrate responses
- **Services** - Implement business logic
- **Repositories** - Manage data access
- **Decorators** - Handle cross-cutting concerns

### 2. Dependency Inversion Principle (DIP)

High-level modules depend on abstractions:
```python
# High-level handler depends on ServiceContainer interface
async def handler(callback: CallbackQuery, services: ServiceContainer):
    await services.user.get_by_telegram_id(user_id)
```

### 3. Open/Closed Principle (OCP)

Code is open for extension, closed for modification:
```python
# Extend BaseRepository without modifying base class
class UserRepository(BaseRepository[User, UserCreate, UserUpdate]):
    async def get_by_telegram_id(self, telegram_id: int):
        # Custom method - extends base functionality
        pass
```

---

## Architecture Patterns

### Dependency Injection

**Problem**: Services were instantiated repeatedly in every handler, leading to:
- 45+ duplicate instantiations
- Tight coupling
- Difficult testing

**Solution**: Automatic dependency injection via middleware

#### Implementation

**ServiceContainer** (`src/api/dependencies.py`):
```python
class ServiceContainer:
    """Lazy-loading service container."""

    def __init__(self, api_client: Optional[DataAPIClient] = None):
        self._api_client = api_client or get_api_client()
        self._user_service: Optional[UserService] = None
        # ... other services

    @property
    def user(self) -> UserService:
        if self._user_service is None:
            self._user_service = UserService(self._api_client)
        return self._user_service
```

**Middleware** (`src/api/middleware/service_injection.py`):
```python
class ServiceInjectionMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        data["services"] = get_service_container()
        return await handler(event, data)
```

**Usage in Handlers**:
```python
@router.callback_query(F.data == "example")
async def handler(callback: CallbackQuery, services: ServiceContainer):
    user = await services.user.get_by_telegram_id(callback.from_user.id)
    categories = await services.category.get_user_categories(user["id"])
```

**Benefits**:
- ✅ No manual service instantiation
- ✅ Lazy initialization - services created only when needed
- ✅ Easy to mock for testing
- ✅ Centralized configuration

---

### Generic Repository Pattern

**Problem**: Common CRUD methods duplicated across 4 repositories (~100 lines)

**Solution**: Generic base repository with type parameters

#### Implementation

**BaseRepository** (`src/infrastructure/repositories/base.py`):
```python
from typing import TypeVar, Generic, Type, Optional

ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, session: AsyncSession, model: Type[ModelType]):
        self.session = session
        self.model = model

    async def get_by_id(self, id: int) -> Optional[ModelType]:
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def create(self, data: CreateSchemaType) -> ModelType:
        entity = self.model(**data.model_dump())
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def update(self, id: int, data: UpdateSchemaType) -> Optional[ModelType]:
        entity = await self.get_by_id(id)
        if not entity:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(entity, field, value)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, id: int) -> bool:
        result = await self.session.execute(
            delete(self.model).where(self.model.id == id)
        )
        await self.session.flush()
        return result.rowcount > 0
```

**Usage - Concrete Repository**:
```python
class UserRepository(BaseRepository[User, UserCreate, UserUpdate]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, User)

    # Only custom methods needed
    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()
```

**Benefits**:
- ✅ Eliminated ~100 lines of duplicate CRUD code
- ✅ Type-safe through Generic types
- ✅ Consistent interface across all repositories
- ✅ Easy to override methods when custom behavior needed

---

### Service Layer Pattern

**Purpose**: Encapsulate business logic separate from API and data access layers

#### Architecture

```
┌─────────────────────────────────────────┐
│          API Layer (FastAPI)            │
│  - Request validation (Pydantic)        │
│  - HTTP status codes                    │
│  - Response serialization               │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│        Service Layer (Business)         │
│  - Business validation                  │
│  - Business rules enforcement           │
│  - Orchestration logic                  │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│      Repository Layer (Data Access)     │
│  - SQL queries                          │
│  - Database transactions                │
│  - CRUD operations                      │
└─────────────────────────────────────────┘
```

#### Example

**Service Layer** (`src/application/services/user_service.py`):
```python
class UserService:
    def __init__(self, repository: UserRepository):
        self.repository = repository

    async def create_user(self, data: UserCreate) -> User:
        # Business rule: Check for existing user
        existing = await self.repository.get_by_telegram_id(data.telegram_id)
        if existing:
            raise ValueError(f"User with telegram_id {data.telegram_id} already exists")

        # Business validation
        if data.telegram_id < 0:
            raise ValueError("Invalid telegram_id")

        # Delegate to repository
        return await self.repository.create(data)
```

**API Layer** (`src/api/v1/users.py`):
```python
@router.post("/")
@handle_service_errors_with_conflict
async def create_user(
    data: UserCreate,
    service: Annotated[UserService, Depends(get_user_service)]
) -> UserResponse:
    """Create new user."""
    user = await service.create_user(data)
    return UserResponse.model_validate(user)
```

**Benefits**:
- ✅ Business logic in one place
- ✅ Reusable across different API endpoints
- ✅ Easier to test (mock repositories)
- ✅ Clear separation of concerns

---

### Decorator Pattern

**Problem**: Repeated cross-cutting concerns (user retrieval, error handling, logging)

**Solution**: Reusable decorators

#### @require_user Decorator

Eliminates 8-line user retrieval pattern:

```python
@router.callback_query(F.data == "my_activities")
@require_user
async def show_activities(
    callback: CallbackQuery,
    services: ServiceContainer,
    user: dict  # ← Automatically injected
):
    # User already retrieved and validated
    activities = await services.activity.get_user_activities(user["id"])
```

**Implementation** (`src/api/decorators.py`):
```python
def require_user(handler: Callable) -> Callable:
    @wraps(handler)
    async def wrapper(*args, **kwargs) -> Any:
        # Extract event and services from args/kwargs
        event = args[0] if args else None
        services = kwargs.get('services')

        # Get user
        telegram_id = event.from_user.id
        user = await services.user.get_by_telegram_id(telegram_id)

        if not user:
            await event.answer("Ошибка: пользователь не найден")
            return

        # Inject user into kwargs
        kwargs['user'] = user
        return await handler(*args, **kwargs)
    return wrapper
```

**Benefits**:
- ✅ Eliminated 40+ instances of duplicate code
- ✅ Consistent error handling
- ✅ Cleaner handler code

---

### Helper Functions

**Purpose**: Centralize common calculations and utilities

#### FSM Timeout Helpers

**Problem**: FSM timeout management repeated 37+ times

**Solution** (`src/application/utils/fsm_helpers.py`):
```python
async def schedule_fsm_timeout(user_id: int, state: str, bot) -> None:
    """Schedule FSM timeout for user state."""
    if fsm_timeout_module.fsm_timeout_service:
        fsm_timeout_module.fsm_timeout_service.schedule_timeout(
            user_id=user_id, state=state, bot=bot
        )

async def clear_state_and_timeout(state: FSMContext, user_id: int) -> None:
    """Clear FSM state and cancel timeout in one call."""
    await state.clear()
    await cancel_fsm_timeout(user_id)
```

**Usage**:
```python
# Before: 4-5 lines
await state.clear()
if fsm_timeout_module.fsm_timeout_service:
    fsm_timeout_module.fsm_timeout_service.cancel_timeout(user_id)

# After: 1 line
await clear_state_and_timeout(state, user_id)
```

#### Time Calculation Helpers

**Problem**: Weekend/weekday logic duplicated 3+ times

**Solution** (`src/application/utils/time_helpers.py`):
```python
def get_poll_interval(settings: dict, target_time: datetime | None = None) -> int:
    """Get poll interval based on day of week."""
    if target_time is None:
        target_time = datetime.now(timezone.utc)

    is_weekend = target_time.weekday() >= 5  # Saturday=5, Sunday=6

    return (
        settings["poll_interval_weekend"]
        if is_weekend
        else settings["poll_interval_weekday"]
    )

def calculate_poll_start_time(end_time: datetime, settings: dict) -> datetime:
    """Calculate poll start time based on end time and settings."""
    interval_minutes = get_poll_interval(settings, end_time)
    return end_time - timedelta(minutes=interval_minutes)
```

**Usage**:
```python
# Before: 6 lines
is_weekend = end_time.weekday() >= 5
interval_minutes = (
    settings["poll_interval_weekend"] if is_weekend
    else settings["poll_interval_weekday"]
)
start_time = end_time - timedelta(minutes=interval_minutes)

# After: 1 line
start_time = calculate_poll_start_time(end_time, settings)
```

---

## Error Handling Strategy

### Centralized Error Handlers

**Problem**: Try-except blocks repeated in every endpoint (~50 lines)

**Solution**: Error handling decorators

#### Implementation

**Error Handler Decorators** (`src/api/middleware/error_handler.py`):
```python
def handle_service_errors(func: Callable) -> Callable:
    @wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        try:
            return await func(*args, **kwargs)
        except ValueError as e:
            # Business validation errors
            logger.warning(f"Validation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except HTTPException:
            raise  # Re-raise HTTP exceptions
        except Exception as e:
            # Unexpected errors
            logger.error(f"Unexpected error: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )
    return wrapper
```

#### Usage

```python
@router.post("/")
@handle_service_errors
async def create_item(data: ItemCreate, service: ItemService = Depends()):
    # ValueError automatically → 400 BAD REQUEST
    # Other exceptions → 500 INTERNAL SERVER ERROR (logged)
    return await service.create(data)
```

**Error Mapping**:
- `ValueError` → `400 BAD REQUEST` (business validation)
- `ValueError` → `409 CONFLICT` (for create operations with `@handle_service_errors_with_conflict`)
- `HTTPException` → Pass through unchanged
- `Exception` → `500 INTERNAL SERVER ERROR` (logged with stack trace)

**Benefits**:
- ✅ Eliminated ~50 lines of repeated try-except
- ✅ Structured error logging
- ✅ Consistent error responses
- ✅ Automatic exception handling

---

## Code Organization

### Directory Structure

```
services/
├── tracker_activity_bot/          # Telegram Bot Service
│   └── src/
│       ├── api/
│       │   ├── handlers/          # Request handlers
│       │   ├── keyboards/         # Inline keyboard builders
│       │   ├── states/            # FSM state definitions
│       │   ├── middleware/        # Custom middleware
│       │   ├── decorators.py      # Handler decorators
│       │   └── dependencies.py    # DI container
│       ├── application/
│       │   ├── services/          # Business logic
│       │   └── utils/             # Helper functions
│       ├── infrastructure/
│       │   └── http_clients/      # HTTP clients for APIs
│       └── core/
│           ├── config.py          # Configuration
│           └── constants.py       # Constants
│
└── data_postgres_api/             # Data Access Service
    └── src/
        ├── api/
        │   ├── v1/                # API routes
        │   └── middleware/        # Error handlers
        ├── application/
        │   └── services/          # Business logic
        ├── infrastructure/
        │   └── repositories/      # Data access layer
        ├── domain/
        │   └── models/            # SQLAlchemy models
        └── schemas/               # Pydantic schemas
```

### Naming Conventions

**Files**:
- `snake_case.py` for modules
- `PascalCase` for classes
- Test files: `test_*.py`

**Functions/Methods**:
- `async def verb_noun()` - Action-oriented names
- `get_user()`, `create_activity()`, `delete_category()`

**Classes**:
- Services: `*Service` (e.g., `UserService`)
- Repositories: `*Repository` (e.g., `UserRepository`)
- Schemas: `*Create`, `*Update`, `*Response`

---

## Best Practices

### 1. Type Hints Everywhere

```python
async def get_user(user_id: int) -> Optional[User]:
    """Get user by ID."""
    ...
```

### 2. Pydantic for Validation

```python
class UserCreate(BaseModel):
    telegram_id: int = Field(..., gt=0, description="Telegram user ID")
    username: str = Field(..., min_length=1, max_length=100)
```

### 3. Async/Await Consistently

```python
# All I/O operations are async
async def get_user(user_id: int) -> User:
    return await repository.get_by_id(user_id)
```

### 4. Structured Logging

```python
logger.info(
    "User created",
    extra={"user_id": user.id, "telegram_id": user.telegram_id}
)
```

### 5. Docstrings for Public APIs

```python
async def create_activity(data: ActivityCreate) -> Activity:
    """
    Create new activity with validation.

    Args:
        data: Activity creation data

    Returns:
        Created activity with generated ID

    Raises:
        ValueError: If validation fails
    """
```

### 6. Small, Focused Functions

- Max 20-30 lines per function
- One responsibility per function
- Extract complex logic into helpers

### 7. Error Handling Strategy

- **Service Layer**: Raise `ValueError` for business errors
- **API Layer**: Use decorators to convert to HTTP responses
- **Never swallow exceptions** - always log or re-raise

---

## Refactoring Results

### Metrics

**Lines of Code**:
- Added: ~2,000 lines (new helpers, documentation)
- Removed: ~650 lines (duplication, dead code)
- **Net Reduction**: ~450 lines of duplication

**Violations Fixed**:
- ✅ 4 Critical DRY violations
- ✅ 3 High DRY violations
- ✅ 2 Medium DRY violations
- ✅ 2 High KISS violations
- ✅ 1 Medium KISS violation
- ✅ 3 High YAGNI violations

**Commits**: 8 comprehensive refactoring commits

### Key Improvements

1. **Dependency Injection** - Eliminated 45+ service instantiations
2. **BaseRepository** - Removed ~100 lines of CRUD duplication
3. **Error Handling** - Centralized in decorators (~50 lines removed)
4. **Helper Functions** - Consolidated time calculations, FSM management
5. **Code Simplification** - Removed unused features, over-engineered components

---

## References

- [FastAPI Best Practices](https://fastapi.tiangolo.com/tutorial/)
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)
- [Aiogram 3.x Documentation](https://docs.aiogram.dev/en/latest/)
- [Domain-Driven Design Patterns](https://martinfowler.com/bliki/DomainDrivenDesign.html)
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
