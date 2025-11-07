"""
Activities API router.

Handles HTTP requests for activity operations using application service layer.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Query

from src.api.dependencies import get_activity_service
from src.api.middleware import handle_service_errors
from src.application.services.activity_service import ActivityService
from src.schemas.activity import (
    ActivityCreate,
    ActivityResponse,
)

router = APIRouter(prefix="/activities", tags=["activities"])


@router.post(
    "/",
    response_model=ActivityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create activity",
    description="Create new activity record with time validation"
)
@handle_service_errors
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
    activity = await service.create_activity(activity_data)
    return ActivityResponse.model_validate(activity)


@router.get(
    "/",
    response_model=list[ActivityResponse],
    summary="List activities",
    description="Get recent activities for user"
)
@handle_service_errors
async def get_activities(
    user_id: Annotated[int, Query(description="User ID")],
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum items to return")] = 10,
    service: Annotated[ActivityService, Depends(get_activity_service)] = None
) -> list[ActivityResponse]:
    """
    Get recent activities for user.

    Args:
        user_id: User identifier from query string
        limit: Maximum activities to return (default: 10)
        service: Activity service instance (injected)

    Returns:
        List of recent activities

    Raises:
        HTTPException: 400 if limit is invalid
    """
    activities = await service.get_user_activities(user_id, limit)
    return [ActivityResponse.model_validate(act) for act in activities]
