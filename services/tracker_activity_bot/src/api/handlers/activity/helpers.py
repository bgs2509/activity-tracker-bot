"""Common helper functions for activity handlers (DRY principle)."""

import logging
from datetime import datetime

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


async def validate_start_time(start_time: datetime) -> bool:
    """
    Validate that start time is not in the future.

    Args:
        start_time: Parsed start time

    Returns:
        True if valid, False if in future
    """
    now_utc = datetime.now(datetime.timezone.utc)
    return start_time <= now_utc


async def validate_end_time(start_time: datetime, end_time: datetime) -> bool:
    """
    Validate that end time is after start time and not in future.

    Args:
        start_time: Activity start time
        end_time: Activity end time

    Returns:
        True if valid, False otherwise
    """
    now_utc = datetime.now(datetime.timezone.utc)

    if end_time > now_utc:
        return False

    if end_time <= start_time:
        return False

    return True


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
