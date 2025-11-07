"""Category schemas."""
from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict


class CategoryCreate(BaseModel):
    """Schema for creating a category."""

    user_id: int = Field(..., description="User ID")
    name: str = Field(..., min_length=2, max_length=100, description="Category name")
    emoji: str | None = Field(None, max_length=10, description="Category emoji")
    is_default: bool = Field(default=False, description="Is default category")


class CategoryBulkCreate(BaseModel):
    """Schema for bulk creating categories."""

    user_id: int = Field(..., description="User ID")
    categories: list[dict] = Field(..., description="List of categories to create")


class CategoryResponse(BaseModel):
    """Schema for category response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    emoji: str | None
    is_default: bool
    created_at: datetime
