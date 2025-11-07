# data_postgres_api

HTTP Data Access Service for PostgreSQL - FastAPI microservice.

## Architecture

This service is part of the **Improved Hybrid Approach** architecture. It provides HTTP-only access to PostgreSQL database.

**Service Name**: `data_postgres_api` (3-part naming: `{context}_{domain}_{type}`)
**Technology**: FastAPI, SQLAlchemy 2.0 async, Python 3.11+
**Purpose**: Single point of access to PostgreSQL database

## Endpoints

### Users API

- `POST /api/v1/users` - Create user
- `GET /api/v1/users/by-telegram/{telegram_id}` - Get user by Telegram ID

### Categories API

- `POST /api/v1/categories` - Create category
- `POST /api/v1/categories/bulk-create` - Create multiple categories
- `GET /api/v1/categories?user_id={id}` - Get user categories
- `DELETE /api/v1/categories/{id}` - Delete category

### Activities API

- `POST /api/v1/activities` - Create activity
- `GET /api/v1/activities?user_id={id}&limit={n}` - Get recent user activities

### User Settings API

- `POST /api/v1/user-settings` - Create user settings
- `GET /api/v1/user-settings?user_id={id}` - Get user settings
- `PUT /api/v1/user-settings/{user_id}` - Update user settings

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
uvicorn services.data_postgres_api.main:app --reload

# Run with Docker
docker build -t data_postgres_api .
docker run -p 8000:8000 data_postgres_api
```

## Environment Variables

- `DATABASE_URL` - PostgreSQL connection string
- `LOG_LEVEL` - Logging level (default: INFO)
- `API_V1_PREFIX` - API prefix (default: /api/v1)

## Architecture Patterns

### Generic BaseRepository Pattern

All repositories inherit from a generic base repository providing common CRUD operations:

```python
from src.infrastructure.repositories.base import BaseRepository

class UserRepository(BaseRepository[User, UserCreate, UserUpdate]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, User)

    # Only custom methods here
    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()
```

**Base Methods Provided**:
- `get_by_id(id: int)` - Retrieve entity by primary key
- `create(data: CreateSchemaType)` - Create new entity
- `update(id: int, data: UpdateSchemaType)` - Update entity
- `delete(id: int)` - Delete entity

**Benefits**:
- Eliminates ~100 lines of duplicated CRUD code
- Type-safe through Generic types
- Consistent interface across all repositories
- Easy to extend with custom methods

**Implementation**: `src/infrastructure/repositories/base.py`

### Centralized Error Handling

API routes use decorators for consistent error handling:

```python
from src.api.middleware import handle_service_errors

@router.post("/")
@handle_service_errors
async def create_item(data: ItemCreate, service: ItemService = Depends()):
    # ValueError automatically converted to 400 BAD REQUEST
    # Unexpected exceptions logged and return 500
    return await service.create(data)
```

**Error Decorators**:
- `@handle_service_errors` - Maps ValueError → 400 BAD REQUEST
- `@handle_service_errors_with_conflict` - Maps ValueError → 409 CONFLICT

**Benefits**:
- Eliminated ~50 lines of repeated try-except blocks
- Structured error logging
- Consistent error responses
- Automatic exception handling

**Implementation**: `src/api/middleware/error_handler.py`

### Service Layer Pattern

Business logic separated into service classes:

```python
class UserService:
    def __init__(self, repository: UserRepository):
        self.repository = repository

    async def create_user(self, data: UserCreate) -> User:
        # Business validation
        if data.telegram_id < 0:
            raise ValueError("Invalid telegram_id")

        # Delegate to repository
        return await self.repository.create(data)
```

**Layers**:
- **API Layer** (`src/api/v1/`) - HTTP endpoints, request validation
- **Service Layer** (`src/application/services/`) - Business logic, validation
- **Repository Layer** (`src/infrastructure/repositories/`) - Data access

**Benefits**:
- Clear separation of concerns
- Business rules in one place
- Easier testing
- Reusable business logic

## Database Schema

See `models/` directory for SQLAlchemy models:
- `User` - Telegram bot users
- `Category` - Activity categories
- `Activity` - User activities with duration tracking
- `UserSettings` - User preferences and poll intervals
