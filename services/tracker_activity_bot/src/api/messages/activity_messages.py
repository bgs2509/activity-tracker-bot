"""Activity-related message templates and generators.

This module provides unified message generation for activity recording flows
to ensure consistent UI across different entry points (manual and poll-based).
"""

from typing import Optional


# Message constants for category selection headers
CATEGORY_HEADER_MANUAL = "📝 Запись активности"
CATEGORY_HEADER_POLL = "📊 Отчет по активности"
CATEGORY_PROMPT = "📂 Выбери категорию"


def get_category_selection_message(
    source: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    duration: Optional[str] = None,
) -> str:
    """Generate unified category selection message.

    This function creates a consistent category selection prompt that adapts
    based on the source (manual entry vs poll response) while maintaining
    a unified interface structure.

    Args:
        source: Entry point source - "manual" for main menu entry,
                "poll" for poll/reminder-based entry
        start_time: Optional start time string (e.g., "14:06")
        end_time: Optional end time string (e.g., "14:36")
        duration: Optional duration string (e.g., "30м")

    Returns:
        Formatted message string with appropriate header and optional time range

    Examples:
        Manual entry with time:
        >>> get_category_selection_message("manual", "14:06", "14:36", "30м")
        '📝 Запись активности\\n\\n⏰ 14:06 — 14:36 (30м)\\n\\n📂 Выбери категорию'

        Poll entry without time:
        >>> get_category_selection_message("poll")
        '📊 Отчет по активности\\n\\n📂 Выбери категорию'
    """
    headers = {
        "manual": CATEGORY_HEADER_MANUAL,
        "poll": CATEGORY_HEADER_POLL,
    }

    if source not in headers:
        raise ValueError(f"Invalid source: {source}. Must be 'manual' or 'poll'")

    message_parts = [headers[source]]

    # Add time range if provided (typically for manual entry)
    if start_time and end_time and duration:
        message_parts.append(f"⏰ {start_time} — {end_time} ({duration})")

    # Add unified category selection prompt
    message_parts.append(CATEGORY_PROMPT)

    return "\n\n".join(message_parts)
