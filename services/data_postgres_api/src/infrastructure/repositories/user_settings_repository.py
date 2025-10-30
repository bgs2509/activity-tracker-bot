"""User Settings repository."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models.user_settings import UserSettings


class UserSettingsRepository:
    """Repository for UserSettings CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user_settings: UserSettings) -> UserSettings:
        """Create new user settings."""
        self.session.add(user_settings)
        await self.session.commit()
        await self.session.refresh(user_settings)
        return user_settings

    async def get_by_user_id(self, user_id: int) -> UserSettings | None:
        """Get user settings by user ID."""
        result = await self.session.execute(
            select(UserSettings).where(UserSettings.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, settings_id: int) -> UserSettings | None:
        """Get user settings by ID."""
        result = await self.session.execute(
            select(UserSettings).where(UserSettings.id == settings_id)
        )
        return result.scalar_one_or_none()

    async def update(self, user_settings: UserSettings) -> UserSettings:
        """Update user settings."""
        await self.session.commit()
        await self.session.refresh(user_settings)
        return user_settings

    async def delete(self, user_settings: UserSettings) -> None:
        """Delete user settings."""
        await self.session.delete(user_settings)
        await self.session.commit()
