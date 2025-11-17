"""Category management handlers.

This package provides handlers for:
- Viewing category list
- Creating new categories (FSM)
- Editing existing categories (FSM)
- Deleting existing categories (FSM)

Structure:
- category_list.py: View user's categories
- category_creation.py: Add new category (name → emoji → save)
- category_edit.py: Edit category (select → choose field → update)
- category_deletion.py: Delete category (select → confirm → delete)
- helpers.py: Keyboard builders, validators, utilities
"""

from aiogram import Router

from .category_list import router as list_router
from .category_creation import router as creation_router
from .category_edit import router as edit_router
from .category_deletion import router as deletion_router

# Combine all routers
router = Router()
router.include_router(creation_router)  # FSM handlers first
router.include_router(edit_router)      # FSM handlers
router.include_router(deletion_router)  # FSM handlers
router.include_router(list_router)      # General handlers last

__all__ = ["router"]
