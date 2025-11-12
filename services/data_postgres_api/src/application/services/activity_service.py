"""
Activity application service.

This module contains business logic for activity operations,
orchestrating between API layer and data layer.
"""

from datetime import timedelta
from typing import Optional
import logging

from src.application.validators.time_validators import validate_end_time
from src.domain.models.activity import Activity
from src.infrastructure.repositories.activity_repository import ActivityRepository
from src.schemas.activity import ActivityCreate

logger = logging.getLogger(__name__)


class ActivityService:
    """
    Application service for activity business logic.

    Orchestrates repository calls and business rules.
    Does NOT contain infrastructure concerns (HTTP, DB).
    """

    def __init__(self, repository: ActivityRepository):
        """
        Initialize service with repository.

        Args:
            repository: Activity repository instance for data access
        """
        self.repository = repository

    async def create_activity(self, activity_data: ActivityCreate) -> Activity:
        """
        Create new activity with business validation.

        Automatically caps activity duration at 24 hours maximum.

        Args:
            activity_data: Activity creation data from API request

        Returns:
            Created activity with generated ID and calculated duration

        Raises:
            ValueError: If business rules violated (e.g., invalid time range)
        """
        # Business validation
        validate_end_time(activity_data.end_time, activity_data.start_time)

        # Cap duration at 24 hours maximum (similar to sleep handling in bot)
        max_duration = timedelta(hours=24)
        duration = activity_data.end_time - activity_data.start_time

        if duration > max_duration:
            # Adjust end_time to cap at 24 hours
            original_end = activity_data.end_time
            activity_data.end_time = activity_data.start_time + max_duration

            logger.warning(
                "Activity duration capped at 24 hours",
                extra={
                    "user_id": activity_data.user_id,
                    "original_duration_hours": duration.total_seconds() / 3600,
                    "capped_duration_hours": 24.0,
                    "original_end_time": original_end.isoformat(),
                    "adjusted_end_time": activity_data.end_time.isoformat(),
                }
            )

        # Delegate to repository for persistence
        activity = await self.repository.create(activity_data)
        return activity

    async def get_activity_by_id(self, activity_id: int) -> Optional[Activity]:
        """
        Get activity by ID.

        Args:
            activity_id: Activity identifier

        Returns:
            Activity if found, None otherwise
        """
        return await self.repository.get_by_id(activity_id)

    async def get_user_activities(
        self,
        user_id: int,
        limit: int = 10
    ) -> list[Activity]:
        """
        Get recent activities for user.

        Args:
            user_id: User identifier
            limit: Maximum activities to return (default: 10)

        Returns:
            List of recent activities

        Raises:
            ValueError: If limit is invalid
        """
        # Business validation: limit parameter
        if limit < 1 or limit > 100:
            raise ValueError(f"Limit must be between 1 and 100, got {limit}")

        return await self.repository.get_recent_by_user(user_id, limit)

    async def get_user_activities_by_category(
        self,
        user_id: int,
        category_id: int,
        limit: int = 10
    ) -> list[Activity]:
        """
        Get recent activities for user filtered by category.

        Args:
            user_id: User identifier
            category_id: Category identifier to filter by
            limit: Maximum activities to return (default: 10)

        Returns:
            List of recent activities for the specified category

        Raises:
            ValueError: If limit is invalid
        """
        # Business validation: limit parameter
        if limit < 1 or limit > 100:
            raise ValueError(f"Limit must be between 1 and 100, got {limit}")

        return await self.repository.get_recent_by_user_and_category(user_id, category_id, limit)
