"""Activity repository."""
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from pydantic import BaseModel

from src.domain.models.activity import Activity
from src.schemas.activity import ActivityCreate
from src.infrastructure.repositories.base import BaseRepository


# Placeholder update schema for BaseRepository (activities don't have updates)
class ActivityUpdate(BaseModel):
    """Placeholder update schema for Activity."""
    pass


class ActivityRepository(BaseRepository[Activity, ActivityCreate, ActivityUpdate]):
    """Repository for Activity model."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Activity)

    async def create(self, data: ActivityCreate) -> Activity:
        """
        Create a new activity with calculated duration and formatted tags.

        Overrides base create() to add custom logic for:
        - Duration calculation from start_time to end_time
        - Tag list to comma-separated string conversion

        Args:
            data: Activity creation data

        Returns:
            Created activity with generated ID
        """
        # Calculate duration in minutes
        duration = (data.end_time - data.start_time).total_seconds() / 60
        duration_minutes = round(duration)

        # Convert tags list to comma-separated string
        tags_str = None
        if data.tags:
            tags_str = ",".join(data.tags)

        activity = Activity(
            user_id=data.user_id,
            category_id=data.category_id,
            description=data.description,
            tags=tags_str,
            start_time=data.start_time,
            end_time=data.end_time,
            duration_minutes=duration_minutes,
        )
        self.session.add(activity)
        await self.session.flush()
        await self.session.refresh(activity)
        return activity

    async def get_recent_by_user(
        self,
        user_id: int,
        limit: int = 10
    ) -> list[Activity]:
        """
        Get recent activities for a user with category data.

        Args:
            user_id: User identifier
            limit: Maximum activities to return

        Returns:
            List of activities with category relationship loaded, ordered by most recent first
        """
        result = await self.session.execute(
            select(Activity)
            .options(joinedload(Activity.category))
            .where(Activity.user_id == user_id)
            .order_by(Activity.start_time.desc())
            .limit(limit)
        )
        return list(result.unique().scalars().all())

    async def get_recent_by_user_and_category(
        self,
        user_id: int,
        category_id: int,
        limit: int = 10
    ) -> list[Activity]:
        """
        Get recent activities for a user filtered by category with category data.

        Args:
            user_id: User identifier
            category_id: Category identifier to filter by
            limit: Maximum activities to return

        Returns:
            List of activities with category relationship loaded for the specified category, ordered by most recent first
        """
        result = await self.session.execute(
            select(Activity)
            .options(joinedload(Activity.category))
            .where(Activity.user_id == user_id, Activity.category_id == category_id)
            .order_by(Activity.start_time.desc())
            .limit(limit)
        )
        return list(result.unique().scalars().all())
