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

| ADR ID | Title | Date | Status | Description |
|--------|-------|------|--------|-------------|
| [ADR-20251107-001](ADR-20251107-001-activity-tracker-architecture.md) | Activity Tracker Bot - Improved Hybrid Architecture | 2025-11-07 | ✅ Accepted | Core architectural foundation following .ai-framework principles with KISS, YAGNI, DRY |

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
