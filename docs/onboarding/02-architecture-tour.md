# Architecture Tour

**Time**: 20 minutes

**Goal**: Understand the codebase structure and key concepts.

## High-Level Architecture

```
┌─────────────────────────────────────────────┐
│  Telegram Users                             │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  tracker_activity_bot (Aiogram)             │
│  • Handles user interactions                │
│  • FSM state management (Redis)             │
│  • HTTP client ONLY (no database access)    │
│  Port: None (polling mode)                  │
└──────────────────┬──────────────────────────┘
                   │ HTTP REST API
                   ▼
┌─────────────────────────────────────────────┐
│  data_postgres_api (FastAPI)                │
│  • REST API endpoints                       │
│  • Business logic (Service layer)           │
│  • Data access (Repository layer)           │
│  Port: 8080:8000                            │
└──────────────────┬──────────────────────────┘
                   │ SQL
                   ▼
┌─────────────────────────────────────────────┐
│  PostgreSQL 15                              │
│  • Users, Categories, Activities            │
│  Port: 5433:5432                            │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│  Redis 7                                    │
│  • FSM state storage (TTL: 15 min)          │
│  Port: 6379:6379                            │
└─────────────────────────────────────────────┘
```

**Key Principle**: Bot NEVER touches database directly, only through HTTP API!

## Bot Service Structure

```
services/tracker_activity_bot/src/
│
├── main.py                   # 🚀 Entry point
│
├── api/                      # API Layer (Presentation)
│   ├── handlers/            # Message/callback handlers
│   │   ├── start.py         # /start command
│   │   ├── activity/        # Activity recording
│   │   ├── categories/      # Category management
│   │   ├── poll/            # Automatic polls
│   │   └── settings/        # User settings
│   │
│   ├── keyboards/           # Inline keyboards (UI)
│   │   ├── main_menu.py     # Main menu buttons
│   │   ├── time_select.py   # Time selection
│   │   └── ...
│   │
│   ├── states/              # FSM state definitions
│   │   ├── activity.py      # Activity creation states
│   │   ├── category.py      # Category creation states
│   │   └── ...
│   │
│   └── dependencies.py      # DI container
│
├── application/             # Application Layer (Business)
│   ├── services/           # Business services
│   │   ├── scheduler_service.py    # Poll scheduling
│   │   └── fsm_timeout_service.py  # FSM timeout management
│   │
│   └── utils/              # Helper functions
│       ├── time_parser.py  # Parse user time input
│       └── fsm_helpers.py  # FSM utilities
│
├── infrastructure/          # Infrastructure Layer
│   └── http_clients/       # HTTP clients to Data API
│       ├── http_client.py         # Base HTTP client
│       ├── user_service.py        # User API wrapper
│       ├── category_service.py    # Category API wrapper
│       └── activity_service.py    # Activity API wrapper
│
└── core/                    # Core Configuration
    ├── config.py           # Environment settings
    ├── constants.py        # Constants
    └── logging.py          # Logging setup
```

## API Service Structure

```
services/data_postgres_api/src/
│
├── main.py                  # 🚀 Entry point
│
├── api/                     # API Layer (Presentation)
│   ├── v1/                 # Versioned routes
│   │   ├── users.py        # User endpoints
│   │   ├── categories.py   # Category endpoints
│   │   ├── activities.py   # Activity endpoints
│   │   └── user_settings.py
│   │
│   ├── middleware/         # Request middleware
│   │   ├── logging.py      # Request logging
│   │   ├── correlation.py  # Correlation IDs
│   │   └── error_handler.py
│   │
│   └── dependencies.py     # DI for repositories
│
├── application/            # Application Layer (Business)
│   └── services/          # Business logic
│       ├── user_service.py
│       ├── category_service.py
│       ├── activity_service.py
│       └── user_settings_service.py
│
├── infrastructure/         # Infrastructure Layer
│   ├── database/          # Database connection
│   │   └── connection.py
│   │
│   └── repositories/      # Data access
│       ├── base.py               # Generic Repository<T>
│       ├── user_repository.py
│       ├── category_repository.py
│       └── activity_repository.py
│
├── domain/                 # Domain Layer
│   └── models/            # SQLAlchemy models
│       ├── user.py
│       ├── category.py
│       ├── activity.py
│       └── user_settings.py
│
├── schemas/               # Pydantic DTOs
│   ├── user.py
│   ├── category.py
│   └── activity.py
│
└── core/                  # Core Configuration
    ├── config.py
    └── logging.py
```

## Layer Responsibilities

### API Layer
**What**: Presentation layer, handles HTTP/user input
**Responsibilities**:
- Validate requests (Pydantic schemas)
- Route requests to services
- Format responses
- Handle HTTP errors

**Bot Example**: `handlers/activity/activity_creation.py`
**API Example**: `api/v1/activities.py`

### Application Layer
**What**: Business logic layer
**Responsibilities**:
- Business rules enforcement
- Business validation
- Orchestration of repository calls
- NO direct database access

**Bot Example**: `services/scheduler_service.py`
**API Example**: `application/services/activity_service.py`

### Infrastructure Layer
**What**: External integrations
**Responsibilities**:
- Database access (repositories)
- HTTP communication
- External services
- Technical implementations

**Bot Example**: `http_clients/activity_service.py`
**API Example**: `infrastructure/repositories/activity_repository.py`

### Domain Layer
**What**: Core domain entities (API only)
**Responsibilities**:
- Database models
- Domain logic
- Relationships

**Example**: `domain/models/activity.py`

## Key Patterns

### 1. Generic Repository Pattern

**Location**: `services/data_postgres_api/src/infrastructure/repositories/base.py`

**Why**: Eliminates ~100 lines of duplicate CRUD code

**Example**:
```python
# Instead of writing get_by_id, create, update, delete in every repository...
class UserRepository(BaseRepository[User, UserCreate, UserUpdate]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, User)

    # Only add custom methods
    async def get_by_telegram_id(self, tid: int):
        ...
```

**See**: `docs/project-context/code-patterns.md#generic-repository-pattern`

### 2. Service Layer Pattern

**Why**: Business logic separate from API routes and data access

**Example**:
```python
# Route (thin controller)
@router.post("/activities")
async def create_activity(data: ActivityCreate, service: ActivityService):
    return await service.create(data)

# Service (business logic)
class ActivityService:
    async def create(self, data: ActivityCreate):
        # Business validation here
        if data.end_time <= data.start_time:
            raise ValueError("end_time must be after start_time")

        return await self.repository.create(data)
```

**See**: `docs/project-context/code-patterns.md#service-layer-pattern`

### 3. Dependency Injection

**Location**: `services/tracker_activity_bot/src/api/dependencies.py`

**Why**: Centralized service management, easy testing

**Example**:
```python
# In handler
async def handler(callback: CallbackQuery, services: ServiceContainer):
    user = await services.user.get_by_telegram_id(123)
    activity = await services.activity.create({...})
```

**See**: `docs/project-context/code-patterns.md#dependency-injection-pattern`

## Data Flow Example

Let's trace creating an activity:

```
1. User clicks "📝 Записать" button in Telegram
   ↓
2. handlers/activity/activity_creation.py → start_add_activity()
   ↓
3. FSM state set to waiting_for_start_time
   ↓
4. User enters start time
   ↓
5. Handler processes input, sets waiting_for_end_time
   ↓
6. ... (collect end_time, description, category)
   ↓
7. All data collected → Call services.activity.create()
   ↓
8. http_clients/activity_service.py → POST /api/v1/activities
   ↓
9. api/v1/activities.py → create_activity()
   ↓
10. application/services/activity_service.py → create()
    • Validates: end_time > start_time
    • Calculates duration_minutes
    ↓
11. infrastructure/repositories/activity_repository.py → create()
    ↓
12. PostgreSQL: INSERT INTO activities (...)
    ↓
13. Response flows back up the chain
    ↓
14. User sees "✅ Активность сохранена!"
```

## Where to Find Things

### Want to add new handler?
→ `services/tracker_activity_bot/src/api/handlers/`
→ See pattern: `docs/project-context/code-patterns.md#handler-pattern`

### Want to add new API endpoint?
→ `services/data_postgres_api/src/api/v1/`
→ See contract: `docs/api/bot-to-api-contract.md`

### Want to add new database model?
→ `services/data_postgres_api/src/domain/models/`
→ Then: repository, service, schema, route

### Want to understand FSM flow?
→ `services/tracker_activity_bot/src/api/states/`
→ `services/tracker_activity_bot/src/api/handlers/activity/activity_creation.py`
→ See pattern: `docs/project-context/code-patterns.md#fsm-flow-pattern`

### Want to see API endpoints?
→ http://localhost:8080/docs (Swagger UI)
→ `docs/api/endpoints-reference.md`

## Testing Structure

```
tests/
├── integration/              # Service integration tests
│   ├── test_handler_registration.py  # All buttons have handlers?
│   └── test_api_contracts.py         # Bot ↔ API contracts match?
│
└── smoke/                    # Smoke tests
    └── test_docker_health.py # Docker containers healthy?

services/data_postgres_api/tests/
├── unit/                     # Unit tests
│   ├── repositories/
│   └── services/
│
└── contract/                 # API contract tests
    ├── test_users_api.py
    └── test_activities_api.py

services/tracker_activity_bot/tests/
└── unit/                     # Unit tests
    ├── handlers/
    ├── http_client/
    └── services/
```

## Development Commands Cheat Sheet

```bash
# Logs
make logs-bot              # Bot logs
make logs-api              # API logs

# Restart
make restart-bot           # Restart bot only
make restart-api           # Restart API only

# Database
make shell-db              # Open psql
make migrate               # Run migrations
make migrate-create MSG="..." # Create migration

# Testing
make test-unit-docker      # Unit tests
make test-all-docker       # All tests

# Code quality
make lint                  # Lint code
make format                # Format code
```

## Next Steps

Now that you understand the architecture:

1. **Explore Real Code**
   - Read `handlers/start.py` - Simple handler
   - Read `handlers/activity/activity_creation.py` - Complex FSM flow
   - Read `api/v1/activities.py` - API endpoint
   - Read `application/services/activity_service.py` - Business logic

2. **Read Patterns**
   - `docs/project-context/code-patterns.md` - How to write code
   - `docs/project-context/anti-patterns.md` - What NOT to do

3. **Try Making Changes**
   - Add log statement to handler
   - Restart bot: `make restart-bot`
   - Test in Telegram
   - Check logs: `make logs-bot`

4. **Pick Good First Issue**
   - Look for `good-first-issue` label
   - Start small (docs, tests, minor bug)
   - Follow existing patterns

## Congratulations! 🎉

You've completed the onboarding! You now know:

- ✅ How services communicate (Bot → HTTP → API → DB)
- ✅ Where code lives (layer architecture)
- ✅ Key patterns (Generic Repository, Service Layer, DI)
- ✅ How to find things (handlers, endpoints, models)
- ✅ How to develop (logs, restart, test)

**Ready to contribute?** Start coding! 🚀

---

**Last Updated**: 2025-11-08
**Est. Time**: 20 minutes

**Further Reading**:
- [Architecture Details](../../ARCHITECTURE.md)
- [Testing Guide](../../TESTING.md)
- [API Documentation](../api/)
- [Code Patterns](../project-context/code-patterns.md)
