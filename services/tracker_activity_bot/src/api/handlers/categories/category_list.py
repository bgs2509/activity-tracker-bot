"""Category list view handler.

Displays user's categories with options to add or delete.
"""

import logging
from aiogram import Router, types, F

from src.api.dependencies import ServiceContainer
from src.api.decorators import require_user
from src.api.keyboards.main_menu import get_main_menu_keyboard
from src.application.utils.decorators import with_typing_action
from src.core.logging_middleware import log_user_action

from .helpers import build_category_list_keyboard

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "categories")
@with_typing_action
@log_user_action("categories_button_clicked")
@require_user
async def show_categories_list(
    callback: types.CallbackQuery,
    services: ServiceContainer,
    user: dict
):
    """Show list of user's categories.

    Triggered by: Main menu "📂 Категории" button

    Args:
        callback: Callback query from button press
        services: Service container for API access
        user: Current user data (injected by @require_user)
    """
    logger.debug(
        "User opened categories list",
        extra={"user_id": callback.from_user.id}
    )

    # Get categories
    categories = await services.category.get_user_categories(user["id"])

    # Build category list text
    text = "📂 Твои категории активностей:\n\n"
    for cat in categories:
        emoji = cat.get("emoji", "")
        name = cat["name"]
        text += f"{emoji} {name}\n"

    # Build keyboard
    keyboard = build_category_list_keyboard()

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "main_menu")
@with_typing_action
async def show_main_menu(callback: types.CallbackQuery):
    """Return to main menu.

    Handles navigation back to main menu from categories.

    Args:
        callback: Callback query from button press
    """
    text = "Выбери действие:"
    await callback.message.edit_text(text, reply_markup=get_main_menu_keyboard())
    await callback.answer()
