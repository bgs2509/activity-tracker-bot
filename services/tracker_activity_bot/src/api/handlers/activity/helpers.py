"""Common helper functions for activity handlers (DRY principle)."""

import logging

from aiogram.fsm.context import FSMContext

from src.application.utils.fsm_helpers import clear_state_and_timeout

logger = logging.getLogger(__name__)

# Quick time selection maps (DRY)
START_TIME_MAP = {
    "15m": "15м",
    "30m": "30м",
    "1h": "1ч",
    "2h": "2ч",
    "3h": "3ч",
    "8h": "8ч",
}

END_TIME_MAP = {
    "now": "0",
    "15m": "15м",
    "30m": "30м",
    "1h": "1ч",
    "2h": "2ч",
    "3h": "3ч",
    "8h": "8ч",
}


async def cancel_activity_recording(
    state: FSMContext,
    user_id: int
) -> None:
    """
    Cancel activity recording and cleanup.

    This helper eliminates duplication in cancel handlers.

    Args:
        state: FSM context to clear
        user_id: Telegram user ID
    """
    await clear_state_and_timeout(state, user_id)

    logger.info(
        "Activity recording cancelled",
        extra={"user_id": user_id}
    )
