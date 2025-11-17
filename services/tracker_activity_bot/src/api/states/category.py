"""FSM states for category management."""
from aiogram.fsm.state import State, StatesGroup


class CategoryStates(StatesGroup):
    """States for category management."""

    # Creation states
    waiting_for_name = State()
    waiting_for_emoji = State()

    # Edit states
    editing_select_field = State()
    editing_name = State()
    editing_emoji = State()
