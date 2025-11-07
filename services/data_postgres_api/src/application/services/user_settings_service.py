"""
User settings application service.

This module contains business logic for user settings operations.
"""

from typing import Optional

from src.domain.models.user_settings import UserSettings
from src.infrastructure.repositories.user_settings_repository import UserSettingsRepository
from src.schemas.user_settings import UserSettingsCreate, UserSettingsUpdate


class UserSettingsService:
    """
    Application service for user settings business logic.

    Handles user settings creation, retrieval, and updates with
    business rule validation (e.g., time ranges, intervals).
    """

    def __init__(self, repository: UserSettingsRepository):
        """
        Initialize service with repository.

        Args:
            repository: User settings repository instance for data access
        """
        self.repository = repository

    async def create_settings(self, settings_data: UserSettingsCreate) -> UserSettings:
        """
        Create new user settings with validation.

        Args:
            settings_data: Settings creation data from API request

        Returns:
            Created settings with generated ID

        Raises:
            ValueError: If validation fails or settings already exist for user
        """
        # Business rule: Only one settings record per user
        existing = await self.repository.get_by_user_id(settings_data.user_id)
        if existing:
            raise ValueError(
                f"Settings already exist for user {settings_data.user_id}. "
                f"Use update endpoint instead."
            )

        # Business validation: poll intervals
        self._validate_poll_intervals(
            settings_data.poll_interval_weekday,
            settings_data.poll_interval_weekend
        )

        # Note: Quiet hours validation is handled by Pydantic schema (time type)

        return await self.repository.create(settings_data)

    async def get_by_user_id(self, user_id: int) -> Optional[UserSettings]:
        """
        Get settings for user.

        Args:
            user_id: User identifier

        Returns:
            User settings if found, None otherwise
        """
        return await self.repository.get_by_user_id(user_id)

    async def update_settings(
        self,
        user_id: int,
        settings_data: UserSettingsUpdate
    ) -> Optional[UserSettings]:
        """
        Update user settings with validation.

        Args:
            user_id: User identifier
            settings_data: Settings update data (partial updates allowed)

        Returns:
            Updated settings if user found, None otherwise

        Raises:
            ValueError: If validation fails or settings not found
        """
        existing = await self.repository.get_by_user_id(user_id)
        if not existing:
            raise ValueError(
                f"Settings not found for user {user_id}. "
                f"Create settings first."
            )

        # Business validation: poll intervals (if provided)
        if settings_data.poll_interval_weekday is not None or settings_data.poll_interval_weekend is not None:
            weekday = settings_data.poll_interval_weekday or existing.poll_interval_weekday
            weekend = settings_data.poll_interval_weekend or existing.poll_interval_weekend
            self._validate_poll_intervals(weekday, weekend)

        # Note: Quiet hours validation is handled by Pydantic schema (time type)

        return await self.repository.update(user_id, settings_data)

    def _validate_poll_intervals(self, weekday: int, weekend: int) -> None:
        """
        Validate poll interval values.

        Args:
            weekday: Weekday poll interval in minutes
            weekend: Weekend poll interval in minutes

        Raises:
            ValueError: If intervals are invalid
        """
        if weekday < 30:
            raise ValueError(
                f"Weekday poll interval ({weekday}m) must be at least 30 minutes"
            )
        if weekend < 30:
            raise ValueError(
                f"Weekend poll interval ({weekend}m) must be at least 30 minutes"
            )
        if weekday > 1440:  # 24 hours
            raise ValueError(
                f"Weekday poll interval ({weekday}m) cannot exceed 24 hours (1440m)"
            )
        if weekend > 1440:
            raise ValueError(
                f"Weekend poll interval ({weekend}m) cannot exceed 24 hours (1440m)"
            )
