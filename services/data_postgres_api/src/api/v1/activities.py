"""Activities API router."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.connection import get_db
from src.infrastructure.repositories.activity_repository import ActivityRepository
from src.schemas.activity import (
    ActivityCreate,
    ActivityResponse,
    ActivityListResponse,
)

router = APIRouter(prefix="/activities", tags=["activities"])


@router.post("/", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED)
async def create_activity(
    activity_data: ActivityCreate,
    db: AsyncSession = Depends(get_db)
) -> ActivityResponse:
    """Create a new activity."""
    repository = ActivityRepository(db)
    activity = await repository.create(activity_data)
    return ActivityResponse.model_validate(activity)


@router.get("/", response_model=ActivityListResponse)
async def get_activities(
    user_id: int = Query(..., description="User ID"),
    limit: int = Query(10, ge=1, le=100, description="Number of activities to return"),
    offset: int = Query(0, ge=0, description="Number of activities to skip"),
    db: AsyncSession = Depends(get_db)
) -> ActivityListResponse:
    """Get activities for a user with pagination."""
    repository = ActivityRepository(db)
    activities, total = await repository.get_by_user(user_id, limit, offset)

    return ActivityListResponse(
        total=total,
        items=[ActivityResponse.model_validate(act) for act in activities]
    )
