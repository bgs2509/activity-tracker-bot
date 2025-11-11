"""Database connection management with SQLAlchemy async."""
import logging
import time
from typing import AsyncGenerator, Any, Dict, List, Optional, Tuple, Union

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import settings

logger = logging.getLogger(__name__)

# Slow query threshold in seconds
SLOW_QUERY_THRESHOLD = 1.0

# Create async engine
engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=False,
    future=True,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

# Create async sessionmaker
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database session.

    Yields:
        AsyncSession: Database session
    """
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def _sanitize_parameters(
    parameters: Union[Dict[str, Any], List, Tuple, None]
) -> Optional[str]:
    """Sanitize sensitive data in SQL parameters.

    Args:
        parameters: Query parameters to sanitize

    Returns:
        Sanitized parameters safe for logging
    """
    if not parameters:
        return None

    # List of sensitive field names to redact
    sensitive_fields = ['password', 'token', 'secret', 'api_key', 'auth']

    if isinstance(parameters, dict):
        sanitized = {
            k: '***REDACTED***' if any(s in str(k).lower() for s in sensitive_fields) else v
            for k, v in parameters.items()
        }
        return str(sanitized)[:100]
    elif isinstance(parameters, (list, tuple)):
        # For positional parameters, just return count
        return f"<{len(parameters)} parameters>"

    return str(parameters)[:100]


@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Log SQL query execution start.

    Args:
        conn: Database connection
        cursor: Database cursor
        statement: SQL statement
        parameters: Query parameters
        context: Execution context
        executemany: Whether executing multiple statements
    """
    conn.info.setdefault("query_start_time", []).append(time.time())

    # Sanitize sensitive data in parameters
    safe_params = _sanitize_parameters(parameters)

    logger.debug(
        "Executing SQL query",
        extra={
            "sql_preview": statement[:200],  # First 200 chars
            "params_preview": safe_params,
            "executemany": executemany
        }
    )


@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Log SQL query execution completion with timing.

    Args:
        conn: Database connection
        cursor: Database cursor
        statement: SQL statement
        parameters: Query parameters
        context: Execution context
        executemany: Whether executing multiple statements
    """
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
        safe_params = _sanitize_parameters(parameters)
        logger.warning(
            "Slow SQL query detected",
            extra={
                "sql": statement,
                "duration_ms": duration_ms,
                "params": safe_params,
                "threshold_ms": SLOW_QUERY_THRESHOLD * 1000
            }
        )
