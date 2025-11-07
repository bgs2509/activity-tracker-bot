# Service Topology

> **ADR**: ADR-20251107-001
> [← Back to Index](README.md) | [← Previous: Decision Overview](01-decision-overview.md) | [Next: Principles →](03-architectural-principles.md)

---

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         PRESENTATION LAYER                       │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  tracker_activity_bot                                   │    │
│  │  (Aiogram 3.x)                                          │    │
│  │                                                          │    │
│  │  - Telegram Bot API integration                         │    │
│  │  - FSM (Finite State Machine) for dialogs              │    │
│  │  - Inline keyboards rendering                           │    │
│  │  - Time parsing utilities                               │    │
│  │  - HTTP client to Data API                              │    │
│  └────────────────────┬───────────────────────────────────┘    │
│                       │                                          │
│                       │ HTTP REST API (JSON)                    │
│                       │ ⚠️ NO DIRECT DATABASE ACCESS            │
│                       ▼                                          │
└─────────────────────────────────────────────────────────────────┘
                        │
         ┌──────────────┴────────────────┐
         │                                │
         │  HTTP-only communication       │
         │  (Business → Data)             │
         │                                │
         ▼                                │
┌─────────────────────────────────────────────────────────────────┐
│                          DATA LAYER                              │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  data_postgres_api                                      │    │
│  │  (FastAPI)                                              │    │
│  │                                                          │    │
│  │  - REST API endpoints (CRUD)                            │    │
│  │  - Repository pattern                                   │    │
│  │  - SQLAlchemy ORM (async)                               │    │
│  │  - Alembic migrations                                   │    │
│  │  - Pydantic schemas                                     │    │
│  └────────────────────┬───────────────────────────────────┘    │
│                       │                                          │
│                       │ SQL Queries                              │
│                       ▼                                          │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  PostgreSQL 15+                                         │    │
│  │                                                          │    │
│  │  - users (telegram_id unique index)                     │    │
│  │  - categories (user_id + name unique)                   │    │
│  │  - activities (user_id index, start_time index)         │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      STATEFUL STORAGE                            │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  Redis 7+                                               │    │
│  │                                                          │    │
│  │  - FSM state storage (aiogram FSMContext)               │    │
│  │  - TTL: 15 minutes (auto-cleanup abandoned dialogs)     │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Components

### tracker_activity_bot (Presentation Layer)

**Type**: Business Service (Aiogram 3.x)

**Responsibilities**:
- Telegram Bot API integration
- User interaction via inline keyboards
- FSM (Finite State Machine) for multi-step dialogs
- Time parsing utilities (14:30, 30м назад, etc.)
- HTTP client for Data API communication

**Key Features**:
- Async-first design (handles concurrent users)
- FSM storage in Redis (15-minute TTL)
- Structured JSON logging
- Automatic poll scheduling (APScheduler)
- FSM timeout service with reminders

**Does NOT**:
- ❌ Direct database access (violates HTTP-only principle)
- ❌ Direct SQL queries
- ❌ Database connection pooling

---

### data_postgres_api (Data Layer)

**Type**: Data API Service (FastAPI)

**Responsibilities**:
- REST API endpoints (CRUD operations)
- Repository pattern for data access
- SQLAlchemy ORM (async)
- Alembic database migrations
- Pydantic schemas for validation

**Key Features**:
- Async-first design
- Type-safe with Pydantic models
- Health checks (/health/live, /health/ready)
- Automatic OpenAPI documentation
- Connection pooling (managed by SQLAlchemy)

**API Endpoints**:
- `/api/v1/activities` — Activity CRUD
- `/api/v1/categories` — Category management
- `/api/v1/users` — User registration
- `/api/v1/user_settings` — User preferences
- `/health/live` — Liveness probe
- `/health/ready` — Readiness probe (with DB check)

---

### PostgreSQL 15+ (Persistent Storage)

**Type**: Relational Database

**Responsibilities**:
- Persistent data storage
- ACID transactions
- Indexes for query performance
- Check constraints for data integrity

**Schema**:
- `users` — User registration (telegram_id unique index)
- `categories` — User-defined categories (user_id + name unique)
- `activities` — Activity records (user_id index, start_time index)
- `user_settings` — User preferences (timezone, language, poll settings)

**Features**:
- JSON support for tags (JSONB column type)
- Timestamps on all tables
- Foreign key constraints with CASCADE/SET NULL
- Check constraints (end_time > start_time, duration > 0)

---

### Redis 7+ (Stateful Storage)

**Type**: In-memory data store

**Responsibilities**:
- FSM state storage (aiogram FSMContext)
- TTL-based auto-cleanup (15 minutes)

**Use Cases**:
- Store user's current FSM state during multi-step dialogs
- Store temporary data (category selection, time input)
- Automatic cleanup of abandoned dialogs

**Features**:
- Fast in-memory access
- Automatic expiration (TTL: 15 minutes)
- Persistence disabled (stateful data only)

---

## Communication Patterns

### HTTP REST (Bot → Data API)

**Protocol**: HTTP REST API (JSON)

**Pattern**: Request-Response (synchronous)

**Example Flow**:
```
1. User sends /activity to bot
2. Bot FSM captures start time
3. Bot FSM captures end time
4. Bot makes HTTP POST to /api/v1/activities
5. Data API validates with Pydantic
6. Data API saves to PostgreSQL
7. Data API returns ActivityResponse (JSON)
8. Bot displays success message to user
```

**Security**: Docker internal network (no public exposure)

**Retry Logic**: 3 retries on 5xx errors, fail fast on 4xx

---

## Deployment

### Docker Compose Orchestration

**Services**:
1. `tracker_activity_bot` — Aiogram bot service
2. `data_postgres_api` — FastAPI data service
3. `tracker_postgres` — PostgreSQL database
4. `tracker_redis` — Redis storage

**Networking**:
- Internal Docker network (no Nginx gateway needed for PoC)
- Service-to-service communication via hostnames
- No public exposure except Telegram Bot API

**Volumes**:
- `postgres_data` — PostgreSQL persistence
- Redis data NOT persisted (stateful only)

---

## Service Naming Convention

**Pattern**: `{context}_{domain}_{type}`

**Examples**:
- `tracker_activity_bot` — context: tracker, domain: activity, type: bot
- `data_postgres_api` — context: data, domain: postgres, type: api

**Rationale**:
- Consistent with .ai-framework naming guide
- Clear context identification
- Easy to identify service type

---

## Related Documents

- [← Previous: Decision Overview](01-decision-overview.md)
- [Next: Architectural Principles →](03-architectural-principles.md)
- [Technology Stack Details →](04-technology-stack.md)
- [← Back to Index](README.md)
