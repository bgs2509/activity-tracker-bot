# API Endpoints Reference

**Purpose**: Complete reference for all Data API endpoints.

**Base URL**: `http://data_postgres_api:8000`

**API Prefix**: `/api/v1`

## Health Check Endpoints

### Liveness Probe

```
GET /health/live

Response: 200 OK
{
  "status": "ok"
}
```

**Purpose**: Check if service is alive.

### Readiness Probe

```
GET /health/ready

Response: 200 OK
{
  "status": "ok"
}
```

**Purpose**: Check if service is ready to accept traffic.

---

## Users API

Base path: `/api/v1/users`

### Create User

```
POST /api/v1/users
Content-Type: application/json

Request Body:
{
  "telegram_id": 123456789,           # Required: Telegram user ID
  "username": "john_doe",             # Optional: Telegram username
  "first_name": "John",               # Optional: First name
  "timezone": "Europe/Moscow"         # Optional: Timezone (default: Europe/Moscow)
}

Success Response: 201 Created
{
  "id": 1,
  "telegram_id": 123456789,
  "username": "john_doe",
  "first_name": "John",
  "timezone": "Europe/Moscow",
  "created_at": "2025-11-08T12:00:00+03:00",
  "last_poll_time": null
}

Error Responses:
400 Bad Request - User with telegram_id already exists
422 Unprocessable Entity - Validation error
```

### Get User by Telegram ID

```
GET /api/v1/users/by-telegram/{telegram_id}

Path Parameters:
- telegram_id: Telegram user ID (integer)

Success Response: 200 OK
{
  "id": 1,
  "telegram_id": 123456789,
  "username": "john_doe",
  "first_name": "John",
  "timezone": "Europe/Moscow",
  "created_at": "2025-11-08T12:00:00+03:00",
  "last_poll_time": "2025-11-08T14:00:00+03:00"
}

Error Responses:
404 Not Found - User not found
```

### Update Last Poll Time

```
PATCH /api/v1/users/{user_id}/last-poll-time
Content-Type: application/json

Path Parameters:
- user_id: Internal user ID (integer)

Request Body:
{
  "last_poll_time": "2025-11-08T15:00:00+03:00"  # Required: ISO 8601 datetime
}

Success Response: 200 OK
{
  "id": 1,
  "telegram_id": 123456789,
  "last_poll_time": "2025-11-08T15:00:00+03:00",
  ...
}

Error Responses:
404 Not Found - User not found
```

---

## Categories API

Base path: `/api/v1/categories`

### Create Category

```
POST /api/v1/categories
Content-Type: application/json

Request Body:
{
  "user_id": 1,                # Required: User ID
  "name": "Работа",            # Required: Category name (max 100 chars)
  "emoji": "💼",               # Optional: Emoji (max 10 chars)
  "is_default": false          # Optional: Is default category (default: false)
}

Success Response: 201 Created
{
  "id": 1,
  "user_id": 1,
  "name": "Работа",
  "emoji": "💼",
  "is_default": false,
  "created_at": "2025-11-08T12:00:00+03:00"
}

Error Responses:
400 Bad Request - Category with this name already exists for user
404 Not Found - User not found
422 Unprocessable Entity - Validation error
```

### Bulk Create Categories

```
POST /api/v1/categories/bulk-create
Content-Type: application/json

Request Body:
{
  "user_id": 1,                # Required: User ID
  "categories": [              # Required: Array of categories (min 1 item)
    {
      "name": "Работа",        # Required: Category name
      "emoji": "💼",           # Optional: Emoji
      "is_default": true       # Optional: Is default
    },
    {
      "name": "Учеба",
      "emoji": "🎯",
      "is_default": true
    }
  ]
}

Success Response: 201 Created
[
  {
    "id": 1,
    "user_id": 1,
    "name": "Работа",
    "emoji": "💼",
    "is_default": true,
    "created_at": "2025-11-08T12:00:00+03:00"
  },
  {
    "id": 2,
    "user_id": 1,
    "name": "Учеба",
    "emoji": "🎯",
    "is_default": true,
    "created_at": "2025-11-08T12:00:00+03:00"
  }
]

Error Responses:
404 Not Found - User not found
422 Unprocessable Entity - Validation error
```

### Get User Categories

```
GET /api/v1/categories?user_id={user_id}

Query Parameters:
- user_id: User ID (required, integer)

Success Response: 200 OK
[
  {
    "id": 1,
    "user_id": 1,
    "name": "Работа",
    "emoji": "💼",
    "is_default": true,
    "created_at": "2025-11-08T12:00:00+03:00"
  },
  {
    "id": 2,
    "user_id": 1,
    "name": "Учеба",
    "emoji": "🎯",
    "is_default": true,
    "created_at": "2025-11-08T12:00:00+03:00"
  }
]

Returns empty array [] if user has no categories.

Error Responses:
422 Unprocessable Entity - Missing or invalid user_id parameter
```

### Delete Category

```
DELETE /api/v1/categories/{category_id}

Path Parameters:
- category_id: Category ID (integer)

Success Response: 204 No Content
(Empty body)

Error Responses:
404 Not Found - Category not found
400 Bad Request - Cannot delete last category
```

---

## Activities API

Base path: `/api/v1/activities`

### Create Activity

```
POST /api/v1/activities
Content-Type: application/json

Request Body:
{
  "user_id": 1,                           # Required: User ID
  "category_id": 1,                       # Optional: Category ID (null allowed)
  "description": "Работал над проектом",  # Required: Description (max 10000 chars)
  "tags": "важное, проект",               # Optional: Comma-separated tags (max 1000 chars)
  "start_time": "2025-11-08T14:00:00+03:00",  # Required: ISO 8601 datetime
  "end_time": "2025-11-08T16:00:00+03:00"     # Required: ISO 8601 datetime
}

Success Response: 201 Created
{
  "id": 1,
  "user_id": 1,
  "category_id": 1,
  "description": "Работал над проектом",
  "tags": "важное, проект",
  "start_time": "2025-11-08T14:00:00+03:00",
  "end_time": "2025-11-08T16:00:00+03:00",
  "duration_minutes": 120,
  "created_at": "2025-11-08T16:05:00+03:00"
}

Error Responses:
400 Bad Request - end_time must be after start_time
404 Not Found - User or category not found
422 Unprocessable Entity - Validation error
```

### Get User Activities

```
GET /api/v1/activities?user_id={user_id}&limit={limit}

Query Parameters:
- user_id: User ID (required, integer)
- limit: Maximum number of activities (optional, default: 10, max: 100)

Success Response: 200 OK
[
  {
    "id": 1,
    "user_id": 1,
    "category_id": 1,
    "description": "Работал над проектом",
    "tags": "важное, проект",
    "start_time": "2025-11-08T14:00:00+03:00",
    "end_time": "2025-11-08T16:00:00+03:00",
    "duration_minutes": 120,
    "created_at": "2025-11-08T16:05:00+03:00"
  }
]

Returns empty array [] if user has no activities.

Error Responses:
422 Unprocessable Entity - Missing or invalid parameters
```

---

## User Settings API

Base path: `/api/v1/user-settings`

### Get User Settings

```
GET /api/v1/user-settings?user_id={user_id}

Query Parameters:
- user_id: User ID (required, integer)

Success Response: 200 OK
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

Error Responses:
404 Not Found - Settings not found for this user
422 Unprocessable Entity - Missing or invalid user_id
```

### Create User Settings

```
POST /api/v1/user-settings
Content-Type: application/json

Request Body:
{
  "user_id": 1,                        # Required: User ID
  "poll_interval_weekday": 120,        # Optional: 1-720 minutes (default: 120)
  "poll_interval_weekend": 180,        # Optional: 1-1440 minutes (default: 180)
  "quiet_hours_start": "23:00:00",     # Optional: HH:MM:SS (default: 23:00:00)
  "quiet_hours_end": "07:00:00",       # Optional: HH:MM:SS (default: 07:00:00)
  "reminder_enabled": true,            # Optional: boolean (default: true)
  "reminder_delay_minutes": 30         # Optional: 5-120 minutes (default: 30)
}

Success Response: 201 Created
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

Error Responses:
400 Bad Request - Settings already exist for this user
404 Not Found - User not found
422 Unprocessable Entity - Validation error (invalid ranges)
```

### Update User Settings

```
PATCH /api/v1/user-settings/{settings_id}
Content-Type: application/json

Path Parameters:
- settings_id: Settings ID (integer)

Request Body (all fields optional):
{
  "poll_interval_weekday": 90,        # Optional: 1-720 minutes
  "poll_interval_weekend": 150,       # Optional: 1-1440 minutes
  "quiet_hours_start": "22:00:00",    # Optional: HH:MM:SS
  "quiet_hours_end": "08:00:00",      # Optional: HH:MM:SS
  "reminder_enabled": false,          # Optional: boolean
  "reminder_delay_minutes": 45        # Optional: 5-120 minutes
}

Success Response: 200 OK
{
  "id": 1,
  "user_id": 1,
  "poll_interval_weekday": 90,
  "poll_interval_weekend": 150,
  "quiet_hours_start": "22:00:00",
  "quiet_hours_end": "08:00:00",
  "reminder_enabled": false,
  "reminder_delay_minutes": 45
}

Error Responses:
404 Not Found - Settings not found
422 Unprocessable Entity - Validation error (invalid ranges)
```

---

## Common Patterns

### Pagination

Currently: Simple limit parameter
```
GET /api/v1/activities?user_id=1&limit=10
```

Future: Offset-based pagination
```
GET /api/v1/activities?user_id=1&limit=10&offset=20
```

### Filtering

Currently: Basic query parameters
```
GET /api/v1/categories?user_id=1
GET /api/v1/activities?user_id=1&limit=10
```

Future: Advanced filtering
```
GET /api/v1/activities?user_id=1&start_date=2025-11-01&end_date=2025-11-30&category_id=1
```

### Sorting

Currently: Default sorting (most recent first)

Future: Sortable fields
```
GET /api/v1/activities?user_id=1&sort_by=start_time&sort_order=desc
```

---

## Rate Limiting

Currently: No rate limiting (PoC Level 1)

Planned for Level 3+:
- 100 requests per minute per service
- 1000 requests per hour per user
- `X-RateLimit-*` headers in responses

---

## Testing Endpoints

### Interactive Testing

Use Swagger UI when services are running:
```bash
make up
open http://localhost:8080/docs
```

### Curl Examples

Create user:
```bash
curl -X POST http://localhost:8080/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{"telegram_id": 123456789, "username": "test"}'
```

Get user:
```bash
curl http://localhost:8080/api/v1/users/by-telegram/123456789
```

Create activity:
```bash
curl -X POST http://localhost:8080/api/v1/activities \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "category_id": 1,
    "description": "Test activity",
    "start_time": "2025-11-08T14:00:00+03:00",
    "end_time": "2025-11-08T15:00:00+03:00"
  }'
```

---

**Last Updated**: 2025-11-08
**API Version**: v1
**Next Review**: On API changes
