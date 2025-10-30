"""FastAPI application entry point for data_postgres_api service."""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import settings
from src.core.logging import setup_logging
from src.api.v1.users import router as users_router
from src.api.v1.categories import router as categories_router
from src.api.v1.activities import router as activities_router
from src.infrastructure.database.connection import engine
from src.domain.models.base import Base

# Configure structured JSON logging (MANDATORY for Level 1)
setup_logging(service_name="data_postgres_api", log_level=settings.log_level)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="HTTP Data Access Service for PostgreSQL",
    version="1.0.0",
)

# CORS middleware (PoC level - allow all origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Create database tables on startup."""
    logger.info("Starting data_postgres_api service")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down data_postgres_api service")
    await engine.dispose()


# Include routers
app.include_router(users_router, prefix=settings.api_v1_prefix)
app.include_router(categories_router, prefix=settings.api_v1_prefix)
app.include_router(activities_router, prefix=settings.api_v1_prefix)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": settings.app_name,
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
