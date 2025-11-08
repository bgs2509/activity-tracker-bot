# Architecture Snapshot

**Purpose**: Current state of Activity Tracker Bot architecture as of 2025-11-08.

**For AI**: This is the SINGLE SOURCE OF TRUTH for understanding this project's architecture.

## Project Overview

```yaml
Name: Activity Tracker Bot
Type: Telegram Bot for Personal Activity Tracking
Maturity: PoC Level 1 (Proof of Concept)
Architecture: Microservices with "Improved Hybrid Approach"
Deployment: Docker Compose (local), no production yet
```

## Service Topology

```
┌─────────────────────────────────────────────┐
│  Telegram Users                             │
└──────────────────┬──────────────────────────┘
                   │ Telegram Bot API
                   ▼
┌─────────────────────────────────────────────┐
│  tracker_activity_bot                       │
│  • Type: Telegram Bot (Aiogram 3.3.0)      │
│  • Port: None (polling mode)                │
│  • Responsibilities:                        │
│    - User interaction (handlers)            │
│    - FSM state management                   │
│    - HTTP client to Data API                │
│    - Automatic poll scheduling              │
│  • NO direct database access                │
└──────────────────┬──────────────────────────┘
                   │ HTTP REST API
                   │ http://data_postgres_api:8000
                   ▼
┌─────────────────────────────────────────────┐
│  data_postgres_api                          │
│  • Type: REST API (FastAPI 0.109.0)        │
│  • Port: 8080:8000 (external:internal)     │
│  • Responsibilities:                        │
│    - All data access operations             │
│    - Business validation                    │
│    - Database transactions                  │
│  • ONLY service that touches PostgreSQL    │
└──────────────────┬──────────────────────────┘
                   │ SQL Queries
                   ▼
┌─────────────────────────────────────────────┐
│  PostgreSQL 15-alpine                       │
│  • Port: 5433:5432 (external:internal)     │
│  • Database: tracker_db                     │
│  • Tables: users, categories, activities,  │
│            user_settings                    │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│  Redis 7-alpine                             │
│  • Port: 6379:6379                          │
│  • Purpose: FSM state storage (TTL: 15 min)│
│  • Used by: tracker_activity_bot only      │
└─────────────────────────────────────────────┘
```

## Technology Stack

### tracker_activity_bot
```python
Python: 3.12
Framework: Aiogram 3.3.0
HTTP Client: httpx 0.26.0
FSM Storage: Redis 5.0.1
Scheduler: APScheduler 3.10.4
Config: pydantic-settings 2.1.0
Logging: python-json-logger 2.0.7
Testing: pytest 8.0.0 + pytest-asyncio 0.23.5
```

### data_postgres_api
```python
Python: 3.12
Framework: FastAPI 0.109.0
ORM: SQLAlchemy 2.0.25 (async)
Database Driver: asyncpg 0.29.0
Migrations: Alembic 1.13.1
Validation: pydantic 2.5.3
Server: Uvicorn 0.27.0
Logging: python-json-logger 2.0.7
Testing: pytest 8.0.0 + pytest-asyncio 0.23.5
```

### Infrastructure
```yaml
Containerization: Docker + Docker Compose
Database: PostgreSQL 15-alpine
Cache: Redis 7-alpine
Planned (Level 3+): Nginx, Prometheus, Grafana
```

## Layer Architecture

Both services follow Clean Architecture with clear layer separation:

### Bot Service Layers

```
src/
├── api/                      # API Layer (presentation)
│   ├── handlers/            # Message/callback handlers
│   ├── keyboards/           # Inline keyboards (UI)
│   ├── states/              # FSM state definitions
│   ├── middleware/          # Request middleware
│   └── dependencies.py      # DI container
│
├── application/             # Application Layer (business logic)
│   ├── services/           # Business services (Scheduler, FSM timeout)
│   ├── protocols/          # Interfaces
│   └── utils/              # Helpers (time parsing, FSM helpers)
│
├── infrastructure/          # Infrastructure Layer
│   └── http_clients/       # HTTP services to Data API
│       ├── http_client.py      # Base client with middleware
│       ├── user_service.py     # User API wrapper
│       ├── category_service.py # Category API wrapper
│       ├── activity_service.py # Activity API wrapper
│       └── user_settings_service.py
│
└── core/                    # Core configuration
    ├── config.py           # Environment settings
    ├── constants.py        # Constants
    └── logging.py          # Logging setup
```

### Data API Service Layers

```
src/
├── api/                     # API Layer (presentation)
│   ├── v1/                 # API routes (versioned)
│   │   ├── users.py
│   │   ├── categories.py
│   │   ├── activities.py
│   │   └── user_settings.py
│   ├── middleware/         # Request middleware
│   └── dependencies.py     # DI for repositories
│
├── application/            # Application Layer (business logic)
│   └── services/          # Business services
│       ├── user_service.py
│       ├── category_service.py
│       ├── activity_service.py
│       └── user_settings_service.py
│
├── infrastructure/         # Infrastructure Layer
│   ├── database/          # Database connection
│   └── repositories/      # Data access
│       ├── base.py               # Generic Repository<T>
│       ├── user_repository.py
│       ├── category_repository.py
│       ├── activity_repository.py
│       └── user_settings_repository.py
│
├── domain/                 # Domain Layer
│   └── models/            # SQLAlchemy models
│       ├── base.py
│       ├── user.py
│       ├── category.py
│       ├── activity.py
│       └── user_settings.py
│
├── schemas/               # Pydantic DTOs (shared between layers)
│   ├── user.py
│   ├── category.py
│   ├── activity.py
│   └── user_settings.py
│
└── core/                  # Core configuration
    ├── config.py
    └── logging.py
```

## Data Models

### User
```python
# Table: users
id: int (PK)
telegram_id: int (unique, indexed)
username: str | None
first_name: str | None
timezone: str (default: "Europe/Moscow")
created_at: datetime
last_poll_time: datetime | None

# Relationships:
categories: List[Category] (cascade delete)
activities: List[Activity] (cascade delete)
settings: UserSettings (one-to-one, cascade delete)
```

### Category
```python
# Table: categories
id: int (PK)
user_id: int (FK → users.id, cascade delete)
name: str (max 100)
emoji: str | None (max 10)
is_default: bool (default: False)
created_at: datetime

# Constraints:
UNIQUE(user_id, name)

# Relationships:
user: User
activities: List[Activity]
```

### Activity
```python
# Table: activities
id: int (PK)
user_id: int (FK → users.id, cascade delete)
category_id: int | None (FK → categories.id, set null on delete)
description: str (text)
tags: str | None (text)
start_time: datetime (indexed)
end_time: datetime (indexed)
duration_minutes: int
created_at: datetime

# Constraints:
CHECK(end_time > start_time)

# Relationships:
user: User
category: Category | None
```

### UserSettings
```python
# Table: user_settings
id: int (PK)
user_id: int (FK → users.id, unique, cascade delete)
poll_interval_weekday: int (default: 120 min)
poll_interval_weekend: int (default: 180 min)
quiet_hours_start: time (default: 23:00)
quiet_hours_end: time (default: 07:00)
reminder_enabled: bool (default: True)
reminder_delay_minutes: int (default: 30)

# Relationships:
user: User (one-to-one)
```

## API Endpoints

### Users API
```
POST   /api/v1/users                     # Create user
GET    /api/v1/users/by-telegram/{id}    # Get by Telegram ID
PATCH  /api/v1/users/{id}/last-poll-time # Update last poll time
```

### Categories API
```
POST   /api/v1/categories                # Create category
POST   /api/v1/categories/bulk-create    # Bulk create
GET    /api/v1/categories?user_id={id}   # Get user categories
DELETE /api/v1/categories/{id}           # Delete category
```

### Activities API
```
POST   /api/v1/activities                # Create activity
GET    /api/v1/activities?user_id={id}&limit={n}  # Get activities
```

### User Settings API
```
GET    /api/v1/user-settings?user_id={id}  # Get settings
POST   /api/v1/user-settings               # Create settings
PATCH  /api/v1/user-settings/{id}          # Update settings
```

## Key Architectural Decisions

### 1. HTTP-Only Data Access
**Decision**: Bot NEVER accesses database directly, only through HTTP API

**Rationale**:
- Clear separation of concerns
- Independent scaling
- Easier testing and mocking
- Better error handling

### 2. Generic Repository Pattern
**Decision**: Use Generic Repository with TypeVars for CRUD operations

**Code Location**: `services/data_postgres_api/src/infrastructure/repositories/base.py`

**Result**: Eliminated ~100 lines of duplicated CRUD code

### 3. Service Layer Pattern
**Decision**: Business logic in separate service layer, not in routes or repositories

**Rationale**:
- Reusable business logic
- Easier testing
- Clear responsibilities

### 4. FSM State Management
**Decision**: Use Redis with 15-minute TTL for FSM states

**Rationale**:
- Automatic cleanup
- Fast access
- Persistence across bot restarts

### 5. Dependency Injection
**Decision**: ServiceContainer with lazy loading

**Code Location**: `services/tracker_activity_bot/src/api/dependencies.py`

**Result**: Eliminated 45+ duplicate service instantiations

## Critical Constraints

**For AI**: These are HARD RULES. NEVER violate:

1. ✅ **Bot NEVER touches database directly** - Always use HTTP API
2. ✅ **Use Generic Repository for new models** - Don't write duplicate CRUD
3. ✅ **Business logic in Service layer** - Not in routes or repositories
4. ✅ **All async code must have type hints** - Use `async def foo() -> ReturnType:`
5. ✅ **All public functions need docstrings** - English, Google style
6. ✅ **FSM states must have timeout** - Use FSMTimeoutService
7. ✅ **All API calls must handle errors** - Use try/except with logging
8. ✅ **Tests required for new code** - Unit tests minimum

## Current State (as of 2025-11-08)

```yaml
Status: PoC Level 1
Deployment: Local Docker Compose
Test Coverage: ~80-85%
Documentation: Good
Production Ready: No (needs Level 2-3 work)

Recent Changes:
  - Fixed handler registration bugs
  - Added integration tests (handler registration + API contracts)
  - Implemented comprehensive logging
  - Refactored to DRY/KISS/YAGNI principles

Known Gaps:
  - No E2E tests
  - No CI/CD pipeline
  - No production deployment
  - No monitoring/alerting
```

## For AI: Quick Decision Tree

```
Need to add new feature?
│
├─ Needs database table?
│  └─ Create: Model → Repository → Service → API endpoint → Bot HTTP client
│
├─ Needs new handler?
│  └─ Create: Handler → Register router → Add to main.py
│
├─ Needs FSM flow?
│  └─ Create: States → Handlers → Keyboards → Register router
│
└─ Needs business logic?
   └─ Add to: Service layer (never in routes or repositories)
```

---

**Last Updated**: 2025-11-08
**Next Review**: When major architectural changes occur
