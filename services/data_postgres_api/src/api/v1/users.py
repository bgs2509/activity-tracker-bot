"""Users API router."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.connection import get_db
from src.infrastructure.repositories.user_repository import UserRepository
from src.schemas.user import UserCreate, UserUpdate, UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """Create a new user."""
    repository = UserRepository(db)

    # Check if user with this telegram_id already exists
    existing_user = await repository.get_by_telegram_id(user_data.telegram_id)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with telegram_id {user_data.telegram_id} already exists"
        )

    user = await repository.create(user_data)
    return UserResponse.model_validate(user)


@router.get("/by-telegram/{telegram_id}", response_model=UserResponse)
async def get_user_by_telegram_id(
    telegram_id: int,
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """Get user by Telegram ID."""
    repository = UserRepository(db)
    user = await repository.get_by_telegram_id(telegram_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return UserResponse.model_validate(user)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """Update user fields.

    Allows updating user fields like last_poll_time for tracking purposes.
    """
    repository = UserRepository(db)
    user = await repository.update(user_id, user_data)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return UserResponse.model_validate(user)
