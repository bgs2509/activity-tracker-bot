"""
User application service.

This module contains business logic for user operations.
"""

from typing import Optional
from datetime import datetime

from src.domain.models.user import User
from src.infrastructure.repositories.user_repository import UserRepository
from src.schemas.user import UserCreate


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
        # Business rule: Telegram ID must be unique
        existing = await self.repository.get_by_telegram_id(user_data.telegram_id)
        if existing:
            raise ValueError(
                f"User with Telegram ID {user_data.telegram_id} already exists"
            )

        return await self.repository.create(user_data)

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """
        Get user by Telegram ID.

        Args:
            telegram_id: Telegram user ID

        Returns:
            User if found, None otherwise
        """
        return await self.repository.get_by_telegram_id(telegram_id)

    async def get_by_id(self, user_id: int) -> Optional[User]:
        """
        Get user by internal ID.

        Args:
            user_id: Internal user identifier

        Returns:
            User if found, None otherwise
        """
        return await self.repository.get_by_id(user_id)

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
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        return await self.repository.update_last_poll_time(user_id, poll_time)
