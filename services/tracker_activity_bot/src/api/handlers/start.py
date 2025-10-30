"""Start command handler."""
import logging
from aiogram import Router, types
from aiogram.filters import Command

from src.infrastructure.http_clients.http_client import DataAPIClient
from src.infrastructure.http_clients.user_service import UserService
from src.infrastructure.http_clients.category_service import CategoryService
from src.api.keyboards.main_menu import get_main_menu_keyboard

router = Router()
logger = logging.getLogger(__name__)

# Global API client (will be initialized in main.py)
api_client = DataAPIClient()


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    """Handle /start command."""
    user_service = UserService(api_client)
    category_service = CategoryService(api_client)

    telegram_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name

    # Check if user exists
    user = await user_service.get_by_telegram_id(telegram_id)

    if not user:
        # Create new user
        logger.info(f"Creating new user: telegram_id={telegram_id}")
        user = await user_service.create_user(telegram_id, username, first_name)

        # Create default categories
        default_categories = [
            {"name": "Работа", "emoji": "💼", "is_default": True},
            {"name": "Спорт", "emoji": "🏃", "is_default": True},
            {"name": "Отдых", "emoji": "🎮", "is_default": True},
            {"name": "Обучение", "emoji": "📚", "is_default": True},
            {"name": "Сон", "emoji": "😴", "is_default": True},
            {"name": "Еда", "emoji": "🍽️", "is_default": True},
        ]
        await category_service.bulk_create_categories(user["id"], default_categories)

        # Welcome message for new user
        text = (
            f"👋 Привет, {first_name}!\n\n"
            "Я помогу тебе отслеживать твою активность в течение дня.\n\n"
            "Для тебя уже созданы базовые категории:\n"
            "💼 Работа  🏃 Спорт  🎮 Отдых\n"
            "📚 Обучение  😴 Сон  🍽️ Еда\n\n"
            "Выбери действие:"
        )
    else:
        # Welcome message for returning user
        text = (
            f"👋 С возвращением, {first_name}!\n\n"
            "Выбери действие:"
        )

    await message.answer(text, reply_markup=get_main_menu_keyboard())
