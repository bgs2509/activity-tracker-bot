"""Pydantic schemas for UserSettings."""
from datetime import time

from pydantic import BaseModel, Field


class UserSettingsBase(BaseModel):
    """Base schema for user settings."""

    poll_interval_weekday: int = Field(default=120, ge=15, le=360, description="Poll interval for weekdays in minutes")
    poll_interval_weekend: int = Field(default=180, ge=15, le=480, description="Poll interval for weekends in minutes")
    quiet_hours_start: time | None = Field(default=time(23, 0), description="Start of quiet hours")
    quiet_hours_end: time | None = Field(default=time(7, 0), description="End of quiet hours")
    reminder_enabled: bool = Field(default=True, description="Whether reminders are enabled")
    reminder_delay_minutes: int = Field(default=30, ge=5, le=120, description="Reminder delay in minutes")


class UserSettingsCreate(UserSettingsBase):
    """Schema for creating user settings."""

    user_id: int = Field(..., description="User ID")


class UserSettingsUpdate(BaseModel):
    """Schema for updating user settings (all fields optional)."""

    poll_interval_weekday: int | None = Field(None, ge=15, le=360)
    poll_interval_weekend: int | None = Field(None, ge=15, le=480)
    quiet_hours_start: time | None = None
    quiet_hours_end: time | None = None
    reminder_enabled: bool | None = None
    reminder_delay_minutes: int | None = Field(None, ge=5, le=120)


class UserSettingsResponse(UserSettingsBase):
    """Schema for user settings response."""

    id: int
    user_id: int

    class Config:
        from_attributes = True
