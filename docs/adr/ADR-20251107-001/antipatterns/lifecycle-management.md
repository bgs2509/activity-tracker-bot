# Anti-Pattern: Lifecycle Management

> **ADR**: ADR-20251107-001  
> **Category**: 🟠 HIGH  
> [← Back to Anti-Patterns Index](README.md)

---

## Overview

Improper lifecycle management causes breaking changes and data loss.

**Symptom**: Application won't start after framework upgrade, data loss on restart

**Impact**: Breaking changes, corrupted state, lost jobs

---

## ❌ Anti-Pattern 3.1: Deprecated Lifecycle APIs

### Problem

Will break in future framework versions without warning

### Example (WRONG)

```python
# ❌ services/data_postgres_api/src/main.py:37, 50
@app.on_event("startup")  # Deprecated in FastAPI 0.93+
async def startup_event():
    """Application startup tasks."""
    logger.info("Starting data_postgres_api service")
    # ...

@app.on_event("shutdown")  # Will be removed!
async def shutdown_event():
    """Cleanup on shutdown."""
    await engine.dispose()
```

### Why This Matters

- `@app.on_event()` deprecated since FastAPI 0.93
- Will be removed in future versions
- Breaking change will happen without warning
- Technical debt accumulation
- Forces emergency fixes during upgrades

### Solution (CORRECT)

```python
# ✅ Use modern lifespan context manager
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
    
    yield  # Application is running
    
    # Shutdown
    logger.info("Shutting down data_postgres_api service")
    await engine.dispose()
    logger.info("Database engine disposed")

# Create FastAPI app with lifespan
app = FastAPI(
    title=settings.app_name,
    description="HTTP Data Access Service for PostgreSQL",
    version="1.0.0",
    lifespan=lifespan  # ✅ Use lifespan context manager
)
```

### Architecture Rule

> **Use modern lifecycle APIs (lifespan context manager). Monitor framework deprecation warnings.**

---

## ❌ Anti-Pattern 3.2: No Graceful Shutdown

### Problem

Data loss on container stop, interrupted transactions, corrupted state

### Example (WRONG)

```python
# ❌ services/tracker_activity_bot/src/main.py
async def main() -> None:
    """Main bot entry point."""
    # No signal handlers!
    await dp.start_polling(bot)
    # Docker SIGTERM → immediate kill → lost jobs, corrupted FSM state!
```

### Why This Matters

- Docker stop sends SIGTERM → immediate kill
- Pending scheduler jobs lost
- Database transactions interrupted
- FSM state corrupted
- Data inconsistency

### Solution (CORRECT)

```python
# ✅ Proper signal handling
import signal
import asyncio

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
        # Cleanup all resources
        scheduler_service.stop(wait=True)  # ✅ Wait for pending jobs
        logger.info("Scheduler stopped")
        
        await close_fsm_storage()
        await close_api_client()
        await bot.session.close()
        await storage.close()
        
        logger.info("Bot shutdown complete")
```

### Architecture Rule

> **All services MUST handle SIGTERM/SIGINT for graceful shutdown.**

---

## Related Documents

- [← Back to Anti-Patterns Index](README.md)
- [Resource Management →](resource-management.md)
- [Error Handling →](error-handling.md)
- [Fix Guide: Phase 0 URGENT →](../implementation/phase-0-urgent.md)
