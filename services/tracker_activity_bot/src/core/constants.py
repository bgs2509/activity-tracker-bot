"""Application constants."""

# Poll settings
DEFAULT_SLEEP_DURATION_HOURS = 8
"""Default sleep duration when last_poll_time is unknown"""

POLL_POSTPONE_MINUTES = 10
"""Minutes to postpone poll if user is busy"""

# Activity settings
MIN_ACTIVITY_DURATION_MINUTES = 1
"""Minimum activity duration in minutes"""

MAX_ACTIVITY_LIMIT = 10
"""Maximum number of activities to show in list"""

# Validation limits
MIN_POLL_INTERVAL_MINUTES = 30
MAX_POLL_INTERVAL_WEEKDAY_MINUTES = 480  # 8 hours
MAX_POLL_INTERVAL_WEEKEND_MINUTES = 600  # 10 hours

MIN_REMINDER_DELAY_MINUTES = 5
MAX_REMINDER_DELAY_MINUTES = 120

MIN_CATEGORY_NAME_LENGTH = 2
MAX_CATEGORY_NAME_LENGTH = 50
