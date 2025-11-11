"""Common validation utilities for user input.

This module provides reusable validators to eliminate duplication
across handler modules and ensure consistent error messages.
"""


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
    if strip_whitespace:
        value = value.strip()

    if not value and not allow_empty:
        if min_length is not None:
            return f"⚠️ {field_name_ru} должно содержать минимум {min_length} символа. Попробуй ещё раз."
        return f"⚠️ {field_name_ru} не может быть пустым. Попробуй ещё раз."

    if min_length is not None and len(value) < min_length:
        return f"⚠️ {field_name_ru} должно содержать минимум {min_length} символа. Попробуй ещё раз:"

    if max_length is not None and len(value) > max_length:
        return f"⚠️ {field_name_ru} должно содержать максимум {max_length} символов. Попробуй ещё раз:"

    return None
