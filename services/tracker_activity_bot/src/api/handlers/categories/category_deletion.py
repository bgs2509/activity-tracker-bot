"""Category deletion FSM flow.

Handles the multi-step process of deleting a category:
1. User selects category to delete
2. User confirms deletion
3. Category is deleted via API (activities set to no category)
"""

import logging
from aiogram import Router, types, F
import httpx

from src.api.dependencies import ServiceContainer
from src.application.utils.decorators import with_typing_action

from .helpers import (
    build_delete_category_keyboard,
    build_delete_confirmation_keyboard,
    build_post_deletion_keyboard,
)

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "delete_category_start")
@with_typing_action
async def delete_category_select(
    callback: types.CallbackQuery,
    services: ServiceContainer
):
    """Show category selection for deletion.

    Entry point for deleting a category.
    Displays list of categories with delete buttons.

    Args:
        callback: Callback query from button press
        services: Service container
    """
    telegram_id = callback.from_user.id

    # Get user
    user = await services.user.get_by_telegram_id(telegram_id)
    if not user:
        await callback.answer(
            "❌ Пользователь не найден. Используй /start",
            show_alert=True
        )
        return

    # Get categories
    categories = await services.category.get_user_categories(user["id"])

    text = "Выбери категорию для удаления:"

    keyboard = build_delete_category_keyboard(categories)

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("delete_cat:"))
@with_typing_action
async def delete_category_confirm(
    callback: types.CallbackQuery,
    services: ServiceContainer
):
    """Show deletion confirmation.

    Args:
        callback: Callback with category ID to delete
        services: Service container
    """
    category_id = int(callback.data.split(":", 1)[1])
    telegram_id = callback.from_user.id

    # Get user
    user = await services.user.get_by_telegram_id(telegram_id)
    if not user:
        await callback.answer(
            "❌ Пользователь не найден. Используй /start",
            show_alert=True
        )
        return

    # Get category info
    categories = await services.category.get_user_categories(user["id"])
    category = next((cat for cat in categories if cat["id"] == category_id), None)

    if not category:
        await callback.answer("❌ Категория не найдена", show_alert=True)
        return

    emoji = category.get("emoji", "")
    name = category["name"]

    text = (
        f'⚠️ Ты уверен, что хочешь удалить категорию "{emoji} {name}"?\n\n'
        "Все активности с этой категорией останутся, но без категории."
    )

    keyboard = build_delete_confirmation_keyboard(category_id)

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("delete_confirm:"))
@with_typing_action
async def delete_category_execute(
    callback: types.CallbackQuery,
    services: ServiceContainer
):
    """Execute category deletion.

    Step 3: DELETE /api/v1/categories/{id}

    Args:
        callback: Callback with confirmed category ID
        services: Service container
    """
    category_id = int(callback.data.split(":", 1)[1])
    telegram_id = callback.from_user.id

    # Get user
    user = await services.user.get_by_telegram_id(telegram_id)
    if not user:
        await callback.answer(
            "❌ Пользователь не найден. Используй /start",
            show_alert=True
        )
        return

    # Get category info before deletion
    categories = await services.category.get_user_categories(user["id"])
    category = next((cat for cat in categories if cat["id"] == category_id), None)

    if not category:
        await callback.answer("❌ Категория не найдена", show_alert=True)
        return

    emoji = category.get("emoji", "")
    name = category["name"]

    try:
        # Delete category
        await services.category.delete_category(category_id)

        text = f"✅ Категория \"{emoji} {name}\" удалена."

        keyboard = build_post_deletion_keyboard()

        await callback.message.edit_text(text, reply_markup=keyboard)

        logger.info(
            "Category deleted",
            extra={
                "telegram_id": telegram_id,
                "user_id": user["id"],
                "category_id": category_id,
                "category_name": name
            }
        )

    except ValueError as e:
        # Cannot delete last category
        text = (
            "⚠️ Нельзя удалить последнюю категорию. "
            "Должна остаться хотя бы одна."
        )

        keyboard = build_post_deletion_keyboard()

        await callback.message.edit_text(text, reply_markup=keyboard)

        logger.warning(
            "Attempted to delete last category",
            extra={"telegram_id": telegram_id, "user_id": user["id"]}
        )

    except httpx.HTTPStatusError as e:
        logger.error(
            f"Error deleting category: {e}",
            extra={"status_code": e.response.status_code}
        )
        await callback.answer(
            "❌ Произошла ошибка при удалении категории",
            show_alert=True
        )

    await callback.answer()
