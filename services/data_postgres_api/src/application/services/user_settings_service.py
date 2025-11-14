"""
User settings application service.

This module contains business logic for user settings operations.
"""

import logging
from typing import Optional

from src.domain.models.user_settings import UserSettings
from src.infrastructure.repositories.user_settings_repository import UserSettingsRepository
from src.schemas.user_settings import UserSettingsCreate, UserSettingsUpdate

logger = logging.getLogger(__name__)


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
        logger.debug(
            "create_settings started",
            extra={
                "user_id": settings_data.user_id,
                "poll_interval_weekday": settings_data.poll_interval_weekday,
                "poll_interval_weekend": settings_data.poll_interval_weekend,
                "reminders_enabled": settings_data.reminders_enabled
            }
        )

        try:
            # Business rule: Only one settings record per user
            existing = await self.repository.get_by_user_id(settings_data.user_id)
            if existing:
                logger.warning(
                    "settings already exist",
                    extra={"user_id": settings_data.user_id, "settings_id": existing.id}
                )
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

            settings = await self.repository.create(settings_data)
            logger.info(
                "settings_created",
                extra={
                    "settings_id": settings.id,
                    "user_id": settings.user_id,
                    "poll_interval_weekday": settings.poll_interval_weekday,
                    "poll_interval_weekend": settings.poll_interval_weekend
                }
            )
            return settings
        except Exception as e:
            logger.error(
                "create_settings failed",
                extra={"user_id": settings_data.user_id, "error": str(e)},
                exc_info=True
            )
            raise

    async def get_by_user_id(self, user_id: int) -> Optional[UserSettings]:
        """
        Get settings for user.

        Args:
            user_id: User identifier

        Returns:
            User settings if found, None otherwise
        """
        logger.debug("get_by_user_id started", extra={"user_id": user_id})
        settings = await self.repository.get_by_user_id(user_id)
        logger.debug(
            "get_by_user_id completed",
            extra={"user_id": user_id, "found": settings is not None}
        )
        return settings

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
            Updated settings if found, None otherwise

        Raises:
            ValueError: If validation fails or settings not found
        """
        # Collect changed fields for logging
        changed_fields = {}
        if settings_data.poll_interval_weekday is not None:
            changed_fields["poll_interval_weekday"] = settings_data.poll_interval_weekday
        if settings_data.poll_interval_weekend is not None:
            changed_fields["poll_interval_weekend"] = settings_data.poll_interval_weekend
        if settings_data.reminders_enabled is not None:
            changed_fields["reminders_enabled"] = settings_data.reminders_enabled
        if settings_data.quiet_hours_start is not None:
            changed_fields["quiet_hours_start"] = str(settings_data.quiet_hours_start)
        if settings_data.quiet_hours_end is not None:
            changed_fields["quiet_hours_end"] = str(settings_data.quiet_hours_end)

        logger.debug(
            "update_settings started",
            extra={"user_id": user_id, "changed_fields": changed_fields}
        )

        try:
            existing = await self.repository.get_by_user_id(user_id)
            if not existing:
                logger.warning("settings not found for update", extra={"user_id": user_id})
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

            updated_settings = await self.repository.update(user_id, settings_data)
            logger.info(
                "settings_updated",
                extra={"user_id": user_id, "changed_fields": changed_fields}
            )
            return updated_settings
        except Exception as e:
            logger.error(
                "update_settings failed",
                extra={"user_id": user_id, "error": str(e)},
                exc_info=True
            )
            raise

    def _validate_poll_intervals(self, weekday: int, weekend: int) -> None:
        """
        Validate poll interval values.

        Args:
            weekday: Weekday poll interval in minutes
            weekend: Weekend poll interval in minutes

        Raises:
            ValueError: If intervals are invalid
        """
        logger.debug(
            "validating poll intervals",
            extra={"weekday": weekday, "weekend": weekend}
        )

        if weekday < 1:
            logger.warning(
                "invalid weekday interval",
                extra={"weekday": weekday, "reason": "too_small"}
            )
            raise ValueError(
                f"Weekday poll interval ({weekday}m) must be at least 1 minute"
            )
        if weekend < 1:
            logger.warning(
                "invalid weekend interval",
                extra={"weekend": weekend, "reason": "too_small"}
            )
            raise ValueError(
                f"Weekend poll interval ({weekend}m) must be at least 1 minute"
            )
        if weekday > 1440:  # 24 hours
            logger.warning(
                "invalid weekday interval",
                extra={"weekday": weekday, "reason": "too_large"}
            )
            raise ValueError(
                f"Weekday poll interval ({weekday}m) cannot exceed 24 hours (1440m)"
            )
        if weekend > 1440:
            logger.warning(
                "invalid weekend interval",
                extra={"weekend": weekend, "reason": "too_large"}
            )
            raise ValueError(
                f"Weekend poll interval ({weekend}m) cannot exceed 24 hours (1440m)"
            )

        logger.debug("poll intervals validation passed")
