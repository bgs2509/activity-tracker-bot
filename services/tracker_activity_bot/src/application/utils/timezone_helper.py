"""Timezone utilities for poll scheduling."""
import logging
from datetime import datetime, time
import pytz

logger = logging.getLogger(__name__)


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
    logger.debug(
        "is_in_quiet_hours started",
        extra={
            "current_time_utc": current_time.isoformat(),
            "quiet_start": str(quiet_start) if quiet_start else None,
            "quiet_end": str(quiet_end) if quiet_end else None,
            "timezone_str": timezone_str
        }
    )

    if not quiet_start or not quiet_end:
        logger.debug(
            "quiet hours not configured",
            extra={"result": False, "reason": "no_quiet_hours_set"}
        )
        return False

    # Convert to user's timezone
    tz = pytz.timezone(timezone_str)
    local_time = current_time.astimezone(tz).time()

    # If quiet hours don't cross midnight
    if quiet_start < quiet_end:
        result = quiet_start <= local_time < quiet_end
        logger.debug(
            "quiet hours check completed (no midnight crossing)",
            extra={
                "local_time": str(local_time),
                "quiet_start": str(quiet_start),
                "quiet_end": str(quiet_end),
                "crosses_midnight": False,
                "result": result
            }
        )
        return result
    # If quiet hours cross midnight (e.g., 23:00 - 07:00)
    else:
        result = local_time >= quiet_start or local_time < quiet_end
        logger.debug(
            "quiet hours check completed (midnight crossing)",
            extra={
                "local_time": str(local_time),
                "quiet_start": str(quiet_start),
                "quiet_end": str(quiet_end),
                "crosses_midnight": True,
                "result": result
            }
        )
        return result


def is_weekend(current_time: datetime, timezone_str: str) -> bool:
    """Check if current time is weekend.

    Args:
        current_time: Current datetime (UTC)
        timezone_str: User's timezone string

    Returns:
        True if weekend (Saturday or Sunday), False otherwise
    """
    logger.debug(
        "is_weekend started",
        extra={
            "current_time_utc": current_time.isoformat(),
            "timezone_str": timezone_str
        }
    )

    tz = pytz.timezone(timezone_str)
    local_time = current_time.astimezone(tz)
    weekday = local_time.weekday()
    result = weekday >= 5  # 5=Saturday, 6=Sunday

    logger.debug(
        "is_weekend completed",
        extra={
            "weekday": weekday,
            "weekday_name": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][weekday],
            "result": result
        }
    )
    return result


def get_end_of_quiet_hours(quiet_end: time, timezone_str: str) -> datetime:
    """Get the next occurrence of quiet hours end time.

    Args:
        quiet_end: Quiet hours end time
        timezone_str: User's timezone string

    Returns:
        Datetime of next quiet hours end
    """
    logger.debug(
        "get_end_of_quiet_hours started",
        extra={
            "quiet_end": str(quiet_end),
            "timezone_str": timezone_str
        }
    )

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
        logger.debug(
            "quiet hours end is tomorrow",
            extra={
                "now_local": now.isoformat(),
                "end_today_local": end_today.isoformat(),
                "reason": "end_time_already_passed_today"
            }
        )
    else:
        logger.debug(
            "quiet hours end is today",
            extra={
                "now_local": now.isoformat(),
                "end_today_local": end_today.isoformat()
            }
        )

    result = end_today.astimezone(pytz.UTC)
    logger.debug(
        "get_end_of_quiet_hours completed",
        extra={
            "quiet_end": str(quiet_end),
            "result_utc": result.isoformat()
        }
    )
    return result
