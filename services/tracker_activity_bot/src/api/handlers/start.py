"""Start command handler."""
import logging
from aiogram import Router, types
from aiogram.filters import Command

from src.api.dependencies import ServiceContainer
from src.api.keyboards.main_menu import get_main_menu_keyboard
from src.application.services.scheduler_service import scheduler_service

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("start"))
async def cmd_start(message: types.Message, services: ServiceContainer):
    """Handle /start command."""
    telegram_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name

    # Check if user exists
    user = await services.user.get_by_telegram_id(telegram_id)

    if not user:
        # Create new user
        logger.info(f"Creating new user: telegram_id={telegram_id}")
        user = await services.user.create_user(telegram_id, username, first_name)

        # Create default categories
        default_categories = [
            {"name": "Работа", "emoji": "💼", "is_default": True},
            {"name": "Спорт", "emoji": "🏃", "is_default": True},
            {"name": "Отдых", "emoji": "🎮", "is_default": True},
            {"name": "Обучение", "emoji": "📚", "is_default": True},
            {"name": "Сон", "emoji": "😴", "is_default": True},
            {"name": "Еда", "emoji": "🍽️", "is_default": True},
        ]
        await services.category.bulk_create_categories(user["id"], default_categories)

        # Create user settings with defaults
        settings = await services.settings.create_settings(user["id"])
        logger.info(f"Created settings for user {user['id']}: {settings}")

        # Schedule first automatic poll
        user_timezone = user.get("timezone", "Europe/Moscow")
        from src.api.handlers.poll import send_automatic_poll
        await scheduler_service.schedule_poll(
            user_id=telegram_id,
            settings=settings,
            user_timezone=user_timezone,
            send_poll_callback=send_automatic_poll,
            bot=message.bot
        )
        logger.info(f"Scheduled first poll for user {telegram_id}")

        # Welcome message for new user
        text = (
            f"👋 Привет, {first_name}!\n\n"
            "Я помогу тебе отслеживать твою активность в течение дня.\n\n"
            "Для тебя уже созданы базовые категории:\n"
            "💼 Работа  🏃 Спорт  🎮 Отдых\n"
            "📚 Обучение  😴 Сон  🍽️ Еда\n\n"
            "⚙️ Настроены автоматические опросы:\n"
            "• Будни: каждые 2 часа\n"
            "• Выходные: каждые 3 часа\n"
            "• Тихие часы: 23:00 — 07:00 (бот не будет беспокоить)\n\n"
            "Изменить настройки можно в разделе \"Настройки\".\n\n"
            "Выбери действие:"
        )
    else:
        # Check if user has settings (for backward compatibility with existing users)
        settings = await services.settings.get_settings(user["id"])
        if not settings:
            logger.info(f"Creating missing settings for existing user {user['id']}")
            settings = await services.settings.create_settings(user["id"])

            # Schedule poll for existing user who didn't have settings
            user_timezone = user.get("timezone", "Europe/Moscow")
            from src.api.handlers.poll import send_automatic_poll
            await scheduler_service.schedule_poll(
                user_id=telegram_id,
                settings=settings,
                user_timezone=user_timezone,
                send_poll_callback=lambda uid: send_automatic_poll(message.bot, uid)
            )
            logger.info(f"Scheduled poll for existing user {telegram_id}")

        # Welcome message for returning user
        text = (
            f"👋 С возвращением, {first_name}!\n\n"
            "Выбери действие:"
        )

    await message.answer(text, reply_markup=get_main_menu_keyboard())
