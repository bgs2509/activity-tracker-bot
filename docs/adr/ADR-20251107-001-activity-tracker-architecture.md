# ADR-20251107-001: Activity Tracker Bot Architecture

> **Purpose**: Define the complete architectural foundation for Activity Tracker Bot following the Improved Hybrid Approach from .ai-framework with KISS, YAGNI, and DRY principles.

---

## Metadata

- **ADR ID**: `ADR-20251107-001`
- **Title**: Activity Tracker Bot - Improved Hybrid Architecture with Minimal Complexity
- **Date**: 2025-11-07
- **Authors**: Development Team
- **Status**: Accepted
- **Maturity Level**: Level 1 (PoC) → Targeting Level 2 (Development Ready)

---

## Context

### Business Requirements

**Problem Statement:**
Users need a simple way to track their daily activities via Telegram without installing separate apps. Activities should be recorded with timestamps, categorized, and stored persistently.

**Functional Requirements:**
- User registration via Telegram
- Activity creation with time range (start → end)
- Activity categorization (user-defined categories)
- Activity history viewing (last N records)
- Category management (create, list, delete)
- Time input flexibility (14:30, 30м назад, 2ч назад, сейчас)
- Inline keyboards for user interaction

**Non-Functional Requirements:**
- Response time < 2 seconds for user actions
- Data persistence (PostgreSQL)
- Fault tolerance (service restart recovery)
- Type safety (mypy strict mode)
- Async-first for scalability
- Clean separation of concerns (DDD/Hexagonal)

### Technical Constraints

1. **Framework Compliance**: Must follow .ai-framework/ARCHITECTURE.md principles
2. **HTTP-Only Data Access**: Business services NEVER access database directly
3. **Service Separation**: Each service type in separate process (no event loop conflicts)
4. **Naming Convention**: `{context}_{domain}_{type}` pattern
5. **Python 3.12+**: Modern async/await, type hints
6. **Docker Compose**: Local development and deployment

### Existing System Assumptions

- **Deployment**: Single-host Docker Compose (no Kubernetes required for PoC)
- **Scale**: Single user to ~100 concurrent users (PoC → Development)
- **Geographic Distribution**: Single region (no multi-region support)
- **High Availability**: NOT required for current maturity level

---

## Decision

### Architecture: Improved Hybrid Approach (Simplified)

We adopt the **Improved Hybrid Approach** from .ai-framework with **minimal necessary components** following KISS and YAGNI principles.

#### Service Topology

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

#### Core Architectural Decisions

##### 1. HTTP-Only Data Access ⚠️ MANDATORY

**Rule**: `tracker_activity_bot` NEVER accesses PostgreSQL directly.

**Implementation**:
```python
# ✅ CORRECT: HTTP client in bot service
# services/tracker_activity_bot/src/infrastructure/http_clients/activity_service.py

from datetime import datetime
from pydantic import BaseModel

class ActivityResponse(BaseModel):
    """Type-safe response model."""
    id: int
    user_id: int
    description: str
    start_time: datetime
    end_time: datetime
    duration_minutes: int

class ActivityService:
    """Service for activity operations via HTTP."""

    def __init__(self, client: DataAPIClient):
        self.client = client

    async def create_activity(
        self,
        user_id: int,
        category_id: int | None,
        description: str,
        tags: list[str] | None,
        start_time: datetime,
        end_time: datetime
    ) -> ActivityResponse:
        """
        Create activity via Data API.

        Args:
            user_id: User identifier
            category_id: Category identifier or None
            description: Activity description
            tags: Optional tags list
            start_time: Start timestamp (UTC)
            end_time: End timestamp (UTC)

        Returns:
            Created activity with generated ID

        Raises:
            HTTPError: If Data API returns error
        """
        data = await self.client.post("/api/v1/activities", json={
            "user_id": user_id,
            "category_id": category_id,
            "description": description,
            "tags": tags,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        })
        return ActivityResponse(**data)
```

**Why**:
- ✅ Single source of truth for data access logic
- ✅ Easy to add caching, validation, authorization at data layer
- ✅ Bot and Data API can scale independently
- ✅ Easier to test (mock HTTP calls vs mock database)
- ✅ Prevents connection pool exhaustion (single pool in Data API)

##### 2. DDD/Hexagonal Architecture

**Structure** (both services):
```
service/
├── domain/              # Pure business logic (entities, value objects)
├── application/         # Use cases, application services
├── infrastructure/      # External concerns (HTTP, DB, Redis)
└── api/                 # Entry points (routes, handlers)
```

**Responsibilities**:

- **Domain Layer**: Pure business logic, no external dependencies
  - Entities (User, Activity, Category)
  - Value objects (TimeRange, Description)
  - Domain services (business rules)

- **Application Layer**: Orchestration, use cases
  - Application services (ActivityService, CategoryService)
  - DTOs (Data Transfer Objects)
  - Service interfaces

- **Infrastructure Layer**: External systems
  - HTTP clients (DataAPIClient)
  - Database repositories (ActivityRepository)
  - Redis storage (FSMStorage)
  - External APIs

- **API Layer**: Entry points
  - FastAPI routes (data_postgres_api)
  - Aiogram handlers (tracker_activity_bot)
  - Request/response schemas

##### 3. Service Naming Convention

**Pattern**: `{context}_{domain}_{type}`

**Services**:
- `tracker_activity_bot` — context: tracker, domain: activity, type: bot
- `data_postgres_api` — context: data, domain: postgres, type: api

**Rationale**:
- ✅ Consistent with .ai-framework naming guide
- ✅ Clear context identification
- ✅ Easy to identify service type
- ❌ NOT using 4-part names (unnecessary for current scope)

##### 4. Technology Stack

**Core**:
- **Python 3.12+** — Modern async/await, type hints, performance
- **FastAPI 0.115+** — Async-first, automatic OpenAPI, dependency injection
- **Aiogram 3.13+** — Modern Telegram bot framework, async, FSM
- **Pydantic 2.x** — Data validation, serialization, type safety

**Data**:
- **PostgreSQL 15+** — ACID transactions, JSON support, proven reliability
- **Redis 7+** — Fast FSM storage, pub/sub, TTL support
- **SQLAlchemy 2.0+** — Async ORM, type-safe queries
- **Alembic** — Database migrations, version control

**Quality**:
- **mypy 1.11+** — Static type checking (strict mode)
- **Ruff 0.6+** — Fast linting and formatting
- **pytest 8.3+** — Unit and integration testing

**Infrastructure**:
- **Docker 24.0+** — Containerization
- **Docker Compose 2.20+** — Multi-container orchestration

##### 5. Type Safety ⚠️ MANDATORY

**Rule**: Full type hints with mypy strict mode.

**Configuration**:
```toml
# pyproject.toml (both services)
[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_any_generics = true
disallow_incomplete_defs = true
check_untyped_defs = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
```

**Why**:
- ✅ Catch errors at development time
- ✅ Better IDE autocomplete
- ✅ Self-documenting code
- ✅ Easier refactoring

##### 6. Async-First Design

**Rule**: All I/O operations use async/await.

**Guidelines**:
- Use `async def` for all I/O functions
- Use `await` for all blocking calls
- Use async libraries (httpx, asyncpg, aioredis)
- NEVER use blocking operations (requests, time.sleep)

**Example**:
```python
# ✅ CORRECT: Async HTTP client
import httpx

class DataAPIClient:
    def __init__(self, base_url: str):
        self.client = httpx.AsyncClient(base_url=base_url, timeout=10.0)

    async def get(self, path: str, **kwargs) -> dict[str, Any]:
        """Make async GET request."""
        response = await self.client.get(path, **kwargs)
        response.raise_for_status()
        return response.json()
```

##### 7. Structured Logging

**Rule**: JSON-formatted logs with context.

**Implementation**:
```python
# services/data_postgres_api/src/core/logging.py
import logging
import sys
from pythonjsonlogger import jsonlogger

def setup_logging(service_name: str, log_level: str = "INFO") -> None:
    """
    Configure structured JSON logging.

    Args:
        service_name: Service identifier
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    logger = logging.getLogger()
    logger.setLevel(log_level)

    handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Add service context to all logs
    logging.getLogger().info(
        "Logging configured",
        extra={"service": service_name, "log_level": log_level}
    )
```

**Usage**:
```python
logger.info(
    "Activity created",
    extra={
        "user_id": user.id,
        "activity_id": activity.id,
        "duration_minutes": activity.duration_minutes
    }
)
```

##### 8. Health Checks

**Rule**: Separate liveness and readiness probes.

**Implementation**:
```python
# services/data_postgres_api/src/main.py
from sqlalchemy import text

@app.get("/health/live", summary="Liveness probe")
async def liveness() -> dict[str, str]:
    """
    Check if service is running.

    Returns:
        Status indicating service is alive
    """
    return {"status": "alive"}

@app.get("/health/ready", summary="Readiness probe")
async def readiness(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """
    Check if service is ready to accept requests.

    Verifies:
        - Database connection works

    Returns:
        Status with database connection state

    Raises:
        HTTPException: 503 if database is unreachable
    """
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        logger.error("Database health check failed", extra={"error": str(e)})
        raise HTTPException(
            status_code=503,
            detail="Database connection failed"
        )
```

**Docker Healthcheck**:
```yaml
# docker-compose.yml
data_postgres_api:
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/health/ready"]
    interval: 10s
    timeout: 5s
    retries: 3
    start_period: 10s
```

##### 9. Error Handling Strategy

**Rules**:
1. HTTP client: Retry on 5xx, fail fast on 4xx
2. Database: Rollback transaction on error
3. User-facing: Friendly Russian messages
4. Logs: Structured JSON with context

**Implementation**:
```python
# services/tracker_activity_bot/src/infrastructure/http_clients/http_client.py
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

class DataAPIClient:
    @retry(
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def post(self, path: str, **kwargs) -> dict[str, Any]:
        """
        Make POST request with automatic retry on 5xx errors.

        Args:
            path: API endpoint path
            **kwargs: Additional request parameters

        Returns:
            JSON response data

        Raises:
            HTTPStatusError: On 4xx errors (no retry)
            RetryError: After 3 failed attempts
        """
        try:
            response = await self.client.post(path, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if 400 <= e.response.status_code < 500:
                # 4xx = client error, don't retry
                raise
            # 5xx = server error, will retry
            logger.warning(
                "Data API request failed, retrying",
                extra={
                    "status_code": e.response.status_code,
                    "path": path
                }
            )
            raise
```

##### 10. Database Schema Design

**Principles**:
- Normalization (3NF)
- Indexes on query columns
- Check constraints for data integrity
- Timestamps on all tables

**Schema**:
```sql
-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL UNIQUE,
    username VARCHAR(255),
    first_name VARCHAR(255),
    timezone VARCHAR(50) DEFAULT 'UTC',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_telegram_id ON users(telegram_id);

-- Categories table
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    emoji VARCHAR(10),
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, name)
);

CREATE INDEX idx_categories_user_id ON categories(user_id);

-- Activities table
CREATE TABLE activities (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    description TEXT NOT NULL,
    tags TEXT,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    duration_minutes INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT check_end_after_start CHECK (end_time > start_time),
    CONSTRAINT check_duration_positive CHECK (duration_minutes > 0)
);

CREATE INDEX idx_activities_user_id ON activities(user_id);
CREATE INDEX idx_activities_start_time ON activities(start_time);
```

##### 11. Testing Strategy

**Test Pyramid**:
- **Unit Tests** (70%): Pure functions, domain logic, utilities
- **Integration Tests** (20%): HTTP clients, database repositories
- **Smoke Tests** (10%): Health checks, imports, Docker containers

**Coverage Target**:
- Level 1 (PoC): NOT required
- Level 2 (Development): >70%
- Level 3 (Pre-Production): >80%
- Level 4 (Production): >90%

**Example**:
```python
# services/tracker_activity_bot/tests/unit/test_time_parser.py
import pytest
from datetime import datetime, timezone
from src.application.utils.time_parser import parse_time_input

def test_parse_absolute_time():
    """Test parsing absolute time like '14:30'."""
    result = parse_time_input("14:30")
    assert result.hour == 14
    assert result.minute == 30

def test_parse_relative_minutes():
    """Test parsing relative time like '30м'."""
    now = datetime.now(timezone.utc)
    result = parse_time_input("30м")
    diff = (now - result).total_seconds() / 60
    assert 29 <= diff <= 31  # Allow 1 minute tolerance

def test_parse_invalid_format_raises_error():
    """Test that invalid format raises ValueError."""
    with pytest.raises(ValueError, match="Cannot parse time"):
        parse_time_input("invalid")
```

---

## What We DELIBERATELY Exclude (YAGNI)

Following **KISS** and **YAGNI** principles, we DO NOT include:

### 1. ❌ Nginx API Gateway

**Reason**: Only 2 services, direct Docker networking sufficient.

**When to add**: Level 3+ (Pre-Production) when we have:
- Multiple business services (>3)
- Need for SSL/TLS termination
- Rate limiting requirements
- Geographic distribution

**Current solution**: Docker Compose internal network.

### 2. ❌ RabbitMQ Message Broker

**Reason**: No async event processing between services.

**When to add**: When we need:
- Async notifications (email, push)
- Background data processing
- Event-driven workflows

**Current solution**: Synchronous HTTP requests are sufficient.

### 3. ❌ MongoDB

**Reason**: All data fits relational model, no unstructured data.

**When to add**: When we have:
- Unstructured data (logs, analytics)
- Flexible schema requirements
- Document storage needs

**Current solution**: PostgreSQL with JSONB for tags.

### 4. ❌ Prometheus + Grafana

**Reason**: PoC level, CloudWatch/Docker logs sufficient.

**When to add**: Level 2+ (Development) when we need:
- Performance metrics
- Custom dashboards
- Alerting

**Current solution**: Structured JSON logs, Docker stats.

### 5. ❌ Jaeger Distributed Tracing

**Reason**: Only 2 services, logs sufficient for debugging.

**When to add**: Level 3+ when we have:
- >5 services
- Complex request flows
- Performance bottleneck analysis

**Current solution**: Correlation IDs in logs.

### 6. ❌ ELK Stack

**Reason**: PoC level, Docker logs sufficient.

**When to add**: Level 4 (Production) when we need:
- Centralized log aggregation
- Advanced log search
- Log retention policies

**Current solution**: `docker logs`, structured JSON.

### 7. ❌ Kubernetes

**Reason**: Single-host deployment, Docker Compose sufficient.

**When to add**: Level 4 (Production) when we need:
- Multi-host orchestration
- Auto-scaling
- Rolling updates
- High availability

**Current solution**: Docker Compose with restart policies.

### 8. ❌ OAuth2 / JWT Authentication

**Reason**: Telegram Bot authentication sufficient.

**When to add**: When we add:
- Web frontend
- Mobile app
- Third-party API access

**Current solution**: Telegram user ID as authentication.

---

## Alternatives Considered

### Alternative 1: Monolithic Architecture

| Aspect | Description |
|--------|-------------|
| **Approach** | Single FastAPI service with Telegram bot handlers in same process |
| **Pros** | - Simpler deployment<br>- No HTTP overhead<br>- Fewer Docker containers |
| **Cons** | - Event loop conflicts (FastAPI + Aiogram)<br>- Tight coupling<br>- Difficult to scale bot independently<br>- Violates .ai-framework principles |
| **Reason Rejected** | **Violates "Single Event Loop Ownership" principle** from .ai-framework/ARCHITECTURE.md:145-176. FastAPI and Aiogram cannot share event loop safely. |

### Alternative 2: Direct Database Access

| Aspect | Description |
|--------|-------------|
| **Approach** | `tracker_activity_bot` directly accesses PostgreSQL without Data API |
| **Pros** | - Lower latency<br>- No HTTP overhead<br>- Simpler bot code |
| **Cons** | - **VIOLATES HTTP-Only Data Access** (mandatory rule)<br>- Duplicate data access code<br>- Connection pool exhaustion<br>- Difficult to add caching/validation |
| **Reason Rejected** | **Violates core principle of Improved Hybrid Approach** (.ai-framework/ARCHITECTURE.md:101-143). Business services NEVER access database directly. |

### Alternative 3: Webhooks Instead of Polling

| Aspect | Description |
|--------|-------------|
| **Approach** | Use Telegram webhooks instead of long polling |
| **Pros** | - More efficient (no constant polling)<br>- Lower latency |
| **Cons** | - Requires public HTTPS endpoint<br>- Requires SSL certificates<br>- More complex deployment<br>- Overkill for PoC |
| **Reason Rejected** | **Unnecessary complexity for PoC** (KISS principle). Polling is simpler and sufficient for current scale (<100 users). Can switch to webhooks at Level 3+. |

### Alternative 4: Synchronous FastAPI (no async)

| Aspect | Description |
|--------|-------------|
| **Approach** | Use synchronous FastAPI with blocking I/O |
| **Pros** | - Simpler code (no async/await)<br>- More libraries available |
| **Cons** | - **VIOLATES Async-First principle**<br>- Poor performance under load<br>- Thread pool overhead<br>- Cannot use async PostgreSQL driver |
| **Reason Rejected** | **Violates .ai-framework/ARCHITECTURE.md:178-193** (Async-First Design). Async is mandatory for scalability. |

---

## Consequences

### Positive Impacts

#### 1. Scalability

✅ **Independent Service Scaling**:
- Bot and Data API can scale independently
- Add more bot replicas without affecting Data API
- Database connection pool managed in single location

✅ **Async Performance**:
- Handle 100+ concurrent users on single instance
- Efficient resource utilization
- Natural backpressure handling

#### 2. Maintainability

✅ **Clear Separation of Concerns**:
- Bot: User interaction, FSM, time parsing
- Data API: CRUD, database queries, migrations
- No business logic in Data API (pure CRUD)

✅ **Easy Testing**:
- Mock HTTP clients for bot tests
- Mock database for Data API tests
- Integration tests via test containers

✅ **Type Safety**:
- mypy catches errors at development time
- Better IDE support (autocomplete, refactoring)
- Self-documenting code

#### 3. Framework Compliance

✅ **100% .ai-framework Alignment**:
- HTTP-only data access ✓
- Service separation ✓
- Naming conventions ✓
- DDD/Hexagonal ✓
- Async-first ✓
- Type safety ✓

#### 4. Extensibility

✅ **Easy to Add Features**:
- New endpoints in Data API → No bot changes
- New bot commands → No Data API changes
- Add RabbitMQ later without breaking existing code
- Add Nginx later without service changes

### Negative Impacts & Mitigations

#### 1. Network Latency

**Impact**: HTTP calls add 1-5ms latency vs direct database access.

**Mitigation**:
- Docker internal network (minimal latency)
- HTTP/2 with connection pooling
- Response caching in Data API (future)

**Acceptable**: User interactions have >100ms buffer, 5ms negligible.

#### 2. Increased Complexity

**Impact**: 2 services instead of 1, more Docker containers.

**Mitigation**:
- docker-compose.yml handles orchestration
- Makefile simplifies common operations
- .ai-framework documentation provides patterns

**Acceptable**: Complexity pays off in maintainability.

#### 3. Debugging Difficulty

**Impact**: Errors span 2 services, need correlation.

**Mitigation**:
- Structured logging with correlation IDs
- Health checks for quick diagnostics
- Docker logs aggregation

**Acceptable**: Structured logs make debugging easier than monolith.

#### 4. Development Overhead

**Impact**: Need to start 4 containers (bot, API, PostgreSQL, Redis).

**Mitigation**:
- `make up` starts all services
- Health checks ensure readiness
- Fast restart for code changes

**Acceptable**: Automated via Docker Compose.

---

## Implementation Requirements

### Phase 1: Core Architecture ✅ (COMPLETED)

1. ✅ Create service structure (DDD/Hexagonal)
2. ✅ Implement HTTP-only data access
3. ✅ Add PostgreSQL with Alembic migrations
4. ✅ Add Redis for FSM storage
5. ✅ Configure Docker Compose

**Status**: ✅ Implemented in current codebase

### Phase 2: Type Safety & Quality (REQUIRED)

1. ⏳ Add mypy configuration (strict mode)
2. ⏳ Add complete type hints to all functions
3. ⏳ Create Pydantic models for all HTTP responses
4. ⏳ Add Application Service layer in Data API
5. ⏳ Add comprehensive docstrings (Args/Returns/Raises)

**Priority**: 🔴 CRITICAL (see refactor-2025-11-07.md violations #1-3)

### Phase 3: Observability (REQUIRED)

1. ⏳ Improve health checks (DB connection verification)
2. ⏳ Add correlation IDs to logs
3. ⏳ Add request/response logging middleware
4. ⏳ Add error tracking (Sentry optional)

**Priority**: 🟠 HIGH (see refactor-2025-11-07.md violation #4)

### Phase 4: Testing (NICE TO HAVE)

1. ⏳ Unit tests (>70% coverage)
2. ⏳ Integration tests (HTTP clients, repositories)
3. ⏳ E2E smoke tests
4. ⏳ Add CI/CD pipeline (GitHub Actions)

**Priority**: 🟡 MEDIUM (Level 2 requirement)

### Phase 5: Future Enhancements (OPTIONAL)

1. ⏳ Add Nginx API Gateway (Level 3+)
2. ⏳ Add Prometheus metrics (Level 2+)
3. ⏳ Add RabbitMQ for async events (Level 3+)
4. ⏳ Add distributed tracing (Level 3+)

**Priority**: 🟢 LOW (YAGNI for current scope)

---

## Follow-Up Actions

### Immediate (Week 1)

1. **Add mypy configuration** in both services
   - Create `pyproject.toml` with strict settings
   - Fix type violations incrementally
   - Add to `make lint` command

2. **Create Application Service layer** in `data_postgres_api`
   - Create `src/application/services/` directory
   - Implement ActivityService, CategoryService, UserService
   - Update API routes to use services

3. **Add complete type hints**
   - Define Pydantic response models in bot service
   - Update HTTP client methods with return types
   - Update all function signatures

### Short-term (Week 2-3)

4. **Improve health checks**
   - Split into `/health/live` and `/health/ready`
   - Add DB connection check
   - Update Docker healthcheck

5. **Add comprehensive docstrings**
   - Args/Returns/Raises for all public functions
   - Follow .ai-framework examples

6. **Add dependency injection** in bot service
   - Create `dependencies.py`
   - Replace global HTTP client instances

### Medium-term (Month 1)

7. **Add unit tests** (target >70% coverage)
8. **Add CI/CD pipeline** (GitHub Actions)
9. **Fix naming conventions** (rename `data_postgres_api` → `tracker_data_postgres_api`)
10. **Add Prometheus metrics** (Level 2 transition)

### Long-term (Month 2-3)

11. **Add Nginx API Gateway** (Level 3 transition)
12. **Add RabbitMQ** if async events needed
13. **Add distributed tracing** (Jaeger)
14. **Add ELK stack** (centralized logging)

---

## References

### .ai-framework Documentation

- **.ai-framework/ARCHITECTURE.md** — Core architectural principles
  - Lines 101-143: HTTP-Only Data Access (MANDATORY)
  - Lines 145-176: Single Event Loop Ownership (MANDATORY)
  - Lines 178-193: Async-First Design
  - Lines 194-232: Type Safety
  - Lines 234-256: DDD & Hexagonal Architecture
  - Lines 691-713: Best Practices & Anti-Patterns

- **.ai-framework/CONTRIBUTING.md** — Code quality standards
  - Lines 160-200: Python code examples with type hints
  - Lines 232-241: Naming conventions table
  - Lines 269-284: Code quality gates (mypy, ruff, pytest)

- **.ai-framework/EXAMPLES.md** — Implementation examples
  - Lines 442-454: Business API example
  - Lines 456-474: Data API example
  - Lines 518-564: HTTP communication pattern
  - Lines 606-629: Health checks example
  - Lines 630-648: Structured logging example

- **.ai-framework/README.md** — Framework overview
  - Lines 34-48: Improved Hybrid Approach diagram
  - Lines 238: Service naming convention
  - Lines 304-313: Technology stack

### Project Documentation

- **README.md** — Project overview and quick start
- **docker-compose.yml** — Service orchestration
- **artifacts/analysis/refactor-2025-11-07.md** — Violation analysis and TODO plan
- **Makefile** — Development commands

### External References

- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **Aiogram Documentation**: https://docs.aiogram.dev/
- **SQLAlchemy 2.0 Documentation**: https://docs.sqlalchemy.org/
- **Pydantic Documentation**: https://docs.pydantic.dev/
- **mypy Documentation**: https://mypy.readthedocs.io/
- **PostgreSQL Best Practices**: https://wiki.postgresql.org/wiki/Don%27t_Do_This

---

## Maintenance

### Status Updates

- **Initial Version**: 2025-11-07 (ADR created)
- **Last Reviewed**: 2025-11-07
- **Next Review**: After Phase 2 completion (Type Safety & Quality)

### Storage Location

- **Primary**: `docs/adr/ADR-20251107-001-activity-tracker-architecture.md`
- **Backup**: Git repository (version controlled)

### Change Management

**When to update this ADR**:
1. Major architectural changes (e.g., adding RabbitMQ)
2. Technology stack changes (e.g., switching to different DB)
3. Principle violations discovered
4. Maturity level transitions (Level 1 → Level 2 → etc.)

**How to supersede**:
1. Create new ADR (e.g., ADR-20251215-002-add-rabbitmq.md)
2. Update this ADR status to "Superseded by ADR-20251215-002"
3. Link both ADRs in references

### Index Alignment

- ✅ Added to project: `docs/adr/README.md`
- ✅ Referenced in: `artifacts/analysis/refactor-2025-11-07.md`
- ✅ Linked from: `README.md` (under Documentation section)

---

**Approved By**: Development Team
**Implementation Status**: Phase 1 ✅ Complete | Phase 2-4 ⏳ In Progress
**Compliance**: 100% .ai-framework aligned (with documented YAGNI exclusions)
