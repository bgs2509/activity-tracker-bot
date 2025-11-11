"""User Settings repository."""
import logging
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models.user_settings import UserSettings
from src.schemas.user_settings import UserSettingsCreate, UserSettingsUpdate
from src.infrastructure.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class UserSettingsRepository(BaseRepository[UserSettings, UserSettingsCreate, UserSettingsUpdate]):
    """Repository for UserSettings CRUD operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, UserSettings)

    async def get_by_user_id(self, user_id: int) -> UserSettings | None:
        """Get user settings by user ID.

        Args:
            user_id: User ID

        Returns:
            UserSettings if found, None otherwise
        """
        logger.debug(
            "Retrieving user settings by user_id",
            extra={
                "user_id": user_id,
                "operation": "read"
            }
        )

        try:
            result = await self.session.execute(
                select(UserSettings).where(UserSettings.user_id == user_id)
            )
            settings = result.scalar_one_or_none()

            if settings:
                logger.debug(
                    "User settings found",
                    extra={
                        "user_id": user_id,
                        "settings_id": settings.id,
                        "operation": "read"
                    }
                )
            else:
                logger.debug(
                    "User settings not found",
                    extra={
                        "user_id": user_id,
                        "operation": "read"
                    }
                )

            return settings

        except Exception as e:
            logger.error(
                "Error retrieving user settings",
                extra={
                    "user_id": user_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "operation": "read"
                },
                exc_info=True
            )
            raise

    async def update(self, user_id: int, data: UserSettingsUpdate) -> Optional[UserSettings]:
        """
        Update user settings by user_id (overrides base implementation).

        Args:
            user_id: User ID (not settings ID)
            data: Update data (Pydantic schema)

        Returns:
            Updated settings if found, None otherwise
        """
        update_data = data.model_dump(exclude_unset=True)

        logger.debug(
            "Updating user settings",
            extra={
                "user_id": user_id,
                "fields": list(update_data.keys()),
                "operation": "update"
            }
        )

        try:
            entity = await self.get_by_user_id(user_id)
            if not entity:
                logger.warning(
                    "Cannot update user settings - not found",
                    extra={
                        "user_id": user_id,
                        "operation": "update"
                    }
                )
                return None

            # Track changed fields
            changed_fields = []
            for field, value in update_data.items():
                if hasattr(entity, field) and getattr(entity, field) != value:
                    changed_fields.append(field)
                    setattr(entity, field, value)

            await self.session.flush()
            await self.session.refresh(entity)

            logger.info(
                "User settings updated successfully",
                extra={
                    "user_id": user_id,
                    "settings_id": entity.id,
                    "changed_fields": changed_fields,
                    "operation": "update"
                }
            )
            return entity

        except Exception as e:
            logger.error(
                "Error updating user settings",
                extra={
                    "user_id": user_id,
                    "fields": list(update_data.keys()),
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "operation": "update"
                },
                exc_info=True
            )
            raise
