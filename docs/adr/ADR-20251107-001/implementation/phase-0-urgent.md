# Phase 0: URGENT Resource Leak Fixes

> **ADR**: ADR-20251107-001  
> **Priority**: 🔴🔴 CRITICAL  
> **Time**: 4-6 hours  
> [← Back to Implementation Index](README.md)

---

## ⚠️ WARNING

These fixes MUST be done FIRST before any other refactoring!

**Why URGENT**:
- Production crashes after 3-7 days
- Memory exhaustion ("too many open files")
- Connection pool depletion
- Silent failures in production

**Source**: artifacts/analysis/refactor-2025-11-07.md Phase 1.5

---

## Task 0.1: Fix Global FSM Storage Leak (1 hour)

**Current Problem**: FSM storage NEVER closed → memory leak

**Files to Change**:
- `services/tracker_activity_bot/src/api/handlers/poll.py`
- `services/tracker_activity_bot/src/main.py`

**Solution**: Add `close_fsm_storage()` function and call in finally block

**Checklist**:
- [ ] Add close_fsm_storage() to poll.py
- [ ] Call in main.py finally block
- [ ] Test bot restarts cleanly

**Details**: See [Anti-Pattern: Resource Management](../antipatterns/resource-management.md#anti-pattern-11)

---

## Task 0.2: Fix HTTP Client Leaks (1 hour)

**Current Problem**: Multiple HTTP client instances NEVER closed

**Files to Change**:
- `services/tracker_activity_bot/src/api/dependencies.py` (create)
- `services/tracker_activity_bot/src/main.py`

**Solution**: Create shared HTTP client with dependency injection

**Checklist**:
- [ ] Create dependencies.py with get_api_client()
- [ ] Add close_api_client() function
- [ ] Call in main.py finally block
- [ ] Update handlers to use dependency injection

**Details**: See [Anti-Pattern: Resource Management](../antipatterns/resource-management.md#anti-pattern-12)

---

## Task 0.3: Fix Multiple Redis Instances (2 hours)

**Current Problem**: Creating new RedisStorage on every reminder/cleanup

**Files to Change**:
- `services/tracker_activity_bot/src/application/services/fsm_timeout_service.py`

**Solution**: Reuse shared FSM storage instead of creating new

**Checklist**:
- [ ] Replace RedisStorage.from_url() with get_fsm_storage()
- [ ] Remove await storage.close() calls (storage is shared)
- [ ] Test reminders and cleanup still work

**Details**: See [Anti-Pattern: Resource Management](../antipatterns/resource-management.md#anti-pattern-13)

---

## Task 0.4: Fix Bare except:pass (30 min)

**Current Problem**: Silent exception swallowing makes debugging impossible

**Files to Change**:
- `services/tracker_activity_bot/src/application/services/scheduler_service.py`
- Any other files with bare except:pass

**Solution**: Add logging with context to all exception handlers

**Checklist**:
- [ ] Find all except:pass blocks
- [ ] Add logging with context
- [ ] Use appropriate log level (warning/error)

**Details**: See [Anti-Pattern: Error Handling](../antipatterns/error-handling.md)

---

## Task 0.5: Migrate from @app.on_event() (1 hour)

**Current Problem**: Deprecated API will break in future FastAPI versions

**Files to Change**:
- `services/data_postgres_api/src/main.py`

**Solution**: Use modern lifespan context manager

**Checklist**:
- [ ] Create lifespan() context manager
- [ ] Pass lifespan=lifespan to FastAPI()
- [ ] Remove @app.on_event() decorators
- [ ] Test startup and shutdown work

**Details**: See [Anti-Pattern: Lifecycle Management](../antipatterns/lifecycle-management.md#anti-pattern-31)

---

## Task 0.6: Add Graceful Shutdown (1-2 hours) - OPTIONAL

**Problem**: Data loss on container stop

**Files to Change**:
- `services/tracker_activity_bot/src/main.py`

**Solution**: Add SIGTERM/SIGINT signal handlers

**Checklist**:
- [ ] Add signal handlers
- [ ] Implement graceful shutdown logic
- [ ] Test docker compose stop doesn't lose data

**Details**: See [Anti-Pattern: Lifecycle Management](../antipatterns/lifecycle-management.md#anti-pattern-32)

---

## Success Criteria

- [ ] Bot runs 7+ days without memory leaks
- [ ] No "too many open files" errors
- [ ] No "too many connections" errors
- [ ] Clean shutdown without errors
- [ ] All exceptions are logged

---

## Monitoring After Fixes

```bash
# Monitor memory usage (run for 24h)
docker stats tracker_activity_bot

# Monitor open file descriptors
docker exec tracker_activity_bot sh -c 'ls /proc/$$/fd | wc -l'

# Monitor connections
docker exec tracker_activity_bot sh -c 'netstat -an | grep ESTABLISHED | wc -l'

# Monitor Redis connections
docker exec tracker_redis redis-cli CLIENT LIST | wc -l
```

**Expected Values** (healthy system):
- Memory: < 200MB after 24h
- File descriptors: < 100
- Connections: < 50
- Redis connections: 2-5

---

## Related Documents

- [← Implementation Index](README.md)
- [Anti-Patterns Details →](../antipatterns/README.md)
- [Next: Phase 1-2 →](phase-1-2.md)
- **Full Details**: `artifacts/analysis/refactor-2025-11-07.md` Phase 1.5
