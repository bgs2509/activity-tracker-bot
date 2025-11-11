"""FSM states for automatic polls."""
from aiogram.fsm.state import State, StatesGroup


class PollStates(StatesGroup):
    """States for automatic poll responses."""

    waiting_for_poll_response = State()
    waiting_for_poll_category = State()
    waiting_for_poll_description = State()
