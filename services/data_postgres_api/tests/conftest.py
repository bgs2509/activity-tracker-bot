"""
Shared pytest fixtures for data_postgres_api tests.

This module loads test environment variables from .env.test and provides
shared fixtures for all test modules in the service.

Environment Setup:
    Test environment variables are loaded from .env.test in the project root.
    This file contains safe dummy values that satisfy pydantic Settings
    validation without exposing real secrets.

    If .env.test is not found, fallback values are set to ensure tests
    can run in any environment.
"""
import pytest
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load test environment variables FIRST (before any imports from src)
# This ensures Settings classes can initialize without ValidationError
project_root = Path(__file__).parent.parent.parent.parent
test_env_path = project_root / ".env.test"

if test_env_path.exists():
    # Load .env.test with override=False to respect existing environment variables
    load_dotenv(test_env_path, override=False)
else:
    # Fallback: set minimal required values if .env.test doesn't exist
    os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
    os.environ.setdefault("LOG_LEVEL", "DEBUG")
    os.environ.setdefault("ENABLE_DB_AUTO_CREATE", "false")

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


@pytest.fixture(scope="session")
def service_name():
    """Return service name for logging."""
    return "data_postgres_api"
