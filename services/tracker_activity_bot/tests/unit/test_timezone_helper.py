"""
Unit tests for timezone utilities.

Tests is_in_quiet_hours, is_weekend, and get_end_of_quiet_hours.
These utilities are critical for poll scheduling logic.
"""
import pytest
from datetime import datetime, time, timedelta
import pytz

from src.application.utils.timezone_helper import (
    is_in_quiet_hours,
    is_weekend,
    get_end_of_quiet_hours,
)


class TestIsInQuietHours:
    """Test is_in_quiet_hours for quiet hours detection."""

    @pytest.mark.unit
    def test_no_quiet_hours_configured(self):
        """Test when quiet hours are not configured."""
        current_time = datetime(2025, 11, 5, 14, 0, 0, tzinfo=pytz.UTC)

        result = is_in_quiet_hours(current_time, None, None, "Europe/Moscow")

        assert result is False

    @pytest.mark.unit
    def test_quiet_start_is_none(self):
        """Test when only quiet_end is set."""
        current_time = datetime(2025, 11, 5, 14, 0, 0, tzinfo=pytz.UTC)
        quiet_end = time(7, 0)

        result = is_in_quiet_hours(current_time, None, quiet_end, "Europe/Moscow")

        assert result is False

    @pytest.mark.unit
    def test_quiet_end_is_none(self):
        """Test when only quiet_start is set."""
        current_time = datetime(2025, 11, 5, 14, 0, 0, tzinfo=pytz.UTC)
        quiet_start = time(23, 0)

        result = is_in_quiet_hours(current_time, quiet_start, None, "Europe/Moscow")

        assert result is False

    @pytest.mark.unit
    def test_in_quiet_hours_no_midnight_crossing(self):
        """Test time within quiet hours (09:00-17:00)."""
        # 11:00 UTC = 14:00 Moscow
        current_time = datetime(2025, 11, 5, 11, 0, 0, tzinfo=pytz.UTC)
        quiet_start = time(9, 0)   # 09:00 Moscow
        quiet_end = time(17, 0)     # 17:00 Moscow

        result = is_in_quiet_hours(current_time, quiet_start, quiet_end, "Europe/Moscow")

        assert result is True

    @pytest.mark.unit
    def test_before_quiet_hours_no_midnight_crossing(self):
        """Test time before quiet hours start."""
        # 05:00 UTC = 08:00 Moscow
        current_time = datetime(2025, 11, 5, 5, 0, 0, tzinfo=pytz.UTC)
        quiet_start = time(9, 0)
        quiet_end = time(17, 0)

        result = is_in_quiet_hours(current_time, quiet_start, quiet_end, "Europe/Moscow")

        assert result is False

    @pytest.mark.unit
    def test_after_quiet_hours_no_midnight_crossing(self):
        """Test time after quiet hours end."""
        # 15:00 UTC = 18:00 Moscow
        current_time = datetime(2025, 11, 5, 15, 0, 0, tzinfo=pytz.UTC)
        quiet_start = time(9, 0)
        quiet_end = time(17, 0)

        result = is_in_quiet_hours(current_time, quiet_start, quiet_end, "Europe/Moscow")

        assert result is False

    @pytest.mark.unit
    def test_exactly_at_quiet_start_no_midnight(self):
        """Test time exactly at quiet hours start (inclusive)."""
        # 06:00 UTC = 09:00 Moscow
        current_time = datetime(2025, 11, 5, 6, 0, 0, tzinfo=pytz.UTC)
        quiet_start = time(9, 0)
        quiet_end = time(17, 0)

        result = is_in_quiet_hours(current_time, quiet_start, quiet_end, "Europe/Moscow")

        assert result is True

    @pytest.mark.unit
    def test_exactly_at_quiet_end_no_midnight(self):
        """Test time exactly at quiet hours end (exclusive)."""
        # 14:00 UTC = 17:00 Moscow
        current_time = datetime(2025, 11, 5, 14, 0, 0, tzinfo=pytz.UTC)
        quiet_start = time(9, 0)
        quiet_end = time(17, 0)

        result = is_in_quiet_hours(current_time, quiet_start, quiet_end, "Europe/Moscow")

        # Should be exclusive (not in quiet hours at exact end time)
        assert result is False

    @pytest.mark.unit
    def test_in_quiet_hours_midnight_crossing(self):
        """Test quiet hours crossing midnight (23:00-07:00) - during night."""
        # 01:00 UTC = 04:00 Moscow (should be in quiet hours)
        current_time = datetime(2025, 11, 5, 1, 0, 0, tzinfo=pytz.UTC)
        quiet_start = time(23, 0)  # 23:00 Moscow
        quiet_end = time(7, 0)      # 07:00 Moscow next day

        result = is_in_quiet_hours(current_time, quiet_start, quiet_end, "Europe/Moscow")

        assert result is True

    @pytest.mark.unit
    def test_in_quiet_hours_midnight_crossing_late_evening(self):
        """Test quiet hours crossing midnight - late evening part."""
        # 21:00 UTC = 00:00 Moscow (should be in quiet hours)
        current_time = datetime(2025, 11, 5, 21, 0, 0, tzinfo=pytz.UTC)
        quiet_start = time(23, 0)
        quiet_end = time(7, 0)

        result = is_in_quiet_hours(current_time, quiet_start, quiet_end, "Europe/Moscow")

        # 00:00 < 07:00, so should be in quiet hours
        assert result is True

    @pytest.mark.unit
    def test_in_quiet_hours_midnight_crossing_before_start(self):
        """Test time before quiet hours start when crossing midnight."""
        # 18:00 UTC = 21:00 Moscow (before 23:00 start)
        current_time = datetime(2025, 11, 5, 18, 0, 0, tzinfo=pytz.UTC)
        quiet_start = time(23, 0)
        quiet_end = time(7, 0)

        result = is_in_quiet_hours(current_time, quiet_start, quiet_end, "Europe/Moscow")

        assert result is False

    @pytest.mark.unit
    def test_in_quiet_hours_midnight_crossing_after_end(self):
        """Test time after quiet hours end when crossing midnight."""
        # 05:00 UTC = 08:00 Moscow (after 07:00 end)
        current_time = datetime(2025, 11, 5, 5, 0, 0, tzinfo=pytz.UTC)
        quiet_start = time(23, 0)
        quiet_end = time(7, 0)

        result = is_in_quiet_hours(current_time, quiet_start, quiet_end, "Europe/Moscow")

        assert result is False

    @pytest.mark.unit
    def test_exactly_at_quiet_start_midnight_crossing(self):
        """Test exactly at quiet start when crossing midnight."""
        # 20:00 UTC = 23:00 Moscow
        current_time = datetime(2025, 11, 5, 20, 0, 0, tzinfo=pytz.UTC)
        quiet_start = time(23, 0)
        quiet_end = time(7, 0)

        result = is_in_quiet_hours(current_time, quiet_start, quiet_end, "Europe/Moscow")

        assert result is True

    @pytest.mark.unit
    def test_exactly_at_quiet_end_midnight_crossing(self):
        """Test exactly at quiet end when crossing midnight."""
        # 04:00 UTC = 07:00 Moscow
        current_time = datetime(2025, 11, 5, 4, 0, 0, tzinfo=pytz.UTC)
        quiet_start = time(23, 0)
        quiet_end = time(7, 0)

        result = is_in_quiet_hours(current_time, quiet_start, quiet_end, "Europe/Moscow")

        # Should be exclusive
        assert result is False


class TestIsWeekend:
    """Test is_weekend for weekend detection."""

    @pytest.mark.unit
    def test_monday_is_not_weekend(self):
        """Test Monday (weekday 0) is not weekend."""
        # November 3, 2025 is Monday
        current_time = datetime(2025, 11, 3, 12, 0, 0, tzinfo=pytz.UTC)

        result = is_weekend(current_time, "Europe/Moscow")

        assert result is False

    @pytest.mark.unit
    def test_friday_is_not_weekend(self):
        """Test Friday (weekday 4) is not weekend."""
        # November 7, 2025 is Friday
        current_time = datetime(2025, 11, 7, 12, 0, 0, tzinfo=pytz.UTC)

        result = is_weekend(current_time, "Europe/Moscow")

        assert result is False

    @pytest.mark.unit
    def test_saturday_is_weekend(self):
        """Test Saturday (weekday 5) is weekend."""
        # November 8, 2025 is Saturday
        current_time = datetime(2025, 11, 8, 12, 0, 0, tzinfo=pytz.UTC)

        result = is_weekend(current_time, "Europe/Moscow")

        assert result is True

    @pytest.mark.unit
    def test_sunday_is_weekend(self):
        """Test Sunday (weekday 6) is weekend."""
        # November 9, 2025 is Sunday
        current_time = datetime(2025, 11, 9, 12, 0, 0, tzinfo=pytz.UTC)

        result = is_weekend(current_time, "Europe/Moscow")

        assert result is True

    @pytest.mark.unit
    def test_weekend_with_timezone_conversion(self):
        """Test weekend detection with timezone affecting date."""
        # Friday 23:00 UTC = Saturday 02:00 Moscow (should be weekend)
        current_time = datetime(2025, 11, 7, 23, 0, 0, tzinfo=pytz.UTC)

        result = is_weekend(current_time, "Europe/Moscow")

        assert result is True

    @pytest.mark.unit
    def test_weekday_with_timezone_conversion(self):
        """Test weekday with timezone conversion."""
        # Sunday 22:00 UTC = Monday 01:00 Moscow (should NOT be weekend)
        current_time = datetime(2025, 11, 9, 22, 0, 0, tzinfo=pytz.UTC)

        result = is_weekend(current_time, "Europe/Moscow")

        assert result is False


class TestGetEndOfQuietHours:
    """Test get_end_of_quiet_hours for scheduling."""

    @pytest.mark.unit
    def test_quiet_end_in_future_today(self):
        """Test when quiet end is later today."""
        quiet_end = time(17, 0)  # 17:00
        timezone_str = "Europe/Moscow"

        # Mock would be needed for datetime.now, but testing logic
        result = get_end_of_quiet_hours(quiet_end, timezone_str)

        # Should return datetime with hour=17, minute=0
        tz = pytz.timezone(timezone_str)
        result_local = result.astimezone(tz)
        assert result_local.hour == 17
        assert result_local.minute == 0
        assert result.tzinfo == pytz.UTC

    @pytest.mark.unit
    def test_quiet_end_returns_utc(self):
        """Test result is in UTC timezone."""
        quiet_end = time(7, 0)

        result = get_end_of_quiet_hours(quiet_end, "Europe/Moscow")

        assert result.tzinfo == pytz.UTC

    @pytest.mark.unit
    def test_quiet_end_with_minutes(self):
        """Test quiet end with non-zero minutes."""
        quiet_end = time(7, 30)  # 07:30
        timezone_str = "Europe/Moscow"

        result = get_end_of_quiet_hours(quiet_end, timezone_str)

        tz = pytz.timezone(timezone_str)
        result_local = result.astimezone(tz)
        assert result_local.hour == 7
        assert result_local.minute == 30

    @pytest.mark.unit
    def test_quiet_end_midnight(self):
        """Test quiet end at midnight."""
        quiet_end = time(0, 0)  # 00:00
        timezone_str = "Europe/Moscow"

        result = get_end_of_quiet_hours(quiet_end, timezone_str)

        tz = pytz.timezone(timezone_str)
        result_local = result.astimezone(tz)
        assert result_local.hour == 0
        assert result_local.minute == 0


# Total: 29 tests
