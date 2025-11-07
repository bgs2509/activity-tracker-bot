"""Poll handlers package for automatic activity tracking.

This module aggregates all poll-related routers and exports key functions
following the Single Responsibility Principle (SRP).

Module Structure:
- helpers.py: FSM storage management and DRY helpers
- poll_sender.py: Automatic poll and reminder delivery
- poll_response.py: All poll response handlers (skip, sleep, remind, activity recording)

Usage:
    from src.api.handlers.poll import router, send_automatic_poll, close_fsm_storage

    # Include router in dispatcher
    dp.include_router(router)

    # Use in scheduler
    scheduler.add_job(send_automatic_poll, args=[bot, user_id])

    # Cleanup on shutdown
    await close_fsm_storage()
"""

from aiogram import Router

from . import poll_response

# Import key functions for external use
from .poll_sender import send_automatic_poll, send_reminder
from .helpers import close_fsm_storage

# Create main poll router
router = Router(name="poll")

# Include poll response router (handles all poll responses)
router.include_router(poll_response.router)

# Export public API
__all__ = [
    "router",
    "send_automatic_poll",
    "send_reminder",
    "close_fsm_storage"
]
