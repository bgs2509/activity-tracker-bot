"""FSM states for category management."""
from aiogram.fsm.state import State, StatesGroup


class CategoryStates(StatesGroup):
    """States for category management."""

    waiting_for_name = State()
    waiting_for_emoji = State()
