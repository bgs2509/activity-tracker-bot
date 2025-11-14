"""Aiogram bot entry point for tracker_activity_bot service."""
import asyncio
import logging
import signal
from datetime import timedelta

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage

from src.core.config import settings
from src.core.logging import setup_logging
from src.core.logging_middleware import FSMLoggingMiddleware, UserActionLoggingMiddleware
from src.core.correlation_middleware import CorrelationIDMiddleware
from src.api.middleware import ServiceInjectionMiddleware
from src.api.handlers.start import router as start_router
from src.api.handlers.activity import router as activity_router
from src.api.handlers.categories import router as categories_router
from src.api.handlers.settings import router as settings_router
from src.api.handlers.poll import router as poll_router, close_fsm_storage
from src.api.handlers.ai_activity import router as ai_activity_router
from src.api.dependencies import close_api_client, get_service_container
from src.application.services import fsm_timeout_service as fsm_timeout_module

# Configure structured JSON logging (MANDATORY for Level 1)
setup_logging(service_name="tracker_activity_bot", log_level=settings.log_level)
logger = logging.getLogger(__name__)

# Global shutdown event for graceful shutdown
_shutdown_event = asyncio.Event()


def handle_shutdown_signal(signum: int, frame):
    """
    Handle shutdown signals (SIGTERM, SIGINT) for graceful shutdown.

    Args:
        signum: Signal number
        frame: Current stack frame
    """
    signal_name = signal.Signals(signum).name
    logger.info(
        "Received shutdown signal, initiating graceful shutdown",
        extra={"signal": signal_name}
    )
    _shutdown_event.set()


async def main():
    """Main bot entry point with graceful shutdown support."""
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, handle_shutdown_signal)
    signal.signal(signal.SIGINT, handle_shutdown_signal)
    logger.info("Signal handlers registered (SIGTERM, SIGINT)")

    logger.info("Starting tracker_activity_bot")

    # Initialize bot and dispatcher
    try:
        bot = Bot(token=settings.telegram_bot_token)
    except Exception as e:
        logger.critical(
            "Failed to initialize Telegram bot - invalid token or network issue",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "service": "tracker_activity_bot",
                "impact": "service_cannot_start"
            },
            exc_info=True
        )
        raise

    # Redis storage for FSM with automatic state expiration
    # state_ttl protects against stuck FSM states (e.g., user abandoned dialog)
    try:
        storage = RedisStorage.from_url(
            settings.redis_url,
            state_ttl=timedelta(minutes=15),  # Auto-expire FSM state after 15 minutes
            data_ttl=timedelta(minutes=15)    # Auto-expire FSM data after 15 minutes
        )
    except Exception as e:
        logger.critical(
            "Failed to connect to Redis storage - service cannot operate",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "redis_url": settings.redis_url.split('@')[-1] if '@' in settings.redis_url else settings.redis_url,
                "service": "tracker_activity_bot",
                "impact": "service_cannot_start"
            },
            exc_info=True
        )
        raise

    dp = Dispatcher(storage=storage)

    # Register service injection middleware (must be first to provide dependencies)
    dp.update.middleware(ServiceInjectionMiddleware())
    logger.info("Service injection middleware registered")

    # Register correlation ID middleware for distributed tracing
    dp.update.middleware(CorrelationIDMiddleware())
    logger.info("Correlation ID middleware registered")

    # Register logging middleware for comprehensive DEBUG logging
    dp.update.middleware(UserActionLoggingMiddleware())
    dp.update.middleware(FSMLoggingMiddleware())
    logger.info("Logging middleware registered")

    # Register routers
    # NOTE: ai_activity_router MUST be registered LAST to act as catch-all for text messages
    dp.include_router(start_router)
    dp.include_router(activity_router)
    dp.include_router(categories_router)
    dp.include_router(settings_router)
    dp.include_router(poll_router)
    dp.include_router(ai_activity_router)  # LAST: catches all non-command text

    # Get service container and start scheduler for automatic polls
    services = get_service_container()
    services.scheduler.start()
    logger.info("Scheduler started for automatic polls")

    # Initialize FSM timeout service with injected scheduler
    from src.application.services.fsm_timeout_service import FSMTimeoutService
    fsm_timeout_module.fsm_timeout_service = FSMTimeoutService(services.scheduler.scheduler)
    logger.info("FSM timeout service initialized")

    # Restore scheduled polls for all active users
    try:
        from src.api.handlers.poll.poll_sender import send_automatic_poll

        async def get_active_users_wrapper():
            """Wrapper to get active users from API."""
            return await services.user.get_all_active_users()

        async def get_user_settings_wrapper(user_id: int):
            """Wrapper to get user settings from API."""
            return await services.settings.get_settings(user_id)

        await services.scheduler.restore_scheduled_polls(
            get_active_users=get_active_users_wrapper,
            get_user_settings=get_user_settings_wrapper,
            send_poll_callback=send_automatic_poll,
            bot=bot
        )
        logger.info("Poll schedules restored successfully")
    except Exception as e:
        logger.error(
            "Failed to restore poll schedules - continuing without restoration",
            extra={
                "error": str(e),
                "error_type": type(e).__name__
            },
            exc_info=True
        )

    # Start polling with graceful shutdown support
    logger.info("Bot started, polling...")
    try:
        # Start polling in background task
        polling_task = asyncio.create_task(
            dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
        )

        # Wait for either polling to complete or shutdown signal
        shutdown_task = asyncio.create_task(_shutdown_event.wait())

        done, pending = await asyncio.wait(
            [polling_task, shutdown_task],
            return_when=asyncio.FIRST_COMPLETED
        )

        # If shutdown signal received, cancel polling gracefully
        if _shutdown_event.is_set():
            logger.info("Graceful shutdown initiated, stopping polling...")
            polling_task.cancel()
            try:
                await polling_task
            except asyncio.CancelledError:
                logger.info("Polling task cancelled successfully")

    finally:
        # Shutdown scheduler (wait for pending jobs)
        services.scheduler.stop()
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
