# Bot ↔ API Contract

**Purpose**: Formal contract between `tracker_activity_bot` and `data_postgres_api` services.

**For AI**: When adding API endpoints or HTTP client methods, ensure they match this contract.

## Contract Principles

1. **Bot NEVER accesses database directly** - All data operations via HTTP API
2. **API is the single source of truth** - All business rules enforced in API
3. **Stateless HTTP** - No session state in API (FSM state in Redis on bot side)
4. **JSON communication** - All requests/responses in JSON format
5. **Type safety** - Pydantic schemas for validation on both sides

## Service Communication

```
┌──────────────────────┐                    ┌──────────────────────┐
│  tracker_activity_   │   HTTP REST API    │  data_postgres_api   │
│  bot                 │ ─────────────────► │                      │
│                      │                    │                      │
│  HTTP Client         │   JSON Request     │  FastAPI Routes      │
│  (httpx)             │                    │                      │
│                      │ ◄───────────────── │  Service Layer       │
│  ServiceContainer    │   JSON Response    │                      │
│  └─ UserService      │                    │  Repository Layer    │
│  └─ CategoryService  │                    │                      │
│  └─ ActivityService  │                    │  PostgreSQL          │
│  └─ SettingsService  │                    │                      │
└──────────────────────┘                    └──────────────────────┘
```

## Endpoint Contracts

### Users API

#### Create User

```
POST /api/v1/users
Content-Type: application/json

Request:
{
  "telegram_id": 123456789,
  "username": "john_doe",
  "first_name": "John",
  "timezone": "Europe/Moscow"
}

Response: 201 Created
{
  "id": 1,
  "telegram_id": 123456789,
  "username": "john_doe",
  "first_name": "John",
  "timezone": "Europe/Moscow",
  "created_at": "2025-11-08T12:00:00+03:00",
  "last_poll_time": null
}

Errors:
- 400: User with this telegram_id already exists
- 422: Validation error (invalid telegram_id, etc.)
```

**Bot Usage**:
```python
await services.user.create_user(
    telegram_id=message.from_user.id,
    username=message.from_user.username,
    first_name=message.from_user.first_name
)
```

#### Get User by Telegram ID

```
GET /api/v1/users/by-telegram/{telegram_id}

Response: 200 OK
{
  "id": 1,
  "telegram_id": 123456789,
  "username": "john_doe",
  "first_name": "John",
  "timezone": "Europe/Moscow",
  "created_at": "2025-11-08T12:00:00+03:00",
  "last_poll_time": "2025-11-08T14:00:00+03:00"
}

Errors:
- 404: User not found
```

**Bot Usage**:
```python
user = await services.user.get_by_telegram_id(
    telegram_id=message.from_user.id
)
if user is None:
    # User not registered, create
```

#### Update Last Poll Time

```
PATCH /api/v1/users/{user_id}/last-poll-time
Content-Type: application/json

Request:
{
  "last_poll_time": "2025-11-08T15:00:00+03:00"
}

Response: 200 OK
{
  "id": 1,
  "telegram_id": 123456789,
  "last_poll_time": "2025-11-08T15:00:00+03:00",
  ...
}

Errors:
- 404: User not found
```

**Bot Usage**:
```python
await services.user.update_last_poll_time(
    user_id=user["id"],
    poll_time=datetime.now(timezone.utc)
)
```

### Categories API

#### Create Category

```
POST /api/v1/categories
Content-Type: application/json

Request:
{
  "user_id": 1,
  "name": "Работа",
  "emoji": "💼",
  "is_default": false
}

Response: 201 Created
{
  "id": 1,
  "user_id": 1,
  "name": "Работа",
  "emoji": "💼",
  "is_default": false,
  "created_at": "2025-11-08T12:00:00+03:00"
}

Errors:
- 400: Category with this name already exists for user
- 404: User not found
```

**Bot Usage**:
```python
category = await services.category.create_category(
    user_id=user["id"],
    name="Работа",
    emoji="💼"
)
```

#### Bulk Create Categories

```
POST /api/v1/categories/bulk-create
Content-Type: application/json

Request:
{
  "user_id": 1,
  "categories": [
    {"name": "Работа", "emoji": "💼", "is_default": true},
    {"name": "Учеба", "emoji": "🎯", "is_default": true},
    {"name": "Спорт", "emoji": "🏃", "is_default": true}
  ]
}

Response: 201 Created
[
  {"id": 1, "user_id": 1, "name": "Работа", "emoji": "💼", ...},
  {"id": 2, "user_id": 1, "name": "Учеба", "emoji": "🎯", ...},
  {"id": 3, "user_id": 1, "name": "Спорт", "emoji": "🏃", ...}
]

Errors:
- 404: User not found
```

**Bot Usage**:
```python
categories = await services.category.bulk_create_categories(
    user_id=user["id"],
    categories=DEFAULT_CATEGORIES
)
```

#### Get User Categories

```
GET /api/v1/categories?user_id={user_id}

Response: 200 OK
[
  {"id": 1, "name": "Работа", "emoji": "💼", ...},
  {"id": 2, "name": "Учеба", "emoji": "🎯", ...}
]

Returns empty array if user has no categories.
```

**Bot Usage**:
```python
categories = await services.category.get_user_categories(
    user_id=user["id"]
)
```

#### Delete Category

```
DELETE /api/v1/categories/{category_id}

Response: 204 No Content

Errors:
- 404: Category not found
- 400: Cannot delete last category
```

**Bot Usage**:
```python
success = await services.category.delete_category(
    category_id=category_id
)
```

### Activities API

#### Create Activity

```
POST /api/v1/activities
Content-Type: application/json

Request:
{
  "user_id": 1,
  "category_id": 1,
  "description": "Работал над проектом",
  "start_time": "2025-11-08T14:00:00+03:00",
  "end_time": "2025-11-08T16:00:00+03:00",
  "tags": "важное, проект"
}

Response: 201 Created
{
  "id": 1,
  "user_id": 1,
  "category_id": 1,
  "description": "Работал над проектом",
  "start_time": "2025-11-08T14:00:00+03:00",
  "end_time": "2025-11-08T16:00:00+03:00",
  "duration_minutes": 120,
  "tags": "важное, проект",
  "created_at": "2025-11-08T16:05:00+03:00"
}

Errors:
- 400: end_time must be after start_time
- 404: User or category not found
- 422: Validation error
```

**Bot Usage**:
```python
activity = await services.activity.create_activity({
    "user_id": user["id"],
    "category_id": category_id,
    "description": description,
    "start_time": start_time.isoformat(),
    "end_time": end_time.isoformat(),
})
```

#### Get User Activities

```
GET /api/v1/activities?user_id={user_id}&limit={limit}

Query Parameters:
- user_id (required): User ID
- limit (optional, default: 10): Max number of activities

Response: 200 OK
[
  {
    "id": 1,
    "category_id": 1,
    "description": "Работал над проектом",
    "start_time": "2025-11-08T14:00:00+03:00",
    "end_time": "2025-11-08T16:00:00+03:00",
    "duration_minutes": 120,
    ...
  }
]

Returns empty array if user has no activities.
```

**Bot Usage**:
```python
activities = await services.activity.get_user_activities(
    user_id=user["id"],
    limit=10
)
```

### User Settings API

#### Get Settings

```
GET /api/v1/user-settings?user_id={user_id}

Response: 200 OK
{
  "id": 1,
  "user_id": 1,
  "poll_interval_weekday": 120,
  "poll_interval_weekend": 180,
  "quiet_hours_start": "23:00:00",
  "quiet_hours_end": "07:00:00",
  "reminder_enabled": true,
  "reminder_delay_minutes": 30
}

Errors:
- 404: Settings not found (user should create)
```

**Bot Usage**:
```python
settings = await services.settings.get_settings(
    user_id=user["id"]
)
```

#### Create Settings

```
POST /api/v1/user-settings
Content-Type: application/json

Request:
{
  "user_id": 1,
  "poll_interval_weekday": 120,
  "poll_interval_weekend": 180,
  "quiet_hours_start": "23:00:00",
  "quiet_hours_end": "07:00:00",
  "reminder_enabled": true,
  "reminder_delay_minutes": 30
}

Response: 201 Created
{
  "id": 1,
  "user_id": 1,
  ...
}

Errors:
- 400: Settings already exist for this user
- 404: User not found
```

**Bot Usage**:
```python
settings = await services.settings.create_settings(
    user_id=user["id"]
)
```

#### Update Settings

```
PATCH /api/v1/user-settings/{settings_id}
Content-Type: application/json

Request (all fields optional):
{
  "poll_interval_weekday": 90,
  "quiet_hours_start": "22:00:00",
  "reminder_enabled": false
}

Response: 200 OK
{
  "id": 1,
  "poll_interval_weekday": 90,
  "quiet_hours_start": "22:00:00",
  "reminder_enabled": false,
  ...
}

Errors:
- 404: Settings not found
- 422: Validation error
```

**Bot Usage**:
```python
settings = await services.settings.update_settings(
    user_id=user["id"],
    updates={
        "poll_interval_weekday": 90,
        "reminder_enabled": False
    }
)
```

## Data Types

### Datetime Format

**ISO 8601 with timezone**:
```
"2025-11-08T14:00:00+03:00"
```

**Bot Side** (Python):
```python
from datetime import datetime, timezone

# Send to API
dt = datetime.now(timezone.utc)
dt_str = dt.isoformat()  # "2025-11-08T11:00:00+00:00"

# Receive from API
dt = datetime.fromisoformat(response["created_at"])
```

### Time Format

**HH:MM:SS format**:
```
"23:00:00"
```

### Integer Ranges

```python
poll_interval_weekday: 1-720 (1 min to 12 hours)
poll_interval_weekend: 1-1440 (1 min to 24 hours)
reminder_delay_minutes: 5-120 (5 min to 2 hours)
```

## Error Handling

### Bot Side

```python
import httpx

try:
    response = await client.post("/api/v1/users", json=data)
except httpx.HTTPStatusError as e:
    if e.response.status_code == 400:
        # Business rule violation
        logger.warning(f"Business error: {e.response.json()['detail']}")
    elif e.response.status_code == 404:
        # Not found
        logger.error("Resource not found")
    elif e.response.status_code == 422:
        # Validation error
        logger.error(f"Validation error: {e.response.json()}")
    else:
        # Server error
        logger.error(f"Server error: {e.response.status_code}")
except httpx.RequestError as e:
    # Network error
    logger.error(f"Network error: {e}")
```

### API Side

```python
from fastapi import HTTPException

try:
    result = await service.create(data)
    return result
except ValueError as e:
    # Business rule violation
    raise HTTPException(400, str(e))
except Exception as e:
    # Unexpected error
    logger.error(f"Unexpected error: {e}", exc_info=True)
    raise HTTPException(500, "Internal server error")
```

## Version Compatibility

Current version: v1

**Breaking changes** require new version (v2):
- Removing endpoints
- Changing required fields
- Changing data types
- Removing response fields

**Non-breaking changes** allowed in v1:
- Adding new endpoints
- Adding optional fields
- Adding response fields
- Deprecating (not removing) endpoints

## Testing Contract

### Contract Tests Location

`tests/integration/test_api_contracts.py`

### What to Test

1. **Endpoint paths match** - Bot client paths match API routes
2. **Request schemas match** - Bot sends correct format
3. **Response schemas match** - Bot expects correct format
4. **Error codes match** - Bot handles all error codes API can return

### Example Contract Test

```python
@pytest.mark.integration
def test_user_creation_contract():
    """Test bot client matches API contract for user creation."""
    # Bot client
    bot_client_path = "/users"  # From UserService
    bot_request_schema = {"telegram_id": int, "username": str, ...}

    # API route
    api_route_path = "/api/v1/users"  # From users.py
    api_request_schema = UserCreate

    # Assert match
    assert bot_client_path in api_route_path
    assert_schemas_compatible(bot_request_schema, api_request_schema)
```

## Migration Strategy

When changing API contract:

1. **Add new endpoint** (keep old one)
2. **Update bot** to use new endpoint
3. **Deploy bot**
4. **Deprecate old endpoint** (add warning log)
5. **Wait deprecation period** (e.g., 1 month)
6. **Remove old endpoint**

Never break contract without coordination between services!

---

**Last Updated**: 2025-11-08
**Version**: 1.0.0
**Next Review**: On API version change
