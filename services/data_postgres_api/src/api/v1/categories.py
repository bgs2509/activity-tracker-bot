"""Categories API router."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.connection import get_db
from src.infrastructure.repositories.category_repository import CategoryRepository
from src.schemas.category import (
    CategoryCreate,
    CategoryResponse,
    CategoryBulkCreate,
    CategoryBulkResponse,
)

router = APIRouter(prefix="/categories", tags=["categories"])


@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_data: CategoryCreate,
    db: AsyncSession = Depends(get_db)
) -> CategoryResponse:
    """Create a new category."""
    repository = CategoryRepository(db)

    # Check if category with this name already exists for user
    existing_category = await repository.get_by_user_and_name(
        category_data.user_id,
        category_data.name
    )
    if existing_category:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Category with name '{category_data.name}' already exists for this user"
        )

    category = await repository.create(category_data)
    return CategoryResponse.model_validate(category)


@router.post("/bulk-create", response_model=CategoryBulkResponse, status_code=status.HTTP_201_CREATED)
async def bulk_create_categories(
    bulk_data: CategoryBulkCreate,
    db: AsyncSession = Depends(get_db)
) -> CategoryBulkResponse:
    """Create multiple categories at once."""
    repository = CategoryRepository(db)
    created_categories = []

    for category_item in bulk_data.categories:
        # Check if category already exists
        existing = await repository.get_by_user_and_name(
            bulk_data.user_id,
            category_item.name
        )
        if not existing:
            category_data = CategoryCreate(
                user_id=bulk_data.user_id,
                name=category_item.name,
                emoji=category_item.emoji,
                is_default=category_item.is_default
            )
            category = await repository.create(category_data)
            created_categories.append(CategoryResponse.model_validate(category))

    return CategoryBulkResponse(
        created_count=len(created_categories),
        categories=created_categories
    )


@router.get("/", response_model=list[CategoryResponse])
async def get_categories(
    user_id: int = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_db)
) -> list[CategoryResponse]:
    """Get all categories for a user."""
    repository = CategoryRepository(db)
    categories = await repository.get_all_by_user(user_id)
    return [CategoryResponse.model_validate(cat) for cat in categories]


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    db: AsyncSession = Depends(get_db)
) -> None:
    """Delete a category."""
    repository = CategoryRepository(db)

    # Check if category exists
    category = await repository.get_by_id(category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    # Check if this is the last category for the user
    count = await repository.count_by_user(category.user_id)
    if count <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the last category for user"
        )

    await repository.delete(category_id)
