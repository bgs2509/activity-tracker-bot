"""Activity service for interacting with activities API."""
from datetime import datetime
from src.infrastructure.http_clients.http_client import DataAPIClient


class ActivityService:
    """Service for activity-related operations."""

    def __init__(self, client: DataAPIClient):
        self.client = client

    async def create_activity(
        self,
        user_id: int,
        category_id: int | None,
        description: str,
        tags: list[str] | None,
        start_time: datetime,
        end_time: datetime
    ) -> dict:
        """Create a new activity."""
        return await self.client.post("/api/v1/activities", json={
            "user_id": user_id,
            "category_id": category_id,
            "description": description,
            "tags": tags,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        })

    async def get_user_activities(
        self,
        user_id: int,
        limit: int = 10
    ) -> dict:
        """Get recent activities for a user."""
        return await self.client.get(
            f"/api/v1/activities?user_id={user_id}&limit={limit}"
        )

    async def get_user_activities_by_category(
        self,
        user_id: int,
        category_id: int,
        limit: int = 10
    ) -> dict:
        """Get recent activities for a user filtered by category."""
        return await self.client.get(
            f"/api/v1/activities?user_id={user_id}&category_id={category_id}&limit={limit}"
        )
