# Logging Enhancement Plan - Activity Tracker Bot
## Goal: Achieve 90% Logging Coverage

**Document version:** 1.0
**Created:** 2025-11-11
**Author:** System Analysis
**Status:** Planning
**Estimated total effort:** 20-24 hours
**Target completion:** 2-3 weeks

---

## Executive Summary

Current logging coverage: **~70%**
Target logging coverage: **90%**
Gap to close: **20 percentage points**

### Current State Assessment

| Layer | Current Coverage | Target Coverage | Priority |
|-------|-----------------|-----------------|----------|
| Application/Main | 100% | 100% | ✅ Done |
| Middleware | 100% | 100% | ✅ Done |
| HTTP Clients | 100% | 100% | ✅ Done |
| Handlers | 80% | 90% | 🟡 Minor improvement |
| Services | 60% | 90% | 🔴 Major improvement |
| Repositories | 10% | 85% | 🔴 Critical |
| Database Layer | 0% | 80% | 🔴 Critical |
| Models/Domain | 0% | 0% | ⚪ Not required |

### Success Criteria

- ✅ All database operations logged with duration metrics
- ✅ All service layer business decisions logged
- ✅ SQL query performance tracking implemented
- ✅ Correlation ID propagated from Bot to API
- ✅ CRITICAL log level used for critical failures
- ✅ Slow query detection automated
- ✅ All repository CRUD operations logged
- ✅ End-to-end request tracing enabled

---

## Phase 1: Critical Improvements (Priority 1)

**Estimated effort:** 10-12 hours
**Impact:** High
**Urgency:** High

### Task 1.1: SQL Query Logging Infrastructure

**Status:** ⏸️ Not started
**Priority:** P0 (Critical)
**Effort:** 3-4 hours
**Assignee:** TBD

#### Objective
Implement comprehensive SQL query logging with performance tracking to identify slow queries and N+1 problems.

#### Implementation Details

**File:** `services/data_postgres_api/src/infrastructure/database.py`

**Changes required:**

1. Add SQLAlchemy event listeners for query tracking
2. Implement slow query detection (threshold: 1000ms)
3. Log query parameters (sanitized)
4. Track query execution time

**Code implementation:**

```python
# Add imports
from sqlalchemy import event
from sqlalchemy.engine import Engine
import time
import logging

logger = logging.getLogger(__name__)

# Slow query threshold in seconds
SLOW_QUERY_THRESHOLD = 1.0

@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Log SQL query execution start."""
    conn.info.setdefault("query_start_time", []).append(time.time())

    # Sanitize sensitive data in parameters
    safe_params = _sanitize_parameters(parameters)

    logger.debug(
        "Executing SQL query",
        extra={
            "sql_preview": statement[:200],  # First 200 chars
            "params_preview": str(safe_params)[:100] if safe_params else None,
            "executemany": executemany
        }
    )

@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Log SQL query execution completion with timing."""
    total = time.time() - conn.info["query_start_time"].pop(-1)
    duration_ms = round(total * 1000, 2)

    logger.debug(
        "SQL query completed",
        extra={
            "sql_preview": statement[:200],
            "duration_ms": duration_ms,
            "executemany": executemany
        }
    )

    # Detect slow queries
    if total > SLOW_QUERY_THRESHOLD:
        logger.warning(
            "Slow SQL query detected",
            extra={
                "sql": statement,
                "duration_ms": duration_ms,
                "params": str(_sanitize_parameters(parameters))[:500],
                "threshold_ms": SLOW_QUERY_THRESHOLD * 1000
            }
        )

def _sanitize_parameters(parameters):
    """Sanitize sensitive data in SQL parameters.

    Args:
        parameters: Query parameters to sanitize

    Returns:
        Sanitized parameters safe for logging
    """
    if not parameters:
        return None

    # List of sensitive field names to redact
    sensitive_fields = ['password', 'token', 'secret', 'api_key']

    if isinstance(parameters, dict):
        return {
            k: '***REDACTED***' if any(s in k.lower() for s in sensitive_fields) else v
            for k, v in parameters.items()
        }
    elif isinstance(parameters, (list, tuple)):
        # For positional parameters, just return count
        return f"<{len(parameters)} parameters>"

    return str(parameters)[:100]
```

#### Testing Strategy

```python
# Test file: tests/unit/infrastructure/test_database_logging.py

async def test_sql_query_logging_enabled(caplog):
    """Verify SQL queries are logged at DEBUG level."""
    # Execute a simple query
    result = await session.execute(select(User).limit(1))

    # Check logs
    assert any("Executing SQL query" in record.message for record in caplog.records)
    assert any("SQL query completed" in record.message for record in caplog.records)

async def test_slow_query_detection(caplog):
    """Verify slow queries trigger WARNING logs."""
    # Execute slow query (sleep)
    await session.execute(text("SELECT pg_sleep(1.5)"))

    # Check for slow query warning
    assert any("Slow SQL query detected" in record.message for record in caplog.records)

async def test_parameter_sanitization():
    """Verify sensitive parameters are redacted."""
    params = {"user_id": 123, "password": "secret123"}
    sanitized = _sanitize_parameters(params)

    assert sanitized["user_id"] == 123
    assert sanitized["password"] == "***REDACTED***"
```

#### Acceptance Criteria

- ✅ All SQL queries logged at DEBUG level
- ✅ Query duration tracked with millisecond precision
- ✅ Slow queries (>1s) trigger WARNING logs
- ✅ Sensitive parameters sanitized
- ✅ Query preview limited to 200 chars
- ✅ Unit tests pass with >90% coverage

#### Monitoring & Metrics

```
# Expected log volume increase
- DEBUG logs: +30% (all queries)
- WARNING logs: +5% (slow queries in production)

# Performance impact
- Overhead: <1ms per query
- Memory: negligible
```

---

### Task 1.2: Repository Layer Logging

**Status:** ⏸️ Not started
**Priority:** P0 (Critical)
**Effort:** 4-5 hours
**Assignee:** TBD

#### Objective
Add comprehensive logging to all repository CRUD operations to track data layer operations.

#### Scope

**Files to modify:**
- `services/data_postgres_api/src/infrastructure/repositories/user_repository.py`
- `services/data_postgres_api/src/infrastructure/repositories/user_settings_repository.py`
- `services/data_postgres_api/src/infrastructure/repositories/activity_repository.py`
- `services/data_postgres_api/src/infrastructure/repositories/category_repository.py`

**Operations to log:**
- CREATE: Log entity creation with ID
- READ: Log entity retrieval attempts
- UPDATE: Log field updates
- DELETE: Log entity deletion
- BULK operations: Log batch sizes

#### Implementation Pattern

**Template for all repositories:**

```python
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)

class UserRepository:
    """Repository for User entity operations.

    All methods include structured logging for observability.
    """

    async def create(self, user: User) -> User:
        """Create a new user in the database.

        Args:
            user: User entity to create

        Returns:
            Created user with assigned ID

        Raises:
            IntegrityError: If user already exists
        """
        logger.debug(
            "Creating user in database",
            extra={
                "telegram_id": user.telegram_id,
                "username": user.username,
                "operation": "create"
            }
        )

        try:
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)

            logger.info(
                "User created successfully",
                extra={
                    "user_id": user.id,
                    "telegram_id": user.telegram_id,
                    "operation": "create"
                }
            )
            return user

        except IntegrityError as e:
            logger.warning(
                "User creation failed - already exists",
                extra={
                    "telegram_id": user.telegram_id,
                    "error": str(e),
                    "operation": "create"
                }
            )
            await self.session.rollback()
            raise

        except Exception as e:
            logger.error(
                "Unexpected error creating user",
                extra={
                    "telegram_id": user.telegram_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "operation": "create"
                },
                exc_info=True
            )
            await self.session.rollback()
            raise

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Retrieve user by Telegram ID.

        Args:
            telegram_id: Telegram user ID

        Returns:
            User if found, None otherwise
        """
        logger.debug(
            "Retrieving user by telegram_id",
            extra={
                "telegram_id": telegram_id,
                "operation": "read"
            }
        )

        try:
            result = await self.session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()

            if user:
                logger.debug(
                    "User found",
                    extra={
                        "user_id": user.id,
                        "telegram_id": telegram_id,
                        "operation": "read"
                    }
                )
            else:
                logger.debug(
                    "User not found",
                    extra={
                        "telegram_id": telegram_id,
                        "operation": "read"
                    }
                )

            return user

        except Exception as e:
            logger.error(
                "Error retrieving user",
                extra={
                    "telegram_id": telegram_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "operation": "read"
                },
                exc_info=True
            )
            raise

    async def update(self, user_id: int, **kwargs) -> Optional[User]:
        """Update user fields.

        Args:
            user_id: User ID to update
            **kwargs: Fields to update

        Returns:
            Updated user if found, None otherwise
        """
        logger.debug(
            "Updating user",
            extra={
                "user_id": user_id,
                "fields": list(kwargs.keys()),
                "operation": "update"
            }
        )

        try:
            user = await self.get_by_id(user_id)
            if not user:
                logger.warning(
                    "Cannot update user - not found",
                    extra={
                        "user_id": user_id,
                        "operation": "update"
                    }
                )
                return None

            # Track changed fields
            changed_fields = []
            for key, value in kwargs.items():
                if hasattr(user, key) and getattr(user, key) != value:
                    changed_fields.append(key)
                    setattr(user, key, value)

            await self.session.commit()
            await self.session.refresh(user)

            logger.info(
                "User updated successfully",
                extra={
                    "user_id": user_id,
                    "changed_fields": changed_fields,
                    "operation": "update"
                }
            )
            return user

        except Exception as e:
            logger.error(
                "Error updating user",
                extra={
                    "user_id": user_id,
                    "fields": list(kwargs.keys()),
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "operation": "update"
                },
                exc_info=True
            )
            await self.session.rollback()
            raise

    async def delete(self, user_id: int) -> bool:
        """Delete user by ID.

        Args:
            user_id: User ID to delete

        Returns:
            True if deleted, False if not found
        """
        logger.debug(
            "Deleting user",
            extra={
                "user_id": user_id,
                "operation": "delete"
            }
        )

        try:
            user = await self.get_by_id(user_id)
            if not user:
                logger.warning(
                    "Cannot delete user - not found",
                    extra={
                        "user_id": user_id,
                        "operation": "delete"
                    }
                )
                return False

            await self.session.delete(user)
            await self.session.commit()

            logger.info(
                "User deleted successfully",
                extra={
                    "user_id": user_id,
                    "operation": "delete"
                }
            )
            return True

        except Exception as e:
            logger.error(
                "Error deleting user",
                extra={
                    "user_id": user_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "operation": "delete"
                },
                exc_info=True
            )
            await self.session.rollback()
            raise
```

#### Files and LOC Estimates

| File | Methods to Update | Estimated LOC | Effort |
|------|------------------|---------------|--------|
| `user_repository.py` | 5 methods | ~150 lines | 1.5h |
| `user_settings_repository.py` | 6 methods | ~180 lines | 1.5h |
| `activity_repository.py` | 8 methods | ~240 lines | 2h |
| `category_repository.py` | 7 methods | ~210 lines | 1.5h |

#### Acceptance Criteria

- ✅ All CRUD operations logged with structured context
- ✅ Entity IDs included in all logs
- ✅ Field names logged for updates
- ✅ Errors logged with exc_info=True
- ✅ Warnings for not-found cases
- ✅ Operation type included in extra fields
- ✅ No performance degradation (overhead <5ms)

---

### Task 1.3: CRITICAL Log Level Implementation

**Status:** ⏸️ Not started
**Priority:** P0 (Critical)
**Effort:** 1-2 hours
**Assignee:** TBD

#### Objective
Distinguish between recoverable errors (ERROR) and critical system failures (CRITICAL) to enable better alerting and incident response.

#### CRITICAL Level Usage Guidelines

**Use CRITICAL for:**
- ❌ Database connection failures (cannot connect at all)
- ❌ Service startup failures (cannot initialize required components)
- ❌ Data corruption detected
- ❌ Critical infrastructure unavailable (Redis, Message Queue)
- ❌ Security violations (authentication bypass detected)
- ❌ File system full or permissions denied

**Keep ERROR for:**
- ✅ Failed API requests (retryable)
- ✅ Validation errors
- ✅ Business logic errors
- ✅ User not found
- ✅ Temporary network issues

#### Files to Modify

**1. Database Health Check**

**File:** `services/data_postgres_api/src/main.py`

**Current code (lines 188-194):**
```python
try:
    await database_health_check()
except Exception as e:
    logger.error(  # ← Change to CRITICAL
        "Database health check failed",
        extra={
            "error": str(e),
            "error_type": type(e).__name__
        }
    )
```

**Updated code:**
```python
try:
    await database_health_check()
except Exception as e:
    logger.critical(  # ← Changed from ERROR
        "Database health check failed - service cannot operate",
        extra={
            "error": str(e),
            "error_type": type(e).__name__,
            "service": "data_postgres_api",
            "impact": "service_unavailable"
        },
        exc_info=True
    )
    # Re-raise to prevent startup with unhealthy database
    raise SystemExit(1)
```

**2. Database Connection Initialization**

**File:** `services/data_postgres_api/src/infrastructure/database.py`

**Add new error handling:**
```python
async def init_db():
    """Initialize database connection pool.

    Raises:
        SystemExit: If database connection cannot be established
    """
    try:
        engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,
            pool_size=settings.pool_size,
            max_overflow=settings.max_overflow
        )

        # Test connection
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))

        logger.info("Database connection established")
        return engine

    except Exception as e:
        logger.critical(
            "Failed to establish database connection",
            extra={
                "database_url": settings.database_url.replace(
                    settings.database_password, "***"
                ),
                "error": str(e),
                "error_type": type(e).__name__,
                "impact": "service_cannot_start"
            },
            exc_info=True
        )
        raise SystemExit(1)
```

**3. Bot Service Initialization**

**File:** `services/tracker_activity_bot/src/main.py`

**Add critical error handling:**
```python
async def main():
    """Main entry point for the bot service."""
    try:
        setup_logging(
            service_name="tracker_activity_bot",
            log_level=settings.log_level
        )
        logger = logging.getLogger(__name__)

        logger.info("Starting tracker_activity_bot service")

        # Initialize critical components
        try:
            bot = Bot(token=settings.telegram_bot_token)
            dp = Dispatcher(storage=MemoryStorage())
        except Exception as e:
            logger.critical(
                "Failed to initialize bot components",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "impact": "service_cannot_start"
                },
                exc_info=True
            )
            raise SystemExit(1)

        # ... rest of initialization

    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.critical(
            "Unexpected critical error in main loop",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "impact": "service_crashed"
            },
            exc_info=True
        )
        raise SystemExit(1)
```

#### Implementation Checklist

- [ ] Update database health check to CRITICAL
- [ ] Update database connection errors to CRITICAL
- [ ] Update bot initialization errors to CRITICAL
- [ ] Add SystemExit(1) for critical failures
- [ ] Update monitoring alerts to trigger on CRITICAL
- [ ] Document CRITICAL level usage in logging.py
- [ ] Test that CRITICAL logs trigger proper alerts

#### Acceptance Criteria

- ✅ CRITICAL logs used only for fatal errors
- ✅ All CRITICAL logs include "impact" field
- ✅ Service exits with code 1 on CRITICAL errors
- ✅ ERROR logs still used for recoverable issues
- ✅ Monitoring alerts configured for CRITICAL level
- ✅ Documentation updated with usage guidelines

---

## Phase 2: High-Value Improvements (Priority 2)

**Estimated effort:** 6-8 hours
**Impact:** Medium-High
**Urgency:** Medium

### Task 2.1: Correlation ID Propagation (Bot → API)

**Status:** ⏸️ Not started
**Priority:** P1 (High)
**Effort:** 3-4 hours
**Assignee:** TBD

#### Objective
Enable end-to-end request tracing by propagating correlation IDs from Bot service through to API service, allowing complete request lifecycle tracking across service boundaries.

#### Current State

- ✅ API generates correlation_id for incoming requests
- ❌ Bot does NOT send correlation_id when calling API
- ❌ Cannot trace user action from bot → API → database

#### Target State

```
[User Action] → [Bot Handler] → [HTTP Client] → [API Endpoint] → [Repository] → [Database]
     ↓              ↓                ↓               ↓                ↓              ↓
correlation_id  correlation_id  X-Correlation-ID  correlation_id  correlation_id  (SQL)
     same          same            same             same            same
```

#### Implementation Steps

**Step 1: Create Context Storage for Correlation ID**

**File:** `services/tracker_activity_bot/src/infrastructure/context.py` (new file)

```python
"""Context storage for request-scoped data like correlation IDs.

This module provides thread-safe storage for correlation IDs that need
to be propagated across the application stack.
"""

import contextvars
from typing import Optional
import uuid

# Context variable for storing correlation ID
_correlation_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    'correlation_id',
    default=None
)

def get_correlation_id() -> str:
    """Get current correlation ID or generate new one.

    Returns:
        Current correlation ID or newly generated UUID
    """
    correlation_id = _correlation_id.get()
    if not correlation_id:
        correlation_id = str(uuid.uuid4())
        _correlation_id.set(correlation_id)
    return correlation_id

def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID for current context.

    Args:
        correlation_id: Correlation ID to set
    """
    _correlation_id.set(correlation_id)

def clear_correlation_id() -> None:
    """Clear correlation ID from current context."""
    _correlation_id.set(None)
```

**Step 2: Create Correlation ID Middleware for Bot**

**File:** `services/tracker_activity_bot/src/core/correlation_middleware.py` (new file)

```python
"""Middleware for correlation ID management in bot handlers.

Automatically generates and propagates correlation IDs for all incoming
telegram events (messages, callbacks, etc.).
"""

import logging
from typing import Callable, Dict, Any, Awaitable
import uuid

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User

from infrastructure.context import set_correlation_id, clear_correlation_id

logger = logging.getLogger(__name__)

class CorrelationIDMiddleware(BaseMiddleware):
    """Middleware to generate and manage correlation IDs.

    Creates a unique correlation ID for each incoming telegram event
    and stores it in context for downstream propagation to API calls.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        """Process event with correlation ID.

        Args:
            handler: Next handler in chain
            event: Telegram event (Message, CallbackQuery, etc.)
            data: Handler data dictionary

        Returns:
            Handler result
        """
        # Generate new correlation ID for this request
        correlation_id = str(uuid.uuid4())
        set_correlation_id(correlation_id)

        # Extract user info for logging
        user: Optional[User] = data.get("event_from_user")
        user_id = user.id if user else None

        # Determine event type
        event_type = type(event).__name__

        logger.debug(
            "Correlation ID generated for incoming event",
            extra={
                "correlation_id": correlation_id,
                "event_type": event_type,
                "user_id": user_id
            }
        )

        try:
            # Execute handler with correlation ID in context
            result = await handler(event, data)
            return result
        finally:
            # Clean up context after handler completes
            clear_correlation_id()
```

**Step 3: Add Correlation ID Header to HTTP Client**

**File:** `services/tracker_activity_bot/src/infrastructure/http_clients/middleware/correlation_middleware.py` (new file)

```python
"""HTTP client middleware for correlation ID propagation.

Automatically adds X-Correlation-ID header to all outgoing HTTP requests
using the correlation ID from the current context.
"""

import logging
from typing import Optional

import httpx

from infrastructure.context import get_correlation_id
from infrastructure.http_clients.middleware.base import RequestMiddleware

logger = logging.getLogger(__name__)

class CorrelationIDMiddleware(RequestMiddleware):
    """Middleware to add correlation ID header to HTTP requests.

    Retrieves correlation ID from current context and adds it as
    X-Correlation-ID header for distributed tracing.
    """

    async def process_request(self, request: httpx.Request) -> httpx.Request:
        """Add correlation ID header to outgoing request.

        Args:
            request: HTTP request to process

        Returns:
            Request with X-Correlation-ID header added
        """
        correlation_id = get_correlation_id()

        # Add header
        request.headers["X-Correlation-ID"] = correlation_id

        logger.debug(
            "Added correlation ID to outgoing HTTP request",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "url": str(request.url),
                "path": request.url.path
            }
        )

        return request
```

**Step 4: Register Middleware**

**File:** `services/tracker_activity_bot/src/main.py`

**Add correlation middleware (after line 67):**

```python
# Register middlewares (order matters - innermost first during request)
dp.update.middleware(ServiceInjectionMiddleware(container))

# Add correlation middleware FIRST (outermost)
from core.correlation_middleware import CorrelationIDMiddleware
dp.update.middleware(CorrelationIDMiddleware())

# Existing middlewares
dp.update.middleware(UserActionLoggingMiddleware())
dp.update.middleware(FSMLoggingMiddleware())
```

**Step 5: Update HTTP Client Initialization**

**File:** `services/tracker_activity_bot/src/infrastructure/http_clients/http_client.py`

**Update default middleware stack (around line 75):**

```python
from infrastructure.http_clients.middleware.correlation_middleware import (
    CorrelationIDMiddleware as HTTPCorrelationMiddleware
)

# Default middleware stack
default_middlewares = [
    HTTPCorrelationMiddleware(),  # ← Add FIRST
    TimingMiddleware(),
    LoggingMiddleware(),
    ErrorHandlingMiddleware(),
]
```

#### Testing Strategy

**Test file:** `tests/unit/middleware/test_correlation_middleware.py`

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from aiogram.types import Message, User

from core.correlation_middleware import CorrelationIDMiddleware
from infrastructure.context import get_correlation_id

@pytest.mark.asyncio
async def test_correlation_id_generated():
    """Verify correlation ID is generated for each event."""
    middleware = CorrelationIDMiddleware()

    handler = AsyncMock()
    event = MagicMock(spec=Message)
    data = {"event_from_user": User(id=123, is_bot=False, first_name="Test")}

    await middleware(handler, event, data)

    # Verify handler was called
    handler.assert_called_once()

    # Verify correlation ID was generated (check in handler call)
    # Note: correlation_id is cleared after handler, so test inside handler

@pytest.mark.asyncio
async def test_correlation_id_propagated_to_http():
    """Verify correlation ID is added to HTTP requests."""
    from infrastructure.http_clients.middleware.correlation_middleware import (
        CorrelationIDMiddleware as HTTPMiddleware
    )
    from infrastructure.context import set_correlation_id

    # Set correlation ID in context
    test_correlation_id = "test-uuid-123"
    set_correlation_id(test_correlation_id)

    # Create HTTP middleware
    http_middleware = HTTPMiddleware()

    # Create test request
    request = httpx.Request("GET", "http://api.example.com/test")

    # Process request
    processed = await http_middleware.process_request(request)

    # Verify header added
    assert "X-Correlation-ID" in processed.headers
    assert processed.headers["X-Correlation-ID"] == test_correlation_id

@pytest.mark.asyncio
async def test_correlation_id_cleaned_up():
    """Verify correlation ID is cleared after handler completes."""
    middleware = CorrelationIDMiddleware()

    async def handler_with_check(event, data):
        # Inside handler - correlation ID should exist
        correlation_id = get_correlation_id()
        assert correlation_id is not None
        return correlation_id

    event = MagicMock(spec=Message)
    data = {"event_from_user": User(id=123, is_bot=False, first_name="Test")}

    result = await middleware(handler_with_check, event, data)

    # After handler - correlation ID should be cleared
    # (new one generated if requested)
    new_id = get_correlation_id()
    assert new_id != result  # Different ID generated
```

#### Acceptance Criteria

- ✅ Correlation ID generated for every telegram event
- ✅ Correlation ID stored in context (thread-safe)
- ✅ Correlation ID added to all HTTP requests as header
- ✅ Correlation ID logged at DEBUG level
- ✅ Correlation ID cleaned up after handler completes
- ✅ API receives and logs correlation ID
- ✅ End-to-end tracing works in production logs
- ✅ Unit tests pass with >90% coverage

#### Verification

**Manual verification steps:**

1. Start both services (bot + API)
2. Send message to bot
3. Check bot logs for correlation_id
4. Check API logs for same correlation_id
5. Verify both services use identical correlation_id

**Example log sequence:**

```json
// Bot log
{
  "timestamp": "2025-11-11T10:00:00.000Z",
  "service": "tracker_activity_bot",
  "logger": "core.correlation_middleware",
  "levelname": "DEBUG",
  "message": "Correlation ID generated for incoming event",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": 123456
}

// Bot HTTP client log
{
  "timestamp": "2025-11-11T10:00:00.050Z",
  "service": "tracker_activity_bot",
  "logger": "infrastructure.http_clients.middleware.correlation",
  "levelname": "DEBUG",
  "message": "Added correlation ID to outgoing HTTP request",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "method": "POST",
  "path": "/api/users"
}

// API log
{
  "timestamp": "2025-11-11T10:00:00.100Z",
  "service": "data_postgres_api",
  "logger": "api.middleware.logging",
  "levelname": "INFO",
  "message": "HTTP request started",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "method": "POST",
  "path": "/api/users"
}
```

---

### Task 2.2: Service Layer Logging Enhancement

**Status:** ⏸️ Not started
**Priority:** P1 (High)
**Effort:** 3-4 hours
**Assignee:** TBD

#### Objective
Enhance logging in service layer to capture business logic decisions and state changes.

#### Scope

**Files to modify:**

**Bot Service:**
- `services/tracker_activity_bot/src/application/services/user_service.py`
- `services/tracker_activity_bot/src/application/services/user_settings_service.py`
- `services/tracker_activity_bot/src/application/services/category_service.py`
- `services/tracker_activity_bot/src/application/services/activity_service.py`
- `services/tracker_activity_bot/src/application/services/scheduler_service.py`
- `services/tracker_activity_bot/src/application/services/fsm_timeout_service.py`

**API Service:**
- `services/data_postgres_api/src/application/services/*` (if any)

#### Implementation Pattern

**Example: UserSettingsService**

**File:** `services/tracker_activity_bot/src/application/services/user_settings_service.py`

**Current code:**
```python
async def update_settings(
    self,
    user_id: int,
    **kwargs
) -> Optional[UserSettingsDict]:
    """Update user settings."""
    existing = await self.get_by_user_id(user_id)
    if not existing:
        logger.warning(f"Settings not found for user {user_id}")
        return None
    # ← Missing: log of update operation
    return await self.data_api_client.user_settings.update(user_id, **kwargs)
```

**Enhanced code:**
```python
async def update_settings(
    self,
    user_id: int,
    **kwargs
) -> Optional[UserSettingsDict]:
    """Update user settings.

    Args:
        user_id: User ID to update settings for
        **kwargs: Settings fields to update

    Returns:
        Updated settings if found, None otherwise
    """
    logger.debug(
        "Updating user settings",
        extra={
            "user_id": user_id,
            "fields": list(kwargs.keys()),
            "service": "user_settings"
        }
    )

    existing = await self.get_by_user_id(user_id)
    if not existing:
        logger.warning(
            "Cannot update settings - user not found",
            extra={
                "user_id": user_id,
                "service": "user_settings"
            }
        )
        return None

    try:
        result = await self.data_api_client.user_settings.update(user_id, **kwargs)

        logger.info(
            "User settings updated successfully",
            extra={
                "user_id": user_id,
                "updated_fields": list(kwargs.keys()),
                "service": "user_settings"
            }
        )
        return result

    except Exception as e:
        logger.error(
            "Failed to update user settings",
            extra={
                "user_id": user_id,
                "fields": list(kwargs.keys()),
                "error": str(e),
                "error_type": type(e).__name__,
                "service": "user_settings"
            },
            exc_info=True
        )
        raise
```

#### Service-Specific Logging Requirements

**SchedulerService:**
- Log poll scheduling with next_run_time
- Log rescheduling decisions (quiet hours, user disabled)
- Log job cancellations
- Log scheduler startup/shutdown

**FSMTimeoutService:**
- Log reminder scheduling with delay
- Log reminder sends
- Log cleanup operations
- Log timer cancellations

**CategoryService:**
- Log category creation with validation
- Log category updates
- Log category deletion with activity cleanup
- Log list operations with filters

**ActivityService:**
- Log activity creation with all fields
- Log activity retrieval with filters
- Log activity updates
- Log statistics calculations

#### Acceptance Criteria

- ✅ All service methods have DEBUG entry logs
- ✅ All successful operations have INFO logs
- ✅ All errors have ERROR logs with exc_info
- ✅ All warnings have WARNING logs
- ✅ Business decisions logged (e.g., "rescheduling due to quiet hours")
- ✅ Field names included for update operations
- ✅ Service name included in extra context

---

## Phase 3: Nice-to-Have Improvements (Priority 3)

**Estimated effort:** 4-6 hours
**Impact:** Medium
**Urgency:** Low

### Task 3.1: Enhanced Bot Message Logging

**Status:** ⏸️ Not started
**Priority:** P2 (Medium)
**Effort:** 2-3 hours
**Assignee:** TBD

#### Objective
Add metadata to bot message logging for better analysis of message patterns and user interactions.

#### Implementation

**File:** `services/tracker_activity_bot/src/core/logging_middleware.py`

**Enhance log_bot_message function (lines 258-325):**

```python
async def log_bot_message(
    send_func: Callable,
    chat_id: int,
    text: str,
    user_id: Optional[int] = None,
    **kwargs
) -> types.Message:
    """Log bot message sending with enhanced metadata.

    Args:
        send_func: Message sending function
        chat_id: Target chat ID
        text: Message text
        user_id: User ID for context
        **kwargs: Additional arguments

    Returns:
        Sent message object
    """
    start_time = time.time()

    # Extract keyboard info
    keyboard_info = _extract_keyboard_info(kwargs.get("reply_markup"))

    # Analyze message content
    message_analysis = {
        "length": len(text),
        "preview": text[:100],
        "has_markdown": "**" in text or "__" in text or "`" in text,
        "has_links": "http://" in text or "https://" in text,
        "line_count": text.count("\n") + 1,
        **keyboard_info
    }

    logger.debug(
        "Sending bot message",
        extra={
            "user_id": user_id,
            "chat_id": chat_id,
            **message_analysis,
            "parse_mode": kwargs.get("parse_mode")
        }
    )

    try:
        message = await send_func(chat_id=chat_id, text=text, **kwargs)
        duration_ms = round((time.time() - start_time) * 1000, 2)

        logger.info(
            "Bot message sent successfully",
            extra={
                "user_id": user_id,
                "chat_id": chat_id,
                "message_id": message.message_id,
                "duration_ms": duration_ms,
                **message_analysis
            }
        )
        return message

    except Exception as e:
        duration_ms = round((time.time() - start_time) * 1000, 2)

        logger.error(
            "Failed to send bot message",
            extra={
                "user_id": user_id,
                "chat_id": chat_id,
                "duration_ms": duration_ms,
                "error": str(e),
                "error_type": type(e).__name__,
                **message_analysis
            },
            exc_info=False  # Telegram errors are expected, don't need full trace
        )
        raise

def _extract_keyboard_info(reply_markup) -> dict:
    """Extract keyboard metadata for logging.

    Args:
        reply_markup: Keyboard markup object

    Returns:
        Dictionary with keyboard metadata
    """
    if not reply_markup:
        return {"has_keyboard": False}

    keyboard_type = type(reply_markup).__name__

    info = {
        "has_keyboard": True,
        "keyboard_type": keyboard_type
    }

    # Count buttons for inline keyboards
    if keyboard_type == "InlineKeyboardMarkup":
        button_count = sum(len(row) for row in reply_markup.inline_keyboard)
        info["button_count"] = button_count
        info["row_count"] = len(reply_markup.inline_keyboard)

    # Count buttons for reply keyboards
    elif keyboard_type == "ReplyKeyboardMarkup":
        button_count = sum(len(row) for row in reply_markup.keyboard)
        info["button_count"] = button_count
        info["row_count"] = len(reply_markup.keyboard)

    return info
```

#### Acceptance Criteria

- ✅ Message length logged
- ✅ Markdown/links detected
- ✅ Keyboard metadata captured
- ✅ Line count calculated
- ✅ Parse mode logged
- ✅ Duration tracked

---

### Task 3.2: Log Sampling for High-Volume Operations

**Status:** ⏸️ Not started
**Priority:** P2 (Medium)
**Effort:** 2-3 hours
**Assignee:** TBD

#### Objective
Implement log sampling for DEBUG logs to reduce volume in production while maintaining visibility.

#### Implementation

**File:** `services/tracker_activity_bot/src/core/logging.py`

**Add sampling configuration:**

```python
import random
from typing import Optional

class SamplingFilter(logging.Filter):
    """Filter to sample logs based on log level and sampling rate.

    Allows selective sampling of high-volume logs (DEBUG) while
    keeping all important logs (INFO, WARNING, ERROR, CRITICAL).
    """

    def __init__(
        self,
        sample_rate: float = 1.0,
        sample_debug_only: bool = True
    ):
        """Initialize sampling filter.

        Args:
            sample_rate: Probability of keeping a log (0.0 to 1.0)
            sample_debug_only: If True, only sample DEBUG logs
        """
        super().__init__()
        self.sample_rate = sample_rate
        self.sample_debug_only = sample_debug_only

    def filter(self, record: logging.LogRecord) -> bool:
        """Determine if log record should be kept.

        Args:
            record: Log record to evaluate

        Returns:
            True if record should be logged, False to discard
        """
        # Always keep non-DEBUG logs
        if self.sample_debug_only and record.levelno > logging.DEBUG:
            return True

        # Always keep if sampling disabled
        if self.sample_rate >= 1.0:
            return True

        # Sample based on probability
        return random.random() < self.sample_rate

def setup_logging(
    service_name: str,
    log_level: str = "INFO",
    debug_sample_rate: Optional[float] = None
) -> None:
    """Set up structured JSON logging with optional sampling.

    Args:
        service_name: Name of the service for log context
        log_level: Minimum log level to capture
        debug_sample_rate: Sampling rate for DEBUG logs (None = no sampling)
    """
    # ... existing setup code ...

    # Add sampling filter if configured
    if debug_sample_rate is not None and debug_sample_rate < 1.0:
        sampling_filter = SamplingFilter(
            sample_rate=debug_sample_rate,
            sample_debug_only=True
        )
        handler.addFilter(sampling_filter)

        logger = logging.getLogger(__name__)
        logger.info(
            f"Debug log sampling enabled",
            extra={
                "sample_rate": debug_sample_rate,
                "service": service_name
            }
        )
```

**Configuration:**

```python
# In main.py
# Development: Full logging
setup_logging(
    service_name="tracker_activity_bot",
    log_level="DEBUG",
    debug_sample_rate=None  # No sampling
)

# Production: Sampled DEBUG logs
setup_logging(
    service_name="tracker_activity_bot",
    log_level="DEBUG",
    debug_sample_rate=0.1  # Keep 10% of DEBUG logs
)
```

#### Acceptance Criteria

- ✅ Sampling configurable via parameter
- ✅ INFO/WARNING/ERROR/CRITICAL never sampled
- ✅ DEBUG logs sampled based on rate
- ✅ Sampling rate logged at startup
- ✅ No performance impact

---

## Implementation Timeline

### Week 1: Critical Foundation
```
Monday-Tuesday: Task 1.1 - SQL Query Logging (3-4h)
Wednesday-Thursday: Task 1.2 - Repository Logging (4-5h)
Friday: Task 1.3 - CRITICAL Level (1-2h)
```

### Week 2: High-Value Features
```
Monday-Tuesday: Task 2.1 - Correlation ID (3-4h)
Wednesday-Thursday: Task 2.2 - Service Layer (3-4h)
Friday: Testing & Bug fixes
```

### Week 3: Polish & Nice-to-Haves
```
Monday: Task 3.1 - Message Logging (2-3h)
Tuesday: Task 3.2 - Log Sampling (2-3h)
Wednesday-Friday: Integration testing, documentation, deployment
```

---

## Testing Strategy

### Unit Tests
- Repository logging: Verify logs generated for CRUD operations
- Correlation ID: Verify propagation across boundaries
- Sampling: Verify correct sampling rates

### Integration Tests
- End-to-end correlation: User action → Bot → API → DB
- SQL logging: Verify queries captured
- Error scenarios: Verify CRITICAL vs ERROR usage

### Performance Tests
- Logging overhead: <5ms per operation
- Log volume: Measure before/after
- Sampling effectiveness: Verify volume reduction

### Manual Verification
- Check production logs in ELK/Grafana
- Verify alert triggers on CRITICAL
- Trace sample requests end-to-end

---

## Monitoring & Metrics

### Log Volume Metrics

**Current estimated volume (per day):**
```
DEBUG:   ~50,000 logs
INFO:    ~30,000 logs
WARNING: ~1,000 logs
ERROR:   ~200 logs
CRITICAL: 0 logs

Total: ~81,200 logs/day
```

**Expected after implementation:**
```
DEBUG:   ~80,000 logs (+60% from SQL/Repository)
INFO:    ~40,000 logs (+33% from Service layer)
WARNING: ~1,200 logs (+20%)
ERROR:   ~250 logs (+25%)
CRITICAL: ~5 logs (new)

Total: ~121,455 logs/day (+50% increase)

With sampling (10% DEBUG):
Total: ~49,455 logs/day (-39% from current)
```

### Coverage Metrics

**Target coverage by layer:**
```
Application/Main:  100% ✅
Middleware:        100% ✅
HTTP Clients:      100% ✅
Handlers:          90%  ← +10%
Services:          90%  ← +30%
Repositories:      85%  ← +75%
Database Layer:    80%  ← +80%

Overall:           90%  ← From 70%
```

### Performance Metrics

**Acceptable overhead:**
- Per log statement: <1ms
- Per SQL query: <1ms
- Per HTTP request: <2ms
- Per repository operation: <5ms

**Monitor:**
- P95 response time increase: <5%
- Memory usage increase: <10MB
- CPU usage increase: <2%

---

## Rollout Plan

### Phase 1: Development Environment
1. Implement all tasks
2. Run full test suite
3. Manual verification
4. Performance baseline

### Phase 2: Staging Environment
1. Deploy with full logging (no sampling)
2. Monitor for 48 hours
3. Analyze log volume and patterns
4. Verify end-to-end tracing
5. Test alert triggers

### Phase 3: Production Environment
1. Deploy with 10% DEBUG sampling
2. Monitor for 24 hours
3. Gradually increase sampling if needed
4. Set up alerts for CRITICAL logs
5. Create dashboards for key metrics

### Rollback Plan
- Keep previous logging code for 2 weeks
- Feature flags for new logging features
- Revert individual tasks if needed
- Emergency disable via environment variable

---

## Documentation Updates

### Files to Update

1. **README.md** - Logging section
2. **docs/LOGGING.md** (new) - Comprehensive logging guide
3. **docs/DEVELOPMENT.md** - Logging best practices
4. **docs/TROUBLESHOOTING.md** - Using logs for debugging

### Key Documentation Topics

- When to use each log level
- CRITICAL vs ERROR guidelines
- Correlation ID usage
- SQL query logging interpretation
- Log sampling configuration
- Structured logging best practices
- Adding logs to new code

---

## Success Metrics

### Quantitative Metrics

- ✅ Logging coverage: 70% → 90%
- ✅ Repository coverage: 10% → 85%
- ✅ Service coverage: 60% → 90%
- ✅ Database visibility: 0% → 80%
- ✅ End-to-end tracing: 0% → 100%
- ✅ Mean time to debug: Reduce by 40%

### Qualitative Metrics

- ✅ Can trace any user action end-to-end
- ✅ Can identify slow SQL queries
- ✅ Can debug repository issues
- ✅ Can distinguish critical from normal errors
- ✅ Can analyze service layer decisions
- ✅ Alert fatigue reduced (CRITICAL only)

---

## Risk Management

### Identified Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Log volume explosion | Medium | High | Implement sampling first |
| Performance degradation | Low | High | Benchmark each task |
| Sensitive data leakage | Low | Critical | Parameter sanitization |
| Alert fatigue | Medium | Medium | Clear CRITICAL criteria |
| Development slowdown | Low | Low | Good documentation |

### Mitigation Strategies

1. **Log volume control:**
   - Start with 10% DEBUG sampling in production
   - Monitor volume daily for first week
   - Adjust sampling rate as needed

2. **Performance monitoring:**
   - Establish baseline before changes
   - Monitor P95 latency continuously
   - Rollback if degradation >5%

3. **Sensitive data:**
   - Review all parameter logging
   - Sanitize passwords, tokens, secrets
   - Add tests for sanitization

4. **Alert management:**
   - CRITICAL alerts go to PagerDuty
   - ERROR alerts to Slack channel
   - Weekly review of alert patterns

---

## Appendix A: Log Level Decision Tree

```
Is service unable to start or operate?
├─ YES → CRITICAL (log + exit)
└─ NO → ↓

Is this an unexpected error requiring investigation?
├─ YES → ERROR (log with exc_info=True)
└─ NO → ↓

Is this a concerning situation but recoverable?
├─ YES → WARNING (log with context)
└─ NO → ↓

Is this a significant business event?
├─ YES → INFO (log with metadata)
└─ NO → ↓

Is this detailed operational information?
└─ YES → DEBUG (consider sampling)
```

---

## Appendix B: Structured Logging Template

```python
# Template for new logging statements

logger.{level}(
    "{action_description}",  # Clear, concise description
    extra={
        # Required fields
        "operation": "{operation_type}",  # create, read, update, delete, etc.

        # Context fields (as applicable)
        "user_id": user_id,
        "entity_id": entity_id,
        "entity_type": "user|activity|category|settings",

        # Operation details
        "fields": list(kwargs.keys()),  # For updates
        "duration_ms": duration_ms,  # For timed operations

        # Error fields (for warnings/errors)
        "error": str(e),
        "error_type": type(e).__name__,

        # Service identification
        "service": "service_name",
        "component": "component_name"
    },
    exc_info=True  # Only for ERROR/CRITICAL
)
```

---

## Appendix C: Quick Reference Checklist

### Adding Logs to New Code

- [ ] Entry point: DEBUG log with parameters
- [ ] Business logic: INFO log for significant events
- [ ] External calls: DEBUG log request + INFO log response
- [ ] Errors: ERROR log with exc_info=True
- [ ] Critical failures: CRITICAL log + exit
- [ ] Use structured logging (extra={...})
- [ ] Include operation type in context
- [ ] Include relevant IDs (user_id, entity_id)
- [ ] Sanitize sensitive data
- [ ] Add tests for logging statements

### Code Review Checklist

- [ ] All error paths have ERROR logs
- [ ] CRITICAL only for fatal errors
- [ ] Structured context included
- [ ] No sensitive data in logs
- [ ] Performance impact acceptable
- [ ] Log level appropriate
- [ ] Message clear and actionable

---

## Appendix D: Environment Variables

```bash
# Logging configuration
LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL
DEBUG_SAMPLE_RATE=0.0-1.0  # Log sampling rate
SLOW_QUERY_THRESHOLD_MS=1000  # Slow query detection

# Correlation tracking
ENABLE_CORRELATION_ID=true|false

# Log output
LOG_FORMAT=json|text  # json for production
LOG_OUTPUT=stdout|file  # stdout for docker
```

---

## Contact & Support

**For questions or issues:**
- Technical lead: TBD
- Documentation: `docs/LOGGING.md`
- Issues: GitHub Issues tracker

**Review schedule:**
- Weekly: Implementation progress
- Bi-weekly: Metrics review
- Monthly: Coverage assessment

---

**End of Document**
