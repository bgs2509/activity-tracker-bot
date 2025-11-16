"""Structured JSON logging setup for data_postgres_api.

This module provides structured JSON logging using python-json-logger,
which is MANDATORY for Level 1 (PoC) according to .framework/ requirements.

Usage:
    from src.core.logging import setup_logging

    # Initialize logging FIRST in main.py
    setup_logging(service_name="data_postgres_api", log_level="INFO")
    logger = logging.getLogger(__name__)

    # All logs will be in JSON format
    logger.info("FastAPI app started", extra={"port": 8000})

Output Example:
    {"timestamp": "2025-10-30T12:00:00Z", "logger": "main",
     "levelname": "INFO", "message": "FastAPI app started",
     "service": "data_postgres_api", "port": 8000}

Reference:
    - .framework/docs/reference/maturity-levels.md (Level 1, lines 48-52)
    - artifacts/prompts/step-01-v01.md (lines 1131-1234)
"""
import json
import logging
import sys
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


def setup_logging(service_name: str, log_level: str = "INFO") -> None:
    """
    Setup structured JSON logging for the service.

    This function configures the root logger to output JSON-formatted logs
    to stdout. All subsequent logging calls will produce structured JSON output.

    Args:
        service_name: Name of the service for log identification.
                      Example: "data_postgres_api"
        log_level: Logging level string (INFO, DEBUG, ERROR, WARNING, CRITICAL).
                   Default: "INFO"

    Why JSON Logging is Mandatory for Level 1:
        1. Parsable by log aggregators (even without ELK on PoC)
        2. Structured metadata via extra={} parameters
        3. Preparation for Level 2 (Request ID tracking)
        4. Production-ready (console logs not suitable for production)

    Example:
        >>> setup_logging(service_name="data_postgres_api")
        >>> logger = logging.getLogger(__name__)
        >>> logger.info("User created", extra={"user_id": 1, "telegram_id": 123456789})
        # Output: {"timestamp": "2025-10-30T12:00:00Z", "logger": "api.users",
        #          "levelname": "INFO", "message": "User created",
        #          "service": "data_postgres_api", "user_id": 1, "telegram_id": 123456789}
    """
    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(log_level.upper())

    # Clear any existing handlers to avoid duplicate logs
    logger.handlers = []

    # Create console handler (stdout for Docker log capture)
    handler = logging.StreamHandler(sys.stdout)

    # Create JSON formatter with Unicode support and field renaming
    formatter = UnicodeJsonFormatter(
        fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
        rename_fields={
            "asctime": "timestamp",  # More standard field name
            "name": "logger",        # Clearer than 'name'
        },
        static_fields={
            "service": service_name  # Service identifier in every log
        },
    )

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Log initialization (this will be in JSON format)
    logger.info(
        f"Structured JSON logging initialized for {service_name}",
        extra={"log_level": log_level}
    )
