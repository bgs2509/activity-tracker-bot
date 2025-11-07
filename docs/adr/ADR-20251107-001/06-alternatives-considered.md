# Alternatives Considered

> **ADR**: ADR-20251107-001  
> [← Back to Index](README.md) | [← Previous: YAGNI](05-yagni-exclusions.md) | [Next: Consequences →](07-consequences.md)

---

## Overview

This document explains alternative approaches we evaluated and why they were rejected in favor of the chosen architecture.

---

## Alternative 1: Monolithic Architecture

### Approach
Single FastAPI service with Telegram bot handlers in the same process.

### Pros
- Simpler deployment (1 service instead of 2)
- No HTTP overhead between bot and data layer
- Fewer Docker containers to manage
- Shared memory space

### Cons
- **Event loop conflicts** (FastAPI + Aiogram cannot share event loop safely)
- Tight coupling between presentation and data layers
- Difficult to scale bot independently of data API
- Violates .ai-framework principles
- Testing becomes more complex

### Reason Rejected
**Violates "Single Event Loop Ownership" principle** from .ai-framework/ARCHITECTURE.md:145-176.

FastAPI (via Uvicorn) and Aiogram both need exclusive control of the event loop. Running them in the same process causes:
- Race conditions
- Deadlocks
- Unpredictable behavior
- Difficult debugging

**Decision**: Service separation is MANDATORY.

---

## Alternative 2: Direct Database Access

### Approach
`tracker_activity_bot` directly accesses PostgreSQL without Data API intermediary.

### Pros
- Lower latency (no HTTP overhead)
- Simpler code (direct SQL queries)
- One less service to maintain

### Cons
- **VIOLATES HTTP-Only Data Access** (mandatory rule)
- Duplicate data access code in multiple services
- Connection pool exhaustion (multiple services = multiple pools)
- Difficult to add caching/validation layer later
- Harder to test (mock database vs mock HTTP)
- Violates DDD (business logic accesses infrastructure directly)

### Reason Rejected
**Violates core principle of Improved Hybrid Approach** (.ai-framework/ARCHITECTURE.md:101-143).

Business services NEVER access database directly. This is a foundational principle.

**Decision**: HTTP-only data access is NON-NEGOTIABLE.

---

## Alternative 3: Webhooks Instead of Polling

### Approach
Use Telegram webhooks instead of long polling for receiving updates.

### Pros
- More efficient (no constant polling)
- Lower latency (immediate update delivery)
- Lower bandwidth usage

### Cons
- Requires public HTTPS endpoint
- Requires SSL certificates (Let's Encrypt or purchased)
- More complex deployment (reverse proxy, domain name)
- Overkill for PoC level (<100 users)
- Adds infrastructure complexity

### Reason Rejected
**Unnecessary complexity for PoC** (KISS principle).

Long polling is:
- Simpler to deploy (no public endpoint needed)
- Sufficient for current scale (<100 users)
- Easy to switch to webhooks later (Aiogram supports both)

**Decision**: Use polling for PoC, consider webhooks at Level 3+.

---

## Alternative 4: Synchronous FastAPI (no async)

### Approach
Use synchronous FastAPI with blocking I/O instead of async.

### Pros
- Simpler code (no async/await)
- More libraries available (sync ecosystem larger)
- Easier for junior developers

### Cons
- **VIOLATES Async-First principle**
- Poor performance under load (thread pool overhead)
- Cannot handle concurrent requests efficiently
- Cannot use async PostgreSQL driver (asyncpg)
- Blocking calls block entire thread

### Reason Rejected
**Violates .ai-framework/ARCHITECTURE.md:178-193** (Async-First Design).

Async is mandatory for scalability. Non-functional requirement: handle 100+ concurrent users.

**Decision**: Async-first is MANDATORY.

---

## Decision Matrix

| Criterion | Chosen Architecture | Monolith | Direct DB | Webhooks | Sync FastAPI |
|-----------|---------------------|----------|-----------|----------|--------------|
| Framework Compliance | ✅ Yes | ❌ No | ❌ No | ✅ Yes | ❌ No |
| Scalability | ✅ High | 🟡 Medium | 🟡 Medium | ✅ High | ❌ Low |
| Complexity | 🟡 Medium | ✅ Low | ✅ Low | 🔴 High | ✅ Low |
| Maintainability | ✅ High | 🟡 Medium | ❌ Low | ✅ High | 🟡 Medium |
| Testability | ✅ High | 🟡 Medium | ❌ Low | ✅ High | ✅ High |
| Event Loop Safety | ✅ Yes | ❌ No | N/A | ✅ Yes | N/A |
| KISS Principle | ✅ Yes | ✅ Yes | ✅ Yes | ❌ No | ✅ Yes |

---

## Why Our Choice is Best

### Framework Compliance
✅ 100% aligned with .ai-framework mandatory principles

### Scalability
✅ Services scale independently, async handles 100+ concurrent users

### Balance
✅ Optimal tradeoff between complexity and benefits

### Future-Proof
✅ Easy to add features (RabbitMQ, Nginx, etc.) without breaking changes

---

## Related Documents

- [← Previous: YAGNI Exclusions](05-yagni-exclusions.md)
- [Next: Consequences →](07-consequences.md)
- [Decision Overview](01-decision-overview.md)
- [← Back to Index](README.md)
