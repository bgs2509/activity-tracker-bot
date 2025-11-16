"""FSM states for AI-powered activity creation flow.

This module defines the state machine for natural language activity input.
Unlike the manual flow, AI flow has fewer states as it processes text directly.

State Flow:
    waiting_for_ai_confirmation -> Activity saved or cancelled (high confidence)
    waiting_for_ai_clarification -> Activity saved or cancelled (medium/low confidence)
"""

from aiogram.fsm.state import State, StatesGroup


class AIActivityStates(StatesGroup):
    """FSM states for AI activity creation.

    States:
        waiting_for_ai_confirmation: User is confirming high-confidence AI parsing
            with complete data (category, description, time)
        waiting_for_ai_clarification: User is choosing from AI suggestions
            or providing refined text input (medium/low confidence)
    """

    # User is confirming high-confidence complete AI parsing
    waiting_for_ai_confirmation = State()

    # User is reviewing AI suggestions and may provide refined input
    waiting_for_ai_clarification = State()
