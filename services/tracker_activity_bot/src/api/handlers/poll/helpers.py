"""Common helper functions for poll handlers (DRY principle)."""

import logging

from aiogram.fsm.storage.redis import RedisStorage

from src.application.utils.user_helpers import get_user_and_settings  # noqa: F401
from src.core.config import settings as app_settings

logger = logging.getLogger(__name__)

# Redis storage for FSM state checking
# Note: This is a separate instance from the main dispatcher's storage,
# but both connect to the same Redis, so state is shared
_fsm_storage = None


def get_fsm_storage() -> RedisStorage:
    """
    Get or create FSM storage instance for state checking.

    Returns:
        RedisStorage instance

    Note:
        This creates a shared FSM storage instance for checking user states.
        Must call close_fsm_storage() on shutdown to prevent connection leaks.
    """
    global _fsm_storage
    if _fsm_storage is None:
        _fsm_storage = RedisStorage.from_url(app_settings.redis_url)
        logger.info("Created shared FSM storage instance")
    return _fsm_storage


async def close_fsm_storage() -> None:
    """
    Close FSM storage and cleanup Redis connections.

    This function must be called during application shutdown to prevent
    connection pool leaks. It's safe to call multiple times.
    """
    global _fsm_storage
    if _fsm_storage is not None:
        await _fsm_storage.close()
        _fsm_storage = None
        logger.info("Closed FSM storage")
