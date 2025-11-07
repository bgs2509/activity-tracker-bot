"""
Category application service.

This module contains business logic for category operations.
"""

from typing import Optional

from src.domain.models.category import Category
from src.infrastructure.repositories.category_repository import CategoryRepository
from src.schemas.category import CategoryCreate


class CategoryService:
    """
    Application service for category business logic.

    Handles category creation, retrieval, and deletion with
    business rule enforcement (e.g., duplicate prevention, last category protection).
    """

    def __init__(self, repository: CategoryRepository):
        """
        Initialize service with repository.

        Args:
            repository: Category repository instance for data access
        """
        self.repository = repository

    async def create_category(self, category_data: CategoryCreate) -> Category:
        """
        Create new category with duplicate name check.

        Args:
            category_data: Category creation data from API request

        Returns:
            Created category with generated ID

        Raises:
            ValueError: If category name already exists for user
        """
        # Business rule: check for duplicate category name per user
        existing = await self.repository.get_by_user_and_name(
            category_data.user_id,
            category_data.name
        )
        if existing:
            raise ValueError(
                f"Category with name '{category_data.name}' already exists for user {category_data.user_id}"
            )

        return await self.repository.create(category_data)

    async def get_user_categories(self, user_id: int) -> list[Category]:
        """
        Get all categories for user.

        Args:
            user_id: User identifier

        Returns:
            List of user categories ordered by creation time
        """
        return await self.repository.get_all_by_user(user_id)

    async def get_category_by_id(self, category_id: int) -> Optional[Category]:
        """
        Get category by ID.

        Args:
            category_id: Category identifier

        Returns:
            Category if found, None otherwise
        """
        return await self.repository.get_by_id(category_id)

    async def delete_category(self, category_id: int) -> None:
        """
        Delete category by ID with business rule validation.

        Args:
            category_id: Category identifier

        Raises:
            ValueError: If category not found or is last category for user
        """
        # Business rule: category must exist
        category = await self.repository.get_by_id(category_id)
        if not category:
            raise ValueError(f"Category {category_id} not found")

        # Business rule: cannot delete last category
        count = await self.repository.count_by_user(category.user_id)
        if count <= 1:
            raise ValueError(
                "Cannot delete the last category. User must have at least one category."
            )

        # Business rule: cannot delete default category (optional)
        if category.is_default:
            raise ValueError(
                f"Cannot delete default category '{category.name}'. "
                f"Remove default status first."
            )

        await self.repository.delete(category_id)
