# Technology Stack

> **ADR**: ADR-20251107-001  
> [← Back to Index](README.md) | [← Previous: Principles](03-architectural-principles.md) | [Next: YAGNI →](05-yagni-exclusions.md)

---

## Core Technologies

### Python 3.12+
**Why**: Modern async/await, type hints, performance improvements, pattern matching

**Key Features Used**:
- Async/await syntax
- Type hints with `|` union operator
- Structural pattern matching
- Improved error messages

---

### FastAPI 0.115+
**Why**: Async-first, automatic OpenAPI, dependency injection, high performance

**Key Features**:
- Async request handlers
- Automatic validation (Pydantic)
- OpenAPI/Swagger documentation
- Dependency injection system
- ASGI server support (Uvicorn)

---

### Aiogram 3.13+
**Why**: Modern Telegram bot framework, async, FSM support, type-safe

**Key Features**:
- Async-first design
- FSM (Finite State Machine) for dialogs
- Redis storage support
- Middleware system
- Type-safe handlers

---

### Pydantic 2.x
**Why**: Data validation, serialization, type safety

**Use Cases**:
- Request/response models
- Configuration management
- Type validation at runtime
- JSON serialization

---

## Data Layer

### PostgreSQL 15+
**Why**: ACID transactions, JSON support (JSONB), proven reliability, excellent performance

**Features Used**:
- JSONB for flexible data (tags)
- Indexes for query performance
- Check constraints for data integrity
- Foreign key constraints
- Row-level security (future)

---

### Redis 7+
**Why**: Fast in-memory storage, TTL support, persistence optional

**Use Cases**:
- FSM state storage (aiogram FSMContext)
- TTL-based auto-cleanup (15 minutes)
- Fast session data access

---

### SQLAlchemy 2.0+
**Why**: Async ORM, type-safe queries, migration support

**Features**:
- Async query execution
- ORM models with relationships
- Transaction management
- Connection pooling

---

### Alembic
**Why**: Database migration management, version control for schema

**Features**:
- Auto-generate migrations from models
- Up/down migration support
- Branch merging for team collaboration

---

## Quality Tools

### mypy 1.11+
**Why**: Static type checking, catch errors before runtime

**Configuration**: Strict mode enabled

---

### Ruff 0.6+
**Why**: Fast Python linter/formatter (100x faster than pylint)

**Features**:
- Linting (replaces flake8, pylint)
- Formatting (replaces black)
- Auto-fix capabilities

---

### pytest 8.3+
**Why**: Modern testing framework, fixtures, parametrization

**Features**:
- Async test support (pytest-asyncio)
- Fixtures for DI in tests
- Parametrized tests
- Coverage reporting

---

## Infrastructure

### Docker 24.0+
**Why**: Containerization, consistent environments, isolation

---

### Docker Compose 2.20+
**Why**: Multi-container orchestration, local development

**Services Managed**:
- tracker_activity_bot
- data_postgres_api
- tracker_postgres
- tracker_redis

---

## Decision Rationale

| Requirement | Technology | Why This Choice |
|-------------|-----------|-----------------|
| Async-first | Python 3.12+ asyncio | Native async support, mature ecosystem |
| Web framework | FastAPI | Automatic validation, OpenAPI, async, type-safe |
| Bot framework | Aiogram 3.x | Modern, async, FSM support, type-safe |
| Database | PostgreSQL 15+ | ACID, JSONB, reliability, performance |
| Cache/FSM | Redis 7+ | Fast, TTL support, in-memory |
| ORM | SQLAlchemy 2.0 | Async support, type-safe, mature |
| Validation | Pydantic 2.x | Type-safe, fast, good DX |
| Type checking | mypy | Industry standard, strict mode |
| Linting | Ruff | Fast, comprehensive, auto-fix |
| Testing | pytest | Async support, fixtures, mature |
| Containers | Docker + Compose | Standard, easy orchestration |

---

## Related Documents

- [← Previous: Architectural Principles](03-architectural-principles.md)
- [Next: YAGNI Exclusions →](05-yagni-exclusions.md)
- [Implementation: Type Safety →](implementation/phase-1-2.md)
- [← Back to Index](README.md)
