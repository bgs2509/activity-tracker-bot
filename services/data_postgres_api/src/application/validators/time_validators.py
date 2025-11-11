"""Time validation utilities for activity operations.

This module provides centralized time validation logic to ensure
consistency across all activity-related operations.
"""

from datetime import datetime, timezone


def validate_start_time(start_time: datetime) -> None:
    """
    Validate that start_time is valid for an activity.

    Args:
        start_time: Activity start time (naive datetime treated as UTC)

    Raises:
        ValueError: If start_time is invalid

    Example:
        >>> from datetime import datetime, timezone
        >>> validate_start_time(datetime.now(timezone.utc))  # OK
        >>> validate_start_time(datetime.now(timezone.utc) + timedelta(hours=1))
        ValueError: Start time cannot be in the future
    """
    # Convert naive datetime to UTC for backward compatibility
    if not start_time.tzinfo:
        start_time = start_time.replace(tzinfo=timezone.utc)

    now_utc = datetime.now(timezone.utc)
    if start_time > now_utc:
        raise ValueError("Start time cannot be in the future")


def validate_end_time(end_time: datetime, start_time: datetime) -> None:
    """
    Validate that end_time is valid relative to start_time.

    Args:
        end_time: Activity end time (naive datetime treated as UTC)
        start_time: Activity start time (naive datetime treated as UTC)

    Raises:
        ValueError: If end_time is invalid

    Example:
        >>> from datetime import datetime, timezone, timedelta
        >>> start = datetime.now(timezone.utc) - timedelta(hours=1)
        >>> end = datetime.now(timezone.utc)
        >>> validate_end_time(end, start)  # OK
        >>> validate_end_time(start, end)  # Raises ValueError
    """
    # Convert naive datetimes to UTC for backward compatibility
    if not end_time.tzinfo:
        end_time = end_time.replace(tzinfo=timezone.utc)
    if not start_time.tzinfo:
        start_time = start_time.replace(tzinfo=timezone.utc)

    if end_time <= start_time:
        raise ValueError(
            f"End time ({end_time}) must be after start time ({start_time})"
        )

    now_utc = datetime.now(timezone.utc)
    if end_time > now_utc:
        raise ValueError("End time cannot be in the future")


def validate_activity_duration(
    start_time: datetime,
    end_time: datetime,
    max_hours: int = 24
) -> None:
    """
    Validate that activity duration is within acceptable limits.

    Args:
        start_time: Activity start time
        end_time: Activity end time
        max_hours: Maximum allowed duration in hours (default: 24)

    Raises:
        ValueError: If duration exceeds max_hours

    Example:
        >>> from datetime import datetime, timezone, timedelta
        >>> start = datetime.now(timezone.utc) - timedelta(hours=2)
        >>> end = datetime.now(timezone.utc)
        >>> validate_activity_duration(start, end)  # OK (2 hours)
        >>> validate_activity_duration(start, end, max_hours=1)  # Raises ValueError
    """
    duration = end_time - start_time
    duration_hours = duration.total_seconds() / 3600

    if duration_hours > max_hours:
        raise ValueError(
            f"Activity duration ({duration_hours:.1f}h) exceeds "
            f"maximum allowed duration ({max_hours}h)"
        )
