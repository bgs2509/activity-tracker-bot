"""
Base repository with common CRUD operations.

This module provides a generic base repository class that eliminates
code duplication across all repository implementations.
"""

import logging
from typing import TypeVar, Generic, Type, Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

logger = logging.getLogger(__name__)


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
        logger.debug(
            "Retrieving entity by ID",
            extra={
                "entity_type": self.model.__name__,
                "entity_id": id,
                "operation": "read"
            }
        )

        try:
            result = await self.session.execute(
                select(self.model).where(self.model.id == id)
            )
            entity = result.scalar_one_or_none()

            if entity:
                logger.debug(
                    "Entity found",
                    extra={
                        "entity_type": self.model.__name__,
                        "entity_id": id,
                        "operation": "read"
                    }
                )
            else:
                logger.debug(
                    "Entity not found",
                    extra={
                        "entity_type": self.model.__name__,
                        "entity_id": id,
                        "operation": "read"
                    }
                )

            return entity

        except Exception as e:
            logger.error(
                "Error retrieving entity",
                extra={
                    "entity_type": self.model.__name__,
                    "entity_id": id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "operation": "read"
                },
                exc_info=True
            )
            raise

    async def create(self, data: CreateSchemaType) -> ModelType:
        """
        Create new entity.

        Args:
            data: Creation data (Pydantic schema)

        Returns:
            Created entity with generated ID
        """
        logger.debug(
            "Creating entity",
            extra={
                "entity_type": self.model.__name__,
                "operation": "create"
            }
        )

        try:
            entity = self.model(**data.model_dump())
            self.session.add(entity)
            await self.session.flush()
            await self.session.refresh(entity)

            logger.info(
                "Entity created successfully",
                extra={
                    "entity_type": self.model.__name__,
                    "entity_id": entity.id,
                    "operation": "create"
                }
            )
            return entity

        except Exception as e:
            logger.error(
                "Error creating entity",
                extra={
                    "entity_type": self.model.__name__,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "operation": "create"
                },
                exc_info=True
            )
            raise

    async def update(self, id: int, data: UpdateSchemaType) -> Optional[ModelType]:
        """
        Update entity by ID.

        Args:
            id: Entity ID
            data: Update data (Pydantic schema)

        Returns:
            Updated entity if found, None otherwise
        """
        update_data = data.model_dump(exclude_unset=True)

        logger.debug(
            "Updating entity",
            extra={
                "entity_type": self.model.__name__,
                "entity_id": id,
                "fields": list(update_data.keys()),
                "operation": "update"
            }
        )

        try:
            entity = await self.get_by_id(id)
            if not entity:
                logger.warning(
                    "Cannot update entity - not found",
                    extra={
                        "entity_type": self.model.__name__,
                        "entity_id": id,
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
                "Entity updated successfully",
                extra={
                    "entity_type": self.model.__name__,
                    "entity_id": id,
                    "changed_fields": changed_fields,
                    "operation": "update"
                }
            )
            return entity

        except Exception as e:
            logger.error(
                "Error updating entity",
                extra={
                    "entity_type": self.model.__name__,
                    "entity_id": id,
                    "fields": list(update_data.keys()),
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "operation": "update"
                },
                exc_info=True
            )
            raise

    async def delete(self, id: int) -> bool:
        """
        Delete entity by ID.

        Args:
            id: Entity ID

        Returns:
            True if deleted, False if not found
        """
        logger.debug(
            "Deleting entity",
            extra={
                "entity_type": self.model.__name__,
                "entity_id": id,
                "operation": "delete"
            }
        )

        try:
            result = await self.session.execute(
                delete(self.model).where(self.model.id == id)
            )
            await self.session.flush()

            deleted = result.rowcount > 0

            if deleted:
                logger.info(
                    "Entity deleted successfully",
                    extra={
                        "entity_type": self.model.__name__,
                        "entity_id": id,
                        "operation": "delete"
                    }
                )
            else:
                logger.warning(
                    "Cannot delete entity - not found",
                    extra={
                        "entity_type": self.model.__name__,
                        "entity_id": id,
                        "operation": "delete"
                    }
                )

            return deleted

        except Exception as e:
            logger.error(
                "Error deleting entity",
                extra={
                    "entity_type": self.model.__name__,
                    "entity_id": id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "operation": "delete"
                },
                exc_info=True
            )
            raise
