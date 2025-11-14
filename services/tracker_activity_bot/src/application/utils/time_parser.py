"""Time parsing utilities.

This module provides functions to parse user time input in various formats
(relative times, exact times, durations, periods) and convert them to UTC datetimes.

Supported Patterns:
    EXACT_TIME_PATTERN: Matches "14:30", "14-30" (exact time)
    MINUTES_PATTERN: Matches "30", "30м", "30min" (minutes)
    HOURS_PATTERN: Matches "2", "2ч", "2h", "2час" (hours)
    NOW_KEYWORDS: Keywords for current time ("сейчас", "now", "0")
"""
import logging
import re
from datetime import datetime, timedelta
import pytz

logger = logging.getLogger(__name__)

# ============================================================================
# Regex Patterns (DRY)
# ============================================================================

# Exact time formats: "14:30", "14-30"
EXACT_TIME_PATTERN = re.compile(r"^(\d{1,2})[-:](\d{2})$")

# Minutes formats: "30", "30м", "30min"
MINUTES_PATTERN = re.compile(r"^(\d+)(м|min)?$")

# Hours formats: "2", "2ч", "2h", "2час"
HOURS_PATTERN = re.compile(r"^(\d+)(ч|h|час)$")

# Period pattern: "14:30 — 15:30", "14:30-15:30", "14:30 - 15:30"
PERIOD_PATTERN = re.compile(r"^(\d{1,2})[-:](\d{2})\s*[—\-]\s*(\d{1,2})[-:](\d{2})$")

# Keywords for "now"
NOW_KEYWORDS = ["сейчас", "now", "0"]


# ============================================================================
# Helper Functions
# ============================================================================

def _parse_minutes(time_str: str) -> int | None:
    """
    Extract minutes from string using MINUTES_PATTERN.

    Args:
        time_str: String like "30", "30м", "30min"

    Returns:
        Integer minutes or None if no match

    Example:
        >>> _parse_minutes("30м")
        30
        >>> _parse_minutes("45min")
        45
    """
    logger.debug("_parse_minutes started", extra={"time_str": time_str})
    match = MINUTES_PATTERN.match(time_str.lower())
    if match:
        minutes = int(match.group(1))
        logger.debug(
            "minutes parsed successfully",
            extra={"time_str": time_str, "minutes": minutes}
        )
        return minutes
    logger.debug("no minutes match", extra={"time_str": time_str})
    return None


def _parse_hours(time_str: str) -> int | None:
    """
    Extract hours from string using HOURS_PATTERN.

    Args:
        time_str: String like "2", "2ч", "2h", "2час"

    Returns:
        Integer hours or None if no match

    Example:
        >>> _parse_hours("2ч")
        2
        >>> _parse_hours("3h")
        3
    """
    logger.debug("_parse_hours started", extra={"time_str": time_str})
    match = HOURS_PATTERN.match(time_str.lower())
    if match:
        hours = int(match.group(1))
        logger.debug(
            "hours parsed successfully",
            extra={"time_str": time_str, "hours": hours}
        )
        return hours
    logger.debug("no hours match", extra={"time_str": time_str})
    return None


def _parse_exact_time(time_str: str) -> tuple[int, int] | None:
    """
    Extract hour and minute from exact time string.

    Args:
        time_str: String like "14:30", "14-30"

    Returns:
        Tuple of (hour, minute) or None if no match

    Raises:
        ValueError: If hour/minute values are out of valid range

    Example:
        >>> _parse_exact_time("14:30")
        (14, 30)
        >>> _parse_exact_time("25:00")
        ValueError: Invalid time format: hour must be 0-23, minute 0-59
    """
    logger.debug("_parse_exact_time started", extra={"time_str": time_str})
    match = EXACT_TIME_PATTERN.match(time_str)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))

        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            logger.warning(
                "invalid time values",
                extra={"time_str": time_str, "hour": hour, "minute": minute}
            )
            raise ValueError("Invalid time format: hour must be 0-23, minute 0-59")

        logger.debug(
            "exact time parsed successfully",
            extra={"time_str": time_str, "hour": hour, "minute": minute}
        )
        return hour, minute
    logger.debug("no exact time match", extra={"time_str": time_str})
    return None


# ============================================================================
# Public API
# ============================================================================


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
    logger.debug(
        "parse_time_input started",
        extra={
            "time_str": time_str,
            "timezone": timezone,
            "has_reference_time": reference_time is not None
        }
    )

    try:
        time_str = time_str.strip().lower()
        tz = pytz.timezone(timezone)

        # Use reference time or current time
        if reference_time:
            now = reference_time.astimezone(tz)
        else:
            now = datetime.now(tz)

        # Pattern 1: Keywords for current time
        if time_str in NOW_KEYWORDS:
            result = now.astimezone(pytz.UTC)
            logger.debug(
                "time parsed as now keyword",
                extra={
                    "time_str": time_str,
                    "format": "now_keyword",
                    "result_utc": result.isoformat()
                }
            )
            return result

        # Pattern 2: Exact time "14:30" or "14-30"
        exact_time = _parse_exact_time(time_str)
        if exact_time:
            hour, minute = exact_time
            result_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            result = result_time.astimezone(pytz.UTC)
            logger.debug(
                "time parsed as exact time",
                extra={
                    "time_str": time_str,
                    "format": "exact_time",
                    "hour": hour,
                    "minute": minute,
                    "result_utc": result.isoformat()
                }
            )
            return result

        # Pattern 3: Minutes ago "30м", "30", "30min"
        minutes = _parse_minutes(time_str)
        if minutes is not None:
            result_time = now - timedelta(minutes=minutes)
            result = result_time.astimezone(pytz.UTC)
            logger.debug(
                "time parsed as minutes ago",
                extra={
                    "time_str": time_str,
                    "format": "minutes_ago",
                    "minutes": minutes,
                    "result_utc": result.isoformat()
                }
            )
            return result

        # Pattern 4: Hours ago "2ч", "2h", "2час"
        hours = _parse_hours(time_str)
        if hours is not None:
            result_time = now - timedelta(hours=hours)
            result = result_time.astimezone(pytz.UTC)
            logger.debug(
                "time parsed as hours ago",
                extra={
                    "time_str": time_str,
                    "format": "hours_ago",
                    "hours": hours,
                    "result_utc": result.isoformat()
                }
            )
            return result

        # No pattern matched
        logger.error(
            "parse_time_input failed: no format matched",
            extra={"time_str": time_str, "timezone": timezone}
        )
        raise ValueError(f"Cannot parse time format: {time_str}")
    except ValueError:
        # Re-raise ValueError (already logged)
        raise
    except Exception as e:
        logger.error(
            "parse_time_input failed with unexpected error",
            extra={"time_str": time_str, "timezone": timezone, "error": str(e)},
            exc_info=True
        )
        raise


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
    logger.debug(
        "parse_duration started",
        extra={
            "duration_str": duration_str,
            "start_time_utc": start_time.isoformat(),
            "timezone": timezone
        }
    )

    try:
        duration_str = duration_str.strip().lower()

        # Convert start_time to user timezone for calculation
        tz = pytz.timezone(timezone)
        start_local = start_time.astimezone(tz)

        # Pattern 1: Keywords for current time
        if duration_str in NOW_KEYWORDS:
            result = datetime.now(tz).astimezone(pytz.UTC)
            logger.debug(
                "duration parsed as now keyword",
                extra={
                    "duration_str": duration_str,
                    "format": "now_keyword",
                    "result_utc": result.isoformat()
                }
            )
            return result

        # Pattern 2: Exact time "16:00"
        exact_time = _parse_exact_time(duration_str)
        if exact_time:
            hour, minute = exact_time
            end_time = start_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
            result = end_time.astimezone(pytz.UTC)
            logger.debug(
                "duration parsed as exact end time",
                extra={
                    "duration_str": duration_str,
                    "format": "exact_time",
                    "hour": hour,
                    "minute": minute,
                    "result_utc": result.isoformat()
                }
            )
            return result

        # Pattern 3: Minutes duration "30м", "30"
        minutes = _parse_minutes(duration_str)
        if minutes is not None:
            end_time = start_local + timedelta(minutes=minutes)
            result = end_time.astimezone(pytz.UTC)
            logger.debug(
                "duration parsed as minutes",
                extra={
                    "duration_str": duration_str,
                    "format": "minutes_duration",
                    "minutes": minutes,
                    "result_utc": result.isoformat()
                }
            )
            return result

        # Pattern 4: Hours duration "2ч", "2h"
        hours = _parse_hours(duration_str)
        if hours is not None:
            end_time = start_local + timedelta(hours=hours)
            result = end_time.astimezone(pytz.UTC)
            logger.debug(
                "duration parsed as hours",
                extra={
                    "duration_str": duration_str,
                    "format": "hours_duration",
                    "hours": hours,
                    "result_utc": result.isoformat()
                }
            )
            return result

        # No pattern matched
        logger.error(
            "parse_duration failed: no format matched",
            extra={"duration_str": duration_str, "start_time_utc": start_time.isoformat()}
        )
        raise ValueError(f"Cannot parse duration format: {duration_str}")
    except ValueError:
        # Re-raise ValueError (already logged)
        raise
    except Exception as e:
        logger.error(
            "parse_duration failed with unexpected error",
            extra={
                "duration_str": duration_str,
                "start_time_utc": start_time.isoformat(),
                "error": str(e)
            },
            exc_info=True
        )
        raise


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
    logger.debug(
        "parse_period started",
        extra={
            "period_str": period_str,
            "timezone": timezone,
            "has_reference_time": reference_time is not None
        }
    )

    try:
        period_str = period_str.strip()
        tz = pytz.timezone(timezone)

        # Use reference time or current time
        if reference_time:
            now = reference_time.astimezone(tz)
        else:
            now = datetime.now(tz)

        # Pattern 1: Relative period "30м", "2ч", etc.
        # Minutes: "30м", "30", "30min"
        minutes = _parse_minutes(period_str)
        if minutes is not None:
            start_time = now - timedelta(minutes=minutes)
            end_time = now
            start_utc = start_time.astimezone(pytz.UTC)
            end_utc = end_time.astimezone(pytz.UTC)
            logger.debug(
                "period parsed as relative minutes",
                extra={
                    "period_str": period_str,
                    "format": "relative_minutes",
                    "minutes": minutes,
                    "start_utc": start_utc.isoformat(),
                    "end_utc": end_utc.isoformat()
                }
            )
            return start_utc, end_utc

        # Hours: "2ч", "2h", "2час"
        hours = _parse_hours(period_str)
        if hours is not None:
            start_time = now - timedelta(hours=hours)
            end_time = now
            start_utc = start_time.astimezone(pytz.UTC)
            end_utc = end_time.astimezone(pytz.UTC)
            logger.debug(
                "period parsed as relative hours",
                extra={
                    "period_str": period_str,
                    "format": "relative_hours",
                    "hours": hours,
                    "start_utc": start_utc.isoformat(),
                    "end_utc": end_utc.isoformat()
                }
            )
            return start_utc, end_utc

        # Pattern 2: Exact time period "14:30 — 15:30" or "14:30-15:30" or "14:30 - 15:30"
        period_match = PERIOD_PATTERN.match(period_str)
        if period_match:
            start_hour = int(period_match.group(1))
            start_minute = int(period_match.group(2))
            end_hour = int(period_match.group(3))
            end_minute = int(period_match.group(4))

            # Validate time values
            if not (0 <= start_hour <= 23 and 0 <= start_minute <= 59):
                logger.warning(
                    "invalid start time in period",
                    extra={
                        "period_str": period_str,
                        "start_hour": start_hour,
                        "start_minute": start_minute
                    }
                )
                raise ValueError("Invalid start time: hour must be 0-23, minute 0-59")
            if not (0 <= end_hour <= 23 and 0 <= end_minute <= 59):
                logger.warning(
                    "invalid end time in period",
                    extra={
                        "period_str": period_str,
                        "end_hour": end_hour,
                        "end_minute": end_minute
                    }
                )
                raise ValueError("Invalid end time: hour must be 0-23, minute 0-59")

            start_time = now.replace(
                hour=start_hour, minute=start_minute, second=0, microsecond=0
            )
            end_time = now.replace(
                hour=end_hour, minute=end_minute, second=0, microsecond=0
            )

            # Validate: end time must be after start time
            if end_time <= start_time:
                logger.warning(
                    "end time before start time in period",
                    extra={
                        "period_str": period_str,
                        "start_time": start_time.isoformat(),
                        "end_time": end_time.isoformat()
                    }
                )
                raise ValueError("End time must be after start time")

            start_utc = start_time.astimezone(pytz.UTC)
            end_utc = end_time.astimezone(pytz.UTC)
            logger.debug(
                "period parsed as exact time range",
                extra={
                    "period_str": period_str,
                    "format": "exact_period",
                    "start_hour": start_hour,
                    "start_minute": start_minute,
                    "end_hour": end_hour,
                    "end_minute": end_minute,
                    "start_utc": start_utc.isoformat(),
                    "end_utc": end_utc.isoformat()
                }
            )
            return start_utc, end_utc

        # No pattern matched
        logger.error(
            "parse_period failed: no format matched",
            extra={"period_str": period_str, "timezone": timezone}
        )
        raise ValueError(
            f"Cannot parse period format: {period_str}. "
            f"Use formats like: 30м, 2ч, or 14:30 — 15:30"
        )
    except ValueError:
        # Re-raise ValueError (already logged)
        raise
    except Exception as e:
        logger.error(
            "parse_period failed with unexpected error",
            extra={"period_str": period_str, "timezone": timezone, "error": str(e)},
            exc_info=True
        )
        raise
