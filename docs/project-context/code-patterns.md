# Code Patterns

**Purpose**: Established code patterns in Activity Tracker Bot that MUST be followed.

**For AI**: Use these patterns when generating new code. Do NOT invent new patterns.

## Table of Contents

1. [Generic Repository Pattern](#generic-repository-pattern)
2. [Service Layer Pattern](#service-layer-pattern)
3. [Handler Pattern](#handler-pattern)
4. [FSM Flow Pattern](#fsm-flow-pattern)
5. [HTTP Client Pattern](#http-client-pattern)
6. [Dependency Injection Pattern](#dependency-injection-pattern)
7. [Error Handling Pattern](#error-handling-pattern)
8. [Testing Pattern](#testing-pattern)

---

## Generic Repository Pattern

**Location**: `services/data_postgres_api/src/infrastructure/repositories/base.py`

**When**: Creating new database model and repository

**Pattern**:

```python
from typing import TypeVar, Generic
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models.base import Base
from src.schemas.your_model import YourModelCreate, YourModelUpdate

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Generic repository with common CRUD operations.

    Eliminates code duplication across repositories.
    """

    def __init__(self, session: AsyncSession, model: type[ModelType]):
        self.session = session
        self.model = model

    async def get_by_id(self, id: int) -> ModelType | None:
        """Get entity by ID."""
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def create(self, data: CreateSchemaType) -> ModelType:
        """Create new entity."""
        instance = self.model(**data.model_dump())
        self.session.add(instance)
        await self.session.commit()
        await self.session.refresh(instance)
        return instance

    # ... other CRUD methods


# Concrete repository - only add custom methods
class YourModelRepository(
    BaseRepository[YourModel, YourModelCreate, YourModelUpdate]
):
    """Repository for YourModel with custom methods."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, YourModel)

    async def get_by_custom_field(self, field_value: str) -> YourModel | None:
        """Custom query specific to this model."""
        result = await self.session.execute(
            select(YourModel).where(YourModel.custom_field == field_value)
        )
        return result.scalar_one_or_none()
```

**Why**: Eliminates ~20-30 lines of duplicate CRUD code per repository.

**Real Example**: See `user_repository.py`, `category_repository.py`, `activity_repository.py`

---

## Service Layer Pattern

**Location**: `services/data_postgres_api/src/application/services/`

**When**: Implementing business logic

**Pattern**:

```python
from src.infrastructure.repositories.your_model_repository import YourModelRepository
from src.schemas.your_model import YourModelCreate, YourModelUpdate
from src.domain.models.your_model import YourModel


class YourModelService:
    """
    Business logic for YourModel.

    Responsibilities:
    - Business validation
    - Business rules enforcement
    - Orchestration of repository calls
    - NO direct database access
    """

    def __init__(self, repository: YourModelRepository):
        self.repository = repository

    async def create(self, data: YourModelCreate) -> YourModel:
        """
        Create new entity with business validation.

        Args:
            data: Entity creation data

        Returns:
            Created entity

        Raises:
            ValueError: If business rules violated
        """
        # 1. Business validation
        if not self._validate_business_rules(data):
            raise ValueError("Business rule violated: ...")

        # 2. Check for duplicates (if needed)
        existing = await self.repository.get_by_custom_field(data.field)
        if existing:
            raise ValueError(f"Entity already exists: {data.field}")

        # 3. Create via repository
        return await self.repository.create(data)

    async def get_by_id(self, id: int) -> YourModel | None:
        """Get entity by ID."""
        return await self.repository.get_by_id(id)

    def _validate_business_rules(self, data: YourModelCreate) -> bool:
        """Private method for business validation."""
        # Business rules here
        return True
```

**Key Points**:
- ✅ Constructor takes repository as dependency
- ✅ All business validation in service
- ✅ Service calls repository, NEVER direct DB access
- ✅ Raise `ValueError` for business rule violations
- ✅ All public methods have docstrings

**Real Example**: See `user_service.py`, `category_service.py`, `activity_service.py`

---

## Handler Pattern

**Location**: `services/tracker_activity_bot/src/api/handlers/`

**When**: Creating new message or callback handler

**Pattern**:

```python
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from src.api.dependencies import ServiceContainer
from src.api.states.your_module import YourStates
from src.api.keyboards.your_module import get_your_keyboard

router = Router(name="your_module")


@router.callback_query(F.data == "your_action")
async def handle_your_action(
    callback: CallbackQuery,
    services: ServiceContainer,
    state: FSMContext
):
    """
    Handle your action.

    This is a callback query handler that...

    Args:
        callback: Callback query from Telegram
        services: Injected service container
        state: FSM state context
    """
    # 1. Extract data
    user_id = callback.from_user.id

    # 2. Call service via HTTP
    try:
        user = await services.user.get_by_telegram_id(user_id)
        result = await services.your_service.do_something(user["id"])
    except Exception as e:
        await callback.answer("❌ Ошибка. Попробуйте позже.")
        logger.error(f"Error in handle_your_action: {e}")
        return

    # 3. Update FSM state if needed
    await state.set_state(YourStates.next_state)
    await state.update_data(key=result)

    # 4. Send response
    await callback.message.answer(
        "✅ Успешно!",
        reply_markup=get_your_keyboard()
    )

    # 5. Answer callback (ALWAYS!)
    await callback.answer()


@router.message(YourStates.waiting_for_input)
async def handle_your_input(
    message: Message,
    services: ServiceContainer,
    state: FSMContext
):
    """
    Handle user input in FSM state.

    Args:
        message: Message from user
        services: Injected service container
        state: FSM state context
    """
    # 1. Extract and validate input
    user_input = message.text
    if not user_input or len(user_input) > 100:
        await message.answer("❌ Некорректный ввод. Попробуйте еще раз.")
        return

    # 2. Get FSM data
    data = await state.get_data()

    # 3. Process with service
    try:
        result = await services.your_service.process(user_input, data)
    except ValueError as e:
        await message.answer(f"❌ Ошибка: {e}")
        return

    # 4. Clear state or move to next
    await state.clear()

    # 5. Send result
    await message.answer(
        f"✅ Обработано: {result}",
        reply_markup=get_main_menu_keyboard()
    )
```

**Key Points**:
- ✅ Use Router with descriptive name
- ✅ Use F.data for callback query filters
- ✅ Inject ServiceContainer for dependencies
- ✅ ALWAYS call `await callback.answer()` for callbacks
- ✅ Try/except for service calls with user-friendly errors
- ✅ Clear or update FSM state appropriately
- ✅ Russian text for user messages
- ✅ English docstrings

**Real Example**: See `handlers/activity/activity_creation.py`, `handlers/categories/category_creation.py`

---

## FSM Flow Pattern

**Location**: `services/tracker_activity_bot/src/api/states/` + `handlers/`

**When**: Creating multi-step user interaction

**Pattern**:

### 1. Define States

```python
# src/api/states/your_module.py
from aiogram.fsm.state import State, StatesGroup


class YourStates(StatesGroup):
    """FSM states for your flow."""

    waiting_for_step1 = State()
    waiting_for_step2 = State()
    waiting_for_step3 = State()
```

### 2. Create Flow Handlers

```python
# src/api/handlers/your_module/your_flow.py
from aiogram import Router
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from src.api.states.your_module import YourStates
from src.api.dependencies import ServiceContainer

router = Router(name="your_flow")


# Entry point - start flow
@router.callback_query(F.data == "start_your_flow")
async def start_flow(
    callback: CallbackQuery,
    state: FSMContext
):
    """Start your flow."""
    await state.set_state(YourStates.waiting_for_step1)
    await callback.message.answer("Введите данные для шага 1:")
    await callback.answer()


# Step 1 handler
@router.message(YourStates.waiting_for_step1)
async def process_step1(
    message: Message,
    state: FSMContext
):
    """Process step 1 input."""
    # Validate input
    if not message.text:
        await message.answer("❌ Введите текст")
        return

    # Save to FSM
    await state.update_data(step1_value=message.text)

    # Move to next state
    await state.set_state(YourStates.waiting_for_step2)
    await message.answer("Введите данные для шага 2:")


# Step 2 handler
@router.message(YourStates.waiting_for_step2)
async def process_step2(
    message: Message,
    state: FSMContext,
    services: ServiceContainer
):
    """Process step 2 and complete flow."""
    # Get all FSM data
    data = await state.get_data()
    step1_value = data["step1_value"]
    step2_value = message.text

    # Call service to save
    try:
        result = await services.your_service.create({
            "field1": step1_value,
            "field2": step2_value
        })
    except ValueError as e:
        await message.answer(f"❌ Ошибка: {e}")
        return

    # Clear state (flow complete!)
    await state.clear()

    # Send success
    await message.answer(
        "✅ Готово!",
        reply_markup=get_main_menu_keyboard()
    )
```

### 3. Schedule FSM Timeout

```python
# In entry point handler
from src.application.services.fsm_timeout_service import get_fsm_timeout_service

@router.callback_query(F.data == "start_your_flow")
async def start_flow(
    callback: CallbackQuery,
    state: FSMContext,
    bot
):
    """Start your flow with timeout."""
    await state.set_state(YourStates.waiting_for_step1)

    # Schedule timeout (15 minutes)
    fsm_service = get_fsm_timeout_service()
    fsm_service.schedule_timeout(
        user_id=callback.from_user.id,
        state=state,
        bot=bot
    )

    await callback.message.answer("Введите данные (15 мин):")
    await callback.answer()


# Cancel timeout when flow completes
async def process_final_step(...):
    # ... process data ...

    # Cancel timeout
    fsm_service.cancel_timeout(message.from_user.id)

    # Clear state
    await state.clear()
```

**Key Points**:
- ✅ States in separate file
- ✅ Entry point sets initial state
- ✅ Each step validates input
- ✅ Use `state.update_data()` to accumulate data
- ✅ Use `state.get_data()` to retrieve all data
- ✅ ALWAYS `await state.clear()` when flow completes
- ✅ Schedule timeout for all FSM flows
- ✅ Cancel timeout when flow completes

**Real Example**: See `handlers/activity/activity_creation.py` (complete 4-step flow)

---

## HTTP Client Pattern

**Location**: `services/tracker_activity_bot/src/infrastructure/http_clients/`

**When**: Creating wrapper for Data API endpoint

**Pattern**:

```python
# src/infrastructure/http_clients/your_service.py
from typing import Any

from src.infrastructure.http_clients.http_client import DataAPIClient


class YourService:
    """HTTP client for Your API endpoints."""

    def __init__(self, client: DataAPIClient):
        self.client = client

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Create new entity.

        Args:
            data: Entity creation data

        Returns:
            Created entity data

        Raises:
            httpx.HTTPStatusError: On HTTP error
        """
        response = await self.client.post("/your-entities", json=data)
        return response.json()

    async def get_by_id(self, entity_id: int) -> dict[str, Any]:
        """
        Get entity by ID.

        Args:
            entity_id: Entity ID

        Returns:
            Entity data or None if not found
        """
        response = await self.client.get(f"/your-entities/{entity_id}")
        if response.status_code == 404:
            return None
        return response.json()

    async def get_by_filter(
        self,
        user_id: int,
        limit: int = 10
    ) -> list[dict[str, Any]]:
        """
        Get entities with filters.

        Args:
            user_id: User ID to filter by
            limit: Maximum number of results

        Returns:
            List of entities
        """
        response = await self.client.get(
            "/your-entities",
            params={"user_id": user_id, "limit": limit}
        )
        return response.json()
```

**Key Points**:
- ✅ Constructor takes `DataAPIClient` dependency
- ✅ Methods match HTTP verbs (get, post, patch, delete)
- ✅ Return `dict[str, Any]` or `list[dict[str, Any]]`
- ✅ Let HTTP errors propagate (handled in handlers)
- ✅ Use `params={}` for query parameters
- ✅ Use `json={}` for request body

**Real Example**: See `user_service.py`, `category_service.py`, `activity_service.py`

---

## Dependency Injection Pattern

**Location**: `services/tracker_activity_bot/src/api/dependencies.py`

**When**: Need to inject services into handlers

**Pattern**:

```python
# src/api/dependencies.py
from src.infrastructure.http_clients.http_client import DataAPIClient
from src.infrastructure.http_clients.user_service import UserService
from src.application.services.scheduler_service import SchedulerService


class ServiceContainer:
    """
    Centralized service container with lazy loading.

    Benefits:
    - Single instantiation point
    - Lazy loading (services created only when needed)
    - Easy mocking for tests
    """

    def __init__(self, api_client: DataAPIClient = None, scheduler: SchedulerService = None):
        # Allow injection for testing
        self._api_client = api_client or get_api_client()
        self._scheduler = scheduler or SchedulerService()

        # Lazy-loaded services
        self._user_service: UserService | None = None
        self._your_service: YourService | None = None

    @property
    def user(self) -> UserService:
        """Get user service (lazy loading)."""
        if self._user_service is None:
            self._user_service = UserService(self._api_client)
        return self._user_service

    @property
    def your_service(self) -> YourService:
        """Get your service (lazy loading)."""
        if self._your_service is None:
            self._your_service = YourService(self._api_client)
        return self._your_service

    @property
    def scheduler(self) -> SchedulerService:
        """Get scheduler service."""
        return self._scheduler


# Global instance
_service_container: ServiceContainer | None = None


def get_service_container() -> ServiceContainer:
    """Get global service container."""
    global _service_container
    if _service_container is None:
        _service_container = ServiceContainer()
    return _service_container
```

**Usage in Handlers**:

```python
from src.api.dependencies import ServiceContainer

async def handler(callback: CallbackQuery, services: ServiceContainer):
    user = await services.user.get_by_telegram_id(123)
    result = await services.your_service.create({})
```

**Usage in Main**:

```python
from src.api.dependencies import get_service_container

async def main():
    services = get_service_container()
    services.scheduler.start()
```

**Key Points**:
- ✅ Lazy loading with `@property`
- ✅ Allow dependency injection in constructor (for tests)
- ✅ Global singleton via `get_service_container()`
- ✅ Add new services as properties

**Real Example**: See `src/api/dependencies.py`

---

## Error Handling Pattern

**When**: All service calls, all HTTP calls

**Pattern**:

### In Handlers

```python
@router.callback_query(F.data == "action")
async def handler(callback: CallbackQuery, services: ServiceContainer):
    """Handle action."""
    try:
        result = await services.your_service.do_something()
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
        await callback.answer("❌ Ошибка сервера. Попробуйте позже.")
        return
    except Exception as e:
        logger.error(f"Unexpected error in handler: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка. Попробуйте позже.")
        return

    # Success path
    await callback.message.answer(f"✅ Готово: {result}")
    await callback.answer()
```

### In Services

```python
class YourService:
    async def create(self, data: YourCreateSchema) -> YourModel:
        """Create with validation."""
        # Business validation - raise ValueError
        if not self._validate(data):
            raise ValueError("Invalid data: specific reason")

        # Check duplicates - raise ValueError
        existing = await self.repository.get_by_field(data.field)
        if existing:
            raise ValueError(f"Already exists: {data.field}")

        # Create
        return await self.repository.create(data)
```

### In HTTP Clients

```python
class YourService:
    async def create(self, data: dict) -> dict:
        """Create via API."""
        # Let HTTP errors propagate - handled in handlers
        response = await self.client.post("/entities", json=data)
        return response.json()
```

**Key Points**:
- ✅ Services raise `ValueError` for business errors
- ✅ Handlers catch `httpx.HTTPStatusError` and `Exception`
- ✅ Always log errors with context
- ✅ User-friendly Russian error messages
- ✅ Never silently swallow errors (`except: pass` is FORBIDDEN)

---

## Testing Pattern

**Location**: `services/*/tests/unit/`

**When**: Writing tests for new code

**Pattern**:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.application.services.your_service import YourService
from src.domain.models.your_model import YourModel


@pytest.fixture
def mock_repository():
    """Mock repository."""
    repo = AsyncMock()
    return repo


@pytest.fixture
def service(mock_repository):
    """Service instance with mocked repository."""
    return YourService(repository=mock_repository)


@pytest.mark.asyncio
async def test_create_success(service, mock_repository):
    """Test successful entity creation."""
    # Arrange
    input_data = YourModelCreate(field="value")
    expected = YourModel(id=1, field="value")
    mock_repository.create.return_value = expected
    mock_repository.get_by_field.return_value = None  # No duplicate

    # Act
    result = await service.create(input_data)

    # Assert
    assert result == expected
    mock_repository.create.assert_called_once()


@pytest.mark.asyncio
async def test_create_duplicate_error(service, mock_repository):
    """Test creation fails when duplicate exists."""
    # Arrange
    input_data = YourModelCreate(field="existing")
    mock_repository.get_by_field.return_value = YourModel(id=1, field="existing")

    # Act & Assert
    with pytest.raises(ValueError, match="Already exists"):
        await service.create(input_data)
```

**Key Points**:
- ✅ Use pytest fixtures for setup
- ✅ Use `AsyncMock` for async methods
- ✅ Test both success and error paths
- ✅ Arrange-Act-Assert structure
- ✅ Clear test names: `test_<method>_<scenario>`
- ✅ Mark async tests with `@pytest.mark.asyncio`

**Real Example**: See `tests/unit/services/test_activity_service.py`

---

## Summary for AI

When generating code:

1. **New Model?** → Use Generic Repository Pattern
2. **Business Logic?** → Use Service Layer Pattern
3. **User Interaction?** → Use Handler Pattern
4. **Multi-Step Flow?** → Use FSM Flow Pattern
5. **Call API?** → Use HTTP Client Pattern
6. **Need Services?** → Use Dependency Injection Pattern
7. **Errors?** → Use Error Handling Pattern
8. **Tests?** → Use Testing Pattern

**Golden Rule**: If existing code does something similarly, COPY THAT PATTERN.

---

**Last Updated**: 2025-11-08
**Next Update**: When new patterns are established
