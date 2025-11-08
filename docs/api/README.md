# API Documentation

**Purpose**: Complete reference for Data API endpoints and contracts.

## Quick Navigation

| Document | Purpose |
|----------|---------|
| `bot-to-api-contract.md` | Service contract between Bot and Data API |
| `endpoints-reference.md` | Complete API endpoint reference |
| `schemas/` | JSON schemas for request/response validation |

## API Overview

**Base URL**: `http://data_postgres_api:8000`

**API Version**: v1

**Prefix**: `/api/v1`

## Services

### Users API
Manage Telegram bot users.

**Endpoints**:
- `POST /api/v1/users` - Create new user
- `GET /api/v1/users/by-telegram/{telegram_id}` - Get user by Telegram ID
- `PATCH /api/v1/users/{id}/last-poll-time` - Update last poll time

### Categories API
Manage user activity categories.

**Endpoints**:
- `POST /api/v1/categories` - Create category
- `POST /api/v1/categories/bulk-create` - Create multiple categories
- `GET /api/v1/categories?user_id={id}` - Get user's categories
- `DELETE /api/v1/categories/{id}` - Delete category

### Activities API
Manage user activities.

**Endpoints**:
- `POST /api/v1/activities` - Create activity
- `GET /api/v1/activities?user_id={id}&limit={n}` - Get user's activities

### User Settings API
Manage user settings (poll intervals, quiet hours, reminders).

**Endpoints**:
- `GET /api/v1/user-settings?user_id={id}` - Get settings
- `POST /api/v1/user-settings` - Create settings
- `PATCH /api/v1/user-settings/{id}` - Update settings

## Interactive Documentation

When services are running:

- **Swagger UI**: http://localhost:8080/docs
- **ReDoc**: http://localhost:8080/redoc
- **OpenAPI JSON**: http://localhost:8080/openapi.json

## Authentication

Currently: No authentication (PoC Level 1)

Planned for Level 3+:
- API keys for service-to-service communication
- JWT tokens for user sessions

## Error Responses

All endpoints return standard error format:

```json
{
  "detail": "Error message"
}
```

**HTTP Status Codes**:
- `200 OK` - Success
- `201 Created` - Resource created
- `400 Bad Request` - Validation error
- `404 Not Found` - Resource not found
- `422 Unprocessable Entity` - Pydantic validation error
- `500 Internal Server Error` - Server error

## Rate Limiting

Currently: No rate limiting (PoC Level 1)

Planned for Level 3+:
- 100 requests per minute per service
- 1000 requests per hour per user

## Versioning

Current version: v1

API versioning strategy:
- URL-based versioning (`/api/v1/`, `/api/v2/`)
- Backward compatibility within major version
- Deprecation warnings 6 months before removal

---

**Last Updated**: 2025-11-08
**Maintained By**: Development Team
