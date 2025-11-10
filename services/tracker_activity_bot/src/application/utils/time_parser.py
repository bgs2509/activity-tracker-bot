"""Time parsing utilities."""
import re
from datetime import datetime, timedelta
import pytz


def parse_time_input(
    time_str: str,
    timezone: str = "Europe/Moscow",
    reference_time: datetime | None = None
) -> datetime:
    """
    Parse time input from user.

    Supported formats:
    - "14:30" or "14-30" → exact time today
    - "30м" or "30" or "30min" → N minutes ago
    - "2ч" or "2h" or "2час" → N hours ago
    - "сейчас" or "now" or "0" → current time

    Args:
        time_str: Time string from user
        timezone: User timezone (default: Europe/Moscow)
        reference_time: Reference time for relative calculations (default: now)

    Returns:
        datetime in UTC

    Raises:
        ValueError: If time format is invalid
    """
    time_str = time_str.strip().lower()
    tz = pytz.timezone(timezone)

    # Use reference time or current time
    if reference_time:
        now = reference_time.astimezone(tz)
    else:
        now = datetime.now(tz)

    # Pattern 1: "сейчас", "now", "0" → current time
    if time_str in ["сейчас", "now", "0"]:
        return now.astimezone(pytz.UTC)

    # Pattern 2: Exact time "14:30" or "14-30"
    exact_time_match = re.match(r"^(\d{1,2})[-:](\d{2})$", time_str)
    if exact_time_match:
        hour = int(exact_time_match.group(1))
        minute = int(exact_time_match.group(2))

        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError("Invalid time format: hour must be 0-23, minute 0-59")

        result_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        return result_time.astimezone(pytz.UTC)

    # Pattern 3: Minutes ago "30м", "30", "30min"
    minutes_match = re.match(r"^(\d+)(м|min)?$", time_str)
    if minutes_match:
        minutes = int(minutes_match.group(1))
        result_time = now - timedelta(minutes=minutes)
        return result_time.astimezone(pytz.UTC)

    # Pattern 4: Hours ago "2ч", "2h", "2час"
    hours_match = re.match(r"^(\d+)(ч|h|час)$", time_str)
    if hours_match:
        hours = int(hours_match.group(1))
        result_time = now - timedelta(hours=hours)
        return result_time.astimezone(pytz.UTC)

    raise ValueError(f"Cannot parse time format: {time_str}")


def parse_duration(
    duration_str: str,
    start_time: datetime,
    timezone: str = "Europe/Moscow"
) -> datetime:
    """
    Parse duration input and calculate end time.

    For duration inputs like "30м" (30 minutes lasted), "2ч" (2 hours lasted)

    Args:
        duration_str: Duration string
        start_time: Start time (in UTC)
        timezone: User timezone

    Returns:
        End time in UTC
    """
    duration_str = duration_str.strip().lower()

    # Convert start_time to user timezone for calculation
    tz = pytz.timezone(timezone)
    start_local = start_time.astimezone(tz)

    # Pattern 1: "сейчас", "now" → current time
    if duration_str in ["сейчас", "now", "0"]:
        return datetime.now(tz).astimezone(pytz.UTC)

    # Pattern 2: Exact time "16:00"
    exact_time_match = re.match(r"^(\d{1,2})[-:](\d{2})$", duration_str)
    if exact_time_match:
        hour = int(exact_time_match.group(1))
        minute = int(exact_time_match.group(2))

        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError("Invalid time format")

        end_time = start_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
        return end_time.astimezone(pytz.UTC)

    # Pattern 3: Minutes duration "30м", "30"
    minutes_match = re.match(r"^(\d+)(м|min)?$", duration_str)
    if minutes_match:
        minutes = int(minutes_match.group(1))
        end_time = start_local + timedelta(minutes=minutes)
        return end_time.astimezone(pytz.UTC)

    # Pattern 4: Hours duration "2ч", "2h"
    hours_match = re.match(r"^(\d+)(ч|h|час)$", duration_str)
    if hours_match:
        hours = int(hours_match.group(1))
        end_time = start_local + timedelta(hours=hours)
        return end_time.astimezone(pytz.UTC)

    raise ValueError(f"Cannot parse duration format: {duration_str}")


def parse_period(
    period_str: str,
    timezone: str = "Europe/Moscow",
    reference_time: datetime | None = None
) -> tuple[datetime, datetime]:
    """
    Parse period input from user and return start_time and end_time.

    Supported formats:
    - "30м" or "30min" → last 30 minutes (now - 30m to now)
    - "2ч" or "2h" → last 2 hours (now - 2h to now)
    - "14:30 — 15:30" or "14:30-15:30" → exact period (today)
    - "14:30 - 15:30" → exact period with space

    Args:
        period_str: Period string from user
        timezone: User timezone (default: Europe/Moscow)
        reference_time: Reference time for relative calculations (default: now)

    Returns:
        Tuple of (start_time, end_time) both in UTC

    Raises:
        ValueError: If period format is invalid or end time is before start time
    """
    period_str = period_str.strip()
    tz = pytz.timezone(timezone)

    # Use reference time or current time
    if reference_time:
        now = reference_time.astimezone(tz)
    else:
        now = datetime.now(tz)

    # Pattern 1: Relative period "30м", "2ч", etc.
    # Minutes: "30м", "30", "30min"
    minutes_match = re.match(r"^(\d+)(м|min)?$", period_str.lower())
    if minutes_match:
        minutes = int(minutes_match.group(1))
        start_time = now - timedelta(minutes=minutes)
        end_time = now
        return start_time.astimezone(pytz.UTC), end_time.astimezone(pytz.UTC)

    # Hours: "2ч", "2h", "2час"
    hours_match = re.match(r"^(\d+)(ч|h|час)$", period_str.lower())
    if hours_match:
        hours = int(hours_match.group(1))
        start_time = now - timedelta(hours=hours)
        end_time = now
        return start_time.astimezone(pytz.UTC), end_time.astimezone(pytz.UTC)

    # Pattern 2: Exact time period "14:30 — 15:30" or "14:30-15:30" or "14:30 - 15:30"
    # Support different separators: —, -, space-dash-space
    period_match = re.match(
        r"^(\d{1,2})[-:](\d{2})\s*[—\-]\s*(\d{1,2})[-:](\d{2})$",
        period_str
    )
    if period_match:
        start_hour = int(period_match.group(1))
        start_minute = int(period_match.group(2))
        end_hour = int(period_match.group(3))
        end_minute = int(period_match.group(4))

        # Validate time values
        if not (0 <= start_hour <= 23 and 0 <= start_minute <= 59):
            raise ValueError("Invalid start time: hour must be 0-23, minute 0-59")
        if not (0 <= end_hour <= 23 and 0 <= end_minute <= 59):
            raise ValueError("Invalid end time: hour must be 0-23, minute 0-59")

        start_time = now.replace(
            hour=start_hour, minute=start_minute, second=0, microsecond=0
        )
        end_time = now.replace(
            hour=end_hour, minute=end_minute, second=0, microsecond=0
        )

        # Validate: end time must be after start time
        if end_time <= start_time:
            raise ValueError("End time must be after start time")

        return start_time.astimezone(pytz.UTC), end_time.astimezone(pytz.UTC)

    raise ValueError(
        f"Cannot parse period format: {period_str}. "
        f"Use formats like: 30м, 2ч, or 14:30 — 15:30"
    )
