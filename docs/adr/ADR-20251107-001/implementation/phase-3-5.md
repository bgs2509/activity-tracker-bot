# Phase 3-5: Observability & Future

> **ADR**: ADR-20251107-001  
> **Priority**: 🟠 HIGH → 🟢 LOW  
> **Time**: 30+ hours  
> [← Back to Implementation Index](README.md)

---

## Phase 3: Observability (REQUIRED)

**Priority**: 🟠 HIGH  
**Time**: 8-10 hours

### Task 3.1: Improve Health Checks (2h)

Split into separate /live and /ready endpoints with DB verification

### Task 3.2: Add Correlation IDs (2h)

Add correlation_id to all structured logs for request tracing

### Task 3.3: Add Request/Response Logging (2h)

Middleware to log all HTTP requests/responses with timing

### Task 3.4: Add Error Tracking (2h)

Optional: Integrate Sentry for error aggregation

**Checklist**:
- [ ] Split health checks (/health/live, /health/ready)
- [ ] Add correlation ID middleware
- [ ] Add request logging middleware
- [ ] Optional: Add Sentry integration

---

## Phase 4: Testing (NICE TO HAVE)

**Priority**: 🟡 MEDIUM  
**Time**: 24-30 hours

### Task 4.1: Unit Tests (12-15h)

Target >70% coverage for Level 2

**Focus Areas**:
- Domain logic (pure functions)
- Time parsing utilities
- FSM state transitions
- Business validation rules

### Task 4.2: Integration Tests (8-10h)

Test HTTP clients and database repositories

**Test Cases**:
- HTTP client with mock server
- Repository with test database
- End-to-end activity creation flow

### Task 4.3: Smoke Tests (2h)

Basic health check and import tests

### Task 4.4: CI/CD Pipeline (2-3h)

GitHub Actions for automated testing and linting

**Pipeline Steps**:
1. Run mypy (type checking)
2. Run ruff (linting)
3. Run pytest (unit + integration tests)
4. Build Docker images
5. Run smoke tests

**Checklist**:
- [ ] Write unit tests (>70% coverage)
- [ ] Write integration tests
- [ ] Write smoke tests
- [ ] Create .github/workflows/ci.yml
- [ ] Verify pipeline passes

---

## Phase 5: Future Enhancements (OPTIONAL)

**Priority**: 🟢 LOW  
**Time**: Variable

### 5.1: Add Nginx API Gateway

**When**: Level 3+ (Pre-Production)  
**Why**: Multiple services (>3), SSL/TLS, rate limiting  
**Time**: 4-6h

See [YAGNI Exclusions](../05-yagni-exclusions.md#1-nginx-api-gateway)

---

### 5.2: Add Prometheus Metrics

**When**: Level 2+ (Development)  
**Why**: Performance tracking, custom dashboards  
**Time**: 6-8h

**Metrics to Track**:
- Request rate, latency, errors
- Database query time
- Active users
- Memory usage

---

### 5.3: Add RabbitMQ

**When**: Async event processing needed  
**Why**: Background jobs, async notifications  
**Time**: 8-12h

See [YAGNI Exclusions](../05-yagni-exclusions.md#2-rabbitmq-message-broker)

---

### 5.4: Add Distributed Tracing

**When**: Level 3+ (>5 services)  
**Why**: Performance bottleneck analysis  
**Time**: 6-8h

**Options**: Jaeger, Zipkin, OpenTelemetry

---

## Summary

| Phase | Priority | Time | Status |
|-------|----------|------|--------|
| Phase 3: Observability | 🟠 HIGH | 8-10h | ⏳ Planned |
| Phase 4: Testing | 🟡 MEDIUM | 24-30h | ⏳ Planned |
| Phase 5: Future | 🟢 LOW | Variable | ⏳ Optional |

---

## Related Documents

- [← Implementation Index](README.md)
- [Previous: Phase 1-2](phase-1-2.md)
- [Timeline →](follow-up-timeline.md)
- [YAGNI Exclusions →](../05-yagni-exclusions.md)
