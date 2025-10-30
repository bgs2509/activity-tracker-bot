"""Aiogram bot entry point for tracker_activity_bot service."""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage

from src.core.config import settings
from src.api.handlers.start import router as start_router
from src.api.handlers.activity import router as activity_router

# Configure logging
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Main bot entry point."""
    logger.info("Starting tracker_activity_bot")

    # Initialize bot and dispatcher
    bot = Bot(token=settings.telegram_bot_token)

    # Redis storage for FSM
    storage = RedisStorage.from_url(settings.redis_url)
    dp = Dispatcher(storage=storage)

    # Register routers
    dp.include_router(start_router)
    dp.include_router(activity_router)

    # Start polling
    logger.info("Bot started, polling...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        await storage.close()


if __name__ == "__main__":
    asyncio.run(main())
