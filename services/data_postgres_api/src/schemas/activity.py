"""Activity schemas."""
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, ConfigDict


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
    """Schema for activity response."""

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


class ActivityListResponse(BaseModel):
    """Schema for activity list response."""

    total: int
    items: list[ActivityResponse]
