"""Formatting utilities for bot messages."""
from datetime import datetime
import pytz


def format_duration(minutes: int) -> str:
    """
    Format duration in minutes to human-readable string.

    Examples:
        30 → "30м"
        90 → "1ч 30м"
        120 → "2ч"
    """
    if minutes < 60:
        return f"{minutes}м"

    hours = minutes // 60
    remaining_minutes = minutes % 60

    if remaining_minutes == 0:
        return f"{hours}ч"

    return f"{hours}ч {remaining_minutes}м"


def format_time(dt: datetime, timezone: str = "Europe/Moscow") -> str:
    """Format datetime to time string (HH:MM)."""
    tz = pytz.timezone(timezone)
    local_time = dt.astimezone(tz)
    return local_time.strftime("%H:%M")


def format_date(dt: datetime, timezone: str = "Europe/Moscow") -> str:
    """Format datetime to date string (DD Month YYYY)."""
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

    return f"{day} {month} {year}"


def format_activity_list(activities: list[dict], timezone: str = "Europe/Moscow") -> str:
    """
    Format activities list for display.

    Groups activities by date and formats each entry.
    """
    if not activities:
        return "У тебя пока нет записанных активностей."

    # Group activities by date
    grouped = {}
    for activity in activities:
        start_time = datetime.fromisoformat(activity["start_time"].replace("Z", "+00:00"))
        date_key = format_date(start_time, timezone)

        if date_key not in grouped:
            grouped[date_key] = []

        grouped[date_key].append(activity)

    # Format output
    lines = ["📋 Твои последние активности:\n"]

    for date_key, date_activities in grouped.items():
        lines.append("━━━━━━━━━━━━━━━━━━")
        lines.append(f"📅 {date_key}")
        lines.append("━━━━━━━━━━━━━━━━━━\n")

        for activity in date_activities:
            start_time = datetime.fromisoformat(activity["start_time"].replace("Z", "+00:00"))
            end_time = datetime.fromisoformat(activity["end_time"].replace("Z", "+00:00"))

            start_str = format_time(start_time, timezone)
            end_str = format_time(end_time, timezone)
            duration_str = format_duration(activity["duration_minutes"])

            # Category emoji (if present)
            category_text = ""
            # Note: category data would need to be joined, simplified for PoC

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

    return "\n".join(lines)


def extract_tags(text: str) -> list[str]:
    """
    Extract hashtags from text.

    Examples:
        "Работал над проектом #важное #дедлайн" → ["важное", "дедлайн"]
    """
    import re
    tags = re.findall(r"#(\w+)", text)
    return tags
