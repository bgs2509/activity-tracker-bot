"""
Error handling middleware and decorators for API routes.

Provides centralized error handling to eliminate repetitive try-except blocks.
"""

import logging
from functools import wraps
from typing import Callable, Any

from fastapi import HTTPException, status


logger = logging.getLogger(__name__)


def handle_service_errors(func: Callable) -> Callable:
    """
    Decorator to handle service layer exceptions in API routes.

    Converts service layer exceptions to appropriate HTTP responses:
    - ValueError → 400 BAD REQUEST
    - Other exceptions → 500 INTERNAL SERVER ERROR (logged)

    Usage:
        @router.post("/")
        @handle_service_errors
        async def create_item(data: ItemCreate, service: ItemService = Depends()):
            return await service.create(data)

    Args:
        func: Async route handler function

    Returns:
        Wrapped function with error handling
    """
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except ValueError as e:
            # Business validation errors from service layer
            logger.warning(
                f"Business validation error in {func.__name__}: {str(e)}",
                extra={"function": func.__name__, "error": str(e)}
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except HTTPException:
            # Re-raise HTTP exceptions (404, 409, etc.) without modification
            raise
        except Exception as e:
            # Unexpected errors - log for debugging
            logger.error(
                f"Unexpected error in {func.__name__}: {str(e)}",
                extra={"function": func.__name__, "error": str(e)},
                exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )
    return wrapper


def handle_service_errors_with_conflict(func: Callable) -> Callable:
    """
    Decorator variant for operations that may have conflicts (duplicates).

    Converts service layer exceptions to appropriate HTTP responses:
    - ValueError → 409 CONFLICT (for duplicate/uniqueness violations)
    - Other exceptions → 500 INTERNAL SERVER ERROR (logged)

    Usage:
        @router.post("/")
        @handle_service_errors_with_conflict
        async def create_user(data: UserCreate, service: UserService = Depends()):
            return await service.create(data)

    Args:
        func: Async route handler function

    Returns:
        Wrapped function with error handling
    """
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except ValueError as e:
            # Treat ValueError as conflict for create operations
            logger.warning(
                f"Conflict error in {func.__name__}: {str(e)}",
                extra={"function": func.__name__, "error": str(e)}
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e)
            )
        except HTTPException:
            # Re-raise HTTP exceptions without modification
            raise
        except Exception as e:
            # Unexpected errors - log for debugging
            logger.error(
                f"Unexpected error in {func.__name__}: {str(e)}",
                extra={"function": func.__name__, "error": str(e)},
                exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )
    return wrapper
