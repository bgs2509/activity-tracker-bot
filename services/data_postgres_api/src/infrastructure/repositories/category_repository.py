"""Category repository."""
import logging
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from src.domain.models.category import Category
from src.schemas.category import CategoryCreate
from src.infrastructure.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


# Placeholder update schema for BaseRepository (categories don't have updates)
class CategoryUpdate(BaseModel):
    """Placeholder update schema for Category."""
    pass


class CategoryRepository(BaseRepository[Category, CategoryCreate, CategoryUpdate]):
    """Repository for Category model."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Category)

    async def get_by_user_and_name(self, user_id: int, name: str) -> Category | None:
        """Get category by user ID and name.

        Args:
            user_id: User ID
            name: Category name

        Returns:
            Category if found, None otherwise
        """
        logger.debug(
            "Retrieving category by user_id and name",
            extra={
                "user_id": user_id,
                "category_name": name,
                "operation": "read"
            }
        )

        try:
            result = await self.session.execute(
                select(Category).where(
                    Category.user_id == user_id,
                    Category.name == name
                )
            )
            category = result.scalar_one_or_none()

            if category:
                logger.debug(
                    "Category found",
                    extra={
                        "user_id": user_id,
                        "category_id": category.id,
                        "category_name": name,
                        "operation": "read"
                    }
                )
            else:
                logger.debug(
                    "Category not found",
                    extra={
                        "user_id": user_id,
                        "category_name": name,
                        "operation": "read"
                    }
                )

            return category

        except Exception as e:
            logger.error(
                "Error retrieving category",
                extra={
                    "user_id": user_id,
                    "category_name": name,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "operation": "read"
                },
                exc_info=True
            )
            raise

    async def get_all_by_user(self, user_id: int) -> list[Category]:
        """Get all categories for a user.

        Args:
            user_id: User ID

        Returns:
            List of categories ordered by creation date
        """
        logger.debug(
            "Retrieving all categories for user",
            extra={
                "user_id": user_id,
                "operation": "read"
            }
        )

        try:
            result = await self.session.execute(
                select(Category)
                .where(Category.user_id == user_id)
                .order_by(Category.created_at)
            )
            categories = list(result.scalars().all())

            logger.debug(
                "Categories retrieved",
                extra={
                    "user_id": user_id,
                    "count": len(categories),
                    "operation": "read"
                }
            )

            return categories

        except Exception as e:
            logger.error(
                "Error retrieving categories",
                extra={
                    "user_id": user_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "operation": "read"
                },
                exc_info=True
            )
            raise

    async def count_by_user(self, user_id: int) -> int:
        """Count categories for a user.

        Args:
            user_id: User ID

        Returns:
            Number of categories
        """
        logger.debug(
            "Counting categories for user",
            extra={
                "user_id": user_id,
                "operation": "count"
            }
        )

        try:
            result = await self.session.execute(
                select(func.count(Category.id)).where(Category.user_id == user_id)
            )
            count = result.scalar_one()

            logger.debug(
                "Categories counted",
                extra={
                    "user_id": user_id,
                    "count": count,
                    "operation": "count"
                }
            )

            return count

        except Exception as e:
            logger.error(
                "Error counting categories",
                extra={
                    "user_id": user_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "operation": "count"
                },
                exc_info=True
            )
            raise
