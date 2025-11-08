# Tracker Activity Bot Service

**Type**: Telegram Bot (Aiogram 3.3.0)

**Purpose**: User interaction layer for Activity Tracker Bot.

## Overview

This service is part of the **Improved Hybrid Approach** architecture. It provides user interface through Telegram and communicates with `data_postgres_api` via HTTP.

**Service Name**: `tracker_activity_bot` (3-part naming: `{context}_{domain}_{type}`)
**Technology**: Aiogram 3.3.0, Python 3.12
**Purpose**: Telegram bot interface for activity tracking

**Key Principle**: This service NEVER accesses database directly - all data operations via HTTP API.

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

## Architecture Patterns

### Dependency Injection

Service dependencies are automatically injected into handlers via middleware:

```python
from src.api.dependencies import ServiceContainer

@router.callback_query(F.data == "my_activities")
async def show_activities(callback: CallbackQuery, services: ServiceContainer):
    # Services automatically injected - no manual instantiation
    user = await services.user.get_by_telegram_id(callback.from_user.id)
    activities = await services.activity.get_user_activities(user["id"])
```

**Benefits**:
- No repeated service instantiation
- Centralized configuration
- Easier testing with mock services

**Implementation**: `src/api/middleware/service_injection.py`

### Decorators

#### @require_user Decorator

Automatically retrieves and validates user before handler execution:

```python
from src.api.decorators import require_user

@router.callback_query(F.data == "example")
@require_user
async def handler(callback: CallbackQuery, services: ServiceContainer, user: dict):
    # User automatically retrieved and validated
    # Directly use 'user' dict
    print(user["id"])
```

**Eliminates**:
- 8 lines of repeated user retrieval code
- Duplicate error handling
- Manual validation checks

**Implementation**: `src/api/decorators.py`

### Helper Functions

#### FSM Timeout Helpers

Centralized FSM timeout management:

```python
from src.application.utils.fsm_helpers import (
    schedule_fsm_timeout,
    cancel_fsm_timeout,
    clear_state_and_timeout
)

# Schedule timeout
await schedule_fsm_timeout(user_id, state, bot)

# Clear state and cancel timeout in one call
await clear_state_and_timeout(state, user_id)
```

**Implementation**: `src/application/utils/fsm_helpers.py`

#### Time Calculation Helpers

Poll time calculation utilities:

```python
from src.application.utils.time_helpers import (
    get_poll_interval,
    calculate_poll_start_time
)

# Get interval based on weekday/weekend
interval = get_poll_interval(settings)

# Calculate start time from end time
start_time = calculate_poll_start_time(end_time, settings)
```

**Implementation**: `src/application/utils/time_helpers.py`

#### Duration Formatting

Consistent duration display across the application:

```python
from src.application.utils.formatters import format_duration

# Converts minutes to human-readable format
format_duration(90)   # "1ч 30м"
format_duration(120)  # "2ч"
format_duration(45)   # "45м"
```

**Implementation**: `src/application/utils/formatters.py`

## FSM States

### ActivityStates
- waiting_for_start_time
- waiting_for_end_time
- waiting_for_description
- waiting_for_category

### CategoryStates
- waiting_for_name
- waiting_for_emoji

### PollStates
- waiting_for_poll_description
- waiting_for_poll_tags

## Documentation

- [Code Patterns](../../docs/project-context/code-patterns.md)
- [Anti-Patterns](../../docs/project-context/anti-patterns.md)
- [API Contract](../../docs/api/bot-to-api-contract.md)
- [Onboarding Guide](../../docs/onboarding/)
- [Architecture](../../ARCHITECTURE.md)

---

**Last Updated**: 2025-11-08
**Maintained By**: Development Team
