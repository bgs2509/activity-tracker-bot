"""FSM states for activity recording."""
from aiogram.fsm.state import State, StatesGroup


class ActivityStates(StatesGroup):
    """States for recording activity."""

    waiting_for_start_time = State()
    waiting_for_end_time = State()
    waiting_for_description = State()
    waiting_for_category = State()
