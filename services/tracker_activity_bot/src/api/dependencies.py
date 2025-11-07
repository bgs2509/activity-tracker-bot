"""
Dependency injection providers for bot handlers.

This module provides centralized dependency management for HTTP clients
and services used throughout the bot handlers.
"""

import logging
from typing import Optional

from src.infrastructure.http_clients.http_client import DataAPIClient
from src.infrastructure.http_clients.activity_service import ActivityService
from src.infrastructure.http_clients.category_service import CategoryService
from src.infrastructure.http_clients.user_service import UserService
from src.infrastructure.http_clients.user_settings_service import UserSettingsService

logger = logging.getLogger(__name__)


# Shared HTTP client instance (created once per bot lifetime)
_api_client: Optional[DataAPIClient] = None


def get_api_client() -> DataAPIClient:
    """
    Get or create shared Data API HTTP client.

    Returns:
        Shared HTTP client instance for Data API communication

    Note:
        Creates client on first call, reuses same instance for subsequent calls.
        Must call close_api_client() on shutdown to prevent connection leaks.
    """
    global _api_client
    if _api_client is None:
        _api_client = DataAPIClient()
        logger.info("Created shared Data API HTTP client")
    return _api_client


async def close_api_client() -> None:
    """
    Close shared HTTP client and cleanup connections.

    This function must be called during application shutdown to prevent
    connection pool leaks. It's safe to call multiple times.
    """
    global _api_client
    if _api_client is not None:
        await _api_client.close()
        _api_client = None
        logger.info("Closed Data API HTTP client")


# Service dependency providers


def get_activity_service() -> ActivityService:
    """
    Provide activity service instance with shared HTTP client.

    Returns:
        Activity service for activity-related operations
    """
    client = get_api_client()
    return ActivityService(client)


def get_category_service() -> CategoryService:
    """
    Provide category service instance with shared HTTP client.

    Returns:
        Category service for category-related operations
    """
    client = get_api_client()
    return CategoryService(client)


def get_user_service() -> UserService:
    """
    Provide user service instance with shared HTTP client.

    Returns:
        User service for user-related operations
    """
    client = get_api_client()
    return UserService(client)


def get_user_settings_service() -> UserSettingsService:
    """
    Provide user settings service instance with shared HTTP client.

    Returns:
        User settings service for settings-related operations
    """
    client = get_api_client()
    return UserSettingsService(client)
