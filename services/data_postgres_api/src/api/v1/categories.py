"""
Categories API router with service layer.

Handles HTTP requests for category operations.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Query

from src.api.dependencies import get_category_service
from src.api.middleware import handle_service_errors_with_conflict
from src.application.services.category_service import CategoryService
from src.schemas.category import (
    CategoryCreate,
    CategoryResponse,
)

router = APIRouter(prefix="/categories", tags=["categories"])


@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
@handle_service_errors_with_conflict
async def create_category(
    category_data: CategoryCreate,
    service: Annotated[CategoryService, Depends(get_category_service)]
) -> CategoryResponse:
    """Create new category with duplicate check."""
    category = await service.create_category(category_data)
    return CategoryResponse.model_validate(category)


@router.get("/", response_model=list[CategoryResponse])
async def get_categories(
    user_id: Annotated[int, Query(description="User ID")],
    service: Annotated[CategoryService, Depends(get_category_service)]
) -> list[CategoryResponse]:
    """Get all categories for user."""
    categories = await service.get_user_categories(user_id)
    return [CategoryResponse.model_validate(cat) for cat in categories]


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    service: Annotated[CategoryService, Depends(get_category_service)]
) -> None:
    """Delete category with business rule validation."""
    try:
        await service.delete_category(category_id)
    except ValueError as e:
        # Special handling: distinguish between not found (404) and validation errors (400)
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)
