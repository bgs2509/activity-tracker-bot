"""Category repository."""
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models.category import Category
from src.schemas.category import CategoryCreate


class CategoryRepository:
    """Repository for Category model."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, category_data: CategoryCreate) -> Category:
        """Create a new category."""
        category = Category(**category_data.model_dump())
        self.session.add(category)
        await self.session.flush()
        await self.session.refresh(category)
        return category

    async def get_by_id(self, category_id: int) -> Category | None:
        """Get category by ID."""
        result = await self.session.execute(
            select(Category).where(Category.id == category_id)
        )
        return result.scalar_one_or_none()

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

    async def delete(self, category_id: int) -> None:
        """Delete a category."""
        await self.session.execute(
            delete(Category).where(Category.id == category_id)
        )
        await self.session.flush()
