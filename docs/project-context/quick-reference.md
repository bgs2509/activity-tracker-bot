# Quick Reference

**Purpose**: Cheat sheet for AI tools when working with Activity Tracker Bot.

**For AI**: Use this for quick decisions. For detailed patterns, see `code-patterns.md`.

## Project Structure Quick Map

```
activity-tracker-bot/
├── services/
│   ├── tracker_activity_bot/       # Bot Service (Aiogram)
│   │   └── src/
│   │       ├── api/               # Handlers, keyboards, states
│   │       ├── application/       # Business services
│   │       ├── infrastructure/    # HTTP clients
│   │       └── core/             # Config, constants
│   │
│   └── data_postgres_api/         # Data API (FastAPI)
│       └── src/
│           ├── api/              # Routes, middleware
│           ├── application/      # Services
│           ├── infrastructure/   # Repositories, DB
│           ├── domain/          # Models
│           └── schemas/         # Pydantic DTOs
```

## Quick Decision Tree

```
What are you doing?
│
├─ Adding new database model?
│  └─ Create: Model → Schema → Repository (extend BaseRepository) → Service → Route
│     Files: domain/models/, schemas/, infrastructure/repositories/, application/services/, api/v1/
│
├─ Adding new handler?
│  └─ Create: Handler function → Register in router → Include router in main.py
│     Files: api/handlers/your_module/, main.py
│
├─ Adding FSM flow?
│  └─ Create: States → Handlers → Keyboards
│     Files: api/states/, api/handlers/, api/keyboards/
│
├─ Adding API endpoint?
│  └─ Create: Route → Service → Repository
│     Files: api/v1/your_endpoint.py
│
├─ Adding business logic?
│  └─ Add to: Service layer (NOT in routes or handlers!)
│     Files: application/services/
│
└─ Adding HTTP client method?
   └─ Add to: Existing or new HTTP client service
      Files: infrastructure/http_clients/
```

## File Templates

### New Repository

```python
# services/data_postgres_api/src/infrastructure/repositories/your_model_repository.py
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.repositories.base import BaseRepository
from src.domain.models.your_model import YourModel
from src.schemas.your_model import YourModelCreate, YourModelUpdate


class YourModelRepository(BaseRepository[YourModel, YourModelCreate, YourModelUpdate]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, YourModel)

    # Add ONLY custom methods here (common CRUD inherited from BaseRepository)
```

### New Service

```python
# services/data_postgres_api/src/application/services/your_model_service.py
from src.infrastructure.repositories.your_model_repository import YourModelRepository
from src.schemas.your_model import YourModelCreate
from src.domain.models.your_model import YourModel


class YourModelService:
    def __init__(self, repository: YourModelRepository):
        self.repository = repository

    async def create(self, data: YourModelCreate) -> YourModel:
        """Create with business validation."""
        # Business validation here
        return await self.repository.create(data)
```

### New Handler

```python
# services/tracker_activity_bot/src/api/handlers/your_module.py
from aiogram import Router, F
from aiogram.types import CallbackQuery

from src.api.dependencies import ServiceContainer

router = Router(name="your_module")


@router.callback_query(F.data == "your_action")
async def handle_your_action(
    callback: CallbackQuery,
    services: ServiceContainer
):
    """Handle your action."""
    try:
        result = await services.your_service.do_something()
    except Exception as e:
        logger.error(f"Error: {e}")
        await callback.answer("❌ Ошибка")
        return

    await callback.message.answer(f"✅ Готово: {result}")
    await callback.answer()
```

### New FSM States

```python
# services/tracker_activity_bot/src/api/states/your_module.py
from aiogram.fsm.state import State, StatesGroup


class YourStates(StatesGroup):
    waiting_for_step1 = State()
    waiting_for_step2 = State()
```

### New API Route

```python
# services/data_postgres_api/src/api/v1/your_endpoint.py
from fastapi import APIRouter, Depends, HTTPException

from src.application.services.your_service import YourService
from src.schemas.your_model import YourModelCreate, YourModelResponse
from src.api.dependencies import get_your_service

router = APIRouter(prefix="/your-endpoint", tags=["your-endpoint"])


@router.post("", response_model=YourModelResponse)
async def create_your_model(
    data: YourModelCreate,
    service: YourService = Depends(get_your_service)
):
    """Create your model."""
    try:
        result = await service.create(data)
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))
```

### New HTTP Client

```python
# services/tracker_activity_bot/src/infrastructure/http_clients/your_service.py
from typing import Any

from src.infrastructure.http_clients.http_client import DataAPIClient


class YourService:
    def __init__(self, client: DataAPIClient):
        self.client = client

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create via API."""
        response = await self.client.post("/your-endpoint", json=data)
        return response.json()
```

## Common Commands

```bash
# Development
make build              # Build Docker images
make up                 # Start all services
make down               # Stop all services
make logs-bot           # Bot logs
make logs-api           # API logs
make restart-bot        # Restart bot only
make restart-api        # Restart API only

# Testing
make test-unit-docker   # Unit tests in Docker
make test-all-docker    # All tests in Docker
make lint               # Run linter
make format             # Format code

# Database
make migrate            # Run migrations
make migrate-create MSG="your message"  # Create migration
make shell-db           # Open psql shell

# Shell access
make shell-bot          # Bot container shell
make shell-api          # API container shell
```

## API Endpoints Quick Reference

```
Users:
  POST   /api/v1/users
  GET    /api/v1/users/by-telegram/{telegram_id}
  PATCH  /api/v1/users/{id}/last-poll-time

Categories:
  POST   /api/v1/categories
  POST   /api/v1/categories/bulk-create
  GET    /api/v1/categories?user_id={id}
  DELETE /api/v1/categories/{id}

Activities:
  POST   /api/v1/activities
  GET    /api/v1/activities?user_id={id}&limit={n}

User Settings:
  GET    /api/v1/user-settings?user_id={id}
  POST   /api/v1/user-settings
  PATCH  /api/v1/user-settings/{id}
```

## Default Values

```python
# Timezones
DEFAULT_TIMEZONE = "Europe/Moscow"

# Poll Intervals
DEFAULT_POLL_INTERVAL_WEEKDAY = 120  # minutes
DEFAULT_POLL_INTERVAL_WEEKEND = 180  # minutes

# Quiet Hours
DEFAULT_QUIET_HOURS_START = "23:00"
DEFAULT_QUIET_HOURS_END = "07:00"

# FSM
FSM_STATE_TTL = 15  # minutes

# HTTP
HTTP_TIMEOUT = 30  # seconds
```

## Default Categories

```python
DEFAULT_CATEGORIES = [
    {"name": "Работа", "emoji": "💼", "is_default": True},
    {"name": "Учеба", "emoji": "🎯", "is_default": True},
    {"name": "Спорт", "emoji": "🏃", "is_default": True},
    {"name": "Отдых", "emoji": "🎮", "is_default": True},
    {"name": "Еда", "emoji": "🍽️", "is_default": True},
    {"name": "Дорога", "emoji": "🚗", "is_default": True},
]
```

## Environment Variables

```bash
# Bot Service
TELEGRAM_BOT_TOKEN=your_token_here
DATA_API_URL=http://data_postgres_api:8000
REDIS_URL=redis://redis:6379/0
LOG_LEVEL=INFO

# Data API Service
DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/tracker_db
ENABLE_DB_AUTO_CREATE=false
LOG_LEVEL=INFO
```

## Testing Markers

```python
@pytest.mark.unit          # Unit test
@pytest.mark.integration   # Integration test
@pytest.mark.smoke         # Smoke test
@pytest.mark.asyncio       # Async test (required for async functions)
```

## Common Imports

### Bot Service

```python
# Handlers
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from src.api.dependencies import ServiceContainer

# States
from aiogram.fsm.state import State, StatesGroup

# Keyboards
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
```

### Data API Service

```python
# Routes
from fastapi import APIRouter, Depends, HTTPException
from src.api.dependencies import get_session

# Services
from sqlalchemy.ext.asyncio import AsyncSession
from src.infrastructure.repositories.your_repository import YourRepository

# Models
from sqlalchemy import select
from src.domain.models.your_model import YourModel

# Schemas
from pydantic import BaseModel, Field
```

## Error Messages (Russian for users)

```python
ERROR_MESSAGES = {
    "server_error": "❌ Ошибка сервера. Попробуйте позже.",
    "validation_error": "❌ Некорректные данные. Проверьте ввод.",
    "not_found": "❌ Не найдено.",
    "already_exists": "❌ Уже существует.",
    "invalid_input": "❌ Некорректный ввод. Попробуйте еще раз.",
    "success": "✅ Готово!",
    "canceled": "❌ Отменено.",
}
```

## Logging Format

```python
# Structured JSON logging
logger.info("User action", extra={
    "user_id": user_id,
    "action": "create_activity",
    "duration_ms": 123
})

logger.error("Error occurred", extra={
    "error": str(e),
    "user_id": user_id,
    "context": "handler_name"
}, exc_info=True)
```

## Critical Rules (NEVER violate!)

1. ✅ Bot NEVER imports from `src.domain.models` or `sqlalchemy`
2. ✅ All repositories extend `BaseRepository[T, C, U]`
3. ✅ Business logic ONLY in Service layer
4. ✅ All FSM flows MUST call `await state.clear()` when complete
5. ✅ All service calls MUST be wrapped in try/except
6. ✅ All callback handlers MUST call `await callback.answer()`
7. ✅ All functions MUST have type hints
8. ✅ NEVER use `except: pass`
9. ✅ All new code MUST have tests

## When Stuck

1. Check existing similar code and copy pattern
2. Read `code-patterns.md` for detailed examples
3. Check `anti-patterns.md` for what NOT to do
4. Look at tests for usage examples
5. Check logs: `make logs-bot` or `make logs-api`

---

**Last Updated**: 2025-11-08
**Maintained By**: Development Team
