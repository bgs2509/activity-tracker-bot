# ADR-20251107-001: Activity Tracker Bot Architecture

> **Status**: ✅ Accepted
> **Date**: 2025-11-07
> **Version**: 1.2 (Modular)
> **Authors**: Development Team

---

## Quick Navigation

### 📐 Core Architecture (8 documents)

1. **[Decision Overview](01-decision-overview.md)** — Why this architecture?
   - Context: Business requirements, constraints, assumptions
   - High-level decision and key principles

2. **[Service Topology](02-service-topology.md)** — System diagram & components
   - Architecture diagram (ASCII)
   - Component descriptions and responsibilities

3. **[Architectural Principles](03-architectural-principles.md)** — 11 core rules
   - HTTP-only data access, DDD, naming, type safety, async-first, logging, health checks, error handling, database schema, testing

4. **[Technology Stack](04-technology-stack.md)** — Frameworks & tools
   - Python 3.12+, FastAPI, Aiogram, PostgreSQL, Redis, mypy, pytest
   - Rationale for each choice

5. **[YAGNI Exclusions](05-yagni-exclusions.md)** — What we deliberately DON'T use
   - Nginx, RabbitMQ, MongoDB, Prometheus, Kubernetes, etc.
   - When to add them later

6. **[Alternatives Considered](06-alternatives-considered.md)** — Why NOT other approaches
   - Monolith, direct database access, webhooks, synchronous FastAPI
   - Decision matrices with pros/cons

7. **[Consequences](07-consequences.md)** — Impacts & tradeoffs
   - Positive: Scalability, maintainability, framework compliance
   - Negative: Network latency, complexity (with mitigations)

8. **[References & Maintenance](references.md)** — Links, changelog, status
   - Framework documentation, external resources
   - Version history and maintenance info

---

### ⚠️ Anti-Patterns (4 documents)

**[Anti-Patterns Index](antipatterns/README.md)** — Production issues to avoid

- **[Resource Management](antipatterns/resource-management.md)** — 🔴 CRITICAL
  - Global resources never closed (FSM storage, HTTP clients)
  - Multiple connection pool instances
  - Creating new pools per operation
  - **Symptom**: Crashes after 3-7 days, "too many open files"

- **[Error Handling](antipatterns/error-handling.md)** — 🟠 HIGH
  - Bare except:pass blocks (silent failures)
  - **Symptom**: Impossible debugging, hidden bugs

- **[Lifecycle Management](antipatterns/lifecycle-management.md)** — 🟠 HIGH
  - Deprecated APIs (@app.on_event)
  - No graceful shutdown
  - **Symptom**: Breaking changes, data loss on restart

---

### 🔧 Implementation (5 documents)

**[Implementation Index](implementation/README.md)** — How to implement

- **[Phase 0: URGENT Fixes](implementation/phase-0-urgent.md)** — ⚠️ Week 0 CRITICAL
  - Resource leak fixes (4-6 hours)
  - **MUST DO FIRST** before any other refactoring!

- **[Phase 1-2: Quality](implementation/phase-1-2.md)** — Type Safety & Quality
  - Application Service layer, mypy, type hints, docstrings, DI
  - **Priority**: 🔴 CRITICAL (16-20 hours)

- **[Phase 3-5: Future](implementation/phase-3-5.md)** — Observability & Testing
  - Health checks, tests, metrics, future enhancements
  - **Priority**: 🟠 HIGH to 🟢 LOW

- **[Timeline](implementation/follow-up-timeline.md)** — Week-by-week plan
  - Week 0 (URGENT), Week 1-3, Month 1-3
  - Gantt chart and milestones

---

## Executive Summary

### The Problem

Users need a simple way to track daily activities via Telegram without installing separate apps. Activities must be recorded with timestamps, categorized, and stored persistently.

### The Solution

We adopt the **Improved Hybrid Approach** from .ai-framework with **minimal necessary components** following KISS and YAGNI principles:

- **2 services**: `tracker_activity_bot` (Aiogram) + `data_postgres_api` (FastAPI)
- **HTTP-only communication**: Bot NEVER accesses database directly
- **Clear separation**: DDD/Hexagonal architecture
- **Type safety**: mypy strict mode
- **Async-first**: All I/O operations use async/await

### Key Architectural Decisions

1. ✅ **HTTP-Only Data Access** — Business services NEVER access database directly
2. ✅ **Service Separation** — Each service type in separate process (no event loop conflicts)
3. ✅ **DDD/Hexagonal** — domain/, application/, infrastructure/, api/ layers
4. ✅ **Type Safety** — Full type hints with mypy strict mode
5. ✅ **Async-First** — All I/O operations use async/await

### What We DON'T Use (YAGNI)

Following KISS + YAGNI, we deliberately exclude:
- ❌ Nginx API Gateway (only 2 services)
- ❌ RabbitMQ (no async events)
- ❌ MongoDB (all data is relational)
- ❌ Prometheus/Grafana (PoC level)
- ❌ Kubernetes (single-host deployment)

---

## Current Status

### Implementation Progress

- ✅ **Phase 1**: Complete (Core Architecture)
- 🔴 **Phase 0**: URGENT (Resource leak fixes needed!)
- ⏳ **Phase 2**: Planned (Type Safety & Quality)
- ⏳ **Phase 3-5**: Planned (Observability, Testing, Future)

### Critical Issues

⚠️ **URGENT**: Resource leaks discovered in production analysis!
- Memory leaks causing crashes after 3-7 days
- Connection pool exhaustion
- See [Phase 0 URGENT](implementation/phase-0-urgent.md) for fixes

---

## How to Use This Documentation

### For New Team Members

1. Start with [Decision Overview](01-decision-overview.md) — understand WHY
2. Review [Service Topology](02-service-topology.md) — understand WHAT
3. Study [Architectural Principles](03-architectural-principles.md) — understand HOW
4. Read [Anti-Patterns](antipatterns/README.md) — learn what to AVOID

### For Implementation

1. **First**: Fix [Phase 0 URGENT](implementation/phase-0-urgent.md) resource leaks
2. **Then**: Follow [Timeline](implementation/follow-up-timeline.md) week by week
3. **Review**: Check [Anti-Patterns](antipatterns/README.md) during code review

### For Code Review

- Reference specific anti-patterns: `See antipatterns/resource-management.md #1.1`
- Check compliance with principles: `See 03-architectural-principles.md #5`
- Verify implementation matches plan: `See implementation/phase-1-2.md Task 2.1`

---

## Document Statistics

- **Total Documents**: 19 files
- **Core Architecture**: 8 files (~1,100 lines)
- **Anti-Patterns**: 4 files (~530 lines)
- **Implementation**: 5 files (~750 lines)
- **Average File Size**: ~136 lines (optimal for reading!)

---

## Version History

- **v1.2** (2025-11-07) — Split into 19 modular documents
- **v1.1** (2025-11-07) — Added "Critical Anti-Patterns" section
- **v1.0** (2025-11-07) — Initial ADR created

---

## Related Documentation

- **Parent Index**: [ADR Index](../README.md)
- **Analysis Report**: `artifacts/analysis/refactor-2025-11-07.md`
- **Framework Guide**: `.ai-framework/ARCHITECTURE.md`
- **Project README**: `README.md`

---

**Approved By**: Development Team
**Maturity Level**: Level 1 (PoC) → Targeting Level 2 (Development Ready)
**Compliance**: 100% .ai-framework aligned (with documented YAGNI exclusions)
