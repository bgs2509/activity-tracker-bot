"""
Time calculation utilities.

Helper functions for time-related calculations used across the application.
"""

from datetime import datetime, timedelta


def get_poll_interval(settings: dict, target_time: datetime | None = None) -> int:
    """
    Get poll interval based on day of week.

    Determines appropriate poll interval (weekday or weekend) based on
    the day of the week.

    Args:
        settings: User settings dict containing poll_interval_weekday and poll_interval_weekend
        target_time: Time to check (defaults to current UTC time)

    Returns:
        Poll interval in minutes (weekday or weekend)

    Example:
        >>> settings = {"poll_interval_weekday": 120, "poll_interval_weekend": 180}
        >>> interval = get_poll_interval(settings)  # Returns 120 or 180 based on current day
    """
    if target_time is None:
        from datetime import timezone
        target_time = datetime.now(timezone.utc)

    is_weekend = target_time.weekday() >= 5  # Saturday=5, Sunday=6

    return (
        settings["poll_interval_weekend"]
        if is_weekend
        else settings["poll_interval_weekday"]
    )


def calculate_poll_start_time(
    end_time: datetime,
    settings: dict
) -> datetime:
    """
    Calculate poll start time based on end time and user settings.

    Determines when a poll period should start by subtracting the appropriate
    interval (weekday or weekend) from the end time.

    Args:
        end_time: End time of the poll period
        settings: User settings with poll_interval_weekday and poll_interval_weekend

    Returns:
        Calculated start time for the poll period

    Example:
        >>> from datetime import datetime, timezone
        >>> end_time = datetime(2025, 11, 7, 14, 0, tzinfo=timezone.utc)  # Thursday
        >>> settings = {"poll_interval_weekday": 120, "poll_interval_weekend": 180}
        >>> start_time = calculate_poll_start_time(end_time, settings)
        >>> # Returns: 2025-11-07 12:00:00+00:00 (2 hours earlier)
    """
    interval_minutes = get_poll_interval(settings, end_time)
    return end_time - timedelta(minutes=interval_minutes)
