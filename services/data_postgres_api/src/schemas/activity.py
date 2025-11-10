"""Activity schemas."""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator, ConfigDict, model_validator


class ActivityCreate(BaseModel):
    """Schema for creating an activity."""

    user_id: int = Field(..., description="User ID")
    category_id: int | None = Field(None, description="Category ID")
    description: str = Field(..., min_length=3, description="Activity description")
    tags: list[str] | None = Field(None, description="Activity tags")
    start_time: datetime = Field(..., description="Start time (UTC)")
    end_time: datetime = Field(..., description="End time (UTC)")

    @field_validator("end_time")
    @classmethod
    def validate_end_time(cls, v: datetime, info) -> datetime:
        """Validate that end_time is after start_time."""
        if "start_time" in info.data:
            start_time = info.data["start_time"]
            if v <= start_time:
                raise ValueError("end_time must be after start_time")
        return v


class ActivityResponse(BaseModel):
    """Schema for activity response with category data."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    category_id: int | None
    description: str
    tags: str | None
    start_time: datetime
    end_time: datetime
    duration_minutes: int
    created_at: datetime
    category_name: str | None = None
    category_emoji: str | None = None

    @model_validator(mode='before')
    @classmethod
    def extract_category_data(cls, data: Any) -> Any:
        """Extract category name and emoji from relationship if present."""
        if hasattr(data, 'category') and data.category is not None:
            if not isinstance(data, dict):
                data_dict = {
                    'id': data.id,
                    'user_id': data.user_id,
                    'category_id': data.category_id,
                    'description': data.description,
                    'tags': data.tags,
                    'start_time': data.start_time,
                    'end_time': data.end_time,
                    'duration_minutes': data.duration_minutes,
                    'created_at': data.created_at,
                    'category_name': data.category.name,
                    'category_emoji': data.category.emoji,
                }
                return data_dict
        return data


class ActivityListResponse(BaseModel):
    """Schema for activity list response."""

    total: int
    items: list[ActivityResponse]
