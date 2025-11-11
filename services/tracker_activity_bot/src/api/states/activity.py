"""FSM states for activity recording."""
from aiogram.fsm.state import State, StatesGroup


class ActivityStates(StatesGroup):
    """States for activity recording (both manual and automatic flows).

    This StateGroup is used by both manual activity recording and automatic
    poll response flows. Different flows enter at different states:

    Manual Flow:
        1. waiting_for_period (entry point)
        2. waiting_for_category
        3. waiting_for_description

    Automatic Poll Flow:
        1. waiting_for_category (entry point - period calculated automatically)
        2. waiting_for_description

    The flows converge at waiting_for_category and share handlers from that
    point forward. Flow differentiation is handled via trigger_source in FSM
    state data ("manual" or "automatic").
    """

    waiting_for_period = State()        # Manual: period selection, Auto: skipped
    waiting_for_category = State()      # BOTH flows converge here
    waiting_for_description = State()   # BOTH flows share this
