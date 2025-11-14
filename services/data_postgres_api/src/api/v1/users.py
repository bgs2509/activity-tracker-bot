"""
Users API router with service layer.
"""

from typing import Annotated, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body

from src.api.dependencies import get_user_service
from src.api.middleware import handle_service_errors_with_conflict
from src.application.services.user_service import UserService
from src.schemas.user import UserCreate, UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@handle_service_errors_with_conflict
async def create_user(
    user_data: UserCreate,
    service: Annotated[UserService, Depends(get_user_service)]
) -> UserResponse:
    """Create new user or return existing."""
    existing = await service.get_by_telegram_id(user_data.telegram_id)
    if existing:
        return UserResponse.model_validate(existing)

    user = await service.create_user(user_data)
    return UserResponse.model_validate(user)


@router.get("/by-telegram/{telegram_id}", response_model=UserResponse)
async def get_user_by_telegram_id(
    telegram_id: int,
    service: Annotated[UserService, Depends(get_user_service)]
) -> UserResponse:
    """Get user by Telegram ID."""
    user = await service.get_by_telegram_id(telegram_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse.model_validate(user)


@router.patch("/{user_id}/last-poll-time", response_model=UserResponse)
async def update_last_poll_time(
    user_id: int,
    poll_time: Annotated[datetime, Body(embed=True)],
    service: Annotated[UserService, Depends(get_user_service)]
) -> UserResponse:
    """Update last poll time for user."""
    try:
        user = await service.update_last_poll_time(user_id, poll_time)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return UserResponse.model_validate(user)
    except ValueError as e:
        # Service may raise ValueError for not found cases
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/active", response_model=List[UserResponse])
async def get_active_users(
    service: Annotated[UserService, Depends(get_user_service)]
) -> List[UserResponse]:
    """Get all active users for poll restoration."""
    users = await service.get_all_active_users()
    return [UserResponse.model_validate(user) for user in users]
