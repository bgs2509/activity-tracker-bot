# Decision Overview

> **ADR**: ADR-20251107-001
> **Status**: ✅ Accepted
> [← Back to Index](README.md)

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

---

### Technical Constraints

1. **Framework Compliance**: Must follow .ai-framework/ARCHITECTURE.md principles
2. **HTTP-Only Data Access**: Business services NEVER access database directly
3. **Service Separation**: Each service type in separate process (no event loop conflicts)
4. **Naming Convention**: `{context}_{domain}_{type}` pattern
5. **Python 3.12+**: Modern async/await, type hints
6. **Docker Compose**: Local development and deployment

---

### Existing System Assumptions

- **Deployment**: Single-host Docker Compose (no Kubernetes required for PoC)
- **Scale**: Single user to ~100 concurrent users (PoC → Development)
- **Geographic Distribution**: Single region (no multi-region support)
- **High Availability**: NOT required for current maturity level

---

## Decision

### Architecture: Improved Hybrid Approach (Simplified)

We adopt the **Improved Hybrid Approach** from .ai-framework with **minimal necessary components** following KISS and YAGNI principles.

**Key Decision Points:**

1. ✅ **HTTP-only data access** — Bot NEVER accesses database directly
2. ✅ **Service separation** — Each service in separate process (no event loop conflicts)
3. ✅ **DDD/Hexagonal architecture** — Clear layer separation
4. ✅ **Type safety** — mypy strict mode with full type hints
5. ✅ **Async-first design** — All I/O operations use async/await
6. ✅ **Structured logging** — JSON-formatted logs with context
7. ✅ **Health checks** — Separate liveness/readiness probes
8. ✅ **YAGNI principle** — Only necessary components, no over-engineering

---

### Why This Architecture?

**Problem**: Users need activity tracking without installing separate apps.

**Solution**: Telegram bot with HTTP-only data access pattern.

**Benefits**:
- ✅ Single source of truth for data access
- ✅ Independent service scaling
- ✅ Easy testing (mock HTTP vs mock database)
- ✅ Prevents connection pool exhaustion
- ✅ Framework compliant (100% .ai-framework aligned)

**Tradeoffs**:
- ⚠️ 1-5ms HTTP latency (acceptable: user >100ms buffer)
- ⚠️ Increased complexity (mitigated by docker-compose + Makefile)

---

## Related Documents

- Next: [Service Topology →](02-service-topology.md)
- Principles: [Architectural Principles →](03-architectural-principles.md)
- Tech Stack: [Technology Stack →](04-technology-stack.md)
- What we DON'T use: [YAGNI Exclusions →](05-yagni-exclusions.md)
- Why NOT alternatives: [Alternatives Considered →](06-alternatives-considered.md)
- Impacts: [Consequences →](07-consequences.md)
- How to implement: [Implementation Guide →](implementation/README.md)
- [← Back to Index](README.md)
