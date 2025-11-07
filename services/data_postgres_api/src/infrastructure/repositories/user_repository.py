"""User repository."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models.user import User
from src.schemas.user import UserCreate, UserUpdate
from src.infrastructure.repositories.base import BaseRepository


class UserRepository(BaseRepository[User, UserCreate, UserUpdate]):
    """Repository for User model."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, User)

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        """Get user by Telegram ID."""
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()
