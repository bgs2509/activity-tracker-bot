"""
Settings handlers package.

This module aggregates all settings-related routers into a single router
following the Single Responsibility Principle (SRP).

Module Structure:
- main_menu.py: Settings menu and navigation
- interval_settings.py: Poll interval configuration (weekday/weekend)
- quiet_hours_settings.py: Quiet hours time range configuration
- reminder_settings.py: Reminder notification configuration
- helpers.py: Shared helper functions (DRY principle)

Usage:
    from src.api.handlers.settings import router as settings_router
    dp.include_router(settings_router)
"""

from aiogram import Router

from . import main_menu
from . import interval_settings
from . import quiet_hours_settings
from . import reminder_settings

# Create main settings router
router = Router(name="settings")

# Include all sub-routers
router.include_router(main_menu.router)
router.include_router(interval_settings.router)
router.include_router(quiet_hours_settings.router)
router.include_router(reminder_settings.router)

__all__ = ["router"]
