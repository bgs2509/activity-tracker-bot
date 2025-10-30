"""HTTP client for UserSettings API."""
import logging
from datetime import time

from src.infrastructure.http_clients.http_client import DataAPIClient

logger = logging.getLogger(__name__)


class UserSettingsService:
    """Service for interacting with UserSettings API."""

    def __init__(self, client: DataAPIClient):
        self.client = client

    async def create_settings(self, user_id: int) -> dict:
        """Create default settings for user."""
        data = {"user_id": user_id}
        response = await self.client.post("/api/v1/user-settings", json=data)
        logger.info(f"Created settings for user_id={user_id}")
        return response

    async def get_settings(self, user_id: int) -> dict | None:
        """Get user settings by user_id."""
        try:
            response = await self.client.get("/api/v1/user-settings", params={"user_id": user_id})
            return response
        except Exception as e:
            logger.warning(f"Settings not found for user_id={user_id}: {e}")
            return None

    async def update_settings(self, settings_id: int, **updates) -> dict:
        """Update user settings."""
        response = await self.client.patch(f"/api/v1/user-settings/{settings_id}", json=updates)
        logger.info(f"Updated settings id={settings_id}, fields={list(updates.keys())}")
        return response
