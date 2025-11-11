"""User repository."""
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models.user import User
from src.schemas.user import UserCreate, UserUpdate
from src.infrastructure.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class UserRepository(BaseRepository[User, UserCreate, UserUpdate]):
    """Repository for User model."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, User)

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        """Get user by Telegram ID.

        Args:
            telegram_id: Telegram user ID

        Returns:
            User if found, None otherwise
        """
        logger.debug(
            "Retrieving user by telegram_id",
            extra={
                "telegram_id": telegram_id,
                "operation": "read"
            }
        )

        try:
            result = await self.session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()

            if user:
                logger.debug(
                    "User found by telegram_id",
                    extra={
                        "user_id": user.id,
                        "telegram_id": telegram_id,
                        "operation": "read"
                    }
                )
            else:
                logger.debug(
                    "User not found by telegram_id",
                    extra={
                        "telegram_id": telegram_id,
                        "operation": "read"
                    }
                )

            return user

        except Exception as e:
            logger.error(
                "Error retrieving user by telegram_id",
                extra={
                    "telegram_id": telegram_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "operation": "read"
                },
                exc_info=True
            )
            raise
