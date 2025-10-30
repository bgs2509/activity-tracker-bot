"""FSM states for settings configuration."""
from aiogram.fsm.state import State, StatesGroup


class SettingsStates(StatesGroup):
    """States for settings configuration."""

    # Interval settings
    waiting_for_weekday_interval_custom = State()
    waiting_for_weekend_interval_custom = State()

    # Quiet hours settings
    waiting_for_quiet_hours_start_custom = State()
    waiting_for_quiet_hours_end_custom = State()

    # Reminder settings
    waiting_for_reminder_delay_custom = State()
