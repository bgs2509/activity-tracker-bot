"""FastAPI application entry point for data_postgres_api service."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.logging import setup_logging
from src.api.v1.users import router as users_router
from src.api.v1.categories import router as categories_router
from src.api.v1.activities import router as activities_router
from src.api.v1.user_settings import router as user_settings_router
from src.api.middleware.correlation import CorrelationIDMiddleware
from src.api.middleware.logging import RequestLoggingMiddleware
from src.infrastructure.database.connection import engine, get_db
from src.domain.models.base import Base
# Import all models for SQLAlchemy relationship resolution
from src.domain.models import User, Category, Activity, UserSettings

# Configure structured JSON logging (MANDATORY for Level 1)
setup_logging(service_name="data_postgres_api", log_level=settings.log_level)
logger = logging.getLogger(__name__)

# ============================================================================
# OPTIONAL: Sentry Error Tracking Integration
# ============================================================================
# To enable Sentry error tracking for production monitoring:
#
# 1. Install the SDK: pip install sentry-sdk[fastapi]
#
# 2. Add SENTRY_DSN to environment variables in .env:
#    SENTRY_DSN=https://your-key@sentry.io/your-project-id
#
# 3. Add to src/core/config.py settings:
#    sentry_dsn: str | None = None
#
# 4. Initialize Sentry before creating FastAPI app:
#    if settings.sentry_dsn:
#        import sentry_sdk
#        from sentry_sdk.integrations.fastapi import FastApiIntegration
#        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
#
#        sentry_sdk.init(
#            dsn=settings.sentry_dsn,
#            environment=settings.environment,  # e.g., "production", "staging"
#            traces_sample_rate=1.0,  # Adjust for production (0.1 = 10%)
#            integrations=[
#                FastApiIntegration(transaction_style="endpoint"),
#                SqlalchemyIntegration(),
#            ],
#        )
#        logger.info("Sentry error tracking initialized")
#
# 5. Sentry will automatically capture:
#    - Unhandled exceptions
#    - HTTP request context
#    - Database query performance
#    - Custom breadcrumbs from logs
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.

    Handles startup and shutdown events in modern FastAPI style.
    Replaces deprecated @app.on_event() decorators.

    Args:
        app: FastAPI application instance

    Yields:
        Control to application runtime
    """
    # Startup
    logger.info("Starting data_postgres_api service")

    # Database schema is managed by Alembic migrations
    # For development/testing with auto-creation, set ENABLE_DB_AUTO_CREATE=true
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


# Create FastAPI app with lifespan context manager
app = FastAPI(
    title=settings.app_name,
    description="HTTP Data Access Service for PostgreSQL",
    version="1.0.0",
    lifespan=lifespan,
)

# Register middleware (order matters - executed in reverse order during request)
# 1. CORS - last (outermost layer)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Request logging - logs with correlation ID
app.add_middleware(RequestLoggingMiddleware)

# 3. Correlation ID - first (innermost layer, runs first)
app.add_middleware(CorrelationIDMiddleware)


# Include routers
app.include_router(users_router, prefix=settings.api_v1_prefix)
app.include_router(categories_router, prefix=settings.api_v1_prefix)
app.include_router(activities_router, prefix=settings.api_v1_prefix)
app.include_router(user_settings_router, prefix=settings.api_v1_prefix)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": settings.app_name,
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/health/live")
async def liveness() -> dict[str, str]:
    """
    Liveness probe endpoint.

    Checks if service process is running. This endpoint should ALWAYS
    return 200 unless process is dead. Does NOT check external dependencies.

    Returns:
        Status indicating service is alive

    Notes:
        Used by Docker/Kubernetes for liveness checks
    """
    return {"status": "alive"}


@app.get("/health/ready")
async def readiness(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """
    Readiness probe endpoint.

    Checks if service is ready to accept requests by verifying:
    - Database connection is working
    - Service can handle requests

    Args:
        db: Database session (injected by FastAPI)

    Returns:
        Status with database connection state

    Raises:
        HTTPException: 503 Service Unavailable if database unreachable

    Notes:
        Used by Docker/Kubernetes for readiness checks
    """
    from sqlalchemy import text

    try:
        # Verify database connection with simple query
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
