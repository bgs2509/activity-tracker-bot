"""
Shared pytest fixtures for smoke tests.
"""
import pytest


@pytest.fixture(scope="session")
def docker_services_timeout():
    """Timeout in seconds to wait for Docker services."""
    return 60
