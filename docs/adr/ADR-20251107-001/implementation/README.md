# Implementation Guide

> **ADR**: ADR-20251107-001  
> [← Back to Main ADR](../README.md)

---

## Implementation Phases

### ⚠️ Phase 0: URGENT (Week 0) - 🔴🔴 CRITICAL

**[Phase 0: Resource Leak Fixes](phase-0-urgent.md)**

**Priority**: MUST DO FIRST!  
**Time**: 4-6 hours  
**Why**: Prevents production crashes after 3-7 days

**Tasks**:
- Fix FSM storage leak (1h)
- Fix HTTP client leaks (1h)
- Fix multiple Redis instances (2h)
- Fix bare except:pass (30min)
- Migrate from @app.on_event() (1h)

**Success Criteria**:
- Bot runs 7+ days without crashes
- No "too many open files" errors
- Clean shutdown without errors

---

### Phase 1: Core Architecture - ✅ COMPLETE

Already implemented:
- ✅ Service structure (DDD/Hexagonal)
- ✅ HTTP-only data access
- ✅ PostgreSQL + Alembic migrations
- ✅ Redis FSM storage
- ✅ Docker Compose orchestration

---

### Phase 2: Type Safety & Quality - 🔴 CRITICAL

**[Phase 1-2: Quality](phase-1-2.md)**

**Priority**: Must do after Phase 0  
**Time**: 16-20 hours

**Tasks**:
- Add mypy configuration (strict mode)
- Create Application Service layer in Data API
- Add complete type hints to all functions
- Add comprehensive docstrings (Args/Returns/Raises)
- Implement dependency injection in bot service

---

### Phase 3-5: Observability & Future - ⏳ PLANNED

**[Phase 3-5: Future](phase-3-5.md)**

**Phase 3** (🟠 HIGH, 8-10h):
- Improve health checks (DB connection verification)
- Add correlation IDs to logs
- Add request/response logging middleware

**Phase 4** (🟡 MEDIUM, 24-30h):
- Unit tests (>70% coverage)
- Integration tests
- CI/CD pipeline (GitHub Actions)

**Phase 5** (🟢 LOW, variable):
- Add Nginx API Gateway (Level 3+)
- Add Prometheus metrics (Level 2+)
- Add RabbitMQ (if needed)

---

## Timeline

**[Follow-Up Timeline](follow-up-timeline.md)** — Week-by-week breakdown

- **Week 0** (URGENT): Resource leak fixes
- **Week 1**: mypy configuration, Application Service layer
- **Week 2-3**: Type hints, docstrings, DI
- **Month 1**: Health checks, tests, CI/CD
- **Month 2-3**: Observability, metrics, future enhancements

---

## Related Documents

- [← Back to Main ADR](../README.md)
- [Phase 0 URGENT →](phase-0-urgent.md)
- [Anti-Patterns to Avoid →](../antipatterns/README.md)
- [Architecture Principles →](../03-architectural-principles.md)
