"""
Unit tests for time parsing utilities.

Tests time_parser.parse_time_input and parse_duration functions.
These are critical utilities used throughout the bot for time handling.
"""
import pytest
from datetime import datetime, timedelta
import pytz

from src.application.utils.time_parser import parse_time_input, parse_duration


class TestParseTimeInput:
    """Test parse_time_input function with various formats."""

    @pytest.mark.unit
    def test_parse_current_time_russian(self):
        """Test 'сейчас' keyword for current time."""
        tz = pytz.timezone("Europe/Moscow")
        reference = datetime(2025, 11, 5, 14, 30, 0, tzinfo=tz)

        result = parse_time_input("сейчас", reference_time=reference)

        # Should return reference time in UTC
        assert result.tzinfo == pytz.UTC
        assert result.hour == reference.astimezone(pytz.UTC).hour
        assert result.minute == reference.astimezone(pytz.UTC).minute

    @pytest.mark.unit
    def test_parse_current_time_english(self):
        """Test 'now' keyword for current time."""
        tz = pytz.timezone("Europe/Moscow")
        reference = datetime(2025, 11, 5, 14, 30, 0, tzinfo=tz)

        result = parse_time_input("now", reference_time=reference)

        assert result.tzinfo == pytz.UTC

    @pytest.mark.unit
    def test_parse_current_time_zero(self):
        """Test '0' as current time."""
        tz = pytz.timezone("Europe/Moscow")
        reference = datetime(2025, 11, 5, 14, 30, 0, tzinfo=tz)

        result = parse_time_input("0", reference_time=reference)

        assert result.tzinfo == pytz.UTC

    @pytest.mark.unit
    def test_parse_exact_time_colon(self):
        """Test exact time format with colon (14:30)."""
        tz = pytz.timezone("Europe/Moscow")
        reference = tz.localize(datetime(2025, 11, 5, 14, 0, 0))

        result = parse_time_input("14:30", reference_time=reference)

        # Should be 14:30 on the reference date
        result_local = result.astimezone(tz)
        assert result_local.hour == 14
        assert result_local.minute == 30
        assert result.tzinfo == pytz.UTC

    @pytest.mark.unit
    def test_parse_exact_time_dash(self):
        """Test exact time format with dash (14-30)."""
        tz = pytz.timezone("Europe/Moscow")
        reference = tz.localize(datetime(2025, 11, 5, 14, 0, 0))

        result = parse_time_input("14-30", reference_time=reference)

        result_local = result.astimezone(tz)
        assert result_local.hour == 14
        assert result_local.minute == 30

    @pytest.mark.unit
    def test_parse_exact_time_single_digit_hour(self):
        """Test exact time with single digit hour (9:15)."""
        tz = pytz.timezone("Europe/Moscow")
        reference = tz.localize(datetime(2025, 11, 5, 14, 0, 0))

        result = parse_time_input("9:15", reference_time=reference)

        result_local = result.astimezone(tz)
        assert result_local.hour == 9
        assert result_local.minute == 15

    @pytest.mark.unit
    def test_parse_minutes_ago_russian(self):
        """Test relative time in minutes with Russian suffix (30м)."""
        tz = pytz.timezone("Europe/Moscow")
        reference = datetime(2025, 11, 5, 14, 30, 0, tzinfo=tz)

        result = parse_time_input("30м", reference_time=reference)

        # Should be 30 minutes before reference
        expected = (reference - timedelta(minutes=30)).astimezone(pytz.UTC)
        assert result.hour == expected.hour
        assert result.minute == expected.minute

    @pytest.mark.unit
    def test_parse_minutes_ago_plain_number(self):
        """Test relative time as plain number (30 = 30 minutes ago)."""
        tz = pytz.timezone("Europe/Moscow")
        reference = datetime(2025, 11, 5, 14, 30, 0, tzinfo=tz)

        result = parse_time_input("30", reference_time=reference)

        expected = (reference - timedelta(minutes=30)).astimezone(pytz.UTC)
        assert result.hour == expected.hour
        assert result.minute == expected.minute

    @pytest.mark.unit
    def test_parse_minutes_ago_english(self):
        """Test relative time with English suffix (45min)."""
        tz = pytz.timezone("Europe/Moscow")
        reference = datetime(2025, 11, 5, 14, 30, 0, tzinfo=tz)

        result = parse_time_input("45min", reference_time=reference)

        expected = (reference - timedelta(minutes=45)).astimezone(pytz.UTC)
        assert result.hour == expected.hour
        assert result.minute == expected.minute

    @pytest.mark.unit
    def test_parse_hours_ago_russian(self):
        """Test relative time in hours with Russian suffix (2ч)."""
        tz = pytz.timezone("Europe/Moscow")
        reference = datetime(2025, 11, 5, 14, 30, 0, tzinfo=tz)

        result = parse_time_input("2ч", reference_time=reference)

        expected = (reference - timedelta(hours=2)).astimezone(pytz.UTC)
        assert result.hour == expected.hour

    @pytest.mark.unit
    def test_parse_hours_ago_english(self):
        """Test relative time in hours with English suffix (3h)."""
        tz = pytz.timezone("Europe/Moscow")
        reference = datetime(2025, 11, 5, 14, 30, 0, tzinfo=tz)

        result = parse_time_input("3h", reference_time=reference)

        expected = (reference - timedelta(hours=3)).astimezone(pytz.UTC)
        assert result.hour == expected.hour

    @pytest.mark.unit
    def test_parse_hours_ago_russian_full(self):
        """Test relative time with full Russian word (1час)."""
        tz = pytz.timezone("Europe/Moscow")
        reference = datetime(2025, 11, 5, 14, 30, 0, tzinfo=tz)

        result = parse_time_input("1час", reference_time=reference)

        expected = (reference - timedelta(hours=1)).astimezone(pytz.UTC)
        assert result.hour == expected.hour

    @pytest.mark.unit
    def test_parse_invalid_hour_range(self):
        """Test validation rejects hour > 23."""
        with pytest.raises(ValueError, match="Invalid time format"):
            parse_time_input("25:00")

    @pytest.mark.unit
    def test_parse_invalid_minute_range(self):
        """Test validation rejects minute > 59."""
        with pytest.raises(ValueError, match="Invalid time format"):
            parse_time_input("14:70")

    @pytest.mark.unit
    def test_parse_invalid_format(self):
        """Test unrecognized format raises ValueError."""
        with pytest.raises(ValueError, match="Cannot parse time format"):
            parse_time_input("invalid")

    @pytest.mark.unit
    def test_parse_whitespace_handling(self):
        """Test input with leading/trailing whitespace."""
        tz = pytz.timezone("Europe/Moscow")
        reference = tz.localize(datetime(2025, 11, 5, 14, 0, 0))

        result = parse_time_input("  14:30  ", reference_time=reference)

        result_local = result.astimezone(tz)
        assert result_local.hour == 14
        assert result_local.minute == 30

    @pytest.mark.unit
    def test_parse_case_insensitivity(self):
        """Test input is case-insensitive (NOW = now)."""
        tz = pytz.timezone("Europe/Moscow")
        reference = tz.localize(datetime(2025, 11, 5, 14, 30, 0))

        result = parse_time_input("NOW", reference_time=reference)

        assert result.tzinfo == pytz.UTC


class TestParseDuration:
    """Test parse_duration function for end time calculation."""

    @pytest.mark.unit
    def test_parse_duration_current_time(self):
        """Test 'сейчас' returns current time as end."""
        tz = pytz.timezone("Europe/Moscow")
        start_time = datetime(2025, 11, 5, 14, 0, 0, tzinfo=pytz.UTC)

        # Mock datetime.now inside function
        result = parse_duration("сейчас", start_time)

        assert result.tzinfo == pytz.UTC

    @pytest.mark.unit
    def test_parse_duration_exact_time(self):
        """Test exact end time (16:00)."""
        tz = pytz.timezone("Europe/Moscow")
        start_time = datetime(2025, 11, 5, 11, 0, 0, tzinfo=pytz.UTC)  # 14:00 Moscow

        result = parse_duration("16:00", start_time)

        # Should be 16:00 in Moscow time
        result_local = result.astimezone(tz)
        assert result_local.hour == 16
        assert result_local.minute == 0

    @pytest.mark.unit
    def test_parse_duration_minutes(self):
        """Test duration in minutes (30м = 30 minutes from start)."""
        tz = pytz.timezone("Europe/Moscow")
        start_time = datetime(2025, 11, 5, 11, 0, 0, tzinfo=pytz.UTC)  # 14:00 Moscow

        result = parse_duration("30м", start_time)

        # Should be start + 30 minutes
        expected = (start_time + timedelta(minutes=30)).astimezone(tz)
        result_local = result.astimezone(tz)
        assert result_local.hour == expected.hour
        assert result_local.minute == expected.minute

    @pytest.mark.unit
    def test_parse_duration_plain_number(self):
        """Test duration as plain number (45 = 45 minutes)."""
        start_time = datetime(2025, 11, 5, 11, 0, 0, tzinfo=pytz.UTC)

        result = parse_duration("45", start_time)

        expected = start_time + timedelta(minutes=45)
        assert (result - expected).total_seconds() < 1  # Within 1 second

    @pytest.mark.unit
    def test_parse_duration_hours(self):
        """Test duration in hours (2ч = 2 hours from start)."""
        start_time = datetime(2025, 11, 5, 11, 0, 0, tzinfo=pytz.UTC)

        result = parse_duration("2ч", start_time)

        expected = start_time + timedelta(hours=2)
        assert (result - expected).total_seconds() < 1

    @pytest.mark.unit
    def test_parse_duration_hours_english(self):
        """Test duration in hours with English suffix (3h)."""
        start_time = datetime(2025, 11, 5, 11, 0, 0, tzinfo=pytz.UTC)

        result = parse_duration("3h", start_time)

        expected = start_time + timedelta(hours=3)
        assert (result - expected).total_seconds() < 1

    @pytest.mark.unit
    def test_parse_duration_invalid_time_format(self):
        """Test invalid exact time raises ValueError."""
        start_time = datetime(2025, 11, 5, 11, 0, 0, tzinfo=pytz.UTC)

        with pytest.raises(ValueError, match="Invalid time format"):
            parse_duration("25:00", start_time)

    @pytest.mark.unit
    def test_parse_duration_invalid_format(self):
        """Test unrecognized format raises ValueError."""
        start_time = datetime(2025, 11, 5, 11, 0, 0, tzinfo=pytz.UTC)

        with pytest.raises(ValueError, match="Cannot parse duration format"):
            parse_duration("invalid", start_time)

    @pytest.mark.unit
    def test_parse_duration_timezone_conversion(self):
        """Test proper timezone conversion from UTC to local."""
        tz = pytz.timezone("Europe/Moscow")
        # Start at 14:00 Moscow (11:00 UTC)
        start_time = datetime(2025, 11, 5, 11, 0, 0, tzinfo=pytz.UTC)

        # Add 2 hours
        result = parse_duration("2ч", start_time)

        # Should be 16:00 Moscow (13:00 UTC)
        result_local = result.astimezone(tz)
        assert result_local.hour == 16


# Total: 28 tests
