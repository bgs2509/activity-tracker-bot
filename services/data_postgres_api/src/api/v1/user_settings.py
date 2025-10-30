"""User Settings API endpoints."""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.connection import get_db
from src.infrastructure.repositories.user_settings_repository import UserSettingsRepository
from src.domain.models.user_settings import UserSettings
from src.schemas.user_settings import (
    UserSettingsCreate,
    UserSettingsUpdate,
    UserSettingsResponse,
)

router = APIRouter(prefix="/user-settings", tags=["user-settings"])
logger = logging.getLogger(__name__)


@router.post("", response_model=UserSettingsResponse, status_code=status.HTTP_201_CREATED)
async def create_user_settings(
    settings_data: UserSettingsCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create new user settings."""
    repository = UserSettingsRepository(db)

    # Check if settings already exist for this user
    existing = await repository.get_by_user_id(settings_data.user_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Settings already exist for user_id={settings_data.user_id}"
        )

    # Create new settings
    user_settings = UserSettings(**settings_data.model_dump())
    created_settings = await repository.create(user_settings)

    logger.info(f"Created user settings: id={created_settings.id}, user_id={created_settings.user_id}")
    return created_settings


@router.get("", response_model=UserSettingsResponse)
async def get_user_settings(
    user_id: Annotated[int, Query(description="User ID")],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get user settings by user ID."""
    repository = UserSettingsRepository(db)

    settings = await repository.get_by_user_id(user_id)
    if not settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Settings not found for user_id={user_id}"
        )

    return settings


@router.patch("/{settings_id}", response_model=UserSettingsResponse)
async def update_user_settings(
    settings_id: int,
    updates: UserSettingsUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update user settings."""
    repository = UserSettingsRepository(db)

    settings = await repository.get_by_id(settings_id)
    if not settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Settings not found: id={settings_id}"
        )

    # Apply updates
    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(settings, field, value)

    updated_settings = await repository.update(settings)

    logger.info(f"Updated user settings: id={settings_id}, fields={list(update_data.keys())}")
    return updated_settings
