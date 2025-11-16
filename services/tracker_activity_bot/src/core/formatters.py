"""Custom log formatters for structured logging.

This module provides custom JSON formatters that extend pythonjsonlogger
with additional functionality like Unicode support without escaping.

Usage:
    from src.core.formatters import UnicodeJsonFormatter

    formatter = UnicodeJsonFormatter(
        fmt="%(asctime)s %(name)s %(levelname)s %(message)s"
    )
"""

import json
from pythonjsonlogger import jsonlogger


class UnicodeJsonFormatter(jsonlogger.JsonFormatter):
    """JSON formatter that preserves Unicode characters (no escaping).

    Standard JsonFormatter uses json.dumps with ensure_ascii=True by default,
    which escapes all non-ASCII characters (e.g., Cyrillic → \\uXXXX).

    This formatter overrides the serialization to preserve Unicode characters
    in readable form, making logs much more human-friendly for non-English text.

    Example:
        Standard formatter output:
            {"message": "\\u0422\\u044b \\u2014 \\u043f\\u043e\\u043c\\u043e\\u0449\\u043d\\u0438\\u043a"}

        UnicodeJsonFormatter output:
            {"message": "Ты — помощник"}
    """

    def serialize(self, log_record: dict) -> str:
        """Serialize log record to JSON with Unicode support.

        Args:
            log_record: Dictionary containing log data

        Returns:
            JSON string with unescaped Unicode characters
        """
        return json.dumps(
            log_record,
            ensure_ascii=False,  # Preserve Unicode instead of escaping
            default=str
        )
