"""
Time calculation utilities.

Helper functions for time-related calculations used across the application.
"""

import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


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


async def get_last_activity_end_time(
    activity_service,
    user_id: int
) -> datetime | None:
    """
    Get end_time of the last recorded activity for a user.

    Retrieves the most recent activity for the specified user and returns
    its end_time. This is used to calculate accurate activity periods.

    Args:
        activity_service: Activity service HTTP client instance
        user_id: Internal user identifier

    Returns:
        End time of the last activity, or None if no activities exist
        or if an error occurs

    Example:
        >>> from datetime import timezone
        >>> end_time = await get_last_activity_end_time(services.activity, 123)
        >>> if end_time:
        ...     print(f"Last activity ended at: {end_time}")
    """
    try:
        # Get the most recent activity (limit=1)
        activities = await activity_service.get_user_activities(
            user_id=user_id,
            limit=1
        )

        if activities and len(activities) > 0:
            last_activity = activities[0]
            # Parse ISO format datetime string
            end_time_str = last_activity["end_time"]
            return datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))

        return None

    except Exception as e:
        logger.error(
            "Failed to get last activity end_time",
            extra={"user_id": user_id, "error": str(e)}
        )
        return None


async def calculate_poll_period(
    activity_service,
    user_id: int,
    settings: dict
) -> tuple[datetime, datetime]:
    """
    Calculate time period for poll flow based on last activity.

    Determines the time range for a poll-based activity entry by using
    the end time of the last recorded activity as the start time for the
    new period. Falls back to poll interval calculation if no activities exist.

    Args:
        activity_service: Activity service HTTP client instance
        user_id: Internal user identifier
        settings: User settings with poll_interval_weekday and poll_interval_weekend

    Returns:
        Tuple of (start_time, end_time) for the poll period

    Example:
        >>> start, end = await calculate_poll_period(services.activity, 123, settings)
        >>> print(f"Period: {start} to {end}")
        Period: 2025-11-07 12:30:00+00:00 to 2025-11-07 14:45:00+00:00
    """
    # Current time as the end of the period
    end_time = datetime.now(timezone.utc)

    # Try to get the last activity's end time
    last_activity_end = await get_last_activity_end_time(activity_service, user_id)

    if last_activity_end:
        # Use last activity's end time as the start of new period
        start_time = last_activity_end
        logger.info(
            "Using last activity end_time for poll period",
            extra={
                "user_id": user_id,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat()
            }
        )
    else:
        # Fallback: calculate based on poll interval
        start_time = calculate_poll_start_time(end_time, settings)
        logger.info(
            "Using poll interval fallback for period calculation",
            extra={
                "user_id": user_id,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat()
            }
        )

    return start_time, end_time
