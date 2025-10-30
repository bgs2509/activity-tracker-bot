"""User schemas."""
from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict


class UserCreate(BaseModel):
    """Schema for creating a user."""

    telegram_id: int = Field(..., description="Telegram user ID")
    username: str | None = Field(None, max_length=255, description="Telegram username")
    first_name: str | None = Field(None, max_length=255, description="User first name")
    timezone: str = Field(default="Europe/Moscow", max_length=50, description="User timezone")


class UserResponse(BaseModel):
    """Schema for user response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    telegram_id: int
    username: str | None
    first_name: str | None
    timezone: str
    created_at: datetime
