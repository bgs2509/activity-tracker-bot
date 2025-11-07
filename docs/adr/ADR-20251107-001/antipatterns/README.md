# Critical Anti-Patterns to Avoid

> **ADR**: ADR-20251107-001  
> [← Back to Main ADR](../README.md)

---

## Overview

These anti-patterns cause **memory leaks, connection exhaustion, and production crashes**.

**Source**: artifacts/analysis/refactor-2025-11-07.md (Phase 1.5)  
**Updated**: 2025-11-07  
**Impact**: Production stability, bot crashes after 3-7 days

---

## Anti-Pattern Categories

### 🔴 CRITICAL

**[1. Resource Management](resource-management.md)** (~200 lines)
- ❌ Global resources never closed (FSM storage, HTTP clients)
- ❌ Multiple HTTP client instances
- ❌ Creating new connection pools per operation
- **Symptom**: "too many open files" after 3-7 days, memory exhaustion

### 🟠 HIGH

**[2. Error Handling](error-handling.md)** (~100 lines)
- ❌ Bare except:pass blocks (silent failures)
- **Symptom**: Silent failures, impossible debugging, hidden bugs

**[3. Lifecycle Management](lifecycle-management.md)** (~150 lines)
- ❌ Deprecated APIs (@app.on_event)
- ❌ No graceful shutdown
- **Symptom**: Breaking changes on upgrade, data loss on restart

---

## Summary: Critical Rules

| Rule | Priority | Impact | Symptom |
|------|----------|--------|---------|
| Close all resources | 🔴 CRITICAL | Memory leaks, crashes | "too many open files" after 3-7 days |
| Single HTTP client | 🔴 CRITICAL | Connection exhaustion | High memory, slow responses |
| Always log exceptions | 🟠 HIGH | Debugging impossible | Silent failures, hidden bugs |
| Use modern APIs | 🟠 HIGH | Breaking changes | Won't start on framework upgrade |
| Handle shutdown signals | 🟡 MEDIUM | Data loss | Corrupted state, lost jobs on restart |

---

## Monitoring Commands

```bash
# Monitor memory usage
docker stats tracker_activity_bot

# Monitor open file descriptors
docker exec tracker_activity_bot sh -c 'ls /proc/$$/fd | wc -l'

# Monitor active connections
docker exec tracker_activity_bot sh -c 'netstat -an | grep ESTABLISHED | wc -l'

# Monitor Redis connections
docker exec tracker_redis redis-cli CLIENT LIST | wc -l'
```

---

## Expected Values (Healthy System)

- **Memory usage**: < 200MB after 24h
- **File descriptors**: < 100
- **Active connections**: < 50
- **Redis connections**: 2-5

---

## Prevention Checklist

Before deploying to production, verify:

- [ ] All global resources have explicit `close()` methods
- [ ] All `close()` methods called in `finally` blocks
- [ ] HTTP clients use dependency injection (single shared instance)
- [ ] No `except: pass` without logging
- [ ] Using `lifespan` context manager (not `@app.on_event()`)
- [ ] Signal handlers registered for SIGTERM/SIGINT
- [ ] Health checks verify resource connections
- [ ] Monitoring dashboard tracks memory/connections over time

---

## Related Documents

- [← Back to Main ADR](../README.md)
- [Resource Management Details →](resource-management.md)
- [Error Handling Details →](error-handling.md)
- [Lifecycle Management Details →](lifecycle-management.md)
- [Fix Plan: Phase 0 URGENT →](../implementation/phase-0-urgent.md)
