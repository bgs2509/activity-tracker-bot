# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records for the Activity Tracker Bot project.

---

## What is an ADR?

An **Architecture Decision Record (ADR)** is a document that captures an important architectural decision made along with its context and consequences.

**Purpose**:
- Document WHY decisions were made (not just WHAT)
- Provide context for future maintainers
- Track architectural evolution over time
- Enable informed decision-making

---

## ADR Index

| ADR ID | Title | Date | Status | Description | Documents |
|--------|-------|------|--------|-------------|-----------|
| [ADR-20251107-001](ADR-20251107-001/) | Activity Tracker Bot - Improved Hybrid Architecture | 2025-11-07 | ✅ Accepted | Core architectural foundation following .ai-framework principles with KISS, YAGNI, DRY | 19 docs · [Index](ADR-20251107-001/README.md) |

---

## Featured ADR: ADR-20251107-001 (Modular Structure)

This ADR is split into 19 modular documents for better maintainability and navigation.

### 📐 Core Architecture (8 documents ~1,100 lines)

- **[Main Index](ADR-20251107-001/README.md)** — Navigation hub and executive summary
- **[01. Decision Overview](ADR-20251107-001/01-decision-overview.md)** — Context, business requirements, high-level decision
- **[02. Service Topology](ADR-20251107-001/02-service-topology.md)** — Architecture diagram, components, communication patterns
- **[03. Architectural Principles](ADR-20251107-001/03-architectural-principles.md)** — 11 core principles (HTTP-only, DDD, type safety, async, etc.)
- **[04. Technology Stack](ADR-20251107-001/04-technology-stack.md)** — Python, FastAPI, Aiogram, PostgreSQL, Redis with rationale
- **[05. YAGNI Exclusions](ADR-20251107-001/05-yagni-exclusions.md)** — What we deliberately DON'T use (Nginx, RabbitMQ, MongoDB, etc.)
- **[06. Alternatives Considered](ADR-20251107-001/06-alternatives-considered.md)** — Why NOT monolith, direct DB, webhooks, sync
- **[07. Consequences](ADR-20251107-001/07-consequences.md)** — Positive/negative impacts with mitigations
- **[References](ADR-20251107-001/references.md)** — External docs, maintenance log, version history

### ⚠️ Anti-Patterns (4 documents ~530 lines)

- **[Anti-Patterns Index](ADR-20251107-001/antipatterns/README.md)** — Production issues to avoid, monitoring, checklist
- **[Resource Management](ADR-20251107-001/antipatterns/resource-management.md)** — 🔴 CRITICAL: Memory leaks, connection exhaustion
- **[Error Handling](ADR-20251107-001/antipatterns/error-handling.md)** — 🟠 HIGH: Silent failures, bare except:pass
- **[Lifecycle Management](ADR-20251107-001/antipatterns/lifecycle-management.md)** — 🟠 HIGH: Deprecated APIs, no graceful shutdown

### 🔧 Implementation (5 documents ~750 lines)

- **[Implementation Index](ADR-20251107-001/implementation/README.md)** — Phase overview and timeline
- **[Phase 0: URGENT](ADR-20251107-001/implementation/phase-0-urgent.md)** — ⚠️ Week 0 resource leak fixes (4-6h)
- **[Phase 1-2: Quality](ADR-20251107-001/implementation/phase-1-2.md)** — Type safety, mypy, docstrings (16-20h)
- **[Phase 3-5: Future](ADR-20251107-001/implementation/phase-3-5.md)** — Observability, testing, future enhancements
- **[Timeline](ADR-20251107-001/implementation/follow-up-timeline.md)** — Week-by-week breakdown

### 📊 Statistics

- **Total Documents**: 19 files
- **Average File Size**: ~136 lines (optimal for reading!)
- **Reading Time per File**: 5-10 minutes
- **Total Size**: ~2,580 lines (including cross-references)

---

## ADR Status Definitions

- **Proposed** - Under review, not yet implemented
- **Accepted** - Approved and being implemented
- **Deprecated** - No longer recommended, but still in use
- **Superseded** - Replaced by a newer ADR

---

## How to Create a New ADR

1. **Use the template**: `.ai-framework/docs/reference/architecture-decision-log-template.md`

2. **Naming convention**: `ADR-YYYYMMDD-###-short-title.md`
   - Example: `ADR-20251215-002-add-rabbitmq.md`

3. **Required sections**:
   - Metadata (ID, title, date, status)
   - Context (business requirements, constraints)
   - Decision (what was decided)
   - Alternatives Considered (with pros/cons table)
   - Consequences (positive/negative impacts)
   - Follow-Up Actions
   - References

4. **Update this README**: Add new ADR to index table above

---

## Key Architectural Principles

### From ADR-20251107-001

**Core Decisions**:
1. ✅ **HTTP-only data access** — Bot → Data API (never direct DB)
2. ✅ **Service separation** — Each service in separate process
3. ✅ **DDD/Hexagonal Architecture** — Clear layer separation
4. ✅ **Type safety** — mypy strict mode
5. ✅ **Async-first** — All I/O uses async/await
6. ✅ **Structured logging** — JSON-formatted logs
7. ✅ **Health checks** — Separate liveness/readiness probes

**YAGNI Exclusions** (not needed yet):
- ❌ Nginx — only 2 services, direct networking sufficient
- ❌ RabbitMQ — no async event processing
- ❌ MongoDB — all data is relational
- ❌ Prometheus/Grafana — PoC level, Docker logs sufficient
- ❌ Jaeger — only 2 services, logs sufficient

---

## Related Documentation

- **Framework Guide**: `.ai-framework/ARCHITECTURE.md`
- **Violations Report**: `artifacts/analysis/refactor-2025-11-07.md`
- **Project README**: `README.md`
- **Implementation Plan**: `artifacts/plans/` (future)

---

**Last Updated**: 2025-11-07
**Total ADRs**: 1
