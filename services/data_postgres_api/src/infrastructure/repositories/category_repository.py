"""Category repository."""
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from src.domain.models.category import Category
from src.schemas.category import CategoryCreate
from src.infrastructure.repositories.base import BaseRepository


# Placeholder update schema for BaseRepository (categories don't have updates)
class CategoryUpdate(BaseModel):
    """Placeholder update schema for Category."""
    pass


class CategoryRepository(BaseRepository[Category, CategoryCreate, CategoryUpdate]):
    """Repository for Category model."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Category)

    async def get_by_user_and_name(self, user_id: int, name: str) -> Category | None:
        """Get category by user ID and name."""
        result = await self.session.execute(
            select(Category).where(
                Category.user_id == user_id,
                Category.name == name
            )
        )
        return result.scalar_one_or_none()

    async def get_all_by_user(self, user_id: int) -> list[Category]:
        """Get all categories for a user."""
        result = await self.session.execute(
            select(Category)
            .where(Category.user_id == user_id)
            .order_by(Category.created_at)
        )
        return list(result.scalars().all())

    async def count_by_user(self, user_id: int) -> int:
        """Count categories for a user."""
        result = await self.session.execute(
            select(func.count(Category.id)).where(Category.user_id == user_id)
        )
        return result.scalar_one()
