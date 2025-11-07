"""
FSM helper utilities.

This module provides helper functions for common FSM operations,
reducing code duplication in handlers.
"""

import logging
from aiogram.fsm.context import FSMContext

from src.application.services import fsm_timeout_service as fsm_timeout_module

logger = logging.getLogger(__name__)


async def schedule_fsm_timeout(user_id: int, state: str, bot) -> None:
    """
    Schedule FSM timeout for user state.

    Wraps the conditional timeout scheduling logic to reduce duplication.

    Args:
        user_id: Telegram user ID
        state: FSM state for timeout
        bot: Bot instance

    Example:
        await schedule_fsm_timeout(
            callback.from_user.id,
            ActivityStates.waiting_for_start_time,
            callback.bot
        )
    """
    if fsm_timeout_module.fsm_timeout_service:
        fsm_timeout_module.fsm_timeout_service.schedule_timeout(
            user_id=user_id,
            state=state,
            bot=bot
        )
        logger.debug(
            "Scheduled FSM timeout",
            extra={"user_id": user_id, "state": str(state)}
        )


async def cancel_fsm_timeout(user_id: int) -> None:
    """
    Cancel FSM timeout for user.

    Wraps the conditional timeout cancellation logic to reduce duplication.

    Args:
        user_id: Telegram user ID

    Example:
        await cancel_fsm_timeout(callback.from_user.id)
    """
    if fsm_timeout_module.fsm_timeout_service:
        fsm_timeout_module.fsm_timeout_service.cancel_timeout(user_id)
        logger.debug(
            "Cancelled FSM timeout",
            extra={"user_id": user_id}
        )


async def clear_state_and_timeout(state: FSMContext, user_id: int) -> None:
    """
    Clear FSM state and cancel associated timeout.

    This is the most common cleanup pattern - combines state clearing
    with timeout cancellation in a single call.

    Args:
        state: FSM context to clear
        user_id: User ID for timeout cancellation

    Example:
        await clear_state_and_timeout(state, callback.from_user.id)
    """
    await state.clear()
    await cancel_fsm_timeout(user_id)
    logger.debug(
        "Cleared state and cancelled timeout",
        extra={"user_id": user_id}
    )


async def cancel_cleanup_timer(user_id: int) -> None:
    """
    Cancel cleanup timer for user.

    Used in FSM timeout reminder continuation flow.

    Args:
        user_id: Telegram user ID

    Example:
        await cancel_cleanup_timer(callback.from_user.id)
    """
    if fsm_timeout_module.fsm_timeout_service:
        fsm_timeout_module.fsm_timeout_service.cancel_cleanup_timer(user_id)
        logger.debug(
            "Cancelled cleanup timer",
            extra={"user_id": user_id}
        )
