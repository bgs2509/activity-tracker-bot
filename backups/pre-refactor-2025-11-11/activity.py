"""FSM states for activity recording."""
from aiogram.fsm.state import State, StatesGroup


class ActivityStates(StatesGroup):
    """States for recording activity."""

    waiting_for_period = State()
    waiting_for_category = State()
    waiting_for_description = State()
