"""
Dependency injection providers for FastAPI routes.

This module provides dependency injection for services and repositories,
implementing the Dependency Inversion Principle for clean architecture.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.connection import get_db
from src.infrastructure.repositories.activity_repository import ActivityRepository
from src.infrastructure.repositories.category_repository import CategoryRepository
from src.infrastructure.repositories.user_repository import UserRepository
from src.infrastructure.repositories.user_settings_repository import UserSettingsRepository
from src.application.services.activity_service import ActivityService
from src.application.services.category_service import CategoryService
from src.application.services.user_service import UserService
from src.application.services.user_settings_service import UserSettingsService


# Repository Dependencies


def get_activity_repository(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> ActivityRepository:
    """
    Provide activity repository instance.

    Args:
        db: Database session (injected by FastAPI)

    Returns:
        ActivityRepository instance bound to database session
    """
    return ActivityRepository(db)


def get_category_repository(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> CategoryRepository:
    """
    Provide category repository instance.

    Args:
        db: Database session (injected by FastAPI)

    Returns:
        CategoryRepository instance bound to database session
    """
    return CategoryRepository(db)


def get_user_repository(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> UserRepository:
    """
    Provide user repository instance.

    Args:
        db: Database session (injected by FastAPI)

    Returns:
        UserRepository instance bound to database session
    """
    return UserRepository(db)


def get_user_settings_repository(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> UserSettingsRepository:
    """
    Provide user settings repository instance.

    Args:
        db: Database session (injected by FastAPI)

    Returns:
        UserSettingsRepository instance bound to database session
    """
    return UserSettingsRepository(db)


# Service Dependencies


def get_activity_service(
    repository: Annotated[ActivityRepository, Depends(get_activity_repository)]
) -> ActivityService:
    """
    Provide activity service instance.

    Args:
        repository: Activity repository (injected by FastAPI)

    Returns:
        ActivityService instance with repository dependency
    """
    return ActivityService(repository)


def get_category_service(
    repository: Annotated[CategoryRepository, Depends(get_category_repository)]
) -> CategoryService:
    """
    Provide category service instance.

    Args:
        repository: Category repository (injected by FastAPI)

    Returns:
        CategoryService instance with repository dependency
    """
    return CategoryService(repository)


def get_user_service(
    repository: Annotated[UserRepository, Depends(get_user_repository)]
) -> UserService:
    """
    Provide user service instance.

    Args:
        repository: User repository (injected by FastAPI)

    Returns:
        UserService instance with repository dependency
    """
    return UserService(repository)


def get_user_settings_service(
    repository: Annotated[UserSettingsRepository, Depends(get_user_settings_repository)]
) -> UserSettingsService:
    """
    Provide user settings service instance.

    Args:
        repository: User settings repository (injected by FastAPI)

    Returns:
        UserSettingsService instance with repository dependency
    """
    return UserSettingsService(repository)
