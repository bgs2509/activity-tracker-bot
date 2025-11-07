# Anti-Pattern: Resource Management

> **ADR**: ADR-20251107-001  
> **Category**: 🔴 CRITICAL  
> [← Back to Anti-Patterns Index](README.md)

---

## Overview

Resource leaks cause memory exhaustion and connection pool depletion.

**Symptom**: Bot crashes after 3-7 days with "too many open files"

**Impact**: Production crashes, memory leaks, connection exhaustion

---

## ❌ Anti-Pattern 1.1: Global Resources Never Closed

### Problem

Memory leaks, connection pool exhaustion

### Example (WRONG)

```python
# ❌ services/tracker_activity_bot/src/api/handlers/poll.py:45-48
_fsm_storage: RedisStorage | None = None

def get_fsm_storage() -> RedisStorage:
    """Get or create FSM storage instance for state checking."""
    global _fsm_storage
    if _fsm_storage is None:
        _fsm_storage = RedisStorage.from_url(app_settings.redis_url)
    return _fsm_storage  # ⚠️ NEVER CLOSED → Memory leak!
```

### Why This Matters

- Redis connection pool is NEVER closed
- Each connection holds memory + file descriptors
- Over days/weeks → memory exhaustion → bot crashes
- Symptom: "too many open files" error after 3-7 days uptime

### Solution (CORRECT)

```python
# ✅ services/tracker_activity_bot/src/api/handlers/poll.py
_fsm_storage: RedisStorage | None = None

def get_fsm_storage() -> RedisStorage:
    """
    Get shared FSM storage instance.

    Returns:
        Shared FSM storage instance
    """
    global _fsm_storage
    if _fsm_storage is None:
        _fsm_storage = RedisStorage.from_url(app_settings.redis_url)
    return _fsm_storage

async def close_fsm_storage() -> None:
    """Close FSM storage on shutdown."""
    global _fsm_storage
    if _fsm_storage is not None:
        await _fsm_storage.close()
        _fsm_storage = None
        logger.info("FSM storage closed")

# main.py
async def main() -> None:
    """Main bot entry point."""
    try:
        await dp.start_polling(bot)
    finally:
        await close_fsm_storage()  # ✅ Proper cleanup!
        await bot.session.close()
        await storage.close()
```

### Architecture Rule

> **All stateful resources (Redis, HTTP clients, DB connections) MUST have explicit cleanup in application lifecycle.**

---

## ❌ Anti-Pattern 1.2: Multiple HTTP Client Instances

### Problem

Connection pool proliferation, memory leaks

### Example (WRONG)

```python
# ❌ Multiple global instances across handlers
# services/tracker_activity_bot/src/api/handlers/activity.py:26
api_client = DataAPIClient()  # Instance 1

# services/tracker_activity_bot/src/api/handlers/categories.py
api_client = DataAPIClient()  # Instance 2

# All NEVER closed → Connection pool leak per instance!
```

### Why This Matters

- `httpx.AsyncClient` holds connection pool (default 100 connections)
- Each instance = separate pool = wasted resources
- NEVER closed = connections stay open forever
- Symptom: High connection count, memory growth

### Solution (CORRECT)

```python
# ✅ Single shared client with dependency injection
# services/tracker_activity_bot/src/api/dependencies.py

_api_client: DataAPIClient | None = None

def get_api_client() -> DataAPIClient:
    """Get shared HTTP client instance."""
    global _api_client
    if _api_client is None:
        _api_client = DataAPIClient()
    return _api_client

async def close_api_client() -> None:
    """Close HTTP client on shutdown."""
    global _api_client
    if _api_client is not None:
        await _api_client.close()
        _api_client = None
        logger.info("HTTP client closed")

# Use dependency injection in handlers
def get_activity_service() -> ActivityService:
    """Provide activity service with shared HTTP client."""
    client = get_api_client()  # ✅ Shared instance
    return ActivityService(client)
```

### Architecture Rule

> **Use Dependency Injection for shared resources. Single HTTP client instance per service.**

---

## ❌ Anti-Pattern 1.3: Creating New Pools Per Operation

### Problem

Inefficient resource usage, slow performance

### Example (WRONG)

```python
# ❌ services/tracker_activity_bot/src/application/services/fsm_timeout_service.py:172
async def send_reminder(bot: Bot, user_id: int, state: State, action: str):
    """Send reminder to user about unfinished dialog."""
    try:
        # Creates NEW RedisStorage every time!
        storage = RedisStorage.from_url(app_settings.redis_url)  # New pool!
        
        # ... use storage ...
        
        await storage.close()  # Closes after use
        # BUT: Creating new pool each time is INEFFICIENT!
```

### Why This Matters

- Each `RedisStorage.from_url()` creates NEW connection pool
- Connection pool creation is expensive (DNS, handshake, auth)
- Happening on EVERY reminder/cleanup (every 10-13 minutes)
- Unnecessary overhead, slower performance

### Solution (CORRECT)

```python
# ✅ Reuse shared FSM storage
async def send_reminder(bot: Bot, user_id: int, state: State, action: str):
    """Send reminder to user about unfinished dialog."""
    try:
        # Reuse shared storage instead of creating new one!
        from src.api.handlers.poll import get_fsm_storage
        
        storage = get_fsm_storage()  # ✅ Reuses existing pool!
        
        # ... use storage ...
        
        # DON'T close storage here - it's shared!
```

### Architecture Rule

> **Reuse shared connection pools. NEVER create new pools for each operation.**

---

## Monitoring

```bash
# Check memory growth
docker stats --no-stream tracker_activity_bot

# Check file descriptor leak
docker exec tracker_activity_bot sh -c 'ls /proc/$$/fd | wc -l'

# Check connection count
docker exec tracker_activity_bot sh -c 'netstat -an | grep ESTABLISHED | wc -l'
```

---

## Related Documents

- [← Back to Anti-Patterns Index](README.md)
- [Fix Guide: Phase 0 URGENT →](../implementation/phase-0-urgent.md)
- [Error Handling →](error-handling.md)
- [Lifecycle Management →](lifecycle-management.md)
