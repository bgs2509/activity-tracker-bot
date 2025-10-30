"""
Shared pytest fixtures for data_postgres_api tests.
"""
import pytest
import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


@pytest.fixture(scope="session")
def service_name():
    """Return service name for logging."""
    return "data_postgres_api"
