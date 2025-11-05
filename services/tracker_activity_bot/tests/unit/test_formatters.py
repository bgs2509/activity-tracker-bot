"""
Unit tests for formatting utilities.

Tests formatters.py functions for duration, time, date, activity list,
and hashtag extraction. These utilities format user-facing output.
"""
import pytest
from datetime import datetime
import pytz

from src.application.utils.formatters import (
    format_duration,
    format_time,
    format_date,
    format_activity_list,
    extract_tags,
)


class TestFormatDuration:
    """Test format_duration for human-readable duration strings."""

    @pytest.mark.unit
    def test_format_duration_minutes_only(self):
        """Test duration < 60 minutes shows minutes only."""
        assert format_duration(30) == "30м"
        assert format_duration(45) == "45м"
        assert format_duration(1) == "1м"

    @pytest.mark.unit
    def test_format_duration_exactly_one_hour(self):
        """Test exactly 60 minutes shows as 1ч."""
        assert format_duration(60) == "1ч"

    @pytest.mark.unit
    def test_format_duration_exactly_two_hours(self):
        """Test exactly 120 minutes shows as 2ч."""
        assert format_duration(120) == "2ч"

    @pytest.mark.unit
    def test_format_duration_hours_and_minutes(self):
        """Test duration with both hours and minutes."""
        assert format_duration(90) == "1ч 30м"
        assert format_duration(150) == "2ч 30м"
        assert format_duration(125) == "2ч 5м"

    @pytest.mark.unit
    def test_format_duration_large_value(self):
        """Test large duration values."""
        assert format_duration(480) == "8ч"
        assert format_duration(500) == "8ч 20м"


class TestFormatTime:
    """Test format_time for HH:MM formatting."""

    @pytest.mark.unit
    def test_format_time_utc_to_moscow(self):
        """Test UTC datetime converts to Moscow timezone."""
        dt = datetime(2025, 11, 5, 11, 30, 0, tzinfo=pytz.UTC)  # 14:30 Moscow
        result = format_time(dt, timezone="Europe/Moscow")
        assert result == "14:30"

    @pytest.mark.unit
    def test_format_time_midnight(self):
        """Test midnight time formatting."""
        dt = datetime(2025, 11, 5, 21, 0, 0, tzinfo=pytz.UTC)  # 00:00 Moscow next day
        result = format_time(dt, timezone="Europe/Moscow")
        assert result == "00:00"

    @pytest.mark.unit
    def test_format_time_single_digit_hour(self):
        """Test single digit hour gets leading zero."""
        dt = datetime(2025, 11, 5, 6, 15, 0, tzinfo=pytz.UTC)  # 09:15 Moscow
        result = format_time(dt, timezone="Europe/Moscow")
        assert result == "09:15"

    @pytest.mark.unit
    def test_format_time_single_digit_minute(self):
        """Test single digit minute gets leading zero."""
        dt = datetime(2025, 11, 5, 11, 5, 0, tzinfo=pytz.UTC)  # 14:05 Moscow
        result = format_time(dt, timezone="Europe/Moscow")
        assert result == "14:05"

    @pytest.mark.unit
    def test_format_time_different_timezone(self):
        """Test formatting in different timezone."""
        dt = datetime(2025, 11, 5, 11, 30, 0, tzinfo=pytz.UTC)
        result = format_time(dt, timezone="America/New_York")  # UTC-5
        assert result == "06:30"


class TestFormatDate:
    """Test format_date for Russian date strings."""

    @pytest.mark.unit
    def test_format_date_january(self):
        """Test January date formatting."""
        dt = datetime(2025, 1, 15, 11, 0, 0, tzinfo=pytz.UTC)
        result = format_date(dt, timezone="Europe/Moscow")
        assert result == "15 января 2025"

    @pytest.mark.unit
    def test_format_date_december(self):
        """Test December date formatting."""
        dt = datetime(2025, 12, 25, 11, 0, 0, tzinfo=pytz.UTC)
        result = format_date(dt, timezone="Europe/Moscow")
        assert result == "25 декабря 2025"

    @pytest.mark.unit
    def test_format_date_first_day_of_month(self):
        """Test first day of month."""
        dt = datetime(2025, 5, 1, 11, 0, 0, tzinfo=pytz.UTC)
        result = format_date(dt, timezone="Europe/Moscow")
        assert result == "1 мая 2025"

    @pytest.mark.unit
    def test_format_date_all_months(self):
        """Test all Russian month names."""
        months_map = {
            1: "января", 2: "февраля", 3: "марта", 4: "апреля",
            5: "мая", 6: "июня", 7: "июля", 8: "августа",
            9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
        }

        for month, month_name in months_map.items():
            dt = datetime(2025, month, 15, 11, 0, 0, tzinfo=pytz.UTC)
            result = format_date(dt, timezone="Europe/Moscow")
            assert month_name in result

    @pytest.mark.unit
    def test_format_date_timezone_conversion(self):
        """Test date changes across timezone boundary."""
        # 23:00 UTC on Nov 5 = 02:00 Moscow on Nov 6
        dt = datetime(2025, 11, 5, 23, 0, 0, tzinfo=pytz.UTC)
        result = format_date(dt, timezone="Europe/Moscow")
        assert "6 ноября 2025" in result


class TestExtractTags:
    """Test extract_tags for hashtag extraction."""

    @pytest.mark.unit
    def test_extract_tags_single_tag(self):
        """Test single hashtag extraction."""
        text = "Работал над проектом #важное"
        result = extract_tags(text)
        assert result == ["важное"]

    @pytest.mark.unit
    def test_extract_tags_multiple_tags(self):
        """Test multiple hashtags extraction."""
        text = "Работал над проектом #важное #дедлайн #срочно"
        result = extract_tags(text)
        assert result == ["важное", "дедлайн", "срочно"]

    @pytest.mark.unit
    def test_extract_tags_no_tags(self):
        """Test text without hashtags returns empty list."""
        text = "Работал над проектом без тегов"
        result = extract_tags(text)
        assert result == []

    @pytest.mark.unit
    def test_extract_tags_english(self):
        """Test English hashtags."""
        text = "Working on project #urgent #deadline"
        result = extract_tags(text)
        assert result == ["urgent", "deadline"]

    @pytest.mark.unit
    def test_extract_tags_mixed_language(self):
        """Test mixed Russian and English hashtags."""
        text = "Project #work #работа"
        result = extract_tags(text)
        assert result == ["work", "работа"]

    @pytest.mark.unit
    def test_extract_tags_with_numbers(self):
        """Test hashtags with numbers."""
        text = "Task #task1 #version2"
        result = extract_tags(text)
        assert result == ["task1", "version2"]

    @pytest.mark.unit
    def test_extract_tags_ignores_special_chars(self):
        """Test hashtags stop at special characters."""
        text = "Meeting #важное! #project."
        result = extract_tags(text)
        # Should extract word characters only
        assert "важное" in result
        assert "project" in result


class TestFormatActivityList:
    """Test format_activity_list for activity display."""

    @pytest.mark.unit
    def test_format_empty_activity_list(self):
        """Test empty activity list returns no activities message."""
        result = format_activity_list([])
        assert "У тебя пока нет записанных активностей" in result

    @pytest.mark.unit
    def test_format_single_activity(self):
        """Test single activity formatting."""
        activities = [
            {
                "start_time": "2025-11-05T11:00:00Z",
                "end_time": "2025-11-05T12:30:00Z",
                "duration_minutes": 90,
                "description": "Работа над проектом",
                "tags": ""
            }
        ]

        result = format_activity_list(activities, timezone="Europe/Moscow")

        # Should contain header
        assert "📋 Твои последние активности" in result
        # Should contain date
        assert "5 ноября 2025" in result
        # Should contain time range
        assert "14:00" in result  # 11:00 UTC = 14:00 Moscow
        assert "15:30" in result  # 12:30 UTC = 15:30 Moscow
        # Should contain duration
        assert "1ч 30м" in result
        # Should contain description
        assert "Работа над проектом" in result

    @pytest.mark.unit
    def test_format_activity_with_tags(self):
        """Test activity with tags formatting."""
        activities = [
            {
                "start_time": "2025-11-05T11:00:00Z",
                "end_time": "2025-11-05T12:00:00Z",
                "duration_minutes": 60,
                "description": "Встреча",
                "tags": "важное,срочно"
            }
        ]

        result = format_activity_list(activities, timezone="Europe/Moscow")

        # Should contain tags with # prefix
        assert "#важное" in result
        assert "#срочно" in result
        assert "🏷" in result  # Tag emoji

    @pytest.mark.unit
    def test_format_multiple_activities_same_day(self):
        """Test multiple activities on the same day."""
        activities = [
            {
                "start_time": "2025-11-05T08:00:00Z",
                "end_time": "2025-11-05T09:00:00Z",
                "duration_minutes": 60,
                "description": "Утренняя встреча",
                "tags": ""
            },
            {
                "start_time": "2025-11-05T12:00:00Z",
                "end_time": "2025-11-05T13:00:00Z",
                "duration_minutes": 60,
                "description": "Обед",
                "tags": ""
            }
        ]

        result = format_activity_list(activities, timezone="Europe/Moscow")

        # Should have single date header
        assert result.count("5 ноября 2025") == 1
        # Should have both activities
        assert "Утренняя встреча" in result
        assert "Обед" in result

    @pytest.mark.unit
    def test_format_activities_different_days(self):
        """Test activities from different days grouped by date."""
        activities = [
            {
                "start_time": "2025-11-05T11:00:00Z",
                "end_time": "2025-11-05T12:00:00Z",
                "duration_minutes": 60,
                "description": "День 1",
                "tags": ""
            },
            {
                "start_time": "2025-11-06T11:00:00Z",
                "end_time": "2025-11-06T12:00:00Z",
                "duration_minutes": 60,
                "description": "День 2",
                "tags": ""
            }
        ]

        result = format_activity_list(activities, timezone="Europe/Moscow")

        # Should have two date headers
        assert "5 ноября 2025" in result
        assert "6 ноября 2025" in result
        # Should have separator lines
        assert "━━━━━━━━━━━━━━━━━━" in result

    @pytest.mark.unit
    def test_format_activity_without_tags_field(self):
        """Test activity when tags field is missing."""
        activities = [
            {
                "start_time": "2025-11-05T11:00:00Z",
                "end_time": "2025-11-05T12:00:00Z",
                "duration_minutes": 60,
                "description": "Test"
                # No tags field
            }
        ]

        result = format_activity_list(activities, timezone="Europe/Moscow")

        # Should not crash, should format normally
        assert "Test" in result
        assert "14:00" in result


# Total: 30 tests
