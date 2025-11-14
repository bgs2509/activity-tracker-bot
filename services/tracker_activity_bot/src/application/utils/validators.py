"""Common validation utilities for user input.

This module provides reusable validators to eliminate duplication
across handler modules and ensure consistent error messages.
"""

import logging

logger = logging.getLogger(__name__)


def validate_string_length(
    value: str,
    min_length: int | None = None,
    max_length: int | None = None,
    field_name_ru: str = "Значение",
    strip_whitespace: bool = False,
    allow_empty: bool = False
) -> str | None:
    """
    Validate that a string meets length constraints.

    Args:
        value: String to validate
        min_length: Minimum allowed length (inclusive), None to skip check
        max_length: Maximum allowed length (inclusive), None to skip check
        field_name_ru: Russian field name for error messages (e.g., "Название категории")
        strip_whitespace: Whether to strip whitespace before validation
        allow_empty: Whether empty strings are allowed (default: False)

    Returns:
        None if validation passes, error message string if validation fails

    Examples:
        >>> validate_string_length("test", 3, 10, "Название")
        None
        >>> validate_string_length("ab", 3, 10, "Название")
        '⚠️ Название должно содержать минимум 3 символа. Попробуй ещё раз:'
        >>> validate_string_length("a" * 20, 3, 10, "Название")
        '⚠️ Название должно содержать максимум 10 символов. Попробуй ещё раз:'
        >>> validate_string_length("", 3, 10, "Название", allow_empty=True)
        None
    """
    logger.debug(
        "validate_string_length started",
        extra={
            "value_length": len(value),
            "min_length": min_length,
            "max_length": max_length,
            "field_name_ru": field_name_ru,
            "strip_whitespace": strip_whitespace,
            "allow_empty": allow_empty
        }
    )

    original_value = value
    if strip_whitespace:
        value = value.strip()

    # Check empty value
    if not value and not allow_empty:
        if min_length is not None:
            error_msg = f"⚠️ {field_name_ru} должно содержать минимум {min_length} символа. Попробуй ещё раз."
        else:
            error_msg = f"⚠️ {field_name_ru} не может быть пустым. Попробуй ещё раз."
        logger.debug(
            "validation failed: empty value",
            extra={
                "original_value": original_value,
                "field_name_ru": field_name_ru,
                "reason": "empty_not_allowed",
                "error_message": error_msg
            }
        )
        return error_msg

    # Check minimum length
    if min_length is not None and len(value) < min_length:
        error_msg = f"⚠️ {field_name_ru} должно содержать минимум {min_length} символа. Попробуй ещё раз:"
        logger.debug(
            "validation failed: too short",
            extra={
                "value_length": len(value),
                "min_length": min_length,
                "field_name_ru": field_name_ru,
                "reason": "too_short",
                "error_message": error_msg
            }
        )
        return error_msg

    # Check maximum length
    if max_length is not None and len(value) > max_length:
        error_msg = f"⚠️ {field_name_ru} должно содержать максимум {max_length} символов. Попробуй ещё раз:"
        logger.debug(
            "validation failed: too long",
            extra={
                "value_length": len(value),
                "max_length": max_length,
                "field_name_ru": field_name_ru,
                "reason": "too_long",
                "error_message": error_msg
            }
        )
        return error_msg

    # Validation passed
    logger.debug(
        "validation passed",
        extra={
            "value_length": len(value),
            "min_length": min_length,
            "max_length": max_length,
            "field_name_ru": field_name_ru
        }
    )
    return None
