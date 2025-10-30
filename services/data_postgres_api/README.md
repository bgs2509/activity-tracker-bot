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
- `GET /api/v1/activities?user_id={id}&limit={n}&offset={n}` - Get user activities

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

## Database Schema

See `models/` directory for SQLAlchemy models:
- `User` - Telegram bot users
- `Category` - Activity categories
- `Activity` - User activities
