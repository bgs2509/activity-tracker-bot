"""
Activities API router.

Handles HTTP requests for activity operations using application service layer.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Query

from src.api.dependencies import get_activity_service
from src.application.services.activity_service import ActivityService
from src.schemas.activity import (
    ActivityCreate,
    ActivityResponse,
    ActivityListResponse,
)

router = APIRouter(prefix="/activities", tags=["activities"])


@router.post(
    "/",
    response_model=ActivityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create activity",
    description="Create new activity record with time validation"
)
async def create_activity(
    activity_data: ActivityCreate,
    service: Annotated[ActivityService, Depends(get_activity_service)]
) -> ActivityResponse:
    """
    Create new activity.

    Args:
        activity_data: Activity creation data from request body
        service: Activity service instance (injected)

    Returns:
        Created activity with generated ID

    Raises:
        HTTPException: 400 if business validation fails
    """
    try:
        activity = await service.create_activity(activity_data)
        return ActivityResponse.model_validate(activity)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/",
    response_model=ActivityListResponse,
    summary="List activities",
    description="Get paginated activities for user"
)
async def get_activities(
    user_id: Annotated[int, Query(description="User ID")],
    limit: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 10,
    offset: Annotated[int, Query(ge=0, description="Items to skip")] = 0,
    service: Annotated[ActivityService, Depends(get_activity_service)] = None
) -> ActivityListResponse:
    """
    Get activities for user with pagination.

    Args:
        user_id: User identifier from query string
        limit: Maximum activities to return (default: 10)
        offset: Number of activities to skip (default: 0)
        service: Activity service instance (injected)

    Returns:
        Paginated list of activities with total count

    Raises:
        HTTPException: 400 if pagination parameters invalid
    """
    try:
        activities, total = await service.get_user_activities(user_id, limit, offset)

        return ActivityListResponse(
            total=total,
            items=[ActivityResponse.model_validate(act) for act in activities]
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
