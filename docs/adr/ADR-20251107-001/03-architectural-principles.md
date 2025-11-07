# Architectural Principles

> **ADR**: ADR-20251107-001  
> [← Back to Index](README.md) | [← Previous: Topology](02-service-topology.md) | [Next: Tech Stack →](04-technology-stack.md)

---

## Overview

This document outlines the 11 core architectural principles that guide the Activity Tracker Bot implementation. Each principle is explained with its rationale and enforcement mechanisms.

---

## 1. HTTP-Only Data Access ⚠️ MANDATORY

**Rule**: `tracker_activity_bot` NEVER accesses PostgreSQL directly.

**Why**:
- Single source of truth for data access logic
- Easy to add caching, validation, authorization at data layer
- Prevents connection pool exhaustion (single pool in Data API)
- Services can scale independently

**Enforcement**:
- Code review checklist
- No database credentials in bot service environment
- See [Anti-Pattern: Direct Database Access](antipatterns/resource-management.md)

**Reference**: .ai-framework/ARCHITECTURE.md:101-143

---

## 2. Service Separation

**Rule**: Each service type in separate process (no event loop conflicts).

**Services**:
- `tracker_activity_bot` (Aiogram) — Separate event loop for Telegram polling
- `data_postgres_api` (FastAPI) — Separate event loop for HTTP server

**Why**: FastAPI and Aiogram cannot safely share the same event loop.

**Reference**: .ai-framework/ARCHITECTURE.md:145-176 (Single Event Loop Ownership)

---

## 3. DDD/Hexagonal Architecture

**Structure** (both services):
```
service/
├── domain/              # Pure business logic (entities, value objects)
├── application/         # Use cases, application services
├── infrastructure/      # External concerns (HTTP, DB, Redis)
└── api/                 # Entry points (routes, handlers)
```

**Why**: Clear separation of concerns, easier testing, independent layer changes.

**Reference**: [Service Topology](02-service-topology.md)

---

## 4. Service Naming Convention

**Pattern**: `{context}_{domain}_{type}`

**Examples**:
- `tracker_activity_bot` — context: tracker, domain: activity, type: bot
- `data_postgres_api` — context: data, domain: postgres, type: api

**Why**: Consistent with .ai-framework naming guide.

---

## 5. Type Safety ⚠️ MANDATORY

**Rule**: Full type hints with mypy strict mode.

**Configuration**:
```toml
[tool.mypy]
python_version = "3.12"
strict = true
disallow_untyped_defs = true
warn_return_any = true
```

**Why**: Catch errors at development time, better IDE support, self-documenting code.

**Reference**: [Technology Stack](04-technology-stack.md), [Implementation Phase 2](implementation/phase-1-2.md)

---

## 6. Async-First Design

**Rule**: All I/O operations use async/await.

**Guidelines**:
- Use `async def` for all I/O functions
- Use `await` for all blocking calls
- Use async libraries (httpx, asyncpg, aioredis)
- NEVER use blocking operations (requests, time.sleep)

**Why**: Handle 100+ concurrent users efficiently.

**Reference**: .ai-framework/ARCHITECTURE.md:178-193

---

## 7. Structured Logging

**Rule**: JSON-formatted logs with context.

**Format**:
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

**Why**: Machine-readable logs, easier debugging, correlation across services.

---

## 8. Health Checks

**Rule**: Separate liveness and readiness probes.

**Endpoints**:
- `/health/live` — Service is running
- `/health/ready` — Service ready to accept requests (verifies DB connection)

**Why**: Docker healthchecks, proper service startup ordering.

**Reference**: [Service Topology](02-service-topology.md)

---

## 9. Error Handling Strategy

**Rules**:
1. HTTP client: Retry on 5xx, fail fast on 4xx
2. Database: Rollback transaction on error
3. User-facing: Friendly Russian messages
4. Logs: Structured JSON with context

**Anti-Pattern**: NEVER use bare `except: pass` without logging!

**Reference**: [Anti-Pattern: Error Handling](antipatterns/error-handling.md)

---

## 10. Database Schema Design

**Principles**:
- Normalization (3NF)
- Indexes on query columns
- Check constraints for data integrity
- Timestamps on all tables
- Foreign keys with CASCADE/SET NULL

**Reference**: [Service Topology](02-service-topology.md) for schema details

---

## 11. Testing Strategy

**Test Pyramid**:
- **Unit Tests** (70%): Pure functions, domain logic
- **Integration Tests** (20%): HTTP clients, repositories
- **Smoke Tests** (10%): Health checks, imports

**Coverage Target**:
- Level 1 (PoC): NOT required
- Level 2 (Development): >70%
- Level 3 (Pre-Production): >80%
- Level 4 (Production): >90%

**Reference**: [Implementation Phase 4](implementation/phase-3-5.md)

---

## Summary: Mandatory vs Recommended

| Principle | Status | Priority |
|-----------|--------|----------|
| 1. HTTP-Only Data Access | ⚠️ MANDATORY | 🔴 CRITICAL |
| 2. Service Separation | ⚠️ MANDATORY | 🔴 CRITICAL |
| 3. DDD/Hexagonal | ✅ Required | 🔴 CRITICAL |
| 4. Naming Convention | ✅ Required | 🟠 HIGH |
| 5. Type Safety | ⚠️ MANDATORY | 🔴 CRITICAL |
| 6. Async-First | ⚠️ MANDATORY | 🔴 CRITICAL |
| 7. Structured Logging | ✅ Required | 🟠 HIGH |
| 8. Health Checks | ✅ Required | 🟠 HIGH |
| 9. Error Handling | ✅ Required | 🟠 HIGH |
| 10. Database Schema | ✅ Required | 🟠 HIGH |
| 11. Testing | 🟡 Recommended | 🟡 MEDIUM |

---

## Related Documents

- [← Previous: Service Topology](02-service-topology.md)
- [Next: Technology Stack →](04-technology-stack.md)
- [Anti-Patterns to Avoid →](antipatterns/README.md)
- [Implementation Guide →](implementation/README.md)
- [← Back to Index](README.md)
