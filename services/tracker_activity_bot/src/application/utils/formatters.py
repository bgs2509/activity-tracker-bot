"""Formatting utilities for bot messages."""
import logging
from datetime import datetime, timedelta
import pytz

logger = logging.getLogger(__name__)


def format_duration(minutes: int) -> str:
    """
    Format duration in minutes to human-readable string.

    Examples:
        30 → "30м"
        90 → "1ч 30м"
        120 → "2ч"
    """
    logger.debug("format_duration started", extra={"minutes": minutes})

    if minutes < 60:
        result = f"{minutes}м"
        logger.debug(
            "format_duration completed (minutes only)",
            extra={"minutes": minutes, "result": result}
        )
        return result

    hours = minutes // 60
    remaining_minutes = minutes % 60

    if remaining_minutes == 0:
        result = f"{hours}ч"
        logger.debug(
            "format_duration completed (hours only)",
            extra={"minutes": minutes, "hours": hours, "result": result}
        )
        return result

    result = f"{hours}ч {remaining_minutes}м"
    logger.debug(
        "format_duration completed (hours and minutes)",
        extra={
            "minutes": minutes,
            "hours": hours,
            "remaining_minutes": remaining_minutes,
            "result": result
        }
    )
    return result


def format_time(dt: datetime, timezone: str = "Europe/Moscow") -> str:
    """Format datetime to time string (HH:MM)."""
    logger.debug(
        "format_time started",
        extra={"datetime_utc": dt.isoformat(), "timezone": timezone}
    )

    tz = pytz.timezone(timezone)
    local_time = dt.astimezone(tz)
    result = local_time.strftime("%H:%M")

    logger.debug(
        "format_time completed",
        extra={
            "datetime_utc": dt.isoformat(),
            "timezone": timezone,
            "result": result
        }
    )
    return result


def format_date(dt: datetime, timezone: str = "Europe/Moscow") -> str:
    """Format datetime to date string (DD Month YYYY)."""
    logger.debug(
        "format_date started",
        extra={"datetime_utc": dt.isoformat(), "timezone": timezone}
    )

    tz = pytz.timezone(timezone)
    local_time = dt.astimezone(tz)

    months = {
        1: "января", 2: "февраля", 3: "марта", 4: "апреля",
        5: "мая", 6: "июня", 7: "июля", 8: "августа",
        9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
    }

    day = local_time.day
    month = months[local_time.month]
    year = local_time.year
    result = f"{day} {month} {year}"

    logger.debug(
        "format_date completed",
        extra={
            "datetime_utc": dt.isoformat(),
            "timezone": timezone,
            "day": day,
            "month_name": month,
            "year": year,
            "result": result
        }
    )
    return result


def format_activity_list(
    activities: list[dict],
    timezone: str = "Europe/Moscow",
    reference_time: datetime | None = None
) -> str:
    """
    Format activities list for display.

    Groups activities by date and formats each entry.
    Shows only activities from the last 24 hours, sorted chronologically
    (oldest first, newest last).

    Args:
        activities: List of activity dicts with start_time, end_time, etc.
        timezone: Timezone for display (default: Europe/Moscow)
        reference_time: Reference time for filtering (default: now). Used for testing.

    Returns:
        Formatted activity list as string
    """
    logger.debug(
        "format_activity_list started",
        extra={
            "activity_count": len(activities),
            "timezone": timezone,
            "has_reference_time": reference_time is not None
        }
    )

    if not activities:
        result = "У тебя пока нет записанных активностей."
        logger.debug(
            "format_activity_list completed (empty list)",
            extra={"result": result}
        )
        return result

    # Use timezone for date formatting
    tz = pytz.timezone(timezone)

    # Group activities by date with datetime key for sorting
    grouped = {}
    for activity in activities:
        start_time = datetime.fromisoformat(activity["start_time"].replace("Z", "+00:00"))
        date_key = format_date(start_time, timezone)

        if date_key not in grouped:
            grouped[date_key] = {
                "datetime": start_time,  # Store datetime for sorting
                "activities": []
            }

        grouped[date_key]["activities"].append(activity)

    # Sort dates chronologically (oldest first, newest last)
    sorted_dates = sorted(grouped.items(), key=lambda x: x[1]["datetime"])

    # Format output
    lines = ["📋 Твои последние активности:\n"]

    for date_key, date_data in sorted_dates:
        lines.append("━━━━━━━━━━━━━━━━━━")
        lines.append(f"📅 {date_key}")
        lines.append("━━━━━━━━━━━━━━━━━━\n")

        # Sort activities within date by start time (earliest first)
        date_activities = sorted(
            date_data["activities"],
            key=lambda a: datetime.fromisoformat(a["start_time"].replace("Z", "+00:00"))
        )

        for activity in date_activities:
            start_time = datetime.fromisoformat(activity["start_time"].replace("Z", "+00:00"))
            end_time = datetime.fromisoformat(activity["end_time"].replace("Z", "+00:00"))

            start_str = format_time(start_time, timezone)
            end_str = format_time(end_time, timezone)
            duration_str = format_duration(activity["duration_minutes"])

            # Category name with emoji (if present)
            category_text = ""
            if activity.get("category_name"):
                category_name = activity["category_name"]
                # Add emoji if present
                if activity.get("category_emoji"):
                    category_text = f"{activity['category_emoji']} {category_name} "
                else:
                    category_text = f"{category_name} "

            # Description
            description = activity["description"]

            # Tags
            tags_text = ""
            if activity.get("tags"):
                tags = activity["tags"].split(",")
                tags_text = "\n🏷 " + " ".join(f"#{tag}" for tag in tags)

            lines.append(
                f"{category_text}{start_str} — {end_str} ({duration_str})\n"
                f"{description}{tags_text}\n"
            )

    result = "\n".join(lines)
    logger.debug(
        "format_activity_list completed",
        extra={
            "activity_count": len(activities),
            "date_groups": len(sorted_dates),
            "total_lines": len(lines),
            "result_length": len(result)
        }
    )
    return result


def extract_tags(text: str) -> list[str]:
    """
    Extract hashtags from text.

    Examples:
        "Работал над проектом #важное #дедлайн" → ["важное", "дедлайн"]
    """
    logger.debug("extract_tags started", extra={"text_length": len(text)})

    import re
    tags = re.findall(r"#(\w+)", text)

    logger.debug(
        "extract_tags completed",
        extra={
            "text_length": len(text),
            "tags_found": len(tags),
            "tags": tags
        }
    )
    return tags
