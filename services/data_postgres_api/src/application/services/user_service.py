"""
User application service.

This module contains business logic for user operations.
"""

import logging
from typing import Optional, List
from datetime import datetime

from src.domain.models.user import User
from src.infrastructure.repositories.user_repository import UserRepository
from src.schemas.user import UserCreate

logger = logging.getLogger(__name__)


class UserService:
    """
    Application service for user business logic.

    Handles user creation, retrieval, and updates with
    business rule enforcement (e.g., unique Telegram ID).
    """

    def __init__(self, repository: UserRepository):
        """
        Initialize service with repository.

        Args:
            repository: User repository instance for data access
        """
        self.repository = repository

    async def create_user(self, user_data: UserCreate) -> User:
        """
        Create new user with duplicate Telegram ID check.

        Args:
            user_data: User creation data from API request

        Returns:
            Created user with generated ID

        Raises:
            ValueError: If user with telegram_id already exists
        """
        logger.debug(
            "create_user started",
            extra={
                "telegram_id": user_data.telegram_id,
                "username": user_data.username,
                "first_name": user_data.first_name,
                "timezone": user_data.timezone
            }
        )

        try:
            # Business rule: Telegram ID must be unique
            existing = await self.repository.get_by_telegram_id(user_data.telegram_id)
            if existing:
                logger.debug(
                    "user already exists",
                    extra={"user_id": existing.id, "telegram_id": user_data.telegram_id}
                )
                raise ValueError(
                    f"User with Telegram ID {user_data.telegram_id} already exists"
                )

            user = await self.repository.create(user_data)
            logger.info(
                "user_created",
                extra={
                    "user_id": user.id,
                    "telegram_id": user.telegram_id,
                    "username": user.username
                }
            )
            return user
        except Exception as e:
            logger.error(
                "create_user failed",
                extra={"telegram_id": user_data.telegram_id, "error": str(e)},
                exc_info=True
            )
            raise

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """
        Get user by Telegram ID.

        Args:
            telegram_id: Telegram user ID

        Returns:
            User if found, None otherwise
        """
        logger.debug("get_by_telegram_id started", extra={"telegram_id": telegram_id})
        user = await self.repository.get_by_telegram_id(telegram_id)
        logger.debug(
            "get_by_telegram_id completed",
            extra={"telegram_id": telegram_id, "found": user is not None}
        )
        return user

    async def get_by_id(self, user_id: int) -> Optional[User]:
        """
        Get user by internal ID.

        Args:
            user_id: Internal user identifier

        Returns:
            User if found, None otherwise
        """
        logger.debug("get_by_id started", extra={"user_id": user_id})
        user = await self.repository.get_by_id(user_id)
        logger.debug(
            "get_by_id completed",
            extra={"user_id": user_id, "found": user is not None}
        )
        return user

    async def update_last_poll_time(
        self,
        user_id: int,
        poll_time: datetime
    ) -> Optional[User]:
        """
        Update last poll time for user.

        Args:
            user_id: User identifier
            poll_time: Timestamp of last poll

        Returns:
            Updated user if found, None otherwise

        Raises:
            ValueError: If user not found
        """
        logger.debug(
            "update_last_poll_time started",
            extra={"user_id": user_id, "poll_time": poll_time.isoformat()}
        )

        try:
            user = await self.repository.get_by_id(user_id)
            if not user:
                logger.warning("user not found for poll time update", extra={"user_id": user_id})
                raise ValueError(f"User {user_id} not found")

            updated_user = await self.repository.update_last_poll_time(user_id, poll_time)
            logger.info(
                "last_poll_time_updated",
                extra={"user_id": user_id, "poll_time": poll_time.isoformat()}
            )
            return updated_user
        except Exception as e:
            logger.error(
                "update_last_poll_time failed",
                extra={"user_id": user_id, "error": str(e)},
                exc_info=True
            )
            raise

    async def get_all_active_users(self) -> List[User]:
        """
        Get all active users for poll restoration.

        Returns:
            List of users who have been polled before
        """
        logger.debug("get_all_active_users started")
        users = await self.repository.get_all_active_users()
        logger.debug(
            "get_all_active_users completed",
            extra={"user_count": len(users)}
        )
        return users
