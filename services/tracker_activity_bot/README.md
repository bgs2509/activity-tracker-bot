# tracker_activity_bot

Telegram Bot for activity tracking - Aiogram 3.x microservice.

## Architecture

This service is part of the **Improved Hybrid Approach** architecture. It provides user interface through Telegram and communicates with `data_postgres_api` via HTTP.

**Service Name**: `tracker_activity_bot` (3-part naming: `{context}_{domain}_{type}`)
**Technology**: Aiogram 3.x, Python 3.11+
**Purpose**: Telegram bot interface for activity tracking

## Key Features

- ✅ User registration with default categories
- ✅ Activity recording with FSM (multi-step dialog)
- ✅ Time parsing (14:30, 30м, 2ч)
- ✅ Category management
- ✅ Activity list viewing
- ✅ HTTP-only data access (no direct database connection)

## Commands

- `/start` - Start bot and show main menu

All other actions are performed via inline keyboards.

## HTTP Communication

Bot communicates with `data_postgres_api` service:
- UserService - user management
- CategoryService - category operations
- ActivityService - activity CRUD

**Base URL**: `http://data_postgres_api:8000`

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally (requires Redis and data_postgres_api)
python -m services.tracker_activity_bot.main

# Run with Docker
docker build -t tracker_activity_bot .
docker run tracker_activity_bot
```

## Environment Variables

- `TELEGRAM_BOT_TOKEN` - Telegram bot token
- `DATA_API_URL` - data_postgres_api base URL
- `REDIS_URL` - Redis connection string
- `LOG_LEVEL` - Logging level (default: INFO)

## FSM States

### ActivityStates
- waiting_for_start_time
- waiting_for_end_time
- waiting_for_description
- waiting_for_category

### CategoryStates
- waiting_for_name
- waiting_for_emoji
