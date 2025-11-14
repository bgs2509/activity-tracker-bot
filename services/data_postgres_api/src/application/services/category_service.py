"""
Category application service.

This module contains business logic for category operations.
"""

import logging
from typing import Optional

from src.domain.models.category import Category
from src.infrastructure.repositories.category_repository import CategoryRepository
from src.schemas.category import CategoryCreate

logger = logging.getLogger(__name__)


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
        logger.debug(
            "create_category started",
            extra={
                "user_id": category_data.user_id,
                "name": category_data.name,
                "emoji": category_data.emoji,
                "is_default": category_data.is_default
            }
        )

        try:
            # Business rule: check for duplicate category name per user
            existing = await self.repository.get_by_user_and_name(
                category_data.user_id,
                category_data.name
            )
            if existing:
                logger.warning(
                    "duplicate_category",
                    extra={
                        "user_id": category_data.user_id,
                        "name": category_data.name,
                        "category_id": existing.id
                    }
                )
                raise ValueError(
                    f"Category with name '{category_data.name}' already exists for user {category_data.user_id}"
                )

            category = await self.repository.create(category_data)
            logger.info(
                "category_created",
                extra={
                    "category_id": category.id,
                    "user_id": category.user_id,
                    "name": category.name,
                    "emoji": category.emoji
                }
            )
            return category
        except Exception as e:
            logger.error(
                "create_category failed",
                extra={
                    "user_id": category_data.user_id,
                    "name": category_data.name,
                    "error": str(e)
                },
                exc_info=True
            )
            raise

    async def bulk_create_categories(
        self, user_id: int, categories_data: list[CategoryCreate]
    ) -> list[Category]:
        """
        Bulk create categories for user, skipping duplicates.

        Args:
            user_id: User identifier
            categories_data: List of category creation data

        Returns:
            List of successfully created categories (excludes duplicates)
        """
        logger.debug(
            "bulk_create_categories started",
            extra={"user_id": user_id, "category_count": len(categories_data)}
        )

        created_categories = []

        for category_data in categories_data:
            # Check if category already exists
            existing = await self.repository.get_by_user_and_name(
                user_id, category_data.name
            )
            if existing:
                logger.debug(
                    "skipping duplicate category",
                    extra={"user_id": user_id, "name": category_data.name}
                )
                # Skip duplicate
                continue

            # Create new category
            created = await self.repository.create(category_data)
            logger.debug(
                "category created in bulk",
                extra={
                    "category_id": created.id,
                    "user_id": user_id,
                    "name": created.name
                }
            )
            created_categories.append(created)

        logger.info(
            "bulk_create_categories completed",
            extra={
                "user_id": user_id,
                "requested_count": len(categories_data),
                "created_count": len(created_categories)
            }
        )
        return created_categories

    async def get_user_categories(self, user_id: int) -> list[Category]:
        """
        Get all categories for user.

        Args:
            user_id: User identifier

        Returns:
            List of user categories ordered by creation time
        """
        logger.debug("get_user_categories started", extra={"user_id": user_id})
        categories = await self.repository.get_all_by_user(user_id)
        logger.debug(
            "get_user_categories completed",
            extra={"user_id": user_id, "category_count": len(categories)}
        )
        return categories

    async def get_category_by_id(self, category_id: int) -> Optional[Category]:
        """
        Get category by ID.

        Args:
            category_id: Category identifier

        Returns:
            Category if found, None otherwise
        """
        logger.debug("get_category_by_id started", extra={"category_id": category_id})
        category = await self.repository.get_by_id(category_id)
        logger.debug(
            "get_category_by_id completed",
            extra={"category_id": category_id, "found": category is not None}
        )
        return category

    async def delete_category(self, category_id: int) -> None:
        """
        Delete category by ID with business rule validation.

        Args:
            category_id: Category identifier

        Raises:
            ValueError: If category not found or is last category for user
        """
        logger.debug("delete_category started", extra={"category_id": category_id})

        try:
            # Business rule: category must exist
            category = await self.repository.get_by_id(category_id)
            if not category:
                logger.warning("category not found", extra={"category_id": category_id})
                raise ValueError(f"Category {category_id} not found")

            # Business rule: cannot delete last category
            count = await self.repository.count_by_user(category.user_id)
            if count <= 1:
                logger.warning(
                    "cannot delete last category",
                    extra={
                        "category_id": category_id,
                        "user_id": category.user_id,
                        "category_count": count
                    }
                )
                raise ValueError(
                    "Cannot delete the last category. User must have at least one category."
                )

            # Business rule: cannot delete default category (optional)
            if category.is_default:
                logger.warning(
                    "cannot delete default category",
                    extra={
                        "category_id": category_id,
                        "name": category.name,
                        "user_id": category.user_id
                    }
                )
                raise ValueError(
                    f"Cannot delete default category '{category.name}'. "
                    f"Remove default status first."
                )

            await self.repository.delete(category_id)
            logger.info(
                "category_deleted",
                extra={
                    "category_id": category_id,
                    "user_id": category.user_id,
                    "name": category.name
                }
            )
        except Exception as e:
            logger.error(
                "delete_category failed",
                extra={"category_id": category_id, "error": str(e)},
                exc_info=True
            )
            raise
