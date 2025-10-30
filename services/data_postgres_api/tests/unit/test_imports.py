"""
Import smoke tests for data_postgres_api service.

These tests verify that all modules can be imported without errors.
Catches missing dependencies, circular imports, and syntax errors.
"""
import pytest


@pytest.mark.unit
@pytest.mark.smoke
def test_import_main():
    """Verify main module can be imported."""
    try:
        from src import main
        assert main is not None
        assert hasattr(main, 'app')
    except ImportError as e:
        pytest.fail(f"Failed to import main module: {e}")


@pytest.mark.unit
@pytest.mark.smoke
def test_import_core_modules():
    """Verify core modules can be imported."""
    try:
        from src.core import config
        from src.core import logging

        assert config is not None
        assert logging is not None
    except ImportError as e:
        pytest.fail(f"Failed to import core modules: {e}")


@pytest.mark.unit
@pytest.mark.smoke
def test_import_api_routers():
    """Verify API routers can be imported."""
    try:
        from src.api.v1 import users
        from src.api.v1 import activities
        from src.api.v1 import categories

        assert users is not None
        assert activities is not None
        assert categories is not None
    except ImportError as e:
        pytest.fail(f"Failed to import API routers: {e}")


@pytest.mark.unit
@pytest.mark.smoke
def test_import_domain_models():
    """Verify domain models can be imported."""
    try:
        from src.domain import models
        assert models is not None
    except ImportError as e:
        pytest.fail(f"Failed to import domain models: {e}")


@pytest.mark.unit
@pytest.mark.smoke
def test_import_repositories():
    """Verify repositories can be imported."""
    try:
        from src.infrastructure.repositories import user_repository
        from src.infrastructure.repositories import activity_repository
        from src.infrastructure.repositories import category_repository

        assert user_repository is not None
        assert activity_repository is not None
        assert category_repository is not None
    except ImportError as e:
        pytest.fail(f"Failed to import repositories: {e}")


@pytest.mark.unit
@pytest.mark.smoke
def test_import_database():
    """Verify database infrastructure can be imported."""
    try:
        from src.infrastructure import database
        assert database is not None
    except ImportError as e:
        pytest.fail(f"Failed to import database infrastructure: {e}")
