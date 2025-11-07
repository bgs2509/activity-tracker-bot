"""
User settings API router with service layer.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Query

from src.api.dependencies import get_user_settings_service
from src.api.middleware import handle_service_errors
from src.application.services.user_settings_service import UserSettingsService
from src.schemas.user_settings import (
    UserSettingsCreate,
    UserSettingsUpdate,
    UserSettingsResponse,
)

router = APIRouter(prefix="/user-settings", tags=["user-settings"])


@router.post("/", response_model=UserSettingsResponse, status_code=status.HTTP_201_CREATED)
@handle_service_errors
async def create_settings(
    settings_data: UserSettingsCreate,
    service: Annotated[UserSettingsService, Depends(get_user_settings_service)]
) -> UserSettingsResponse:
    """Create new user settings with validation."""
    settings = await service.create_settings(settings_data)
    return UserSettingsResponse.model_validate(settings)


@router.get("/", response_model=UserSettingsResponse)
async def get_settings(
    user_id: Annotated[int, Query(description="User ID")],
    service: Annotated[UserSettingsService, Depends(get_user_settings_service)]
) -> UserSettingsResponse:
    """Get settings for user."""
    settings = await service.get_by_user_id(user_id)
    if not settings:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Settings not found")
    return UserSettingsResponse.model_validate(settings)


@router.put("/{user_id}", response_model=UserSettingsResponse)
@handle_service_errors
async def update_settings(
    user_id: int,
    settings_data: UserSettingsUpdate,
    service: Annotated[UserSettingsService, Depends(get_user_settings_service)]
) -> UserSettingsResponse:
    """Update user settings with validation."""
    settings = await service.update_settings(user_id, settings_data)
    if not settings:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Settings not found")
    return UserSettingsResponse.model_validate(settings)
