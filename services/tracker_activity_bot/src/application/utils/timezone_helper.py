"""Timezone utilities for poll scheduling."""
from datetime import datetime, time
import pytz


def is_in_quiet_hours(current_time: datetime, quiet_start: time | None, quiet_end: time | None, timezone_str: str) -> bool:
    """Check if current time is within quiet hours.

    Args:
        current_time: Current datetime (UTC)
        quiet_start: Quiet hours start time
        quiet_end: Quiet hours end time
        timezone_str: User's timezone string

    Returns:
        True if in quiet hours, False otherwise
    """
    if not quiet_start or not quiet_end:
        return False

    # Convert to user's timezone
    tz = pytz.timezone(timezone_str)
    local_time = current_time.astimezone(tz).time()

    # If quiet hours don't cross midnight
    if quiet_start < quiet_end:
        return quiet_start <= local_time < quiet_end
    # If quiet hours cross midnight (e.g., 23:00 - 07:00)
    else:
        return local_time >= quiet_start or local_time < quiet_end


def is_weekend(current_time: datetime, timezone_str: str) -> bool:
    """Check if current time is weekend.

    Args:
        current_time: Current datetime (UTC)
        timezone_str: User's timezone string

    Returns:
        True if weekend (Saturday or Sunday), False otherwise
    """
    tz = pytz.timezone(timezone_str)
    local_time = current_time.astimezone(tz)
    return local_time.weekday() >= 5  # 5=Saturday, 6=Sunday


def get_end_of_quiet_hours(quiet_end: time, timezone_str: str) -> datetime:
    """Get the next occurrence of quiet hours end time.

    Args:
        quiet_end: Quiet hours end time
        timezone_str: User's timezone string

    Returns:
        Datetime of next quiet hours end
    """
    tz = pytz.timezone(timezone_str)
    now = datetime.now(tz)

    # Create datetime for today's quiet_end
    end_today = now.replace(
        hour=quiet_end.hour,
        minute=quiet_end.minute,
        second=0,
        microsecond=0
    )

    # If end_today is in the past, use tomorrow
    if end_today <= now:
        from datetime import timedelta
        end_today = end_today + timedelta(days=1)

    return end_today.astimezone(pytz.UTC)
