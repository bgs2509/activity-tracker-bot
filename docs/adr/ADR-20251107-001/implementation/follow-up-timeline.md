# Follow-Up Timeline

> **ADR**: ADR-20251107-001  
> [← Back to Implementation Index](README.md)

---

## Week 0 (URGENT) ⚠️

**Phase 0: Resource Leak Fixes**

See [Phase 0 URGENT](phase-0-urgent.md) for details

**Time**: 4-6 hours  
**Priority**: 🔴🔴 CRITICAL

**Tasks**:
1. Fix FSM storage leak (1h)
2. Fix HTTP client leaks (1h)
3. Fix multiple Redis instances (2h)
4. Fix bare except:pass (30min)
5. Migrate @app.on_event() (1h)
6. Add signal handlers (1-2h) - optional

**Deliverable**: Bot stable for 7+ days without crashes

---

## Week 1 (Immediate)

**Phase 2: Type Safety & Quality (Start)**

**Tasks**:
1. Add mypy configuration (2-3h)
2. Create Application Service layer (4-5h)
3. Start adding type hints (initial 3-4h)

**Deliverable**: mypy strict mode enabled, service layer created

---

## Week 2-3 (Short-term)

**Phase 2: Type Safety & Quality (Complete)**

**Tasks**:
4. Complete type hints (remaining time)
5. Add comprehensive docstrings (4-5h)
6. Implement dependency injection (2-3h)

**Deliverable**: 100% type coverage, all functions documented, DI implemented

---

## Month 1 (Medium-term)

**Phase 3: Observability + Phase 4: Testing (Start)**

**Tasks**:
7. Improve health checks (2h)
8. Add correlation IDs (2h)
9. Start unit tests (12-15h target)
10. Add CI/CD pipeline (2-3h)

**Deliverable**: Health checks improved, unit tests >50% coverage, CI/CD running

---

## Month 2-3 (Long-term)

**Phase 4: Testing (Complete) + Phase 5: Future**

**Tasks**:
11. Complete unit tests (>70% coverage)
12. Add integration tests (8-10h)
13. Optional: Add Prometheus metrics
14. Optional: Add Nginx if needed

**Deliverable**: >70% test coverage, observability ready for Level 2

---

## Gantt Chart

```
Week 0:  [████████████████████] Phase 0 URGENT (4-6h)
Week 1:  [██████████          ] Phase 2 Start (10h)
Week 2-3:[          ██████████] Phase 2 Complete (10h)
Month 1: [████████            ] Phase 3 + 4 Start (20h)
Month 2-3:[      ████████████ ] Phase 4 + 5 (30h+)
```

---

## Milestone Checklist

### Milestone 0: Production Stable ✅
- [ ] Phase 0 complete
- [ ] Bot runs 7+ days without crashes
- [ ] All resource leaks fixed

### Milestone 1: Type Safe ✅
- [ ] Phase 2 complete
- [ ] mypy strict passes
- [ ] All functions have type hints
- [ ] All functions have docstrings
- [ ] Dependency injection implemented

### Milestone 2: Development Ready ✅
- [ ] Phase 3 complete
- [ ] Health checks improved
- [ ] Correlation IDs implemented
- [ ] Request logging enabled

### Milestone 3: Test Coverage ✅
- [ ] Phase 4 complete
- [ ] >70% unit test coverage
- [ ] Integration tests written
- [ ] CI/CD pipeline active

### Milestone 4: Production Ready ✅
- [ ] Phase 5 evaluated
- [ ] Optional: Prometheus metrics
- [ ] Optional: Nginx if needed
- [ ] Ready for Level 4 transition

---

## Priority Matrix

```
Critical (Week 0):
├─ Phase 0: Resource leaks

High (Week 1-3):
├─ Phase 2: Type safety
└─ Phase 3: Observability

Medium (Month 1):
├─ Phase 4: Testing
└─ CI/CD pipeline

Low (Month 2-3):
└─ Phase 5: Future enhancements
```

---

## Related Documents

- [← Implementation Index](README.md)
- [Phase 0 Details →](phase-0-urgent.md)
- [Phase 1-2 Details →](phase-1-2.md)
- [Phase 3-5 Details →](phase-3-5.md)
- **Full Plan**: `artifacts/analysis/refactor-2025-11-07.md`
