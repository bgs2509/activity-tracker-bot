"""
Base repository with common CRUD operations.

This module provides a generic base repository class that eliminates
code duplication across all repository implementations.
"""

from typing import TypeVar, Generic, Type, Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel


# Generic type for SQLAlchemy models
ModelType = TypeVar("ModelType")
# Generic type for Pydantic create schemas
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
# Generic type for Pydantic update schemas
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Base repository providing common CRUD operations.

    This eliminates repeated get_by_id, create, and delete implementations
    across all repository classes.

    Type Parameters:
        ModelType: SQLAlchemy model class
        CreateSchemaType: Pydantic schema for creation
        UpdateSchemaType: Pydantic schema for updates

    Example:
        class UserRepository(BaseRepository[User, UserCreate, UserUpdate]):
            def __init__(self, session: AsyncSession):
                super().__init__(session, User)

            # Only custom methods here
            async def get_by_telegram_id(self, telegram_id: int) -> User | None:
                ...
    """

    def __init__(self, session: AsyncSession, model: Type[ModelType]):
        """
        Initialize repository.

        Args:
            session: SQLAlchemy async session
            model: SQLAlchemy model class
        """
        self.session = session
        self.model = model

    async def get_by_id(self, id: int) -> Optional[ModelType]:
        """
        Get entity by ID.

        Args:
            id: Entity ID

        Returns:
            Entity if found, None otherwise
        """
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def create(self, data: CreateSchemaType) -> ModelType:
        """
        Create new entity.

        Args:
            data: Creation data (Pydantic schema)

        Returns:
            Created entity with generated ID
        """
        entity = self.model(**data.model_dump())
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def update(self, id: int, data: UpdateSchemaType) -> Optional[ModelType]:
        """
        Update entity by ID.

        Args:
            id: Entity ID
            data: Update data (Pydantic schema)

        Returns:
            Updated entity if found, None otherwise
        """
        entity = await self.get_by_id(id)
        if not entity:
            return None

        # Update only provided fields (exclude_unset=True)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(entity, field, value)

        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, id: int) -> bool:
        """
        Delete entity by ID.

        Args:
            id: Entity ID

        Returns:
            True if deleted, False if not found
        """
        result = await self.session.execute(
            delete(self.model).where(self.model.id == id)
        )
        await self.session.flush()
        return result.rowcount > 0
