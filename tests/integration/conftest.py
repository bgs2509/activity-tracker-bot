"""
Pytest configuration and fixtures for integration tests.

This module provides session-scoped Test Containers and other fixtures
for running integration tests with real PostgreSQL and Redis instances.

Fixtures:
    Session-scoped containers:
    - postgres_container: PostgreSQL Test Container
    - redis_container: Redis Test Container

    Database fixtures:
    - database_url: Database connection URL
    - engine: SQLAlchemy async engine
    - db_session: SQLAlchemy async session with automatic rollback
    - clean_db: Truncates all tables before test

    API client:
    - api_client: HTTP client for Data API

    Test data factories:
    - test_user_factory: Factory for creating test users
    - test_category_factory: Factory for creating test categories

    Standard test data:
    - test_user: Standard test user (telegram_id=123456789)
    - test_category: Standard test category for test_user
    - test_activity: Standard test activity (1-hour duration)
    - test_user_settings: Standard user settings

    Telegram mocks:
    - mock_bot: Mocked Telegram bot
    - mock_message: Mocked Telegram message
    - mock_callback: Mocked callback query

    FSM storage:
    - fake_redis_storage: Fast fake Redis for Level 1/2 tests
    - redis_storage: Real Redis for Level 3 tests
    - redis_url: Redis connection URL
"""

import asyncio
import os
from typing import AsyncGenerator, Callable
from unittest.mock import AsyncMock, MagicMock

import pytest
import fakeredis.aioredis
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer


# ============================================================================
# SESSION-SCOPED CONTAINERS
# ============================================================================


@pytest.fixture(scope="session")
def postgres_container():
    """
    Create a PostgreSQL Test Container for the entire test session.

    This container is started once and reused across all tests for performance.
    The container is automatically stopped and removed after all tests complete.

    Yields:
        PostgresContainer: Running PostgreSQL container
    """
    container = PostgresContainer("postgres:15-alpine")
    try:
        container.start()
        yield container
    finally:
        container.stop()


@pytest.fixture(scope="session")
def redis_container():
    """
    Create a Redis Test Container for the entire test session.

    This container is started once and reused across all tests for performance.
    The container is automatically stopped and removed after all tests complete.

    Yields:
        RedisContainer: Running Redis container
    """
    container = RedisContainer("redis:7-alpine")
    try:
        container.start()
        yield container
    finally:
        container.stop()


# ============================================================================
# DATABASE FIXTURES
# ============================================================================


@pytest.fixture(scope="session")
def database_url(postgres_container: PostgresContainer) -> str:
    """
    Get database connection URL from Test Container.
    
    Args:
        postgres_container: PostgreSQL container fixture
        
    Returns:
        Database URL compatible with asyncpg
    """
    # Get connection URL and replace psycopg2 driver with asyncpg
    url = postgres_container.get_connection_url()
    return url.replace("psycopg2", "asyncpg")


@pytest.fixture(scope="session")
async def engine(database_url: str):
    """
    Create SQLAlchemy async engine for the test session.
    
    Args:
        database_url: Database connection URL
        
    Yields:
        AsyncEngine: SQLAlchemy async engine
    """
    from services.data_postgres_api.src.domain.models.base import Base
    
    engine = create_async_engine(database_url, echo=False, future=True)
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Create a new database session for each test with proper isolation.

    Uses connection-level transaction with savepoint to ensure
    complete test isolation. All changes are rolled back after each test.

    This pattern ensures:
    - No data leaks between tests
    - Proper rollback even with nested transactions
    - Clean database state for each test

    Args:
        engine: SQLAlchemy async engine

    Yields:
        AsyncSession: Isolated database session for the test
    """
    # Get connection from engine
    async with engine.connect() as connection:
        # Start outer transaction (will be rolled back)
        trans = await connection.begin()

        # Create session bound to this connection
        async_session = async_sessionmaker(
            bind=connection,
            class_=AsyncSession,
            expire_on_commit=False
        )

        async with async_session() as session:
            try:
                yield session
            finally:
                # Rollback session changes
                await session.close()
                # Rollback outer transaction (undoes everything)
                await trans.rollback()


@pytest.fixture
async def clean_db(engine):
    """
    Clean database before a test.

    Truncates all tables using metadata reflection (no hardcoded table names).
    This fixture is optional - use it only when you need explicit table truncation.

    Note: With the new db_session fixture using transaction rollback,
    this fixture is rarely needed. Use it only for special cases.

    Args:
        engine: SQLAlchemy async engine

    Yields:
        None: Database is cleaned before test runs
    """
    from services.data_postgres_api.src.domain.models.base import Base

    # Clean database before test
    async with engine.begin() as conn:
        # Get all table names from metadata (in reverse dependency order)
        tables = reversed(Base.metadata.sorted_tables)
        table_names = ", ".join([f'"{table.name}"' for table in tables])

        if table_names:
            # Truncate all tables with CASCADE to handle foreign keys
            await conn.execute(
                text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE")
            )

    yield

    # No cleanup needed - db_session handles rollback


# ============================================================================
# API CLIENT FIXTURES
# ============================================================================


@pytest.fixture(scope="session")
def api_base_url() -> str:
    """
    Get base URL for Data API.
    
    Returns:
        Base URL for the API (default: http://localhost:8080)
    """
    return os.getenv("DATA_API_URL", "http://localhost:8080")


@pytest.fixture
async def api_client(api_base_url: str) -> AsyncGenerator[AsyncClient, None]:
    """
    Create HTTP client for Data API.
    
    Args:
        api_base_url: Base URL for the API
        
    Yields:
        AsyncClient: HTTP client for making requests
    """
    async with AsyncClient(base_url=api_base_url, timeout=10.0) as client:
        yield client


# ============================================================================
# TEST DATA FACTORIES
# ============================================================================


@pytest.fixture
def test_user_factory(db_session: AsyncSession) -> Callable:
    """
    Factory for creating test users.
    
    Args:
        db_session: Database session
        
    Returns:
        Async function that creates and returns a user
        
    Example:
        user = await test_user_factory(telegram_id=12345, username="testuser")
    """
    from services.data_postgres_api.src.domain.models.user import User
    
    async def create_user(
        telegram_id: int = 123456789,
        username: str = "test_user",
        first_name: str = "Test",
        last_name: str = "User"
    ) -> User:
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user
    
    return create_user


@pytest.fixture
def test_category_factory(db_session: AsyncSession) -> Callable:
    """
    Factory for creating test categories.
    
    Args:
        db_session: Database session
        
    Returns:
        Async function that creates and returns a category
    """
    from services.data_postgres_api.src.domain.models.category import Category
    
    async def create_category(
        user_id: int,
        name: str = "Test Category",
        emoji: str = "📝"
    ) -> Category:
        category = Category(
            user_id=user_id,
            name=name,
            emoji=emoji
        )
        db_session.add(category)
        await db_session.commit()
        await db_session.refresh(category)
        return category
    
    return create_category


# ============================================================================
# STANDARD TEST DATA FIXTURES
# ============================================================================


@pytest.fixture
async def test_user(test_user_factory):
    """
    Standard test user fixture.

    Creates a default test user with predictable attributes.
    Use this when you need a single user for testing.

    Returns:
        User: Test user with telegram_id=123456789
    """
    return await test_user_factory(
        telegram_id=123456789,
        username="test_user",
        first_name="Test",
        last_name="User"
    )


@pytest.fixture
async def test_category(test_category_factory, test_user):
    """
    Standard test category fixture.

    Creates a default test category for the test user.
    Use this when you need a single category for testing.

    Args:
        test_category_factory: Category factory fixture
        test_user: Test user fixture

    Returns:
        Category: Test category belonging to test_user
    """
    return await test_category_factory(
        user_id=test_user.id,
        name="Test Category",
        emoji="📝"
    )


@pytest.fixture
async def test_activity(db_session, test_user, test_category):
    """
    Standard test activity fixture.

    Creates a completed activity for testing.
    Use this when you need a single activity for testing.

    Args:
        db_session: Database session
        test_user: Test user fixture
        test_category: Test category fixture

    Returns:
        Activity: Test activity with 1-hour duration
    """
    from datetime import datetime, timedelta
    from services.data_postgres_api.src.domain.models.activity import Activity

    activity = Activity(
        user_id=test_user.id,
        category_id=test_category.id,
        start_time=datetime.now() - timedelta(hours=1),
        end_time=datetime.now(),
        description="Test activity"
    )
    db_session.add(activity)
    await db_session.commit()
    await db_session.refresh(activity)
    return activity


@pytest.fixture
async def test_user_settings(db_session, test_user):
    """
    Standard test user settings fixture.

    Creates default user settings for testing.
    Use this when you need user settings for testing.

    Args:
        db_session: Database session
        test_user: Test user fixture

    Returns:
        UserSettings: Test user settings with default intervals
    """
    from services.data_postgres_api.src.domain.models.user_settings import UserSettings

    settings = UserSettings(
        user_id=test_user.id,
        poll_interval_weekday=30,
        poll_interval_weekend=60,
        polls_enabled=True,
        quiet_hours_start=None,
        quiet_hours_end=None
    )
    db_session.add(settings)
    await db_session.commit()
    await db_session.refresh(settings)
    return settings


# ============================================================================
# TELEGRAM BOT MOCKS
# ============================================================================


@pytest.fixture
def mock_bot():
    """
    Create mocked Telegram Bot for testing handlers.
    
    Returns:
        MagicMock: Mocked bot instance with common methods
    """
    bot = MagicMock()
    bot.send_message = AsyncMock()
    bot.edit_message_text = AsyncMock()
    bot.answer_callback_query = AsyncMock()
    bot.delete_message = AsyncMock()
    return bot


@pytest.fixture
def mock_message(mock_bot):
    """
    Create mocked Telegram Message.
    
    Args:
        mock_bot: Mocked bot instance
        
    Returns:
        MagicMock: Mocked message with common attributes
    """
    message = MagicMock()
    message.bot = mock_bot
    message.chat.id = 123456789
    message.from_user.id = 123456789
    message.from_user.username = "test_user"
    message.text = "Test message"
    message.answer = AsyncMock()
    message.edit_text = AsyncMock()
    message.delete = AsyncMock()
    return message


@pytest.fixture
def mock_callback(mock_bot):
    """
    Create mocked Telegram CallbackQuery.
    
    Args:
        mock_bot: Mocked bot instance
        
    Returns:
        MagicMock: Mocked callback query with common attributes
    """
    callback = MagicMock()
    callback.bot = mock_bot
    callback.from_user.id = 123456789
    callback.from_user.username = "test_user"
    callback.data = "test_callback"
    callback.message = mock_message(mock_bot)
    callback.answer = AsyncMock()
    callback.message.edit_text = AsyncMock()
    callback.message.delete = AsyncMock()
    return callback


# ============================================================================
# FSM STORAGE FIXTURES
# ============================================================================


@pytest.fixture
async def fake_redis_storage():
    """
    Create fake Redis storage for FSM testing.
    
    Uses fakeredis for fast in-memory FSM state management.
    Suitable for Level 1 and Level 2 tests.
    
    Yields:
        FakeRedis: In-memory Redis-compatible storage
    """
    fake_redis = fakeredis.aioredis.FakeRedis()
    yield fake_redis
    await fake_redis.flushall()
    await fake_redis.close()


@pytest.fixture
def redis_url(redis_container: RedisContainer) -> str:
    """
    Get Redis connection URL from Test Container.

    Args:
        redis_container: Redis container fixture

    Returns:
        Redis URL for FSM storage (for Level 3 tests)
    """
    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)
    return f"redis://{host}:{port}/0"


@pytest.fixture
async def redis_storage(redis_container: RedisContainer):
    """
    Create real Redis storage for Level 3 integration tests.

    Uses actual Redis container for full-stack testing.
    Data is flushed after each test for isolation.

    Args:
        redis_container: Redis container fixture

    Yields:
        Redis: Real Redis client connected to container
    """
    import redis.asyncio as aioredis

    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)

    client = await aioredis.from_url(
        f"redis://{host}:{port}/0",
        encoding="utf-8",
        decode_responses=True
    )

    try:
        yield client
    finally:
        await client.flushall()
        await client.close()


# ============================================================================
# PYTEST CONFIGURATION
# ============================================================================


@pytest.fixture(scope="session")
def event_loop():
    """
    Create event loop for async tests.
    
    Yields:
        asyncio event loop
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "level1: Level 1 integration tests (Handler → Service)"
    )
    config.addinivalue_line(
        "markers", "level2: Level 2 integration tests (Service → API)"
    )
    config.addinivalue_line(
        "markers", "level3: Level 3 integration tests (Full Stack)"
    )
