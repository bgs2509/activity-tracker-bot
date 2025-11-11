"""
Unit tests for time_parser utilities.

Tests time parsing functions that convert user input to datetime objects.
Critical for activity tracking - users input times in various formats.

Test Coverage:
    - parse_time_input(): Exact time, relative time, "now"
    - parse_duration(): Duration calculation from start time
    - Timezone handling: UTC conversion, user timezone
    - Error handling: Invalid formats, out of range values

Coverage Target: 100% of time_parser.py
Execution Time: < 0.3 seconds

Author: Testing Team
Date: 2025-11-07
"""

import pytest
from datetime import datetime, timedelta
import pytz

from src.application.utils.time_parser import (
    parse_time_input,
    parse_duration
)


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def moscow_tz():
    """
    Fixture: Moscow timezone.

    Returns:
        timezone: pytz timezone object for Europe/Moscow
    """
    return pytz.timezone("Europe/Moscow")


@pytest.fixture
def reference_time(moscow_tz):
    """
    Fixture: Fixed reference time for testing.

    Returns:
        datetime: 2025-11-07 14:30:00 Moscow time
    """
    return moscow_tz.localize(datetime(2025, 11, 7, 14, 30, 0))


# ============================================================================
# TEST SUITES
# ============================================================================

class TestParseTimeInputExactTime:
    """
    Test suite for parse_time_input() with exact time formats.

    Tests "HH:MM" and "HH-MM" patterns.
    """

    @pytest.mark.unit
    def test_parse_time_input_with_colon_format_returns_exact_time_today(
        self,
        reference_time,
        moscow_tz
    ):
        """
        Test parsing "HH:MM" format.

        GIVEN: Time string "10:30" (with colon)
        WHEN: parse_time_input() is called
        THEN: datetime for 10:30 today in user timezone is returned (as UTC)
        """
        # Act
        result = parse_time_input(
            "10:30",
            timezone="Europe/Moscow",
            reference_time=reference_time
        )

        # Assert: Exact time on reference date
        result_moscow = result.astimezone(moscow_tz)
        assert result_moscow.hour == 10
        assert result_moscow.minute == 30
        assert result_moscow.second == 0
        assert result_moscow.day == reference_time.day
        assert result_moscow.month == reference_time.month

        # UTC conversion
        assert result.tzinfo == pytz.UTC

    @pytest.mark.unit
    def test_parse_time_input_with_dash_format_returns_exact_time(
        self,
        reference_time,
        moscow_tz
    ):
        """
        Test parsing "HH-MM" format (alternative separator).

        GIVEN: Time string "14-45" (with dash)
        WHEN: parse_time_input() is called
        THEN: datetime for 14:45 today is returned
        """
        # Act
        result = parse_time_input(
            "14-45",
            timezone="Europe/Moscow",
            reference_time=reference_time
        )

        # Assert
        result_moscow = result.astimezone(moscow_tz)
        assert result_moscow.hour == 14
        assert result_moscow.minute == 45

    @pytest.mark.unit
    def test_parse_time_input_with_single_digit_hour(
        self,
        reference_time,
        moscow_tz
    ):
        """
        Test parsing "H:MM" format (single digit hour).

        GIVEN: Time string "9:15"
        WHEN: parse_time_input() is called
        THEN: datetime for 09:15 is returned
        """
        # Act
        result = parse_time_input(
            "9:15",
            timezone="Europe/Moscow",
            reference_time=reference_time
        )

        # Assert
        result_moscow = result.astimezone(moscow_tz)
        assert result_moscow.hour == 9
        assert result_moscow.minute == 15

    @pytest.mark.unit
    def test_parse_time_input_with_midnight_time(
        self,
        reference_time,
        moscow_tz
    ):
        """
        Test parsing "00:00" (midnight).

        GIVEN: Time string "00:00"
        WHEN: parse_time_input() is called
        THEN: datetime for midnight today is returned
        """
        # Act
        result = parse_time_input(
            "00:00",
            timezone="Europe/Moscow",
            reference_time=reference_time
        )

        # Assert
        result_moscow = result.astimezone(moscow_tz)
        assert result_moscow.hour == 0
        assert result_moscow.minute == 0

    @pytest.mark.unit
    def test_parse_time_input_with_end_of_day_time(
        self,
        reference_time,
        moscow_tz
    ):
        """
        Test parsing "23:59" (last minute of day).

        GIVEN: Time string "23:59"
        WHEN: parse_time_input() is called
        THEN: datetime for 23:59 is returned
        """
        # Act
        result = parse_time_input(
            "23:59",
            timezone="Europe/Moscow",
            reference_time=reference_time
        )

        # Assert
        result_moscow = result.astimezone(moscow_tz)
        assert result_moscow.hour == 23
        assert result_moscow.minute == 59

    @pytest.mark.unit
    def test_parse_time_input_with_invalid_hour_raises_error(
        self,
        reference_time
    ):
        """
        Test error handling for invalid hour.

        GIVEN: Time string "25:30" (hour > 23)
        WHEN: parse_time_input() is called
        THEN: ValueError is raised
        """
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid time format"):
            parse_time_input(
                "25:30",
                timezone="Europe/Moscow",
                reference_time=reference_time
            )

    @pytest.mark.unit
    def test_parse_time_input_with_invalid_minute_raises_error(
        self,
        reference_time
    ):
        """
        Test error handling for invalid minute.

        GIVEN: Time string "14:70" (minute > 59)
        WHEN: parse_time_input() is called
        THEN: ValueError is raised
        """
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid time format"):
            parse_time_input(
                "14:70",
                timezone="Europe/Moscow",
                reference_time=reference_time
            )


class TestParseTimeInputRelativeMinutes:
    """
    Test suite for parse_time_input() with relative minutes.

    Tests "Nм", "N", "Nmin" patterns (N minutes ago).
    """

    @pytest.mark.unit
    def test_parse_time_input_with_minutes_ago_cyrillic(
        self,
        reference_time,
        moscow_tz
    ):
        """
        Test parsing "Nм" format (minutes ago, Cyrillic).

        GIVEN: Time string "30м" (30 minutes ago)
        WHEN: parse_time_input() is called at 14:30
        THEN: datetime for 14:00 is returned
        """
        # Act
        result = parse_time_input(
            "30м",
            timezone="Europe/Moscow",
            reference_time=reference_time
        )

        # Assert: 30 minutes before reference time
        result_moscow = result.astimezone(moscow_tz)
        expected = reference_time - timedelta(minutes=30)
        assert result_moscow.hour == expected.hour
        assert result_moscow.minute == expected.minute

    @pytest.mark.unit
    def test_parse_time_input_with_minutes_ago_latin(
        self,
        reference_time,
        moscow_tz
    ):
        """
        Test parsing "Nmin" format (minutes ago, Latin).

        GIVEN: Time string "45min"
        WHEN: parse_time_input() is called at 14:30
        THEN: datetime for 13:45 is returned
        """
        # Act
        result = parse_time_input(
            "45min",
            timezone="Europe/Moscow",
            reference_time=reference_time
        )

        # Assert
        result_moscow = result.astimezone(moscow_tz)
        expected = reference_time - timedelta(minutes=45)
        assert result_moscow.hour == expected.hour
        assert result_moscow.minute == expected.minute

    @pytest.mark.unit
    def test_parse_time_input_with_plain_number_interpreted_as_minutes(
        self,
        reference_time,
        moscow_tz
    ):
        """
        Test parsing "N" format (plain number = minutes ago).

        GIVEN: Time string "15" (no unit)
        WHEN: parse_time_input() is called at 14:30
        THEN: datetime for 14:15 is returned (15 minutes ago)
        """
        # Act
        result = parse_time_input(
            "15",
            timezone="Europe/Moscow",
            reference_time=reference_time
        )

        # Assert
        result_moscow = result.astimezone(moscow_tz)
        expected = reference_time - timedelta(minutes=15)
        assert result_moscow.hour == expected.hour
        assert result_moscow.minute == expected.minute

    @pytest.mark.unit
    def test_parse_time_input_with_large_minutes_value(
        self,
        reference_time,
        moscow_tz
    ):
        """
        Test parsing large minute values (>60).

        GIVEN: Time string "90м" (90 minutes ago)
        WHEN: parse_time_input() is called at 14:30
        THEN: datetime for 13:00 is returned
        """
        # Act
        result = parse_time_input(
            "90м",
            timezone="Europe/Moscow",
            reference_time=reference_time
        )

        # Assert
        result_moscow = result.astimezone(moscow_tz)
        expected = reference_time - timedelta(minutes=90)
        assert result_moscow.hour == expected.hour
        assert result_moscow.minute == expected.minute


class TestParseTimeInputRelativeHours:
    """
    Test suite for parse_time_input() with relative hours.

    Tests "Nч", "Nh", "Nчас" patterns (N hours ago).
    """

    @pytest.mark.unit
    def test_parse_time_input_with_hours_ago_cyrillic_short(
        self,
        reference_time,
        moscow_tz
    ):
        """
        Test parsing "Nч" format (hours ago, Cyrillic short).

        GIVEN: Time string "2ч" (2 hours ago)
        WHEN: parse_time_input() is called at 14:30
        THEN: datetime for 12:30 is returned
        """
        # Act
        result = parse_time_input(
            "2ч",
            timezone="Europe/Moscow",
            reference_time=reference_time
        )

        # Assert
        result_moscow = result.astimezone(moscow_tz)
        expected = reference_time - timedelta(hours=2)
        assert result_moscow.hour == expected.hour
        assert result_moscow.minute == expected.minute

    @pytest.mark.unit
    def test_parse_time_input_with_hours_ago_latin(
        self,
        reference_time,
        moscow_tz
    ):
        """
        Test parsing "Nh" format (hours ago, Latin).

        GIVEN: Time string "3h"
        WHEN: parse_time_input() is called at 14:30
        THEN: datetime for 11:30 is returned
        """
        # Act
        result = parse_time_input(
            "3h",
            timezone="Europe/Moscow",
            reference_time=reference_time
        )

        # Assert
        result_moscow = result.astimezone(moscow_tz)
        expected = reference_time - timedelta(hours=3)
        assert result_moscow.hour == expected.hour

    @pytest.mark.unit
    def test_parse_time_input_with_hours_ago_cyrillic_long(
        self,
        reference_time,
        moscow_tz
    ):
        """
        Test parsing "Nчас" format (hours ago, Cyrillic long).

        GIVEN: Time string "1час"
        WHEN: parse_time_input() is called at 14:30
        THEN: datetime for 13:30 is returned
        """
        # Act
        result = parse_time_input(
            "1час",
            timezone="Europe/Moscow",
            reference_time=reference_time
        )

        # Assert
        result_moscow = result.astimezone(moscow_tz)
        expected = reference_time - timedelta(hours=1)
        assert result_moscow.hour == expected.hour


class TestParseTimeInputNowKeyword:
    """
    Test suite for parse_time_input() with "now" keywords.

    Tests "сейчас", "now", "0" patterns (current time).
    """

    @pytest.mark.unit
    def test_parse_time_input_with_cyrillic_now(
        self,
        reference_time
    ):
        """
        Test parsing "сейчас" (now in Russian).

        GIVEN: Time string "сейчас"
        WHEN: parse_time_input() is called
        THEN: Reference time is returned
        """
        # Act
        result = parse_time_input(
            "сейчас",
            timezone="Europe/Moscow",
            reference_time=reference_time
        )

        # Assert: Same as reference time
        assert result.astimezone(pytz.timezone("Europe/Moscow")) == reference_time

    @pytest.mark.unit
    def test_parse_time_input_with_latin_now(
        self,
        reference_time
    ):
        """
        Test parsing "now" (English).

        GIVEN: Time string "now"
        WHEN: parse_time_input() is called
        THEN: Reference time is returned
        """
        # Act
        result = parse_time_input(
            "now",
            timezone="Europe/Moscow",
            reference_time=reference_time
        )

        # Assert
        assert result.astimezone(pytz.timezone("Europe/Moscow")) == reference_time

    @pytest.mark.unit
    def test_parse_time_input_with_zero(
        self,
        reference_time
    ):
        """
        Test parsing "0" (zero = now).

        GIVEN: Time string "0"
        WHEN: parse_time_input() is called
        THEN: Reference time is returned
        """
        # Act
        result = parse_time_input(
            "0",
            timezone="Europe/Moscow",
            reference_time=reference_time
        )

        # Assert
        assert result.astimezone(pytz.timezone("Europe/Moscow")) == reference_time


class TestParseTimeInputErrorHandling:
    """
    Test suite for parse_time_input() error handling.
    """

    @pytest.mark.unit
    def test_parse_time_input_with_invalid_format_raises_error(
        self,
        reference_time
    ):
        """
        Test error for unrecognized format.

        GIVEN: Time string "abc123" (invalid)
        WHEN: parse_time_input() is called
        THEN: ValueError is raised
        """
        # Act & Assert
        with pytest.raises(ValueError, match="Cannot parse time format"):
            parse_time_input(
                "abc123",
                timezone="Europe/Moscow",
                reference_time=reference_time
            )

    @pytest.mark.unit
    def test_parse_time_input_with_empty_string_raises_error(
        self,
        reference_time
    ):
        """
        Test error for empty input.

        GIVEN: Empty time string
        WHEN: parse_time_input() is called
        THEN: ValueError is raised
        """
        # Act & Assert
        with pytest.raises(ValueError):
            parse_time_input(
                "",
                timezone="Europe/Moscow",
                reference_time=reference_time
            )

    @pytest.mark.unit
    def test_parse_time_input_trims_whitespace(
        self,
        reference_time,
        moscow_tz
    ):
        """
        Test whitespace trimming.

        GIVEN: Time string "  10:30  " (with spaces)
        WHEN: parse_time_input() is called
        THEN: Spaces are trimmed, time parsed correctly
        """
        # Act
        result = parse_time_input(
            "  10:30  ",
            timezone="Europe/Moscow",
            reference_time=reference_time
        )

        # Assert
        result_moscow = result.astimezone(moscow_tz)
        assert result_moscow.hour == 10
        assert result_moscow.minute == 30

    @pytest.mark.unit
    def test_parse_time_input_is_case_insensitive(
        self,
        reference_time
    ):
        """
        Test case insensitivity.

        GIVEN: Time string "NOW" (uppercase)
        WHEN: parse_time_input() is called
        THEN: Parsed correctly as "now"
        """
        # Act
        result = parse_time_input(
            "NOW",
            timezone="Europe/Moscow",
            reference_time=reference_time
        )

        # Assert: Parsed as "now"
        assert result.astimezone(pytz.timezone("Europe/Moscow")) == reference_time


class TestParseDuration:
    """
    Test suite for parse_duration() function.

    Calculates end time from start time and duration input.
    """

    @pytest.mark.unit
    def test_parse_duration_with_exact_end_time(
        self,
        moscow_tz
    ):
        """
        Test duration as exact end time.

        GIVEN: start_time=10:00, duration="12:30"
        WHEN: parse_duration() is called
        THEN: end_time=12:30 is returned
        """
        # Arrange
        start_time = datetime(2025, 11, 7, 10, 0, 0, tzinfo=pytz.UTC)

        # Act
        result = parse_duration(
            "12:30",
            start_time=start_time,
            timezone="Europe/Moscow"
        )

        # Assert
        result_moscow = result.astimezone(moscow_tz)
        assert result_moscow.hour == 12
        assert result_moscow.minute == 30

    @pytest.mark.unit
    def test_parse_duration_with_minutes_duration(
        self,
        moscow_tz
    ):
        """
        Test duration in minutes.

        GIVEN: start_time=10:00, duration="30м" (30 minutes)
        WHEN: parse_duration() is called
        THEN: end_time=10:30 is returned
        """
        # Arrange
        start_time_moscow = moscow_tz.localize(datetime(2025, 11, 7, 10, 0, 0))
        start_time_utc = start_time_moscow.astimezone(pytz.UTC)

        # Act
        result = parse_duration(
            "30м",
            start_time=start_time_utc,
            timezone="Europe/Moscow"
        )

        # Assert
        result_moscow = result.astimezone(moscow_tz)
        expected = start_time_moscow + timedelta(minutes=30)
        assert result_moscow.hour == expected.hour
        assert result_moscow.minute == expected.minute

    @pytest.mark.unit
    def test_parse_duration_with_hours_duration(
        self,
        moscow_tz
    ):
        """
        Test duration in hours.

        GIVEN: start_time=10:00, duration="2ч" (2 hours)
        WHEN: parse_duration() is called
        THEN: end_time=12:00 is returned
        """
        # Arrange
        start_time_moscow = moscow_tz.localize(datetime(2025, 11, 7, 10, 0, 0))
        start_time_utc = start_time_moscow.astimezone(pytz.UTC)

        # Act
        result = parse_duration(
            "2ч",
            start_time=start_time_utc,
            timezone="Europe/Moscow"
        )

        # Assert
        result_moscow = result.astimezone(moscow_tz)
        expected = start_time_moscow + timedelta(hours=2)
        assert result_moscow.hour == expected.hour

    @pytest.mark.unit
    def test_parse_duration_with_now_keyword(
        self,
        moscow_tz
    ):
        """
        Test duration="сейчас" (current time).

        GIVEN: start_time and duration="сейчас"
        WHEN: parse_duration() is called
        THEN: Current time is returned (not start_time + duration)
        """
        # Arrange
        start_time = datetime(2025, 11, 7, 10, 0, 0, tzinfo=pytz.UTC)

        # Act
        result = parse_duration(
            "сейчас",
            start_time=start_time,
            timezone="Europe/Moscow"
        )

        # Assert: Returns current time (not calculated from start_time)
        # Just verify it's a valid datetime in UTC
        assert result.tzinfo == pytz.UTC

    @pytest.mark.unit
    def test_parse_duration_with_invalid_format_raises_error(self):
        """
        Test error for invalid duration format.

        GIVEN: Invalid duration string
        WHEN: parse_duration() is called
        THEN: ValueError is raised
        """
        # Arrange
        start_time = datetime(2025, 11, 7, 10, 0, 0, tzinfo=pytz.UTC)

        # Act & Assert
        with pytest.raises(ValueError, match="Cannot parse duration format"):
            parse_duration(
                "invalid",
                start_time=start_time,
                timezone="Europe/Moscow"
            )
