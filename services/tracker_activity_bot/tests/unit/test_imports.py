"""
Import smoke tests for tracker_activity_bot service.

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
def test_import_api_handlers():
    """Verify API handlers can be imported."""
    try:
        from src.api.handlers import start
        from src.api.handlers import activity
        from src.api.handlers import categories
        from src.api.handlers import poll
        from src.api.handlers import settings

        assert start is not None
        assert activity is not None
        assert categories is not None
        assert poll is not None
        assert settings is not None
    except ImportError as e:
        pytest.fail(f"Failed to import API handlers: {e}")


@pytest.mark.unit
@pytest.mark.smoke
def test_import_infrastructure_http_clients():
    """Verify infrastructure HTTP clients can be imported."""
    try:
        from src.infrastructure.http_clients import activity_service
        from src.infrastructure.http_clients import category_service
        from src.infrastructure.http_clients import user_service
        from src.infrastructure.http_clients import user_settings_service
        from src.infrastructure.http_clients import http_client

        assert activity_service is not None
        assert category_service is not None
        assert user_service is not None
        assert user_settings_service is not None
        assert http_client is not None
    except ImportError as e:
        pytest.fail(f"Failed to import infrastructure HTTP clients: {e}")


@pytest.mark.unit
@pytest.mark.smoke
def test_import_keyboards():
    """Verify keyboard builders can be imported."""
    try:
        from src.api.keyboards import main_menu
        from src.api.keyboards import time_select
        from src.api.keyboards import poll
        from src.api.keyboards import settings

        assert main_menu is not None
        assert time_select is not None
        assert poll is not None
        assert settings is not None
    except ImportError as e:
        pytest.fail(f"Failed to import keyboards: {e}")


@pytest.mark.unit
@pytest.mark.smoke
def test_import_states():
    """Verify FSM states can be imported."""
    try:
        from src.api.states import activity
        from src.api.states import category
        from src.api.states import settings

        assert activity is not None
        assert category is not None
        assert settings is not None
    except ImportError as e:
        pytest.fail(f"Failed to import states: {e}")


@pytest.mark.unit
@pytest.mark.smoke
def test_import_application_services():
    """Verify application services can be imported."""
    try:
        from src.application.services import scheduler_service

        assert scheduler_service is not None
    except ImportError as e:
        pytest.fail(f"Failed to import application services: {e}")


@pytest.mark.unit
@pytest.mark.smoke
def test_import_application_utils():
    """Verify application utilities can be imported."""
    try:
        from src.application.utils import formatters
        from src.application.utils import time_parser
        from src.application.utils import timezone_helper

        assert formatters is not None
        assert time_parser is not None
        assert timezone_helper is not None
    except ImportError as e:
        pytest.fail(f"Failed to import application utilities: {e}")
