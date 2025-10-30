"""Activity repository."""
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models.activity import Activity
from src.schemas.activity import ActivityCreate


class ActivityRepository:
    """Repository for Activity model."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, activity_data: ActivityCreate) -> Activity:
        """Create a new activity."""
        # Calculate duration in minutes
        duration = (activity_data.end_time - activity_data.start_time).total_seconds() / 60
        duration_minutes = round(duration)

        # Convert tags list to comma-separated string
        tags_str = None
        if activity_data.tags:
            tags_str = ",".join(activity_data.tags)

        activity = Activity(
            user_id=activity_data.user_id,
            category_id=activity_data.category_id,
            description=activity_data.description,
            tags=tags_str,
            start_time=activity_data.start_time,
            end_time=activity_data.end_time,
            duration_minutes=duration_minutes,
        )
        self.session.add(activity)
        await self.session.flush()
        await self.session.refresh(activity)
        return activity

    async def get_by_id(self, activity_id: int) -> Activity | None:
        """Get activity by ID."""
        result = await self.session.execute(
            select(Activity).where(Activity.id == activity_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user(
        self,
        user_id: int,
        limit: int = 10,
        offset: int = 0
    ) -> tuple[list[Activity], int]:
        """
        Get activities for a user with pagination.

        Returns:
            Tuple of (activities list, total count)
        """
        # Get total count
        count_result = await self.session.execute(
            select(func.count(Activity.id)).where(Activity.user_id == user_id)
        )
        total = count_result.scalar_one()

        # Get paginated activities
        result = await self.session.execute(
            select(Activity)
            .where(Activity.user_id == user_id)
            .order_by(Activity.start_time.desc())
            .limit(limit)
            .offset(offset)
        )
        activities = list(result.scalars().all())

        return activities, total
