"""
Activity application service.

This module contains business logic for activity operations,
orchestrating between API layer and data layer.
"""

from typing import Optional

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
        # Business validation: end_time must be after start_time
        if activity_data.end_time <= activity_data.start_time:
            raise ValueError(
                f"End time ({activity_data.end_time}) must be after "
                f"start time ({activity_data.start_time})"
            )

        # Business validation: duration shouldn't exceed 24 hours
        duration_seconds = (activity_data.end_time - activity_data.start_time).total_seconds()
        if duration_seconds > 24 * 3600:
            raise ValueError(
                f"Activity duration ({duration_seconds / 3600:.1f}h) "
                f"exceeds maximum allowed duration (24h)"
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
        limit: int = 10,
        offset: int = 0
    ) -> tuple[list[Activity], int]:
        """
        Get paginated activities for user.

        Args:
            user_id: User identifier
            limit: Maximum activities to return (default: 10)
            offset: Number of activities to skip (default: 0)

        Returns:
            Tuple of (activities list, total count)

        Raises:
            ValueError: If limit or offset are invalid
        """
        # Business validation: pagination parameters
        if limit < 1 or limit > 100:
            raise ValueError(f"Limit must be between 1 and 100, got {limit}")
        if offset < 0:
            raise ValueError(f"Offset must be >= 0, got {offset}")

        return await self.repository.get_by_user(user_id, limit, offset)
