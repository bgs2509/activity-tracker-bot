"""
Activity application service.

This module contains business logic for activity operations,
orchestrating between API layer and data layer.
"""

from typing import Optional

from src.application.validators.time_validators import (
    validate_activity_duration,
    validate_end_time,
)
from src.domain.models.activity import Activity
from src.infrastructure.repositories.activity_repository import ActivityRepository
from src.schemas.activity import ActivityCreate


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

        Args:
            activity_data: Activity creation data from API request

        Returns:
            Created activity with generated ID and calculated duration

        Raises:
            ValueError: If business rules violated (e.g., invalid time range)
        """
        # Business validation using centralized validators
        validate_end_time(activity_data.end_time, activity_data.start_time)
        validate_activity_duration(activity_data.start_time, activity_data.end_time, max_hours=24)

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
