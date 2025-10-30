"""User service for interacting with users API."""
import httpx
from src.infrastructure.http_clients.http_client import DataAPIClient


class UserService:
    """Service for user-related operations."""

    def __init__(self, client: DataAPIClient):
        self.client = client

    async def get_by_telegram_id(self, telegram_id: int) -> dict | None:
        """Get user by Telegram ID."""
        try:
            return await self.client.get(f"/api/v1/users/by-telegram/{telegram_id}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

    async def create_user(
        self,
        telegram_id: int,
        username: str | None,
        first_name: str | None
    ) -> dict:
        """Create a new user."""
        return await self.client.post("/api/v1/users", json={
            "telegram_id": telegram_id,
            "username": username,
            "first_name": first_name,
            "timezone": "Europe/Moscow"
        })
