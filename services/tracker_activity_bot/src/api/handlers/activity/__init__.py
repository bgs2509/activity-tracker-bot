"""
Activity handlers package for activity recording and management.

This module aggregates all activity-related routers following the
Single Responsibility Principle (SRP).

Module Structure:
- helpers.py: DRY helpers and validation functions
- activity_creation.py: Activity recording flow (time, description, category, save)
- activity_management.py: Activity viewing, cancellation, FSM control, help

Usage:
    from src.api.handlers.activity import router
    dp.include_router(router)
"""

from aiogram import Router

from . import activity_creation
from . import activity_management

# Create main activity router
router = Router(name="activity")

# Include all sub-routers
router.include_router(activity_creation.router)
router.include_router(activity_management.router)

__all__ = ["router"]
