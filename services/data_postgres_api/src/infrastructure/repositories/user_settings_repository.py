"""User Settings repository."""
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models.user_settings import UserSettings
from src.schemas.user_settings import UserSettingsCreate, UserSettingsUpdate
from src.infrastructure.repositories.base import BaseRepository


class UserSettingsRepository(BaseRepository[UserSettings, UserSettingsCreate, UserSettingsUpdate]):
    """Repository for UserSettings CRUD operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, UserSettings)

    async def get_by_user_id(self, user_id: int) -> UserSettings | None:
        """Get user settings by user ID."""
        result = await self.session.execute(
            select(UserSettings).where(UserSettings.user_id == user_id)
        )
        return result.scalar_one_or_none()
