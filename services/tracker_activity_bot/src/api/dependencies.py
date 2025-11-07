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
from src.application.services.scheduler_service import SchedulerService
from src.application.protocols.scheduler import PollSchedulerProtocol

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


# Service Container with lazy initialization


class ServiceContainer:
    """
    Service container providing lazy initialization of all services.

    This container eliminates repeated service instantiation across handlers
    by providing centralized, lazy-loaded service instances.

    Now includes scheduler for DIP compliance (no global state).

    Example:
        @router.callback_query(F.data == "action")
        async def handler(callback: types.CallbackQuery, services: ServiceContainer):
            user = await services.user.get_by_telegram_id(callback.from_user.id)
            await services.scheduler.schedule_poll(...)
    """

    def __init__(
        self,
        api_client: Optional[DataAPIClient] = None,
        scheduler: Optional[PollSchedulerProtocol] = None
    ):
        """
        Initialize service container.

        Args:
            api_client: HTTP client instance, uses shared client if not provided
            scheduler: Scheduler instance, creates new if not provided (DIP)
        """
        self._api_client = api_client or get_api_client()
        self._scheduler = scheduler or SchedulerService()
        self._user_service: Optional[UserService] = None
        self._category_service: Optional[CategoryService] = None
        self._activity_service: Optional[ActivityService] = None
        self._settings_service: Optional[UserSettingsService] = None

    @property
    def user(self) -> UserService:
        """Get user service instance (lazy initialization)."""
        if self._user_service is None:
            self._user_service = UserService(self._api_client)
        return self._user_service

    @property
    def category(self) -> CategoryService:
        """Get category service instance (lazy initialization)."""
        if self._category_service is None:
            self._category_service = CategoryService(self._api_client)
        return self._category_service

    @property
    def activity(self) -> ActivityService:
        """Get activity service instance (lazy initialization)."""
        if self._activity_service is None:
            self._activity_service = ActivityService(self._api_client)
        return self._activity_service

    @property
    def settings(self) -> UserSettingsService:
        """Get user settings service instance (lazy initialization)."""
        if self._settings_service is None:
            self._settings_service = UserSettingsService(self._api_client)
        return self._settings_service

    @property
    def scheduler(self) -> PollSchedulerProtocol:
        """
        Get scheduler service instance.

        Returns scheduler for poll scheduling operations.
        Injected via constructor for testability (DIP compliance).

        Returns:
            Scheduler implementing PollSchedulerProtocol
        """
        return self._scheduler


# Shared service container instance
_service_container: Optional[ServiceContainer] = None


def get_service_container() -> ServiceContainer:
    """
    Get or create shared service container.

    Returns:
        Shared service container instance
    """
    global _service_container
    if _service_container is None:
        _service_container = ServiceContainer()
        logger.info("Created shared service container")
    return _service_container


# Legacy service dependency providers (kept for backward compatibility)


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
