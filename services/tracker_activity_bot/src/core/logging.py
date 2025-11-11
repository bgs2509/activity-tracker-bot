"""Structured JSON logging setup for tracker_activity_bot.

This module provides structured JSON logging using python-json-logger,
which is MANDATORY for Level 1 (PoC) according to .framework/ requirements.

Usage:
    from src.core.logging import setup_logging

    # Initialize logging FIRST in main.py
    setup_logging(service_name="tracker_activity_bot", log_level="INFO")
    logger = logging.getLogger(__name__)

    # All logs will be in JSON format
    logger.info("Bot started", extra={"telegram_id": 123456789})

Output Example:
    {"timestamp": "2025-10-30T12:00:00Z", "logger": "main",
     "levelname": "INFO", "message": "Bot started",
     "service": "tracker_activity_bot", "telegram_id": 123456789}

Reference:
    - .framework/docs/reference/maturity-levels.md (Level 1, lines 48-52)
    - artifacts/prompts/step-01-v01.md (lines 1131-1234)
"""
import logging
import random
import sys
from typing import Optional
from pythonjsonlogger import jsonlogger


class SamplingFilter(logging.Filter):
    """Filter to sample logs based on log level and sampling rate.

    Allows selective sampling of high-volume logs (DEBUG) while
    keeping all important logs (INFO, WARNING, ERROR, CRITICAL).
    """

    def __init__(
        self,
        sample_rate: float = 1.0,
        sample_debug_only: bool = True
    ):
        """Initialize sampling filter.

        Args:
            sample_rate: Probability of keeping a log (0.0 to 1.0)
            sample_debug_only: If True, only sample DEBUG logs
        """
        super().__init__()
        self.sample_rate = sample_rate
        self.sample_debug_only = sample_debug_only

    def filter(self, record: logging.LogRecord) -> bool:
        """Determine if log record should be kept.

        Args:
            record: Log record to evaluate

        Returns:
            True if record should be logged, False to discard
        """
        # Always keep non-DEBUG logs
        if self.sample_debug_only and record.levelno > logging.DEBUG:
            return True

        # Always keep if sampling disabled
        if self.sample_rate >= 1.0:
            return True

        # Sample based on probability
        return random.random() < self.sample_rate


def setup_logging(
    service_name: str,
    log_level: str = "INFO",
    debug_sample_rate: Optional[float] = None
) -> None:
    """
    Setup structured JSON logging for the service with optional sampling.

    This function configures the root logger to output JSON-formatted logs
    to stdout. All subsequent logging calls will produce structured JSON output.

    Args:
        service_name: Name of the service for log identification.
                      Example: "tracker_activity_bot"
        log_level: Logging level string (INFO, DEBUG, ERROR, WARNING, CRITICAL).
                   Default: "INFO"
        debug_sample_rate: Sampling rate for DEBUG logs (None = no sampling).
                          Example: 0.1 = keep 10% of DEBUG logs.
                          Only affects DEBUG level, all other levels always logged.

    Why JSON Logging is Mandatory for Level 1:
        1. Parsable by log aggregators (even without ELK on PoC)
        2. Structured metadata via extra={} parameters
        3. Preparation for Level 2 (Request ID tracking)
        4. Production-ready (console logs not suitable for production)

    Example:
        >>> setup_logging(service_name="tracker_activity_bot")
        >>> logger = logging.getLogger(__name__)
        >>> logger.info("User registered", extra={"telegram_id": 123456789})
        # Output: {"timestamp": "2025-10-30T12:00:00Z", "logger": "main",
        #          "levelname": "INFO", "message": "User registered",
        #          "service": "tracker_activity_bot", "telegram_id": 123456789}

        >>> # With sampling (production)
        >>> setup_logging(service_name="bot", debug_sample_rate=0.1)
        # Only 10% of DEBUG logs will be output, reducing volume
    """
    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(log_level.upper())

    # Clear any existing handlers to avoid duplicate logs
    logger.handlers = []

    # Create console handler (stdout for Docker log capture)
    handler = logging.StreamHandler(sys.stdout)

    # Add sampling filter if configured
    if debug_sample_rate is not None and debug_sample_rate < 1.0:
        sampling_filter = SamplingFilter(
            sample_rate=debug_sample_rate,
            sample_debug_only=True
        )
        handler.addFilter(sampling_filter)

    # Create JSON formatter with field renaming for consistency
    formatter = jsonlogger.JsonFormatter(
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
    log_extra = {"log_level": log_level}
    if debug_sample_rate is not None and debug_sample_rate < 1.0:
        log_extra["debug_sample_rate"] = debug_sample_rate

    logger.info(
        f"Structured JSON logging initialized for {service_name}",
        extra=log_extra
    )
