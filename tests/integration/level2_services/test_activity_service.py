"""
Level 2 Integration Tests: Activity Service.

Test Coverage:
    - Create activity stores in database
    - Get activity by ID retrieves correct record
    - Update activity modifies existing record
    - Delete activity removes from database
    - List activities with filters
    - Get activities by user
    - Get activities by category
    - Validate overlapping activities
    - Get activity statistics
    - Error handling for invalid operations
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch


@pytest.mark.integration
@pytest.mark.level2
async def test_create_activity_stores_in_database(db_session, test_user, test_category):
    """
    GIVEN: Valid activity data
    WHEN: Service creates activity
    THEN: Activity is stored in database with correct attributes

    Mocks: None (uses real DB)
    Real: Service, Repository, Database
    Time: ~150ms
    """
    # Arrange
    from services.data_postgres_api.src.application.services.activity_service import ActivityService
    from services.data_postgres_api.src.infrastructure.repositories.activity_repository import ActivityRepository

    repo = ActivityRepository(db_session)
    service = ActivityService(repo)

    activity_data = {
        "user_id": test_user.id,
        "category_id": test_category.id,
        "start_time": datetime.now(),
        "end_time": datetime.now() + timedelta(hours=1),
        "description": "Test activity"
    }

    # Act
    created = await service.create_activity(**activity_data)

    # Assert
    assert created.id is not None
    assert created.user_id == test_user.id
    assert created.category_id == test_category.id
    assert created.description == "Test activity"

    # Verify in database
    retrieved = await service.get_activity_by_id(created.id)
    assert retrieved is not None
    assert retrieved.id == created.id


@pytest.mark.integration
@pytest.mark.level2
async def test_get_activity_by_id_retrieves_correct_record(db_session, test_activity):
    """
    GIVEN: Activity exists in database
    WHEN: Service retrieves by ID
    THEN: Correct activity is returned with all attributes

    Mocks: None
    Real: Service, Repository, Database
    Time: ~120ms
    """
    # Arrange
    from services.data_postgres_api.src.application.services.activity_service import ActivityService
    from services.data_postgres_api.src.infrastructure.repositories.activity_repository import ActivityRepository

    repo = ActivityRepository(db_session)
    service = ActivityService(repo)

    # Act
    retrieved = await service.get_activity_by_id(test_activity.id)

    # Assert
    assert retrieved is not None
    assert retrieved.id == test_activity.id
    assert retrieved.user_id == test_activity.user_id
    assert retrieved.category_id == test_activity.category_id


@pytest.mark.integration
@pytest.mark.level2
async def test_get_activity_by_id_returns_none_for_nonexistent(db_session):
    """
    GIVEN: Activity ID does not exist
    WHEN: Service retrieves by ID
    THEN: None is returned

    Mocks: None
    Real: Service, Repository, Database
    Time: ~100ms
    """
    # Arrange
    from services.data_postgres_api.src.application.services.activity_service import ActivityService
    from services.data_postgres_api.src.infrastructure.repositories.activity_repository import ActivityRepository

    repo = ActivityRepository(db_session)
    service = ActivityService(repo)

    # Act
    retrieved = await service.get_activity_by_id(999999)

    # Assert
    assert retrieved is None


@pytest.mark.integration
@pytest.mark.level2
async def test_update_activity_modifies_existing_record(db_session, test_activity):
    """
    GIVEN: Activity exists in database
    WHEN: Service updates activity attributes
    THEN: Database record is modified
          AND updated activity is returned

    Mocks: None
    Real: Service, Repository, Database
    Time: ~140ms
    """
    # Arrange
    from services.data_postgres_api.src.application.services.activity_service import ActivityService
    from services.data_postgres_api.src.infrastructure.repositories.activity_repository import ActivityRepository

    repo = ActivityRepository(db_session)
    service = ActivityService(repo)

    original_description = test_activity.description
    new_description = "Updated description"

    # Act
    updated = await service.update_activity(
        test_activity.id,
        description=new_description
    )

    # Assert
    assert updated is not None
    assert updated.id == test_activity.id
    assert updated.description == new_description
    assert updated.description != original_description

    # Verify persistence
    retrieved = await service.get_activity_by_id(test_activity.id)
    assert retrieved.description == new_description


@pytest.mark.integration
@pytest.mark.level2
async def test_update_nonexistent_activity_returns_none(db_session):
    """
    GIVEN: Activity ID does not exist
    WHEN: Service attempts to update
    THEN: None is returned

    Mocks: None
    Real: Service, Repository, Database
    Time: ~110ms
    """
    # Arrange
    from services.data_postgres_api.src.application.services.activity_service import ActivityService
    from services.data_postgres_api.src.infrastructure.repositories.activity_repository import ActivityRepository

    repo = ActivityRepository(db_session)
    service = ActivityService(repo)

    # Act
    result = await service.update_activity(999999, description="New description")

    # Assert
    assert result is None


@pytest.mark.integration
@pytest.mark.level2
async def test_delete_activity_removes_from_database(db_session, test_activity):
    """
    GIVEN: Activity exists in database
    WHEN: Service deletes activity
    THEN: Activity is removed from database
          AND subsequent retrieval returns None

    Mocks: None
    Real: Service, Repository, Database
    Time: ~130ms
    """
    # Arrange
    from services.data_postgres_api.src.application.services.activity_service import ActivityService
    from services.data_postgres_api.src.infrastructure.repositories.activity_repository import ActivityRepository

    repo = ActivityRepository(db_session)
    service = ActivityService(repo)

    activity_id = test_activity.id

    # Verify exists first
    exists = await service.get_activity_by_id(activity_id)
    assert exists is not None

    # Act
    result = await service.delete_activity(activity_id)

    # Assert
    assert result is True

    # Verify deleted
    retrieved = await service.get_activity_by_id(activity_id)
    assert retrieved is None


@pytest.mark.integration
@pytest.mark.level2
async def test_delete_nonexistent_activity_returns_false(db_session):
    """
    GIVEN: Activity ID does not exist
    WHEN: Service attempts to delete
    THEN: False is returned (idempotent)

    Mocks: None
    Real: Service, Repository, Database
    Time: ~100ms
    """
    # Arrange
    from services.data_postgres_api.src.application.services.activity_service import ActivityService
    from services.data_postgres_api.src.infrastructure.repositories.activity_repository import ActivityRepository

    repo = ActivityRepository(db_session)
    service = ActivityService(repo)

    # Act
    result = await service.delete_activity(999999)

    # Assert
    assert result is False


@pytest.mark.integration
@pytest.mark.level2
async def test_list_activities_returns_all_user_activities(db_session, test_user, test_category):
    """
    GIVEN: Multiple activities exist for user
    WHEN: Service lists activities
    THEN: All user activities are returned

    Mocks: None
    Real: Service, Repository, Database
    Time: ~180ms
    """
    # Arrange
    from services.data_postgres_api.src.application.services.activity_service import ActivityService
    from services.data_postgres_api.src.infrastructure.repositories.activity_repository import ActivityRepository

    repo = ActivityRepository(db_session)
    service = ActivityService(repo)

    # Create multiple activities
    for i in range(3):
        await service.create_activity(
            user_id=test_user.id,
            category_id=test_category.id,
            start_time=datetime.now() - timedelta(hours=i+1),
            end_time=datetime.now() - timedelta(hours=i),
            description=f"Activity {i+1}"
        )

    # Act
    activities = await service.list_activities(user_id=test_user.id)

    # Assert
    assert len(activities) >= 3
    assert all(a.user_id == test_user.id for a in activities)


@pytest.mark.integration
@pytest.mark.level2
async def test_list_activities_filters_by_date_range(db_session, test_user, test_category):
    """
    GIVEN: Activities exist across different dates
    WHEN: Service lists with date range filter
    THEN: Only activities within range are returned

    Mocks: None
    Real: Service, Repository, Database, Date filtering
    Time: ~200ms
    """
    # Arrange
    from services.data_postgres_api.src.application.services.activity_service import ActivityService
    from services.data_postgres_api.src.infrastructure.repositories.activity_repository import ActivityRepository

    repo = ActivityRepository(db_session)
    service = ActivityService(repo)

    now = datetime.now()

    # Create activities on different dates
    await service.create_activity(
        user_id=test_user.id,
        category_id=test_category.id,
        start_time=now - timedelta(days=5),
        end_time=now - timedelta(days=5, hours=-1),
        description="Old activity"
    )

    await service.create_activity(
        user_id=test_user.id,
        category_id=test_category.id,
        start_time=now - timedelta(hours=2),
        end_time=now - timedelta(hours=1),
        description="Recent activity"
    )

    # Act - filter for last 3 days
    date_from = now - timedelta(days=3)
    activities = await service.list_activities(
        user_id=test_user.id,
        date_from=date_from
    )

    # Assert
    assert len(activities) >= 1
    assert all(a.start_time >= date_from for a in activities)
    assert any(a.description == "Recent activity" for a in activities)


@pytest.mark.integration
@pytest.mark.level2
async def test_list_activities_filters_by_category(db_session, test_user, test_category):
    """
    GIVEN: Activities exist in multiple categories
    WHEN: Service lists with category filter
    THEN: Only activities in specified category are returned

    Mocks: None
    Real: Service, Repository, Database
    Time: ~190ms
    """
    # Arrange
    from services.data_postgres_api.src.application.services.activity_service import ActivityService
    from services.data_postgres_api.src.infrastructure.repositories.activity_repository import ActivityRepository
    from services.data_postgres_api.src.infrastructure.repositories.category_repository import CategoryRepository

    repo = ActivityRepository(db_session)
    category_repo = CategoryRepository(db_session)
    service = ActivityService(repo)

    # Create second category
    from services.data_postgres_api.src.domain.models.category import Category
    category2 = Category(
        user_id=test_user.id,
        name="Category 2",
        emoji="🎯"
    )
    db_session.add(category2)
    await db_session.commit()
    await db_session.refresh(category2)

    # Create activities in both categories
    await service.create_activity(
        user_id=test_user.id,
        category_id=test_category.id,
        start_time=datetime.now() - timedelta(hours=2),
        end_time=datetime.now() - timedelta(hours=1),
        description="Activity in category 1"
    )

    await service.create_activity(
        user_id=test_user.id,
        category_id=category2.id,
        start_time=datetime.now() - timedelta(hours=4),
        end_time=datetime.now() - timedelta(hours=3),
        description="Activity in category 2"
    )

    # Act
    activities = await service.list_activities(
        user_id=test_user.id,
        category_id=test_category.id
    )

    # Assert
    assert len(activities) >= 1
    assert all(a.category_id == test_category.id for a in activities)


@pytest.mark.integration
@pytest.mark.level2
async def test_validate_overlapping_activities_detects_conflicts(db_session, test_user, test_category):
    """
    GIVEN: Activity exists in time range
    WHEN: Service validates new overlapping activity
    THEN: Validation fails with overlap detected

    Mocks: None
    Real: Service, Repository, Database, Business logic
    Time: ~160ms
    """
    # Arrange
    from services.data_postgres_api.src.application.services.activity_service import ActivityService
    from services.data_postgres_api.src.infrastructure.repositories.activity_repository import ActivityRepository

    repo = ActivityRepository(db_session)
    service = ActivityService(repo)

    start_time = datetime.now()
    end_time = start_time + timedelta(hours=2)

    # Create first activity
    await service.create_activity(
        user_id=test_user.id,
        category_id=test_category.id,
        start_time=start_time,
        end_time=end_time,
        description="Existing activity"
    )

    # Act - try to create overlapping activity
    overlap_start = start_time + timedelta(hours=1)
    overlap_end = end_time + timedelta(hours=1)

    overlaps = await service.check_overlapping_activities(
        user_id=test_user.id,
        start_time=overlap_start,
        end_time=overlap_end
    )

    # Assert
    assert len(overlaps) >= 1


@pytest.mark.integration
@pytest.mark.level2
async def test_get_activity_statistics_calculates_totals(db_session, test_user, test_category):
    """
    GIVEN: Multiple activities exist
    WHEN: Service calculates statistics
    THEN: Correct totals (count, duration) are returned

    Mocks: None
    Real: Service, Repository, Database, Aggregations
    Time: ~200ms
    """
    # Arrange
    from services.data_postgres_api.src.application.services.activity_service import ActivityService
    from services.data_postgres_api.src.infrastructure.repositories.activity_repository import ActivityRepository

    repo = ActivityRepository(db_session)
    service = ActivityService(repo)

    # Create activities with known durations
    await service.create_activity(
        user_id=test_user.id,
        category_id=test_category.id,
        start_time=datetime.now() - timedelta(hours=3),
        end_time=datetime.now() - timedelta(hours=2),
        description="1 hour activity"
    )

    await service.create_activity(
        user_id=test_user.id,
        category_id=test_category.id,
        start_time=datetime.now() - timedelta(hours=5),
        end_time=datetime.now() - timedelta(hours=3),
        description="2 hour activity"
    )

    # Act
    stats = await service.get_activity_statistics(
        user_id=test_user.id,
        category_id=test_category.id
    )

    # Assert
    assert stats is not None
    assert stats.get("total_count", 0) >= 2
    assert stats.get("total_duration", 0) >= 180  # At least 3 hours in minutes
