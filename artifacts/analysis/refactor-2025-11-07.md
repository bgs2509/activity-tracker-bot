# Refactoring TODO Plan: ADR Compliance Implementation

**Project:** Activity Tracker Bot
**Date:** 2025-11-07
**Reference ADR:** docs/adr/ADR-20251107-001/ (modular structure - 19 documents)
**Status:** 🔴 Phase 1 Complete | **Phase 1.5 URGENT** | Phase 2-4 Required

**Quick Links:**
- [ADR Main Index](../docs/adr/ADR-20251107-001/README.md)
- [Anti-Patterns](../docs/adr/ADR-20251107-001/antipatterns/README.md)
- [Phase 0 URGENT](../docs/adr/ADR-20251107-001/implementation/phase-0-urgent.md)

---

## Executive Summary

Проект реализует базовую архитектуру (Phase 1 из ADR), но требует существенных доработок для полного соответствия **ADR-20251107-001**.

**⚠️ CRITICAL URGENT:** Обнаружены критические утечки ресурсов (Phase 1.5) — необходимо исправить НЕМЕДЛЕННО!

**Current State:**
- ✅ HTTP-only data access (implemented)
- ✅ Service separation (implemented)
- ✅ Docker Compose (implemented)
- ❌ **Resource leaks** (CRITICAL URGENT - Phase 1.5) — memory/connection leaks!
- ❌ Application Layer (MISSING - critical)
- ❌ Type safety with mypy (MISSING - critical)
- ❌ Complete type hints (PARTIAL - critical)
- ❌ Health checks with DB verification (PARTIAL - high)

**Gap Analysis:**
- **Phase 1**: ✅ 100% complete (Core Architecture)
- **Phase 1.5**: 🔴🔴 0% complete (Resource Leak Fixes) — **CRITICAL URGENT** (must fix FIRST!)
- **Phase 2**: 🔴 0% complete (Type Safety & Quality) — CRITICAL
- **Phase 3**: 🟠 20% complete (Observability)
- **Phase 4**: 🟢 0% complete (Testing) — Optional for Level 1

**Estimated Effort:**
- **Phase 1.5: ~4-6 hours (MUST DO IMMEDIATELY!)** ⚠️
- Phase 2: ~16-20 hours (MUST DO)
- Phase 3: ~8-10 hours (SHOULD DO)
- Phase 4: ~24-30 hours (NICE TO HAVE)

---

## Comparison: Current vs Ideal ADR

### ✅ What is CORRECT (Compliant with ADR)

| Aspect | Current Implementation | ADR Requirement | Status |
|--------|----------------------|-----------------|--------|
| **HTTP-only data access** | Bot uses HTTP client to Data API | MANDATORY | ✅ OK |
| **Service separation** | 2 services in separate containers | MANDATORY | ✅ OK |
| **Async-first** | All I/O uses async/await | MANDATORY | ✅ OK |
| **PostgreSQL** | Used with SQLAlchemy async | Required | ✅ OK |
| **Redis FSM** | Used for Aiogram FSM storage | Required | ✅ OK |
| **Docker Compose** | All services orchestrated | Required | ✅ OK |
| **Structured logging** | JSON logs with context | Required | ✅ OK |
| **DDD structure** | domain/, infrastructure/, api/ | Required | ✅ OK |

### ❌ What is MISSING (Non-Compliant with ADR)

| Aspect | Current State | ADR Requirement | Priority | Phase |
|--------|--------------|-----------------|----------|-------|
| **Resource cleanup** | ❌ FSM storage never closed | MUST close all connections | 🔴🔴 CRITICAL URGENT | Phase 1.5 |
| **Connection pooling** | ❌ HTTP clients never closed | MUST close connection pools | 🔴🔴 CRITICAL URGENT | Phase 1.5 |
| **Error handling** | ❌ Bare except:pass blocks | MUST log all exceptions | 🟠 HIGH | Phase 1.5 |
| **Deprecated APIs** | ❌ Using @app.on_event() | MUST use lifespan context | 🟠 HIGH | Phase 1.5 |
| **Graceful shutdown** | ❌ No signal handlers | SHOULD handle SIGTERM/SIGINT | 🟡 MEDIUM | Phase 1.5 |
| **Application Layer** | ❌ Does NOT exist in data_postgres_api | MUST have application/services/ | 🔴 CRITICAL | Phase 2 |
| **mypy configuration** | ❌ No pyproject.toml with mypy | MUST have strict mode | 🔴 CRITICAL | Phase 2 |
| **Complete type hints** | ⚠️ HTTP clients return dict/Any | MUST return Pydantic models | 🔴 CRITICAL | Phase 2 |
| **Health checks** | ⚠️ No DB connection check | MUST verify DB in /health/ready | 🟠 HIGH | Phase 3 |
| **Comprehensive docstrings** | ⚠️ Missing Args/Returns/Raises | SHOULD have complete docs | 🟠 HIGH | Phase 2 |
| **Dependency injection** | ❌ Global HTTP client instances | SHOULD use DI pattern | 🟠 HIGH | Phase 2 |
| **Unit tests** | ❌ Minimal test coverage | SHOULD have >70% (Level 2) | 🟡 MEDIUM | Phase 4 |
| **CI/CD pipeline** | ❌ No GitHub Actions | SHOULD have automation | 🟡 MEDIUM | Phase 4 |

### 🎯 YAGNI Compliance Check

**ADR excludes these components** — verify we DON'T have them (good!):

| Component | Current State | ADR Decision | Compliance |
|-----------|--------------|--------------|------------|
| Nginx API Gateway | ❌ Not present | ❌ Not needed (YAGNI) | ✅ CORRECT |
| RabbitMQ | ❌ Not present | ❌ Not needed (YAGNI) | ✅ CORRECT |
| MongoDB | ❌ Not present | ❌ Not needed (YAGNI) | ✅ CORRECT |
| Prometheus/Grafana | ❌ Not present | ❌ Not needed (Level 1) | ✅ CORRECT |
| Jaeger Tracing | ❌ Not present | ❌ Not needed (Level 1) | ✅ CORRECT |
| ELK Stack | ❌ Not present | ❌ Not needed (Level 1) | ✅ CORRECT |
| Kubernetes | ❌ Not present | ❌ Not needed (Level 1) | ✅ CORRECT |
| OAuth2/JWT | ❌ Not present | ❌ Not needed (Telegram auth) | ✅ CORRECT |

**Result:** ✅ Perfect YAGNI compliance — no unnecessary components!

---

## Detailed TODO Plan

---

## 🔴 PHASE 1.5: Resource Leak Fixes (CRITICAL - Week 0 - URGENT!)

**Estimated Time:** 4-6 hours
**Priority:** 🔴🔴 CRITICAL URGENT (Memory leaks, connection leaks)
**Impact:** Production stability, memory exhaustion, connection pool exhaustion

**⚠️ ATTENTION:** These are REAL resource leaks causing memory/connection exhaustion in production!
These must be fixed BEFORE any other refactoring work.

---

### Task 1.5.1: Fix Global FSM Storage Leak in poll.py

**Priority:** 🔴🔴 CRITICAL URGENT
**Estimated Time:** 1 hour
**Impact:** Redis connection pool leak, memory leak

**Current Problem:**
```python
# ❌ WRONG: services/tracker_activity_bot/src/api/handlers/poll.py:45-48
_fsm_storage: RedisStorage | None = None

def get_fsm_storage() -> RedisStorage:
    """Get or create FSM storage instance for state checking."""
    global _fsm_storage
    if _fsm_storage is None:
        _fsm_storage = RedisStorage.from_url(app_settings.redis_url)
    return _fsm_storage  # ⚠️ NEVER CLOSED! Memory leak!
```

**Why This is Critical:**
- `_fsm_storage` creates Redis connection pool
- Connection pool is NEVER closed
- Each connection holds memory and file descriptors
- Over time: memory exhaustion, "too many open files" error
- Bot crashes after running for days/weeks

**Solution:**
```python
# ✅ CORRECT: Close storage on bot shutdown
# services/tracker_activity_bot/src/api/handlers/poll.py

_fsm_storage: RedisStorage | None = None


def get_fsm_storage() -> RedisStorage:
    """
    Get or create FSM storage instance for state checking.

    Returns:
        Shared FSM storage instance
    """
    global _fsm_storage
    if _fsm_storage is None:
        _fsm_storage = RedisStorage.from_url(app_settings.redis_url)
    return _fsm_storage


async def close_fsm_storage() -> None:
    """Close FSM storage and cleanup connections."""
    global _fsm_storage
    if _fsm_storage is not None:
        await _fsm_storage.close()
        _fsm_storage = None
        logger.info("FSM storage closed")
```

**Update main.py:**
```python
# services/tracker_activity_bot/src/main.py
from src.api.handlers.poll import close_fsm_storage

async def main() -> None:
    """Main bot entry point."""
    logger.info("Starting tracker_activity_bot")

    # ... existing initialization code ...

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        # Cleanup
        scheduler_service.stop()
        logger.info("Scheduler stopped")

        # Close FSM storage - FIX MEMORY LEAK!
        await close_fsm_storage()
        logger.info("FSM storage closed")

        await bot.session.close()
        await storage.close()
```

**Checklist:**
- [ ] Add `close_fsm_storage()` function to poll.py
- [ ] Call `close_fsm_storage()` in main.py finally block
- [ ] Test bot restarts without "too many open files" error
- [ ] Monitor memory usage over 24 hours

---

### Task 1.5.2: Fix HTTP Client Leak in Bot Service

**Priority:** 🔴🔴 CRITICAL URGENT
**Estimated Time:** 1 hour
**Impact:** HTTP connection pool leak, memory leak

**Current Problem:**
```python
# ❌ WRONG: services/tracker_activity_bot/src/main.py
# HTTP client created but NEVER closed!
# Global instances in handlers:
# - activity.py:26: api_client = DataAPIClient()
# - categories.py: api_client = DataAPIClient()
# All are NEVER closed!
```

**Why This is Critical:**
- `httpx.AsyncClient` holds connection pool (default 100 connections)
- Each connection holds socket + memory
- Multiple global instances = multiple pools!
- NEVER closed = connections stay open forever
- Eventually: "too many open connections" error

**Solution:**

Already documented in **Task 2.5: Implement Dependency Injection**, but needs to be done FIRST!

**Quick fix (before full DI refactor):**
```python
# services/tracker_activity_bot/src/main.py
from src.api.handlers import activity, categories

async def main() -> None:
    """Main bot entry point."""
    # ... existing code ...

    try:
        await dp.start_polling(bot)
    finally:
        # Close all HTTP clients - FIX MEMORY LEAK!
        if hasattr(activity, 'api_client'):
            await activity.api_client.close()
            logger.info("Activity HTTP client closed")

        if hasattr(categories, 'api_client'):
            await categories.api_client.close()
            logger.info("Categories HTTP client closed")

        # ... rest of cleanup ...
```

**Long-term fix:** Implement Task 2.5 (Dependency Injection) to use single shared client.

**Checklist:**
- [ ] Add HTTP client cleanup to main.py finally block
- [ ] Close ALL global api_client instances
- [ ] Test bot restarts without connection leaks
- [ ] Monitor connection count: `netstat -an | grep ESTABLISHED | wc -l`

---

### Task 1.5.3: Fix Multiple Redis Storage Instances in fsm_timeout_service.py

**Priority:** 🟠 HIGH
**Estimated Time:** 2 hours
**Impact:** Connection pool inefficiency, potential memory leak

**Current Problem:**
```python
# ❌ INEFFICIENT: services/tracker_activity_bot/src/application/services/fsm_timeout_service.py

async def send_reminder(bot: Bot, user_id: int, state: State, action: str):
    """Send reminder to user about unfinished dialog."""
    try:
        # Line 172: Creates NEW RedisStorage every time!
        storage = RedisStorage.from_url(app_settings.redis_url)  # New connection pool!

        # ... use storage ...

        await storage.close()  # Closes after use (OK)
        # BUT: Creating new pool each time is INEFFICIENT!

async def cleanup_stale_state(bot: Bot, user_id: int, state: State):
    """Cleanup stale FSM state."""
    try:
        # Line 232: AGAIN creates NEW RedisStorage!
        storage = RedisStorage.from_url(app_settings.redis_url)  # Another new pool!

        # ... use storage ...

        await storage.close()  # Closes after use (OK)
```

**Why This is Problematic:**
- Each `RedisStorage.from_url()` creates NEW connection pool
- Connection pool creation is expensive (DNS, handshake, auth)
- Happening on EVERY reminder/cleanup (every 10-13 minutes)
- Unnecessary overhead, slower performance

**Solution:**
```python
# ✅ CORRECT: Reuse shared FSM storage
# services/tracker_activity_bot/src/application/services/fsm_timeout_service.py

async def send_reminder(bot: Bot, user_id: int, state: State, action: str):
    """Send reminder to user about unfinished dialog."""
    try:
        # Reuse bot's main FSM storage instead of creating new one!
        from aiogram.fsm.context import FSMContext

        # Get storage from bot's dispatcher (passed via context)
        # OR: Use shared get_fsm_storage() from poll.py
        from src.api.handlers.poll import get_fsm_storage

        storage = get_fsm_storage()  # Reuses existing pool!

        # Check if user is still in same state
        key = StorageKey(
            bot_id=bot.id,
            chat_id=user_id,
            user_id=user_id
        )

        current_state = await storage.get_state(key)

        if current_state != state.state:
            logger.info(
                f"User {user_id} no longer in state '{state.state}', skipping reminder"
            )
            return

        # Send reminder with 'Continue' button
        from src.api.keyboards.fsm_reminder import get_fsm_reminder_keyboard

        text = (
            f"⏰ Напоминание\n\n"
            f"Ты начал {action}, но не закончил.\n\n"
            f"Хочешь продолжить?"
        )

        await bot.send_message(
            chat_id=user_id,
            text=text,
            reply_markup=get_fsm_reminder_keyboard()
        )

        logger.info(f"Sent FSM reminder to user {user_id}")

        # Schedule cleanup
        from src.application.services.scheduler_service import scheduler_service
        fsm_timeout_service._schedule_cleanup(bot, user_id, state)

        # DON'T close storage here - it's shared!

    except Exception as e:
        logger.error(f"Error sending FSM reminder to user {user_id}: {e}")


async def cleanup_stale_state(bot: Bot, user_id: int, state: State):
    """Cleanup stale FSM state and send poll immediately."""
    try:
        # Reuse shared storage
        from src.api.handlers.poll import get_fsm_storage

        storage = get_fsm_storage()  # Reuses existing pool!

        # Check if user is still in same state
        key = StorageKey(
            bot_id=bot.id,
            chat_id=user_id,
            user_id=user_id
        )

        current_state = await storage.get_state(key)

        if current_state != state.state:
            logger.info(
                f"User {user_id} no longer in state '{state.state}', skipping cleanup"
            )
            return

        # Silently clear FSM state
        await storage.set_state(key, None)
        await storage.set_data(key, {})

        logger.info(f"Cleared stale FSM state for user {user_id}: {state.state}")

        # Send automatic poll immediately
        from src.api.handlers.poll import send_automatic_poll

        try:
            await send_automatic_poll(bot, user_id)
            logger.info(f"Sent immediate poll after FSM cleanup for user {user_id}")
        except Exception as e:
            logger.error(
                f"Error sending poll after FSM cleanup for user {user_id}: {e}"
            )

        # DON'T close storage here - it's shared!

    except Exception as e:
        logger.error(f"Error cleaning up FSM state for user {user_id}: {e}")
```

**Checklist:**
- [ ] Replace `RedisStorage.from_url()` with `get_fsm_storage()`
- [ ] Remove `await storage.close()` calls (storage is shared)
- [ ] Test reminders and cleanup still work
- [ ] Monitor Redis connection count

---

### Task 1.5.4: Fix Bare except:pass Without Logging

**Priority:** 🟠 HIGH
**Estimated Time:** 30 min
**Impact:** Silent failures, impossible to debug

**Current Problem:**
```python
# ❌ WRONG: services/tracker_activity_bot/src/application/services/scheduler_service.py:103
if user_id in self.jobs:
    try:
        self.scheduler.remove_job(self.jobs[user_id])
    except Exception:
        pass  # ⚠️ Silently swallows ALL exceptions!

# ❌ WRONG: services/tracker_activity_bot/src/api/handlers/poll.py:107
# (similar issue)
```

**Why This is Problematic:**
- `except: pass` silently swallows ALL exceptions
- No way to know something went wrong
- Impossible to debug production issues
- Violates logging best practices

**Solution:**
```python
# ✅ CORRECT: Log the exception
if user_id in self.jobs:
    try:
        self.scheduler.remove_job(self.jobs[user_id])
    except Exception as e:
        logger.warning(
            "Failed to remove scheduler job",
            extra={
                "user_id": user_id,
                "job_id": self.jobs.get(user_id),
                "error": str(e),
                "error_type": type(e).__name__
            }
        )
```

**Checklist:**
- [ ] Find all `except: pass` blocks
- [ ] Add logging with context
- [ ] Use appropriate log level (warning/error)
- [ ] Test error scenarios are logged

---

### Task 1.5.5: Migrate from Deprecated @app.on_event()

**Priority:** 🟠 HIGH
**Estimated Time:** 1 hour
**Impact:** Will break in future FastAPI versions

**Current Problem:**
```python
# ❌ DEPRECATED: services/data_postgres_api/src/main.py:37, 50
@app.on_event("startup")  # Deprecated in FastAPI 0.93+
async def startup_event():
    """Application startup tasks."""
    # ...

@app.on_event("shutdown")  # Deprecated in FastAPI 0.93+
async def shutdown_event():
    """Cleanup on shutdown."""
    # ...
```

**Why This is Problematic:**
- `@app.on_event()` is deprecated since FastAPI 0.93
- Will be removed in future versions
- Breaking change will happen without warning

**Solution:**
```python
# ✅ CORRECT: Use lifespan context manager
# services/data_postgres_api/src/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.

    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting data_postgres_api service")

    if settings.enable_db_auto_create:
        logger.warning("Auto-creating database tables (development mode only!)")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Shutting down data_postgres_api service")
    await engine.dispose()
    logger.info("Database engine disposed")


# Create FastAPI app with lifespan
app = FastAPI(
    title=settings.app_name,
    description="HTTP Data Access Service for PostgreSQL",
    version="1.0.0",
    lifespan=lifespan  # Use lifespan context manager
)

# Remove old event handlers
# @app.on_event("startup")  # DELETE
# @app.on_event("shutdown")  # DELETE
```

**Checklist:**
- [ ] Create `lifespan()` context manager
- [ ] Pass `lifespan=lifespan` to FastAPI()
- [ ] Remove `@app.on_event()` decorators
- [ ] Test startup and shutdown work correctly

---

### Task 1.5.6: Add Graceful Shutdown Signal Handlers

**Priority:** 🟡 MEDIUM
**Estimated Time:** 1-2 hours
**Impact:** Prevents data loss on container stop

**Current Problem:**
- No SIGTERM/SIGINT handlers
- When Docker stops container, bot killed immediately
- Pending jobs may be lost
- Database transactions may be interrupted

**Solution:**
```python
# services/tracker_activity_bot/src/main.py
import signal
import asyncio

# Global flag for graceful shutdown
_shutdown_event = asyncio.Event()


def handle_shutdown_signal(signum, frame):
    """
    Handle shutdown signals (SIGTERM, SIGINT).

    Args:
        signum: Signal number
        frame: Current stack frame
    """
    logger.info(
        "Received shutdown signal",
        extra={"signal": signal.Signals(signum).name}
    )
    _shutdown_event.set()


async def main() -> None:
    """Main bot entry point."""
    # Register signal handlers
    signal.signal(signal.SIGTERM, handle_shutdown_signal)
    signal.signal(signal.SIGINT, handle_shutdown_signal)
    logger.info("Signal handlers registered")

    logger.info("Starting tracker_activity_bot")

    # ... existing initialization ...

    try:
        # Start polling with graceful shutdown
        polling_task = asyncio.create_task(
            dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
        )

        # Wait for either polling to complete or shutdown signal
        await asyncio.wait(
            [polling_task, asyncio.create_task(_shutdown_event.wait())],
            return_when=asyncio.FIRST_COMPLETED
        )

        if _shutdown_event.is_set():
            logger.info("Graceful shutdown initiated")
            polling_task.cancel()
            try:
                await polling_task
            except asyncio.CancelledError:
                logger.info("Polling task cancelled")

    finally:
        # Cleanup
        scheduler_service.stop()
        logger.info("Scheduler stopped")

        # Close FSM storage
        await close_fsm_storage()
        logger.info("FSM storage closed")

        await bot.session.close()
        await storage.close()

        logger.info("Bot shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
```

**Checklist:**
- [ ] Add signal handlers for SIGTERM/SIGINT
- [ ] Implement graceful shutdown logic
- [ ] Test `docker compose stop` doesn't lose data
- [ ] Test `docker compose restart` works cleanly

---

### Task 1.5.7: Improve Scheduler Shutdown

**Priority:** 🟡 MEDIUM
**Estimated Time:** 30 min
**Impact:** Prevents job loss on shutdown

**Current Problem:**
```python
# ❌ services/tracker_activity_bot/src/application/services/scheduler_service.py:45
def stop(self):
    """Stop the scheduler."""
    if self.scheduler.running:
        self.scheduler.shutdown()  # May not wait for pending jobs!
        logger.info("Scheduler stopped")
```

**Solution:**
```python
# ✅ CORRECT: Wait for pending jobs
def stop(self, wait: bool = True):
    """
    Stop the scheduler.

    Args:
        wait: If True, wait for pending jobs to complete
    """
    if self.scheduler.running:
        self.scheduler.shutdown(wait=wait)
        if wait:
            logger.info("Scheduler stopped (waited for pending jobs)")
        else:
            logger.info("Scheduler stopped (did not wait for jobs)")
```

**Checklist:**
- [ ] Add `wait=True` parameter to `scheduler.shutdown()`
- [ ] Test shutdown waits for jobs to complete
- [ ] Add timeout if needed

---

## Phase 1.5 Summary

**Total Estimated Time:** 4-6 hours

**Immediate Actions (Day 1):**
1. ✅ Task 1.5.1: Fix global FSM storage leak (1 hour) — CRITICAL
2. ✅ Task 1.5.2: Fix HTTP client leak (1 hour) — CRITICAL

**Short-term (Day 2):**
3. ✅ Task 1.5.3: Fix multiple Redis instances (2 hours) — HIGH
4. ✅ Task 1.5.4: Fix bare except:pass (30 min) — HIGH
5. ✅ Task 1.5.5: Migrate from deprecated @app.on_event() (1 hour) — HIGH

**Nice to Have (Day 3):**
6. ✅ Task 1.5.6: Add signal handlers (1-2 hours) — MEDIUM
7. ✅ Task 1.5.7: Improve scheduler shutdown (30 min) — MEDIUM

**Success Criteria:**
- [ ] Bot can run for 7+ days without memory leaks
- [ ] No "too many open files" errors
- [ ] No "too many connections" errors
- [ ] Clean shutdown without errors
- [ ] All exceptions are logged

**Monitoring After Fixes:**
```bash
# Monitor memory usage
docker stats tracker_activity_bot

# Monitor open files
docker exec tracker_activity_bot sh -c 'ls /proc/$$/fd | wc -l'

# Monitor connections
docker exec tracker_activity_bot sh -c 'netstat -an | grep ESTABLISHED | wc -l'

# Monitor Redis connections
docker exec tracker_redis redis-cli CLIENT LIST | wc -l
```

---

## 🔴 PHASE 2: Type Safety & Quality (CRITICAL - Week 1-2)

**Estimated Time:** 16-20 hours
**Priority:** 🔴 CRITICAL (blocks Level 2 transition)
**ADR Reference:** Section "Phase 2: Type Safety & Quality"

---

### Task 2.1: Create Application Service Layer in data_postgres_api

**Priority:** 🔴 CRITICAL
**Estimated Time:** 4-5 hours
**ADR Reference:** ADR Section "1. HTTP-Only Data Access", "2. DDD/Hexagonal Architecture"

**Current Problem:**
```python
# ❌ WRONG: services/data_postgres_api/src/api/v1/activities.py:16-24
@router.post("/", response_model=ActivityResponse)
async def create_activity(
    activity_data: ActivityCreate,
    db: AsyncSession = Depends(get_db)
) -> ActivityResponse:
    """Create a new activity."""
    repository = ActivityRepository(db)  # Direct repository call!
    activity = await repository.create(activity_data)
    return ActivityResponse.model_validate(activity)
```

**Goal:**
Create Application Service layer that orchestrates business logic and repository calls.

**Steps:**

#### Step 2.1.1: Create Directory Structure (5 min)
```bash
mkdir -p services/data_postgres_api/src/application/services
touch services/data_postgres_api/src/application/__init__.py
touch services/data_postgres_api/src/application/services/__init__.py
```

#### Step 2.1.2: Create ActivityService (45 min)
```python
# ✅ CORRECT: services/data_postgres_api/src/application/services/activity_service.py
"""
Activity application service.

This module contains business logic for activity operations.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models.activity import Activity
from src.infrastructure.repositories.activity_repository import ActivityRepository
from src.schemas.activity import ActivityCreate


class ActivityService:
    """
    Application service for activity business logic.

    Orchestrates repository calls and business rules.
    Does NOT contain infrastructure concerns (HTTP, DB).
    """

    def __init__(self, repository: ActivityRepository):
        """
        Initialize service with repository.

        Args:
            repository: Activity repository instance
        """
        self.repository = repository

    async def create_activity(self, activity_data: ActivityCreate) -> Activity:
        """
        Create new activity with business validation.

        Args:
            activity_data: Activity creation data

        Returns:
            Created activity with generated ID

        Raises:
            ValueError: If business rules violated
        """
        # Business validation can go here
        # Example: Check if user has permission, validate time ranges, etc.

        activity = await self.repository.create(activity_data)
        return activity

    async def get_activity_by_id(self, activity_id: int) -> Optional[Activity]:
        """
        Get activity by ID.

        Args:
            activity_id: Activity identifier

        Returns:
            Activity if found, None otherwise
        """
        return await self.repository.get_by_id(activity_id)

    async def get_user_activities(
        self,
        user_id: int,
        limit: int = 10,
        offset: int = 0
    ) -> tuple[list[Activity], int]:
        """
        Get paginated activities for user.

        Args:
            user_id: User identifier
            limit: Maximum activities to return
            offset: Number of activities to skip

        Returns:
            Tuple of (activities list, total count)
        """
        return await self.repository.get_by_user(user_id, limit, offset)
```

#### Step 2.1.3: Create CategoryService (30 min)
```python
# services/data_postgres_api/src/application/services/category_service.py
"""Category application service."""

from typing import Optional

from src.domain.models.category import Category
from src.infrastructure.repositories.category_repository import CategoryRepository
from src.schemas.category import CategoryCreate


class CategoryService:
    """Application service for category business logic."""

    def __init__(self, repository: CategoryRepository):
        """
        Initialize service with repository.

        Args:
            repository: Category repository instance
        """
        self.repository = repository

    async def create_category(self, category_data: CategoryCreate) -> Category:
        """
        Create new category.

        Args:
            category_data: Category creation data

        Returns:
            Created category

        Raises:
            ValueError: If category name already exists for user
        """
        # Business rule: Check for duplicate category name
        existing = await self.repository.get_by_user_and_name(
            category_data.user_id,
            category_data.name
        )
        if existing:
            raise ValueError(f"Category '{category_data.name}' already exists")

        return await self.repository.create(category_data)

    async def get_user_categories(self, user_id: int) -> list[Category]:
        """
        Get all categories for user.

        Args:
            user_id: User identifier

        Returns:
            List of user categories
        """
        return await self.repository.get_by_user(user_id)

    async def delete_category(self, category_id: int) -> bool:
        """
        Delete category by ID.

        Args:
            category_id: Category identifier

        Returns:
            True if deleted, False if not found

        Raises:
            ValueError: If trying to delete default category
        """
        category = await self.repository.get_by_id(category_id)
        if not category:
            return False

        if category.is_default:
            raise ValueError("Cannot delete default category")

        await self.repository.delete(category_id)
        return True
```

#### Step 2.1.4: Create UserService (30 min)
```python
# services/data_postgres_api/src/application/services/user_service.py
"""User application service."""

from typing import Optional

from src.domain.models.user import User
from src.infrastructure.repositories.user_repository import UserRepository
from src.schemas.user import UserCreate


class UserService:
    """Application service for user business logic."""

    def __init__(self, repository: UserRepository):
        """
        Initialize service with repository.

        Args:
            repository: User repository instance
        """
        self.repository = repository

    async def create_user(self, user_data: UserCreate) -> User:
        """
        Create new user.

        Args:
            user_data: User creation data

        Returns:
            Created user

        Raises:
            ValueError: If telegram_id already exists
        """
        # Check for existing user
        existing = await self.repository.get_by_telegram_id(user_data.telegram_id)
        if existing:
            raise ValueError(f"User with telegram_id {user_data.telegram_id} already exists")

        return await self.repository.create(user_data)

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """
        Get user by Telegram ID.

        Args:
            telegram_id: Telegram user ID

        Returns:
            User if found, None otherwise
        """
        return await self.repository.get_by_telegram_id(telegram_id)
```

#### Step 2.1.5: Create Dependencies Module (30 min)
```python
# services/data_postgres_api/src/api/dependencies.py
"""
Dependency injection providers for FastAPI.

This module provides dependency injection for services and repositories.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.connection import get_db
from src.infrastructure.repositories.activity_repository import ActivityRepository
from src.infrastructure.repositories.category_repository import CategoryRepository
from src.infrastructure.repositories.user_repository import UserRepository
from src.application.services.activity_service import ActivityService
from src.application.services.category_service import CategoryService
from src.application.services.user_service import UserService


# Repository dependencies

async def get_activity_repository(
    db: AsyncSession = Depends(get_db)
) -> ActivityRepository:
    """
    Provide activity repository instance.

    Args:
        db: Database session

    Returns:
        Activity repository
    """
    return ActivityRepository(db)


async def get_category_repository(
    db: AsyncSession = Depends(get_db)
) -> CategoryRepository:
    """
    Provide category repository instance.

    Args:
        db: Database session

    Returns:
        Category repository
    """
    return CategoryRepository(db)


async def get_user_repository(
    db: AsyncSession = Depends(get_db)
) -> UserRepository:
    """
    Provide user repository instance.

    Args:
        db: Database session

    Returns:
        User repository
    """
    return UserRepository(db)


# Service dependencies

async def get_activity_service(
    repository: ActivityRepository = Depends(get_activity_repository)
) -> ActivityService:
    """
    Provide activity service instance.

    Args:
        repository: Activity repository

    Returns:
        Activity service
    """
    return ActivityService(repository)


async def get_category_service(
    repository: CategoryRepository = Depends(get_category_repository)
) -> CategoryService:
    """
    Provide category service instance.

    Args:
        repository: Category repository

    Returns:
        Category service
    """
    return CategoryService(repository)


async def get_user_service(
    repository: UserRepository = Depends(get_user_repository)
) -> UserService:
    """
    Provide user service instance.

    Args:
        repository: User repository

    Returns:
        User service
    """
    return UserService(repository)
```

#### Step 2.1.6: Update API Routes to Use Services (1 hour)
```python
# ✅ CORRECT: services/data_postgres_api/src/api/v1/activities.py
"""Activities API router with service layer."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Annotated

from src.api.dependencies import get_activity_service
from src.application.services.activity_service import ActivityService
from src.schemas.activity import (
    ActivityCreate,
    ActivityResponse,
    ActivityListResponse,
)

router = APIRouter(prefix="/activities", tags=["activities"])


@router.post(
    "/",
    response_model=ActivityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create activity",
    description="Create new activity record"
)
async def create_activity(
    activity_data: ActivityCreate,
    service: Annotated[ActivityService, Depends(get_activity_service)]
) -> ActivityResponse:
    """
    Create new activity.

    Args:
        activity_data: Activity creation data
        service: Activity service (injected)

    Returns:
        Created activity with generated ID

    Raises:
        HTTPException: 400 if validation fails
    """
    try:
        activity = await service.create_activity(activity_data)
        return ActivityResponse.model_validate(activity)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/",
    response_model=ActivityListResponse,
    summary="List activities",
    description="Get paginated activities for user"
)
async def get_activities(
    user_id: Annotated[int, Query(description="User ID")],
    limit: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 10,
    offset: Annotated[int, Query(ge=0, description="Items to skip")] = 0,
    service: Annotated[ActivityService, Depends(get_activity_service)] = None
) -> ActivityListResponse:
    """
    Get activities for user with pagination.

    Args:
        user_id: User identifier
        limit: Maximum activities to return
        offset: Number of activities to skip
        service: Activity service (injected)

    Returns:
        Paginated list of activities
    """
    activities, total = await service.get_user_activities(user_id, limit, offset)

    return ActivityListResponse(
        total=total,
        items=[ActivityResponse.model_validate(act) for act in activities]
    )
```

#### Step 2.1.7: Update Other Routes (1.5 hours)

Apply same pattern to:
- `src/api/v1/categories.py`
- `src/api/v1/users.py`
- `src/api/v1/user_settings.py`

**Checklist:**
- [ ] Create `application/services/` directory
- [ ] Implement `ActivityService`
- [ ] Implement `CategoryService`
- [ ] Implement `UserService`
- [ ] Implement `UserSettingsService`
- [ ] Create `api/dependencies.py`
- [ ] Update `api/v1/activities.py`
- [ ] Update `api/v1/categories.py`
- [ ] Update `api/v1/users.py`
- [ ] Update `api/v1/user_settings.py`
- [ ] Test all endpoints still work

---

### Task 2.2: Add mypy Configuration (Strict Mode)

**Priority:** 🔴 CRITICAL
**Estimated Time:** 2-3 hours
**ADR Reference:** ADR Section "5. Type Safety"

**Goal:**
Enable mypy strict mode and fix all type violations.

**Steps:**

#### Step 2.2.1: Create pyproject.toml for data_postgres_api (15 min)
```toml
# services/data_postgres_api/pyproject.toml
[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_any_generics = true
disallow_subclassing_any = true
disallow_untyped_calls = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
warn_unreachable = true
strict_equality = true

# Ignore third-party libraries without stubs
[[tool.mypy.overrides]]
module = "asyncpg.*"
ignore_missing_imports = true

[[tool.mypy.overrides]]
module = "alembic.*"
ignore_missing_imports = true

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "N",   # pep8-naming
    "UP",  # pyupgrade
    "ANN", # flake8-annotations
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "DTZ", # flake8-datetimez
    "T10", # flake8-debugger
    "PL",  # pylint
    "RUF", # ruff-specific
]
ignore = [
    "ANN101", # Missing type annotation for self
    "ANN102", # Missing type annotation for cls
]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --tb=short --strict-markers"
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "smoke: Smoke tests",
]
```

#### Step 2.2.2: Create pyproject.toml for tracker_activity_bot (15 min)
```toml
# services/tracker_activity_bot/pyproject.toml
[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_any_generics = true
disallow_incomplete_defs = true
check_untyped_defs = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true

# Ignore third-party libraries
[[tool.mypy.overrides]]
module = "aiogram.*"
ignore_missing_imports = true

[[tool.mypy.overrides]]
module = "apscheduler.*"
ignore_missing_imports = true

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "W", "F", "I", "N", "UP", "ANN", "B", "C4", "DTZ", "T10", "PL", "RUF"]
ignore = ["ANN101", "ANN102"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = "-v --tb=short"
markers = [
    "unit: Unit tests",
    "smoke: Smoke tests",
]
```

#### Step 2.2.3: Run mypy and Fix Violations (2 hours)
```bash
# Run mypy on data_postgres_api
cd services/data_postgres_api
mypy src/ > mypy_report.txt 2>&1

# Run mypy on tracker_activity_bot
cd services/tracker_activity_bot
mypy src/ > mypy_report.txt 2>&1

# Fix violations iteratively
# Common issues:
# 1. Missing return type annotations
# 2. Using Any instead of specific types
# 3. Missing parameter type hints
# 4. Untyped decorators
```

#### Step 2.2.4: Update Makefile (10 min)
```makefile
# Add to Makefile
type-check: ## Run mypy type checking
	@echo "Type checking data_postgres_api..."
	cd services/data_postgres_api && mypy src/
	@echo "\nType checking tracker_activity_bot..."
	cd services/tracker_activity_bot && mypy src/

type-check-report: ## Generate mypy HTML report
	@echo "Generating type check reports..."
	cd services/data_postgres_api && mypy src/ --html-report mypy-report
	cd services/tracker_activity_bot && mypy src/ --html-report mypy-report
```

**Checklist:**
- [ ] Create `pyproject.toml` in data_postgres_api
- [ ] Create `pyproject.toml` in tracker_activity_bot
- [ ] Run mypy on both services
- [ ] Fix all type violations
- [ ] Update Makefile with `type-check` target
- [ ] Verify `make type-check` passes

---

### Task 2.3: Add Complete Type Hints to HTTP Clients

**Priority:** 🔴 CRITICAL
**Estimated Time:** 3-4 hours
**ADR Reference:** ADR Section "5. Type Safety"

**Current Problem:**
```python
# ❌ WRONG: HTTP client returns untyped dict
async def get(self, path: str, **kwargs):  # No return type!
    response = await self.client.get(path, **kwargs)
    return response.json()  # Returns Any

async def create_activity(...) -> dict:  # Returns dict instead of model
    return await self.client.post("/api/v1/activities", json={...})
```

**Goal:**
All HTTP client methods return typed Pydantic models.

**Steps:**

#### Step 2.3.1: Create Response Models in Bot Service (1 hour)
```python
# services/tracker_activity_bot/src/schemas/__init__.py
"""Response models for Data API communication."""

from .activity import ActivityResponse, ActivityListResponse
from .category import CategoryResponse
from .user import UserResponse
from .user_settings import UserSettingsResponse

__all__ = [
    "ActivityResponse",
    "ActivityListResponse",
    "CategoryResponse",
    "UserResponse",
    "UserSettingsResponse",
]
```

```python
# services/tracker_activity_bot/src/schemas/activity.py
"""Activity response models."""

from datetime import datetime
from pydantic import BaseModel, Field


class ActivityResponse(BaseModel):
    """Activity response from Data API."""

    id: int = Field(..., description="Activity ID")
    user_id: int = Field(..., description="User ID")
    category_id: int | None = Field(None, description="Category ID")
    description: str = Field(..., description="Activity description")
    tags: str | None = Field(None, description="Comma-separated tags")
    start_time: datetime = Field(..., description="Start time (UTC)")
    end_time: datetime = Field(..., description="End time (UTC)")
    duration_minutes: int = Field(..., description="Duration in minutes")
    created_at: datetime = Field(..., description="Created timestamp")

    class Config:
        """Pydantic config."""
        from_attributes = True


class ActivityListResponse(BaseModel):
    """Paginated activity list response."""

    total: int = Field(..., description="Total count")
    items: list[ActivityResponse] = Field(..., description="Activity items")
```

```python
# services/tracker_activity_bot/src/schemas/category.py
"""Category response models."""

from datetime import datetime
from pydantic import BaseModel, Field


class CategoryResponse(BaseModel):
    """Category response from Data API."""

    id: int = Field(..., description="Category ID")
    user_id: int = Field(..., description="User ID")
    name: str = Field(..., description="Category name")
    emoji: str | None = Field(None, description="Category emoji")
    is_default: bool = Field(False, description="Is default category")
    created_at: datetime = Field(..., description="Created timestamp")

    class Config:
        """Pydantic config."""
        from_attributes = True
```

```python
# services/tracker_activity_bot/src/schemas/user.py
"""User response models."""

from datetime import datetime
from pydantic import BaseModel, Field


class UserResponse(BaseModel):
    """User response from Data API."""

    id: int = Field(..., description="User ID")
    telegram_id: int = Field(..., description="Telegram user ID")
    username: str | None = Field(None, description="Telegram username")
    first_name: str | None = Field(None, description="First name")
    timezone: str = Field("UTC", description="User timezone")
    created_at: datetime = Field(..., description="Created timestamp")

    class Config:
        """Pydantic config."""
        from_attributes = True
```

#### Step 2.3.2: Update Base HTTP Client (1 hour)
```python
# ✅ CORRECT: services/tracker_activity_bot/src/infrastructure/http_clients/http_client.py
"""Base HTTP client for data API communication."""

import logging
import time
from typing import Any, TypeVar, Type

import httpx
from pydantic import BaseModel

from src.core.config import settings

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


class DataAPIClient:
    """
    Base HTTP client for communication with data_postgres_api.

    Provides type-safe HTTP methods with automatic JSON serialization/deserialization.
    """

    def __init__(self) -> None:
        """Initialize HTTP client with base URL from settings."""
        self.base_url = settings.data_api_url
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=10.0,
            follow_redirects=True
        )

    async def get(
        self,
        path: str,
        response_model: Type[T],
        **kwargs: Any
    ) -> T:
        """
        Make GET request with type-safe response.

        Args:
            path: API endpoint path
            response_model: Pydantic model for response deserialization
            **kwargs: Additional request parameters

        Returns:
            Parsed response as Pydantic model

        Raises:
            HTTPError: If request fails
            ValidationError: If response doesn't match model
        """
        logger.debug(
            "HTTP GET request",
            extra={
                "method": "GET",
                "path": path,
                "base_url": self.base_url,
                "params": kwargs.get("params")
            }
        )
        start_time = time.time()

        try:
            response = await self.client.get(path, **kwargs)
            duration_ms = (time.time() - start_time) * 1000

            logger.debug(
                "HTTP GET response",
                extra={
                    "method": "GET",
                    "path": path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                    "response_size": len(response.content) if response.content else 0
                }
            )

            response.raise_for_status()
            data = response.json()
            return response_model(**data)

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                "HTTP GET failed",
                extra={
                    "method": "GET",
                    "path": path,
                    "duration_ms": round(duration_ms, 2),
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            )
            raise

    async def post(
        self,
        path: str,
        response_model: Type[T],
        **kwargs: Any
    ) -> T:
        """
        Make POST request with type-safe response.

        Args:
            path: API endpoint path
            response_model: Pydantic model for response deserialization
            **kwargs: Additional request parameters (json, data, etc.)

        Returns:
            Parsed response as Pydantic model

        Raises:
            HTTPError: If request fails
            ValidationError: If response doesn't match model
        """
        logger.debug(
            "HTTP POST request",
            extra={
                "method": "POST",
                "path": path,
                "base_url": self.base_url,
                "has_json": "json" in kwargs,
                "has_data": "data" in kwargs
            }
        )
        start_time = time.time()

        try:
            response = await self.client.post(path, **kwargs)
            duration_ms = (time.time() - start_time) * 1000

            logger.debug(
                "HTTP POST response",
                extra={
                    "method": "POST",
                    "path": path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                    "response_size": len(response.content) if response.content else 0
                }
            )

            response.raise_for_status()
            data = response.json()
            return response_model(**data)

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                "HTTP POST failed",
                extra={
                    "method": "POST",
                    "path": path,
                    "duration_ms": round(duration_ms, 2),
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            )
            raise

    async def close(self) -> None:
        """Close HTTP client connection."""
        await self.client.aclose()
```

#### Step 2.3.3: Update Activity Service Client (30 min)
```python
# ✅ CORRECT: services/tracker_activity_bot/src/infrastructure/http_clients/activity_service.py
"""Activity service HTTP client."""

from datetime import datetime

from src.infrastructure.http_clients.http_client import DataAPIClient
from src.schemas.activity import ActivityResponse, ActivityListResponse


class ActivityService:
    """Service for activity-related operations via HTTP."""

    def __init__(self, client: DataAPIClient):
        """
        Initialize service with HTTP client.

        Args:
            client: Data API HTTP client
        """
        self.client = client

    async def create_activity(
        self,
        user_id: int,
        category_id: int | None,
        description: str,
        tags: list[str] | None,
        start_time: datetime,
        end_time: datetime
    ) -> ActivityResponse:
        """
        Create new activity via Data API.

        Args:
            user_id: User identifier
            category_id: Category identifier or None
            description: Activity description
            tags: Optional tags list
            start_time: Start timestamp (UTC)
            end_time: End timestamp (UTC)

        Returns:
            Created activity with generated ID

        Raises:
            HTTPError: If Data API returns error
        """
        return await self.client.post(
            "/api/v1/activities",
            response_model=ActivityResponse,
            json={
                "user_id": user_id,
                "category_id": category_id,
                "description": description,
                "tags": tags,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat()
            }
        )

    async def get_user_activities(
        self,
        user_id: int,
        limit: int = 10,
        offset: int = 0
    ) -> ActivityListResponse:
        """
        Get paginated activities for user.

        Args:
            user_id: User identifier
            limit: Maximum activities to return
            offset: Number of activities to skip

        Returns:
            Paginated activity list

        Raises:
            HTTPError: If Data API returns error
        """
        return await self.client.get(
            "/api/v1/activities",
            response_model=ActivityListResponse,
            params={
                "user_id": user_id,
                "limit": limit,
                "offset": offset
            }
        )
```

#### Step 2.3.4: Update Other Service Clients (1 hour)

Apply same pattern to:
- `category_service.py`
- `user_service.py`
- `user_settings_service.py`

**Checklist:**
- [ ] Create `schemas/` directory in bot service
- [ ] Implement `ActivityResponse`, `ActivityListResponse`
- [ ] Implement `CategoryResponse`
- [ ] Implement `UserResponse`
- [ ] Implement `UserSettingsResponse`
- [ ] Update `DataAPIClient` with generic type support
- [ ] Update `ActivityService` to return typed models
- [ ] Update `CategoryService` to return typed models
- [ ] Update `UserService` to return typed models
- [ ] Update `UserSettingsService` to return typed models
- [ ] Run mypy to verify type safety

---

### Task 2.4: Add Comprehensive Docstrings

**Priority:** 🟠 HIGH
**Estimated Time:** 4-5 hours
**ADR Reference:** ADR Section "7. Structured Logging"

**Goal:**
All public functions have complete docstrings with Args/Returns/Raises sections.

**Pattern:**
```python
def function_name(arg1: Type1, arg2: Type2) -> ReturnType:
    """
    One-line summary.

    Detailed description if needed (optional).

    Args:
        arg1: Description of arg1
        arg2: Description of arg2

    Returns:
        Description of return value

    Raises:
        ExceptionType: When this exception is raised
        AnotherException: When another exception is raised
    """
    pass
```

**Files to Update:**
1. All handlers in `tracker_activity_bot/src/api/handlers/`
2. All services in `data_postgres_api/src/application/services/`
3. All repositories in `data_postgres_api/src/infrastructure/repositories/`
4. All HTTP clients in `tracker_activity_bot/src/infrastructure/http_clients/`

**Checklist:**
- [ ] Update activity.py handler
- [ ] Update categories.py handler
- [ ] Update settings.py handler
- [ ] Update poll.py handler
- [ ] Update all service classes
- [ ] Update all repository classes
- [ ] Update all HTTP client classes
- [ ] Verify with linter

---

### Task 2.5: Implement Dependency Injection in Bot Service

**Priority:** 🟠 HIGH
**Estimated Time:** 2-3 hours
**ADR Reference:** ADR Section "8. Error Handling Strategy"

**Current Problem:**
```python
# ❌ WRONG: Global instance
api_client = DataAPIClient()  # Global!

@router.callback_query(F.data == "add_activity")
async def handler(callback: types.CallbackQuery):
    activity_service = ActivityService(api_client)  # Uses global
```

**Goal:**
Use dependency injection instead of global instances.

**Steps:**

#### Step 2.5.1: Create Dependencies Module (1 hour)
```python
# services/tracker_activity_bot/src/api/dependencies.py
"""Dependency injection providers for bot handlers."""

from typing import AsyncGenerator

from src.infrastructure.http_clients.http_client import DataAPIClient
from src.infrastructure.http_clients.activity_service import ActivityService
from src.infrastructure.http_clients.category_service import CategoryService
from src.infrastructure.http_clients.user_service import UserService
from src.infrastructure.http_clients.user_settings_service import UserSettingsService


# HTTP Client instance (created once per bot lifetime)
_api_client: DataAPIClient | None = None


def get_api_client() -> DataAPIClient:
    """
    Get or create Data API HTTP client.

    Returns:
        Shared HTTP client instance
    """
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


# Service dependencies

def get_activity_service() -> ActivityService:
    """
    Provide activity service instance.

    Returns:
        Activity service with HTTP client
    """
    client = get_api_client()
    return ActivityService(client)


def get_category_service() -> CategoryService:
    """
    Provide category service instance.

    Returns:
        Category service with HTTP client
    """
    client = get_api_client()
    return CategoryService(client)


def get_user_service() -> UserService:
    """
    Provide user service instance.

    Returns:
        User service with HTTP client
    """
    client = get_api_client()
    return UserService(client)


def get_user_settings_service() -> UserSettingsService:
    """
    Provide user settings service instance.

    Returns:
        User settings service with HTTP client
    """
    client = get_api_client()
    return UserSettingsService(client)
```

#### Step 2.5.2: Update main.py with Cleanup (30 min)
```python
# services/tracker_activity_bot/src/main.py
"""Aiogram bot entry point for tracker_activity_bot service."""
import asyncio
import logging
from datetime import timedelta

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage

from src.core.config import settings
from src.core.logging import setup_logging
from src.api.dependencies import close_api_client  # Import cleanup
# ... other imports

# Configure structured JSON logging
setup_logging(service_name="tracker_activity_bot", log_level=settings.log_level)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Main bot entry point."""
    logger.info("Starting tracker_activity_bot")

    # Initialize bot and dispatcher
    bot = Bot(token=settings.telegram_bot_token)
    storage = RedisStorage.from_url(
        settings.redis_url,
        state_ttl=timedelta(minutes=15),
        data_ttl=timedelta(minutes=15)
    )
    dp = Dispatcher(storage=storage)

    # Register middleware
    dp.update.middleware(UserActionLoggingMiddleware())
    dp.update.middleware(FSMLoggingMiddleware())
    logger.info("Logging middleware registered")

    # Register routers
    dp.include_router(start_router)
    dp.include_router(activity_router)
    dp.include_router(categories_router)
    dp.include_router(settings_router)
    dp.include_router(poll_router)

    # Start scheduler
    scheduler_service.start()
    logger.info("Scheduler started for automatic polls")

    # Initialize FSM timeout service
    from src.application.services.fsm_timeout_service import FSMTimeoutService
    fsm_timeout_module.fsm_timeout_service = FSMTimeoutService(scheduler_service.scheduler)
    logger.info("FSM timeout service initialized")

    # Start polling
    logger.info("Bot started, polling...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        # Cleanup
        scheduler_service.stop()
        logger.info("Scheduler stopped")

        # Close HTTP client
        await close_api_client()
        logger.info("HTTP client closed")

        await bot.session.close()
        await storage.close()


if __name__ == "__main__":
    asyncio.run(main())
```

#### Step 2.5.3: Refactor Handlers to Use DI (1-1.5 hours)

**Note:** Aiogram doesn't have built-in DI like FastAPI, so we use factory functions.

```python
# Example: Refactor activity handler
from src.api.dependencies import get_activity_service, get_user_service, get_category_service

# Remove global instance:
# api_client = DataAPIClient()  # DELETE THIS

@router.callback_query(F.data == "add_activity")
@with_typing_action
@log_user_action("add_activity_button_clicked")
async def start_add_activity(callback: types.CallbackQuery, state: FSMContext):
    """Start activity recording process."""
    # Service created on demand
    # No global dependency!
    logger.debug(
        "Starting activity creation",
        extra={
            "user_id": callback.from_user.id,
            "username": callback.from_user.username
        }
    )
    await state.set_state(ActivityStates.waiting_for_start_time)
    # ... rest of handler
```

**Checklist:**
- [ ] Create `api/dependencies.py`
- [ ] Remove global `api_client` instances from handlers
- [ ] Use `get_*_service()` factories in handlers
- [ ] Add HTTP client cleanup to `main.py`
- [ ] Test all handlers still work

---

## 🟠 PHASE 3: Observability (HIGH - Week 3)

**Estimated Time:** 8-10 hours
**Priority:** 🟠 HIGH (required for Level 2)
**ADR Reference:** Section "Phase 3: Observability"

---

### Task 3.1: Improve Health Checks

**Priority:** 🟠 HIGH
**Estimated Time:** 1-2 hours
**ADR Reference:** ADR Section "8. Health Checks"

**Current Problem:**
```python
# ❌ WRONG: No DB connection verification
@app.get("/health")
async def health():
    return {"status": "healthy"}  # Lies! DB might be down
```

**Goal:**
Separate liveness and readiness probes with DB verification.

**Steps:**

#### Step 3.1.1: Update Health Endpoints (45 min)
```python
# ✅ CORRECT: services/data_postgres_api/src/main.py
from sqlalchemy import text
from fastapi import HTTPException

@app.get("/health/live", summary="Liveness probe")
async def liveness() -> dict[str, str]:
    """
    Check if service process is running.

    Returns:
        Status indicating service is alive

    Notes:
        This endpoint should ALWAYS return 200 unless process is dead.
        Does NOT check external dependencies.
    """
    return {"status": "alive"}


@app.get("/health/ready", summary="Readiness probe")
async def readiness(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """
    Check if service is ready to accept requests.

    Verifies:
        - Database connection works
        - Service can handle requests

    Args:
        db: Database session (injected)

    Returns:
        Status with database connection state

    Raises:
        HTTPException: 503 Service Unavailable if database unreachable
    """
    try:
        # Verify database connection
        await db.execute(text("SELECT 1"))
        return {
            "status": "ready",
            "database": "connected"
        }
    except Exception as e:
        logger.error(
            "Database health check failed",
            extra={
                "error": str(e),
                "error_type": type(e).__name__
            }
        )
        raise HTTPException(
            status_code=503,
            detail="Database connection failed"
        )
```

#### Step 3.1.2: Update Docker Healthcheck (15 min)
```yaml
# docker-compose.yml
services:
  data_postgres_api:
    build:
      context: .
      dockerfile: services/data_postgres_api/Dockerfile
    container_name: data_postgres_api
    environment:
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER:-tracker_user}:${POSTGRES_PASSWORD:-tracker_password}@postgres:5432/${POSTGRES_DB:-tracker_db}
      LOG_LEVEL: ${LOG_LEVEL:-INFO}
    env_file:
      - ./.env
    ports:
      - "8080:8000"
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/ready"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 10s
    networks:
      - tracker_network

  tracker_activity_bot:
    build:
      context: .
      dockerfile: services/tracker_activity_bot/Dockerfile
    container_name: tracker_activity_bot
    environment:
      TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN}
      DATA_API_URL: http://data_postgres_api:8000
      REDIS_URL: redis://redis:6379/0
      LOG_LEVEL: ${LOG_LEVEL:-INFO}
    env_file:
      - ./.env
    depends_on:
      data_postgres_api:
        condition: service_healthy  # Wait for API to be ready!
      redis:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - tracker_network
```

**Checklist:**
- [ ] Add `/health/live` endpoint
- [ ] Add `/health/ready` endpoint with DB check
- [ ] Update Docker healthcheck to use `/health/ready`
- [ ] Update bot dependency to wait for API readiness
- [ ] Test health checks work
- [ ] Test service restarts when DB is down

---

### Task 3.2: Add Correlation IDs

**Priority:** 🟡 MEDIUM
**Estimated Time:** 2-3 hours
**ADR Reference:** ADR Section "9. Error Handling Strategy"

**Goal:**
Add request correlation IDs for tracking requests across services.

**Steps:**

#### Step 3.2.1: Add Correlation ID Middleware to Data API (1 hour)
```python
# services/data_postgres_api/src/api/middleware/correlation.py
"""Correlation ID middleware for request tracing."""

import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

CORRELATION_ID_HEADER = "X-Correlation-ID"


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add correlation ID to all requests.

    Generates or extracts correlation ID from headers and
    adds it to response headers and logging context.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """
        Process request with correlation ID.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware in chain

        Returns:
            HTTP response with correlation ID header
        """
        # Extract or generate correlation ID
        correlation_id = request.headers.get(
            CORRELATION_ID_HEADER,
            str(uuid.uuid4())
        )

        # Add to request state
        request.state.correlation_id = correlation_id

        # Process request
        response = await call_next(request)

        # Add to response headers
        response.headers[CORRELATION_ID_HEADER] = correlation_id

        return response
```

#### Step 3.2.2: Register Middleware (15 min)
```python
# services/data_postgres_api/src/main.py
from src.api.middleware.correlation import CorrelationIDMiddleware

app = FastAPI(
    title=settings.app_name,
    description="HTTP Data Access Service for PostgreSQL",
    version="1.0.0",
)

# Add correlation ID middleware FIRST
app.add_middleware(CorrelationIDMiddleware)

# Then CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### Step 3.2.3: Add Correlation ID to Bot HTTP Client (1 hour)
```python
# services/tracker_activity_bot/src/infrastructure/http_clients/http_client.py
import uuid

class DataAPIClient:
    """Base HTTP client with correlation ID support."""

    def __init__(self) -> None:
        self.base_url = settings.data_api_url
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=10.0,
            follow_redirects=True
        )

    def _get_correlation_id(self) -> str:
        """
        Get or generate correlation ID for request.

        Returns:
            Correlation ID string
        """
        # TODO: Get from context if available (e.g., from Telegram update_id)
        return str(uuid.uuid4())

    async def get(
        self,
        path: str,
        response_model: Type[T],
        **kwargs: Any
    ) -> T:
        """Make GET request with correlation ID."""
        correlation_id = self._get_correlation_id()

        # Add correlation ID to headers
        headers = kwargs.get("headers", {})
        headers["X-Correlation-ID"] = correlation_id
        kwargs["headers"] = headers

        logger.debug(
            "HTTP GET request",
            extra={
                "method": "GET",
                "path": path,
                "correlation_id": correlation_id,
                "base_url": self.base_url,
                "params": kwargs.get("params")
            }
        )

        try:
            response = await self.client.get(path, **kwargs)
            response.raise_for_status()
            data = response.json()
            return response_model(**data)
        except Exception as e:
            logger.error(
                "HTTP GET failed",
                extra={
                    "method": "GET",
                    "path": path,
                    "correlation_id": correlation_id,
                    "error": str(e)
                }
            )
            raise
```

**Checklist:**
- [ ] Create `api/middleware/correlation.py`
- [ ] Register middleware in Data API
- [ ] Update HTTP client to send correlation IDs
- [ ] Add correlation ID to all log messages
- [ ] Test correlation IDs appear in logs

---

### Task 3.3: Add Request/Response Logging Middleware

**Priority:** 🟡 MEDIUM
**Estimated Time:** 2-3 hours

**Goal:**
Log all HTTP requests and responses with timing.

**Steps:**

#### Step 3.3.1: Create Logging Middleware (1 hour)
```python
# services/data_postgres_api/src/api/middleware/logging.py
"""Request/response logging middleware."""

import logging
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all HTTP requests and responses.

    Logs request method, path, status code, duration.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """
        Process request with logging.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware in chain

        Returns:
            HTTP response
        """
        start_time = time.time()
        correlation_id = getattr(request.state, "correlation_id", "unknown")

        # Log request
        logger.info(
            "HTTP request started",
            extra={
                "method": request.method,
                "path": request.url.path,
                "correlation_id": correlation_id,
                "client_host": request.client.host if request.client else "unknown"
            }
        )

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Log response
        logger.info(
            "HTTP request completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
                "correlation_id": correlation_id
            }
        )

        return response
```

#### Step 3.3.2: Register Middleware (15 min)
```python
# services/data_postgres_api/src/main.py
from src.api.middleware.logging import RequestLoggingMiddleware

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(CorrelationIDMiddleware)
app.add_middleware(CORSMiddleware, ...)
```

**Checklist:**
- [ ] Create `api/middleware/logging.py`
- [ ] Register logging middleware
- [ ] Test logs contain all required fields
- [ ] Verify performance impact is minimal

---

### Task 3.4: Add Error Tracking (Optional - Sentry)

**Priority:** 🟢 LOW
**Estimated Time:** 2-3 hours

**Goal:**
Integrate Sentry for error tracking and alerting.

**Steps:**

#### Step 3.4.1: Add Sentry Configuration (1 hour)
```python
# services/data_postgres_api/src/core/sentry.py
"""Sentry error tracking configuration."""

import logging
import sentry_sdk
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

from src.core.config import settings

logger = logging.getLogger(__name__)


def init_sentry() -> None:
    """
    Initialize Sentry error tracking.

    Only initializes if SENTRY_DSN environment variable is set.
    """
    if not settings.sentry_dsn:
        logger.info("Sentry not configured (SENTRY_DSN not set)")
        return

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        release=settings.version,
        traces_sample_rate=0.1,  # 10% of transactions
        integrations=[
            AsyncioIntegration(),
            LoggingIntegration(
                level=logging.INFO,
                event_level=logging.ERROR
            )
        ],
    )
    logger.info("Sentry initialized", extra={"environment": settings.environment})
```

#### Step 3.4.2: Update main.py (15 min)
```python
# services/data_postgres_api/src/main.py
from src.core.sentry import init_sentry

# Initialize Sentry on startup
init_sentry()

app = FastAPI(...)
```

#### Step 3.4.3: Add Sentry to Settings (15 min)
```python
# services/data_postgres_api/src/core/config.py
class Settings(BaseSettings):
    # ... existing fields

    # Sentry (optional)
    sentry_dsn: str | None = None
    environment: str = "development"
    version: str = "1.0.0"
```

**Checklist:**
- [ ] Add sentry-sdk to requirements.txt
- [ ] Create sentry.py configuration
- [ ] Add Sentry settings
- [ ] Initialize in main.py
- [ ] Test error tracking works

---

## 🟡 PHASE 4: Testing (MEDIUM - Week 4)

**Estimated Time:** 24-30 hours
**Priority:** 🟡 MEDIUM (required for Level 2)
**ADR Reference:** Section "Phase 4: Testing"

---

### Task 4.1: Add Unit Tests (>70% Coverage)

**Priority:** 🟡 MEDIUM
**Estimated Time:** 12-15 hours

**Goal:**
Achieve >70% test coverage for business logic.

**Areas to Test:**

#### 4.1.1: Time Parser Tests (2 hours)
```python
# services/tracker_activity_bot/tests/unit/test_time_parser.py
"""Unit tests for time parsing utilities."""

import pytest
from datetime import datetime, timezone, timedelta

from src.application.utils.time_parser import (
    parse_time_input,
    parse_duration
)


class TestParseTimeInput:
    """Tests for parse_time_input function."""

    def test_parse_absolute_time_colon(self):
        """Test parsing absolute time with colon (14:30)."""
        result = parse_time_input("14:30")
        assert result.hour == 14
        assert result.minute == 30
        assert result.tzinfo == timezone.utc

    def test_parse_absolute_time_dash(self):
        """Test parsing absolute time with dash (14-30)."""
        result = parse_time_input("14-30")
        assert result.hour == 14
        assert result.minute == 30

    def test_parse_relative_minutes_cyrillic(self):
        """Test parsing relative time in minutes (30м)."""
        now = datetime.now(timezone.utc)
        result = parse_time_input("30м")
        diff = (now - result).total_seconds() / 60
        assert 29 <= diff <= 31  # Allow 1 minute tolerance

    def test_parse_relative_minutes_english(self):
        """Test parsing relative time in minutes (30m)."""
        now = datetime.now(timezone.utc)
        result = parse_time_input("30m")
        diff = (now - result).total_seconds() / 60
        assert 29 <= diff <= 31

    def test_parse_relative_hours_cyrillic(self):
        """Test parsing relative time in hours (2ч)."""
        now = datetime.now(timezone.utc)
        result = parse_time_input("2ч")
        diff = (now - result).total_seconds() / 3600
        assert 1.98 <= diff <= 2.02

    def test_parse_relative_hours_english(self):
        """Test parsing relative time in hours (2h)."""
        now = datetime.now(timezone.utc)
        result = parse_time_input("2h")
        diff = (now - result).total_seconds() / 3600
        assert 1.98 <= diff <= 2.02

    def test_parse_now_cyrillic(self):
        """Test parsing 'сейчас' (now)."""
        now = datetime.now(timezone.utc)
        result = parse_time_input("сейчас")
        diff = abs((now - result).total_seconds())
        assert diff < 1  # Less than 1 second difference

    def test_parse_now_zero(self):
        """Test parsing '0' as now."""
        now = datetime.now(timezone.utc)
        result = parse_time_input("0")
        diff = abs((now - result).total_seconds())
        assert diff < 1

    def test_parse_invalid_format_raises_error(self):
        """Test that invalid format raises ValueError."""
        with pytest.raises(ValueError, match="Cannot parse time"):
            parse_time_input("invalid")

    def test_parse_invalid_hour_raises_error(self):
        """Test that invalid hour raises ValueError."""
        with pytest.raises(ValueError):
            parse_time_input("25:00")


class TestParseDuration:
    """Tests for parse_duration function."""

    def test_parse_duration_minutes(self):
        """Test parsing duration in minutes."""
        start = datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)
        result = parse_duration("30м", start)
        expected = start + timedelta(minutes=30)
        assert result == expected

    def test_parse_duration_hours(self):
        """Test parsing duration in hours."""
        start = datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)
        result = parse_duration("2ч", start)
        expected = start + timedelta(hours=2)
        assert result == expected

    def test_parse_duration_absolute_time(self):
        """Test parsing absolute end time."""
        start = datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)
        result = parse_duration("12:30", start)
        assert result.hour == 12
        assert result.minute == 30

    def test_parse_duration_now(self):
        """Test parsing 'сейчас' as duration."""
        start = datetime.now(timezone.utc) - timedelta(hours=1)
        result = parse_duration("сейчас", start)
        now = datetime.now(timezone.utc)
        diff = abs((result - now).total_seconds())
        assert diff < 1
```

#### 4.1.2: Application Service Tests (4 hours)
```python
# services/data_postgres_api/tests/unit/test_activity_service.py
"""Unit tests for ActivityService."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from src.application.services.activity_service import ActivityService
from src.domain.models.activity import Activity
from src.schemas.activity import ActivityCreate


@pytest.fixture
def mock_repository():
    """Create mock activity repository."""
    return AsyncMock()


@pytest.fixture
def activity_service(mock_repository):
    """Create activity service with mock repository."""
    return ActivityService(mock_repository)


@pytest.fixture
def sample_activity_data():
    """Create sample activity creation data."""
    return ActivityCreate(
        user_id=1,
        category_id=1,
        description="Test activity",
        tags=["test", "unit"],
        start_time=datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc),
        end_time=datetime(2025, 1, 1, 11, 0, tzinfo=timezone.utc)
    )


@pytest.fixture
def sample_activity():
    """Create sample activity model."""
    return Activity(
        id=1,
        user_id=1,
        category_id=1,
        description="Test activity",
        tags="test,unit",
        start_time=datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc),
        end_time=datetime(2025, 1, 1, 11, 0, tzinfo=timezone.utc),
        duration_minutes=60,
        created_at=datetime.now(timezone.utc)
    )


class TestActivityService:
    """Tests for ActivityService."""

    async def test_create_activity_success(
        self,
        activity_service,
        mock_repository,
        sample_activity_data,
        sample_activity
    ):
        """Test successful activity creation."""
        # Arrange
        mock_repository.create.return_value = sample_activity

        # Act
        result = await activity_service.create_activity(sample_activity_data)

        # Assert
        assert result == sample_activity
        mock_repository.create.assert_called_once_with(sample_activity_data)

    async def test_get_activity_by_id_found(
        self,
        activity_service,
        mock_repository,
        sample_activity
    ):
        """Test getting activity by ID when found."""
        # Arrange
        mock_repository.get_by_id.return_value = sample_activity

        # Act
        result = await activity_service.get_activity_by_id(1)

        # Assert
        assert result == sample_activity
        mock_repository.get_by_id.assert_called_once_with(1)

    async def test_get_activity_by_id_not_found(
        self,
        activity_service,
        mock_repository
    ):
        """Test getting activity by ID when not found."""
        # Arrange
        mock_repository.get_by_id.return_value = None

        # Act
        result = await activity_service.get_activity_by_id(999)

        # Assert
        assert result is None
        mock_repository.get_by_id.assert_called_once_with(999)

    async def test_get_user_activities_pagination(
        self,
        activity_service,
        mock_repository,
        sample_activity
    ):
        """Test getting user activities with pagination."""
        # Arrange
        activities = [sample_activity]
        total = 1
        mock_repository.get_by_user.return_value = (activities, total)

        # Act
        result_activities, result_total = await activity_service.get_user_activities(
            user_id=1,
            limit=10,
            offset=0
        )

        # Assert
        assert result_activities == activities
        assert result_total == total
        mock_repository.get_by_user.assert_called_once_with(1, 10, 0)
```

#### 4.1.3: Repository Tests (4 hours)

Use testcontainers for real database tests:

```python
# services/data_postgres_api/tests/integration/test_activity_repository.py
"""Integration tests for ActivityRepository using testcontainers."""

import pytest
from datetime import datetime, timezone
from testcontainers.postgres import PostgresContainer

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.domain.models.base import Base
from src.domain.models.activity import Activity
from src.infrastructure.repositories.activity_repository import ActivityRepository
from src.schemas.activity import ActivityCreate


@pytest.fixture(scope="module")
async def postgres_container():
    """Create PostgreSQL test container."""
    with PostgresContainer("postgres:15-alpine") as postgres:
        yield postgres


@pytest.fixture(scope="module")
async def test_engine(postgres_container):
    """Create test database engine."""
    connection_url = postgres_container.get_connection_url().replace(
        "psycopg2",
        "asyncpg"
    )
    engine = create_async_engine(connection_url, echo=True)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine):
    """Create database session for tests."""
    async_session = sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def activity_repository(db_session):
    """Create activity repository."""
    return ActivityRepository(db_session)


@pytest.mark.integration
class TestActivityRepositoryIntegration:
    """Integration tests for ActivityRepository."""

    async def test_create_activity(self, activity_repository):
        """Test creating activity in real database."""
        # Arrange
        activity_data = ActivityCreate(
            user_id=1,
            category_id=1,
            description="Integration test activity",
            tags=["test", "integration"],
            start_time=datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc),
            end_time=datetime(2025, 1, 1, 11, 0, tzinfo=timezone.utc)
        )

        # Act
        result = await activity_repository.create(activity_data)

        # Assert
        assert result.id is not None
        assert result.user_id == 1
        assert result.description == "Integration test activity"
        assert result.duration_minutes == 60

    # Add more integration tests...
```

**Checklist:**
- [ ] Write time parser tests
- [ ] Write formatters tests
- [ ] Write application service tests
- [ ] Write repository integration tests
- [ ] Add testcontainers for DB tests
- [ ] Achieve >70% coverage
- [ ] Update pytest.ini with markers

---

### Task 4.2: Add Integration Tests

**Priority:** 🟡 MEDIUM
**Estimated Time:** 6-8 hours

**Goal:**
Test HTTP clients, API endpoints end-to-end.

**Checklist:**
- [ ] Test HTTP client with mock server
- [ ] Test API endpoints with test database
- [ ] Test bot handlers with mock Telegram
- [ ] Test error handling scenarios

---

### Task 4.3: Add CI/CD Pipeline

**Priority:** 🟡 MEDIUM
**Estimated Time:** 4-5 hours

**Goal:**
Automate linting, type checking, tests on every commit.

**Steps:**

#### Step 4.3.1: Create GitHub Actions Workflow (2 hours)
```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [ main, master, develop ]
  pull_request:
    branches: [ main, master, develop ]

jobs:
  lint:
    name: Lint & Type Check
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install ruff mypy

      - name: Lint with Ruff
        run: |
          echo "Linting data_postgres_api..."
          cd services/data_postgres_api && ruff check .
          echo "Linting tracker_activity_bot..."
          cd ../tracker_activity_bot && ruff check .

      - name: Type check with mypy
        run: |
          echo "Type checking data_postgres_api..."
          cd services/data_postgres_api && mypy src/
          echo "Type checking tracker_activity_bot..."
          cd ../tracker_activity_bot && mypy src/

  test:
    name: Test
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_pass
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies - data_postgres_api
        run: |
          cd services/data_postgres_api
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-asyncio

      - name: Install dependencies - tracker_activity_bot
        run: |
          cd services/tracker_activity_bot
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-asyncio

      - name: Run tests - data_postgres_api
        env:
          DATABASE_URL: postgresql+asyncpg://test_user:test_pass@localhost:5432/test_db
        run: |
          cd services/data_postgres_api
          pytest tests/ -v --cov=src --cov-report=xml

      - name: Run tests - tracker_activity_bot
        env:
          REDIS_URL: redis://localhost:6379/0
        run: |
          cd services/tracker_activity_bot
          pytest tests/unit/ -v --cov=src --cov-report=xml

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          files: ./services/data_postgres_api/coverage.xml,./services/tracker_activity_bot/coverage.xml
          fail_ci_if_error: false

  docker:
    name: Docker Build
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build Docker images
        run: docker compose build

      - name: Start services
        run: |
          docker compose up -d
          sleep 10

      - name: Run smoke tests
        run: |
          docker compose ps
          curl -f http://localhost:8080/health/ready || exit 1

      - name: Stop services
        run: docker compose down
```

**Checklist:**
- [ ] Create `.github/workflows/ci.yml`
- [ ] Test workflow runs on push
- [ ] Verify all checks pass
- [ ] Add status badge to README

---

## 🟢 PHASE 5: Future Enhancements (LOW - Optional)

**Estimated Time:** TBD
**Priority:** 🟢 LOW (YAGNI for current maturity)

These are **intentionally excluded** per ADR YAGNI principle. Add only when needed.

---

### Task 5.1: Add Nginx API Gateway

**When to add:** Level 3+ (Pre-Production)
**Condition:** When we have >3 business services OR need SSL/TLS

**Steps:**
1. Create `nginx/conf.d/api-gateway.conf`
2. Add nginx service to docker-compose.yml
3. Configure upstream servers
4. Add rate limiting
5. Add SSL/TLS certificates

---

### Task 5.2: Add RabbitMQ for Async Events

**When to add:** Level 3+ OR when we need async processing
**Condition:** When we add background workers for notifications/analytics

**Steps:**
1. Add RabbitMQ to docker-compose.yml
2. Create event publisher in Data API
3. Create event consumer worker
4. Define event schemas

---

### Task 5.3: Add Prometheus Metrics

**When to add:** Level 2+ (Development Ready)
**Condition:** When we need production monitoring

**Steps:**
1. Add prometheus_client to requirements.txt
2. Create metrics module
3. Add metrics to endpoints
4. Configure Prometheus scraping
5. Create Grafana dashboards

---

### Task 5.4: Add Distributed Tracing (Jaeger)

**When to add:** Level 3+ OR when we have >5 services
**Condition:** When debugging cross-service issues

**Steps:**
1. Add OpenTelemetry to requirements.txt
2. Configure tracing
3. Add spans to critical paths
4. Set up Jaeger backend

---

## Summary: Immediate Action Items

### 🔴 MUST DO THIS WEEK (Critical - Week 1)

**Phase 2, Task 2.1-2.3 (10-12 hours):**
1. ✅ **Monday-Tuesday**: Create Application Layer in data_postgres_api (4-5 hours)
   - Create `application/services/` directory
   - Implement ActivityService, CategoryService, UserService
   - Update API routes to use services

2. ✅ **Wednesday**: Add mypy configuration (2-3 hours)
   - Create pyproject.toml in both services
   - Run mypy and fix violations
   - Update Makefile

3. ✅ **Thursday-Friday**: Add complete type hints to HTTP clients (3-4 hours)
   - Create Pydantic response models in bot
   - Update DataAPIClient with generics
   - Update all service clients

### 🟠 SHOULD DO NEXT WEEK (High - Week 2)

**Phase 2, Task 2.4-2.5 + Phase 3, Task 3.1-3.2 (10-12 hours):**
1. ✅ **Monday-Tuesday**: Add comprehensive docstrings (4-5 hours)
2. ✅ **Wednesday**: Implement dependency injection (2-3 hours)
3. ✅ **Thursday**: Improve health checks (1-2 hours)
4. ✅ **Friday**: Add correlation IDs (2-3 hours)

### 🟡 NICE TO HAVE (Medium - Week 3-4)

**Phase 3-4 (16-20 hours):**
1. ✅ **Week 3**: Complete observability tasks (6-8 hours)
2. ✅ **Week 4**: Add unit tests and CI/CD (10-12 hours)

---

## Tracking Progress

### Current Completion Status

- **Phase 1**: ✅ 100% Complete (Core Architecture)
- **Phase 2**: 🔴 0% Complete (Type Safety & Quality)
- **Phase 3**: 🟠 20% Complete (Observability)
- **Phase 4**: 🟢 0% Complete (Testing)

### Success Metrics

**Phase 2 Success Criteria:**
- [ ] Application layer exists with service classes
- [ ] mypy strict mode passes without errors
- [ ] All HTTP clients return Pydantic models
- [ ] >90% of functions have complete docstrings
- [ ] No global HTTP client instances

**Phase 3 Success Criteria:**
- [ ] Health checks verify DB connection
- [ ] All requests have correlation IDs
- [ ] All HTTP calls logged with timing
- [ ] Error tracking configured (optional)

**Phase 4 Success Criteria:**
- [ ] >70% test coverage
- [ ] CI/CD pipeline passes on every commit
- [ ] All smoke tests green
- [ ] Integration tests use testcontainers

---

## Final Notes

### ADR Compliance Checklist

After completing all phases, verify:

- ✅ **HTTP-only data access** - Bot never accesses DB directly
- ✅ **Service separation** - Each service in separate process
- ✅ **DDD/Hexagonal** - domain, application, infrastructure, api layers
- ✅ **Type safety** - mypy strict mode passes
- ✅ **Async-first** - All I/O uses async/await
- ✅ **Structured logging** - JSON logs with context
- ✅ **Health checks** - Separate liveness/readiness
- ✅ **YAGNI** - No unnecessary components (Nginx, RabbitMQ, etc.)

### Maintenance

**This document should be updated:**
- ✅ After each phase completion
- ✅ When new violations discovered
- ✅ When ADR requirements change
- ✅ Weekly during active refactoring

**Last Updated:** 2025-11-07
**Next Review:** After Phase 2 completion
**Owner:** Development Team

---

**End of Refactoring TODO Plan**
