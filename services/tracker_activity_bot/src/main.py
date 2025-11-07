"""Aiogram bot entry point for tracker_activity_bot service."""
import asyncio
import logging
from datetime import timedelta

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage

from src.core.config import settings
from src.core.logging import setup_logging
from src.core.logging_middleware import FSMLoggingMiddleware, UserActionLoggingMiddleware
from src.api.handlers.start import router as start_router
from src.api.handlers.activity import router as activity_router
from src.api.handlers.categories import router as categories_router
from src.api.handlers.settings import router as settings_router
from src.api.handlers.poll import router as poll_router, close_fsm_storage
from src.api.dependencies import close_api_client
from src.application.services.scheduler_service import scheduler_service
from src.application.services import fsm_timeout_service as fsm_timeout_module

# Configure structured JSON logging (MANDATORY for Level 1)
setup_logging(service_name="tracker_activity_bot", log_level=settings.log_level)
logger = logging.getLogger(__name__)


async def main():
    """Main bot entry point."""
    logger.info("Starting tracker_activity_bot")

    # Initialize bot and dispatcher
    bot = Bot(token=settings.telegram_bot_token)

    # Redis storage for FSM with automatic state expiration
    # state_ttl protects against stuck FSM states (e.g., user abandoned dialog)
    storage = RedisStorage.from_url(
        settings.redis_url,
        state_ttl=timedelta(minutes=15),  # Auto-expire FSM state after 15 minutes
        data_ttl=timedelta(minutes=15)    # Auto-expire FSM data after 15 minutes
    )
    dp = Dispatcher(storage=storage)

    # Register logging middleware for comprehensive DEBUG logging
    dp.update.middleware(UserActionLoggingMiddleware())
    dp.update.middleware(FSMLoggingMiddleware())
    logger.info("Logging middleware registered")

    # Register routers
    dp.include_router(start_router)
    dp.include_router(activity_router)
    dp.include_router(categories_router)
    dp.include_router(settings_router)
    dp.include_router(poll_router)

    # Start scheduler for automatic polls
    scheduler_service.start()
    logger.info("Scheduler started for automatic polls")

    # Initialize FSM timeout service
    from src.application.services.fsm_timeout_service import FSMTimeoutService
    fsm_timeout_module.fsm_timeout_service = FSMTimeoutService(scheduler_service.scheduler)
    logger.info("FSM timeout service initialized")

    # Start polling
    logger.info("Bot started, polling...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        # Shutdown scheduler
        scheduler_service.stop()
        logger.info("Scheduler stopped")

        # Close FSM storage to prevent connection leaks
        await close_fsm_storage()
        logger.info("FSM storage closed")

        # Close HTTP API client to prevent connection pool leaks
        await close_api_client()
        logger.info("HTTP API client closed")

        # Close bot session and main storage
        await bot.session.close()
        await storage.close()
        logger.info("Bot shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
