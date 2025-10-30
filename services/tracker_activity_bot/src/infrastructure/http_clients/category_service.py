"""Category service for interacting with categories API."""
import httpx
from src.infrastructure.http_clients.http_client import DataAPIClient


class CategoryService:
    """Service for category-related operations."""

    def __init__(self, client: DataAPIClient):
        self.client = client

    async def create_category(
        self,
        user_id: int,
        name: str,
        emoji: str | None,
        is_default: bool = False
    ) -> dict:
        """Create a new category."""
        return await self.client.post("/api/v1/categories", json={
            "user_id": user_id,
            "name": name,
            "emoji": emoji,
            "is_default": is_default
        })

    async def bulk_create_categories(
        self,
        user_id: int,
        categories: list[dict]
    ) -> dict:
        """Create multiple categories at once."""
        return await self.client.post("/api/v1/categories/bulk-create", json={
            "user_id": user_id,
            "categories": categories
        })

    async def get_user_categories(self, user_id: int) -> list[dict]:
        """Get all categories for a user."""
        return await self.client.get(f"/api/v1/categories?user_id={user_id}")

    async def delete_category(self, category_id: int) -> None:
        """Delete a category."""
        try:
            await self.client.delete(f"/api/v1/categories/{category_id}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                raise ValueError("Cannot delete the last category")
            raise
