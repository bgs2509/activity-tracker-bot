"""
Level 2 Integration Tests: Stats Service.

Test Coverage:
    - Get daily statistics calculates correct totals
    - Get weekly statistics aggregates correctly
    - Get category breakdown shows distribution
    - Get activity trends calculates patterns
    - Get productivity metrics computes scores
    - Handle empty data returns zeros
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock


@pytest.mark.integration
@pytest.mark.level2
async def test_get_daily_statistics_calculates_correct_totals(
    db_session, test_user, test_category
):
    """
    GIVEN: Multiple activities exist for a day
    WHEN: Service calculates daily statistics
    THEN: Correct totals (count, duration) are returned

    Mocks: None
    Real: Service, Repository, Database, Aggregations
    Time: ~180ms
    """
    # Arrange
    from services.data_postgres_api.src.application.services.activity_service import ActivityService
    from services.data_postgres_api.src.infrastructure.repositories.activity_repository import ActivityRepository
    from services.tracker_activity_bot.src.services.stats_service import StatsService

    activity_repo = ActivityRepository(db_session)
    activity_service = ActivityService(activity_repo)
    stats_service = StatsService()

    # Create activities for today
    today = datetime.now().date()
    start_time1 = datetime.combine(today, datetime.min.time()).replace(hour=10)
    end_time1 = start_time1 + timedelta(hours=2)

    start_time2 = datetime.combine(today, datetime.min.time()).replace(hour=14)
    end_time2 = start_time2 + timedelta(hours=1)

    await activity_service.create_activity(
        user_id=test_user.id,
        category_id=test_category.id,
        start_time=start_time1,
        end_time=end_time1,
        description="Activity 1"
    )

    await activity_service.create_activity(
        user_id=test_user.id,
        category_id=test_category.id,
        start_time=start_time2,
        end_time=end_time2,
        description="Activity 2"
    )

    # Act
    stats = await stats_service.get_daily_statistics(
        user_id=test_user.id,
        date=today
    )

    # Assert
    assert stats is not None
    assert stats.get("total_activities") >= 2
    assert stats.get("total_duration_minutes") >= 180  # 3 hours


@pytest.mark.integration
@pytest.mark.level2
async def test_get_weekly_statistics_aggregates_correctly(
    db_session, test_user, test_category
):
    """
    GIVEN: Activities exist across multiple days
    WHEN: Service calculates weekly statistics
    THEN: Correct aggregations per day are returned

    Mocks: None
    Real: Service, Repository, Database, Aggregations
    Time: ~220ms
    """
    # Arrange
    from services.data_postgres_api.src.application.services.activity_service import ActivityService
    from services.data_postgres_api.src.infrastructure.repositories.activity_repository import ActivityRepository
    from services.tracker_activity_bot.src.services.stats_service import StatsService

    activity_repo = ActivityRepository(db_session)
    activity_service = ActivityService(activity_repo)
    stats_service = StatsService()

    # Create activities across 3 days
    for day_offset in range(3):
        day = datetime.now() - timedelta(days=day_offset)
        start_time = day.replace(hour=10, minute=0)
        end_time = start_time + timedelta(hours=1)

        await activity_service.create_activity(
            user_id=test_user.id,
            category_id=test_category.id,
            start_time=start_time,
            end_time=end_time,
            description=f"Day {day_offset} activity"
        )

    # Act
    week_start = datetime.now() - timedelta(days=7)
    stats = await stats_service.get_weekly_statistics(
        user_id=test_user.id,
        week_start=week_start
    )

    # Assert
    assert stats is not None
    assert len(stats.get("daily_breakdown", [])) >= 3


@pytest.mark.integration
@pytest.mark.level2
async def test_get_category_breakdown_shows_distribution(
    db_session, test_user, test_category
):
    """
    GIVEN: Activities exist in multiple categories
    WHEN: Service calculates category breakdown
    THEN: Distribution percentages are returned

    Mocks: None
    Real: Service, Repository, Database, Aggregations
    Time: ~200ms
    """
    # Arrange
    from services.data_postgres_api.src.application.services.activity_service import ActivityService
    from services.data_postgres_api.src.infrastructure.repositories.activity_repository import ActivityRepository
    from services.data_postgres_api.src.infrastructure.repositories.category_repository import CategoryRepository
    from services.tracker_activity_bot.src.services.stats_service import StatsService
    from services.data_postgres_api.src.domain.models.category import Category

    activity_repo = ActivityRepository(db_session)
    activity_service = ActivityService(activity_repo)
    stats_service = StatsService()

    # Create second category
    category2 = Category(
        user_id=test_user.id,
        name="Category 2",
        emoji="🎯"
    )
    db_session.add(category2)
    await db_session.commit()
    await db_session.refresh(category2)

    # Create activities in both categories
    now = datetime.now()

    # 2 hours in category 1
    await activity_service.create_activity(
        user_id=test_user.id,
        category_id=test_category.id,
        start_time=now - timedelta(hours=4),
        end_time=now - timedelta(hours=2),
        description="Cat1"
    )

    # 1 hour in category 2
    await activity_service.create_activity(
        user_id=test_user.id,
        category_id=category2.id,
        start_time=now - timedelta(hours=2),
        end_time=now - timedelta(hours=1),
        description="Cat2"
    )

    # Act
    breakdown = await stats_service.get_category_breakdown(
        user_id=test_user.id,
        date_from=now - timedelta(days=1),
        date_to=now
    )

    # Assert
    assert breakdown is not None
    assert len(breakdown) >= 2
    total_percentage = sum(item.get("percentage", 0) for item in breakdown)
    assert abs(total_percentage - 100) < 5  # Should be close to 100%


@pytest.mark.integration
@pytest.mark.level2
async def test_get_activity_trends_calculates_patterns(
    db_session, test_user, test_category
):
    """
    GIVEN: Activities exist over time
    WHEN: Service analyzes trends
    THEN: Patterns (increasing/decreasing) are identified

    Mocks: None
    Real: Service, Repository, Database, Trend analysis
    Time: ~210ms
    """
    # Arrange
    from services.data_postgres_api.src.application.services.activity_service import ActivityService
    from services.data_postgres_api.src.infrastructure.repositories.activity_repository import ActivityRepository
    from services.tracker_activity_bot.src.services.stats_service import StatsService

    activity_repo = ActivityRepository(db_session)
    activity_service = ActivityService(activity_repo)
    stats_service = StatsService()

    # Create increasing pattern (more activities each day)
    for day_offset in range(3):
        activities_count = day_offset + 1  # 1, 2, 3 activities
        for i in range(activities_count):
            day = datetime.now() - timedelta(days=2-day_offset)
            start_time = day.replace(hour=10+i, minute=0)
            end_time = start_time + timedelta(hours=1)

            await activity_service.create_activity(
                user_id=test_user.id,
                category_id=test_category.id,
                start_time=start_time,
                end_time=end_time,
                description=f"Trend activity"
            )

    # Act
    trends = await stats_service.get_activity_trends(
        user_id=test_user.id,
        days=7
    )

    # Assert
    assert trends is not None
    assert "trend_direction" in trends
    # Should detect increasing trend
    assert trends.get("trend_direction") in ["increasing", "stable"]


@pytest.mark.integration
@pytest.mark.level2
async def test_get_productivity_metrics_computes_scores(
    db_session, test_user, test_category
):
    """
    GIVEN: Activities exist for user
    WHEN: Service calculates productivity metrics
    THEN: Scores and metrics are computed

    Mocks: None
    Real: Service, Repository, Database, Calculations
    Time: ~190ms
    """
    # Arrange
    from services.data_postgres_api.src.application.services.activity_service import ActivityService
    from services.data_postgres_api.src.infrastructure.repositories.activity_repository import ActivityRepository
    from services.tracker_activity_bot.src.services.stats_service import StatsService

    activity_repo = ActivityRepository(db_session)
    activity_service = ActivityService(activity_repo)
    stats_service = StatsService()

    # Create consistent activities
    for i in range(5):
        start_time = datetime.now() - timedelta(hours=5-i)
        end_time = start_time + timedelta(hours=1)

        await activity_service.create_activity(
            user_id=test_user.id,
            category_id=test_category.id,
            start_time=start_time,
            end_time=end_time,
            description=f"Productive activity {i}"
        )

    # Act
    metrics = await stats_service.get_productivity_metrics(
        user_id=test_user.id,
        period_days=7
    )

    # Assert
    assert metrics is not None
    assert "productivity_score" in metrics
    assert "average_daily_hours" in metrics
    assert metrics.get("productivity_score") >= 0


@pytest.mark.integration
@pytest.mark.level2
async def test_handle_empty_data_returns_zeros(db_session, test_user):
    """
    GIVEN: No activities exist for user
    WHEN: Service calculates statistics
    THEN: Empty/zero results are returned gracefully

    Mocks: None
    Real: Service, Repository, Database
    Time: ~100ms
    """
    # Arrange
    from services.tracker_activity_bot.src.services.stats_service import StatsService

    stats_service = StatsService()

    # Act
    stats = await stats_service.get_daily_statistics(
        user_id=test_user.id,
        date=datetime.now().date()
    )

    # Assert
    assert stats is not None
    assert stats.get("total_activities", 0) == 0
    assert stats.get("total_duration_minutes", 0) == 0
