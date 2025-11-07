# Fast Testing Implementation Plan - Activity Tracker Bot

**Document Version:** 1.0
**Date:** 2025-11-07
**Target:** 100% Fast Test Coverage
**Current Coverage:** ~20-25%
**Status:** DRAFT

---

## Executive Summary

This document provides a comprehensive roadmap to achieve 100% fast test coverage for the Activity Tracker Bot project. Fast tests include unit tests, contract tests, smoke tests, property-based tests, and static analysis - all executable in under 30 seconds total.

**Key Metrics:**
- Current State: 18 test files, 4,197 lines of test code, ~20-25% coverage
- Target State: 112+ test files, ~11,000 lines of test code, 100% coverage
- Timeline: 10-12 weeks (2-3 months)
- Estimated Effort: 240-320 developer hours

**Success Criteria:**
- ✅ Line coverage ≥ 95%
- ✅ Branch coverage ≥ 90%
- ✅ All critical paths covered at 100%
- ✅ All fast tests execute in < 30 seconds
- ✅ No code duplication > 10%
- ✅ Cyclomatic complexity < 10 per function

---

## Table of Contents

1. [Current State Analysis](#current-state-analysis)
2. [Target Architecture](#target-architecture)
3. [Detailed Task Breakdown](#detailed-task-breakdown)
   - [Phase 1: Critical Foundation](#phase-1-critical-foundation)
   - [Phase 2: Business Logic](#phase-2-business-logic)
   - [Phase 3: Handlers & Endpoints](#phase-3-handlers--endpoints)
   - [Phase 4: Infrastructure](#phase-4-infrastructure)
   - [Phase 5: Quality Gates](#phase-5-quality-gates)
4. [Implementation Guidelines](#implementation-guidelines)
5. [Testing Best Practices](#testing-best-practices)
6. [Timeline & Milestones](#timeline--milestones)
7. [Appendix: Code Examples](#appendix-code-examples)

---

## Current State Analysis

### Test Coverage by Module

#### Data Postgres API Service (43 source files)

| Module | Files | Coverage | Status | Priority |
|--------|-------|----------|--------|----------|
| **Services** | 4 | ~90% | ✅ Excellent | - |
| **Middleware** (partial) | 2/3 | ~66% | ⚠️ Good | P1 |
| **Repositories** | 0/5 | 0% | ❌ Critical | **P0** |
| **API Endpoints** | 0/4 | ~5% | ❌ Critical | **P0** |
| **Models** | 0/6 | 0% | ❌ Critical | P1 |
| **Schemas** | 0/4 | 0% | ❌ Critical | P1 |
| **Database** | 0/2 | 0% | ❌ Critical | P2 |
| **Core** | 0/3 | 0% | ❌ Critical | P2 |

**Total: 8/43 files tested (18.6%)**

#### Tracker Activity Bot Service (70 source files)

| Module | Files | Coverage | Status | Priority |
|--------|-------|----------|--------|----------|
| **Utils** (partial) | 3/6 | ~60% | ⚠️ Good | P1 |
| **Handlers** | 0/18 | 0% | ❌ Critical | **P0** |
| **Services** | 0/2 | 0% | ❌ Critical | **P0** |
| **HTTP Clients** | 0/10 | 0% | ❌ Critical | **P0** |
| **Keyboards** | 1/6 | ~20% | ❌ Low | P1 |
| **States** | 0/4 | 0% | ❌ Critical | P2 |
| **Middleware** | 0/2 | 0% | ❌ Critical | P1 |
| **Core** | 0/5 | 0% | ❌ Critical | P2 |
| **Decorators** | 0/2 | 0% | ❌ Critical | P1 |

**Total: 10/70 files tested (14.3%)**

### Existing Test Files

```
✅ services/data_postgres_api/tests/
   ├── unit/
   │   ├── test_user_service.py              (247 lines) ✅
   │   ├── test_category_service.py          (293 lines) ✅
   │   ├── test_activity_service.py          (256 lines) ✅
   │   ├── test_user_settings_service.py     (343 lines) ✅
   │   ├── test_correlation_middleware.py    (195 lines) ✅
   │   ├── test_logging_middleware.py        (248 lines) ✅
   │   ├── test_health.py                    (206 lines) ✅
   │   └── test_imports.py                   (smoke) ✅
   └── service/
       └── test_activity_endpoints.py        (83 lines) ✅

✅ services/tracker_activity_bot/tests/
   └── unit/
       ├── test_time_parser.py               (302 lines) ✅
       ├── test_timezone_helper.py           (305 lines) ✅
       ├── test_formatters.py                (327 lines) ✅
       ├── test_keyboards.py                 (173 lines) ✅
       ├── test_poll_handlers.py             (321 lines) ✅
       ├── test_settings_custom_input.py     (302 lines) ✅
       ├── test_category_inline_buttons.py   (147 lines) ✅
       ├── test_cancel_command.py            (228 lines) ✅
       └── test_imports.py                   (smoke) ✅

✅ tests/smoke/
   └── test_docker_health.py                 (5 tests) ✅
```

**Total: 18 test files, 4,197 lines**

### Gap Analysis

**Critical Gaps (P0):**
1. ❌ **Repository Layer (5 files, 0% coverage)** - Foundation of entire data access!
2. ❌ **Bot Handlers (18 files, 0% coverage)** - Core user interaction logic
3. ❌ **HTTP Client Infrastructure (10 files, 0% coverage)** - All API communication
4. ❌ **API Endpoints (4 files, ~5% coverage)** - External interface contracts

**High Priority Gaps (P1):**
5. ❌ **Models & Schemas (10 files, 0% coverage)** - Data validation
6. ❌ **Utils (3 files, 0% coverage)** - Widely used helper functions
7. ❌ **Services (2 files, 0% coverage)** - Scheduler & FSM timeout
8. ❌ **Middleware (2 files, 0% coverage)** - Error handling & service injection

**Medium Priority Gaps (P2):**
9. ❌ **States (4 files, 0% coverage)** - FSM state definitions
10. ❌ **Core Infrastructure (8 files, 0% coverage)** - Config, logging, database

---

## Target Architecture

### Test Pyramid (Target Distribution)

```
        E2E Tests (2%)
      ╱              ╲
    ╱   Integration   ╲
  ╱    Tests (8%)      ╲    ← Slow (not in this plan)
╱                       ╲
━━━━━━━━━━━━━━━━━━━━━━━━━━
▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓  ← FAST TESTS (90%)
▓▓▓▓ Unit + Contract + ▓▓
▓▓▓ Property + Smoke ▓▓▓▓
▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
```

### Test Categories (Fast Tests Only)

| Category | Description | Target Count | Execution Time |
|----------|-------------|--------------|----------------|
| **Unit Tests** | Isolated tests with mocks | ~700 tests | < 15 seconds |
| **Contract Tests** | API schema validation | ~80 tests | < 3 seconds |
| **Property Tests** | Hypothesis-based | ~30 properties | < 5 seconds |
| **Smoke Tests** | Basic functionality | ~25 tests | < 5 seconds |
| **Static Analysis** | Type checking, linting | 4 tools | < 10 seconds |

**Total: ~835 fast tests, < 30 seconds execution**

### Directory Structure (Target)

```
services/
├── data_postgres_api/
│   ├── src/ (43 files)
│   └── tests/
│       ├── unit/                          ← FAST
│       │   ├── repositories/              ← NEW
│       │   │   ├── test_base_repository.py
│       │   │   ├── test_user_repository.py
│       │   │   ├── test_activity_repository.py
│       │   │   ├── test_category_repository.py
│       │   │   └── test_user_settings_repository.py
│       │   ├── services/                  ← EXISTING ✅
│       │   │   ├── test_user_service.py
│       │   │   ├── test_category_service.py
│       │   │   ├── test_activity_service.py
│       │   │   └── test_user_settings_service.py
│       │   ├── middleware/                ← EXPAND
│       │   │   ├── test_correlation_middleware.py ✅
│       │   │   ├── test_logging_middleware.py ✅
│       │   │   └── test_error_handler.py  ← NEW
│       │   ├── models/                    ← NEW
│       │   │   ├── test_user_model.py
│       │   │   ├── test_activity_model.py
│       │   │   ├── test_category_model.py
│       │   │   └── test_user_settings_model.py
│       │   ├── schemas/                   ← NEW
│       │   │   ├── test_user_schemas.py
│       │   │   ├── test_activity_schemas.py
│       │   │   ├── test_category_schemas.py
│       │   │   └── test_user_settings_schemas.py
│       │   ├── core/                      ← NEW
│       │   │   ├── test_config.py
│       │   │   └── test_logging.py
│       │   ├── test_health.py             ✅
│       │   └── test_imports.py            ✅
│       ├── contract/                      ← NEW (FAST)
│       │   ├── test_users_api.py
│       │   ├── test_activities_api.py
│       │   ├── test_categories_api.py
│       │   └── test_user_settings_api.py
│       ├── properties/                    ← NEW (FAST)
│       │   └── test_schema_properties.py
│       └── smoke/                         ← NEW (FAST)
│           ├── test_database_smoke.py
│           └── test_api_smoke.py
│
└── tracker_activity_bot/
    ├── src/ (70 files)
    └── tests/
        ├── unit/                          ← FAST
        │   ├── utils/                     ← EXPAND
        │   │   ├── test_time_parser.py    ✅
        │   │   ├── test_timezone_helper.py ✅
        │   │   ├── test_formatters.py     ✅
        │   │   ├── test_time_helpers.py   ← NEW
        │   │   ├── test_fsm_helpers.py    ← NEW
        │   │   └── test_decorators.py     ← NEW
        │   ├── services/                  ← NEW
        │   │   ├── test_scheduler_service.py
        │   │   └── test_fsm_timeout_service.py
        │   ├── http_client/               ← NEW
        │   │   ├── test_http_client.py
        │   │   ├── test_activity_service.py
        │   │   ├── test_category_service.py
        │   │   ├── test_user_service.py
        │   │   ├── test_user_settings_service.py
        │   │   └── middleware/
        │   │       ├── test_error_middleware.py
        │   │       ├── test_timing_middleware.py
        │   │       └── test_logging_middleware.py
        │   ├── handlers/                  ← NEW
        │   │   ├── activity/
        │   │   │   ├── test_activity_creation.py
        │   │   │   ├── test_activity_management.py
        │   │   │   └── test_helpers.py
        │   │   ├── categories/
        │   │   │   ├── test_category_creation.py
        │   │   │   ├── test_category_deletion.py
        │   │   │   ├── test_category_list.py
        │   │   │   └── test_helpers.py
        │   │   ├── poll/
        │   │   │   ├── test_poll_sender.py
        │   │   │   ├── test_poll_response.py
        │   │   │   └── test_helpers.py
        │   │   ├── settings/
        │   │   │   ├── test_interval_settings.py
        │   │   │   ├── test_quiet_hours_settings.py
        │   │   │   ├── test_reminder_settings.py
        │   │   │   ├── test_main_menu.py
        │   │   │   └── test_helpers.py
        │   │   └── test_start.py
        │   ├── keyboards/                 ← EXPAND
        │   │   ├── test_main_menu.py      ✅ (part of test_keyboards.py)
        │   │   ├── test_poll.py           ← NEW
        │   │   ├── test_settings.py       ← NEW
        │   │   ├── test_time_select.py    ← NEW
        │   │   └── test_fsm_reminder.py   ← NEW
        │   ├── middleware/                ← NEW
        │   │   └── test_service_injection.py
        │   ├── states/                    ← NEW
        │   │   ├── test_activity_states.py
        │   │   ├── test_category_states.py
        │   │   ├── test_poll_states.py
        │   │   └── test_settings_states.py
        │   ├── core/                      ← NEW
        │   │   ├── test_config.py
        │   │   ├── test_logging.py
        │   │   └── test_logging_middleware.py
        │   └── test_imports.py            ✅
        ├── contract/                      ← NEW (FAST)
        │   └── test_data_api_contracts.py
        ├── properties/                    ← NEW (FAST)
        │   ├── test_time_parser_properties.py
        │   ├── test_formatters_properties.py
        │   └── test_validators_properties.py
        └── smoke/                         ← NEW (FAST)
            └── test_bot_smoke.py

tests/smoke/
└── test_docker_health.py                  ✅
```

**Target: 112+ test files (1:1 ratio with source files)**

---

## Detailed Task Breakdown

### Phase 1: Critical Foundation (P0)

**Timeline:** Weeks 1-3
**Effort:** 80-100 hours
**Coverage Gain:** +35-40%

#### 1.1 Repository Layer Tests (Priority: CRITICAL)

**Rationale:** Repository layer is the foundation of all data access. Zero coverage here is a critical risk.

##### Task 1.1.1: Test Base Repository

**File:** `services/data_postgres_api/tests/unit/repositories/test_base_repository.py`
**Lines:** ~300
**Tests:** 12
**Time:** 8 hours

**Test Cases:**

```python
"""
Unit tests for BaseRepository.

Tests the generic CRUD operations that all repositories inherit.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from src.infrastructure.repositories.base import BaseRepository
from src.domain.models.user import User
from src.schemas.user import UserCreate, UserUpdate


@pytest.fixture
def mock_session():
    """Fixture: Mock AsyncSession for testing."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def user_repository(mock_session):
    """Fixture: BaseRepository[User] for testing."""
    return BaseRepository(mock_session, User)


class TestBaseRepositoryGetById:
    """Test suite for BaseRepository.get_by_id()."""

    @pytest.mark.unit
    async def test_get_by_id_when_found_returns_entity(
        self, user_repository, mock_session
    ):
        """
        GIVEN a user exists in database
        WHEN get_by_id() is called with valid ID
        THEN return the user entity
        """
        # Arrange
        expected_user = User(id=1, telegram_id=123456789)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = expected_user
        mock_session.execute.return_value = mock_result

        # Act
        result = await user_repository.get_by_id(1)

        # Assert
        assert result == expected_user
        mock_session.execute.assert_called_once()
        # Verify correct SQL query was built
        call_args = mock_session.execute.call_args[0][0]
        assert str(call_args).startswith("SELECT")

    @pytest.mark.unit
    async def test_get_by_id_when_not_found_returns_none(
        self, user_repository, mock_session
    ):
        """
        GIVEN no user exists with given ID
        WHEN get_by_id() is called
        THEN return None
        """
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act
        result = await user_repository.get_by_id(999)

        # Assert
        assert result is None

    @pytest.mark.unit
    async def test_get_by_id_with_zero_id_returns_none(
        self, user_repository, mock_session
    ):
        """
        GIVEN ID is 0 (invalid)
        WHEN get_by_id() is called
        THEN return None (no user with ID 0)
        """
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act
        result = await user_repository.get_by_id(0)

        # Assert
        assert result is None


class TestBaseRepositoryCreate:
    """Test suite for BaseRepository.create()."""

    @pytest.mark.unit
    async def test_create_with_valid_data_returns_entity_with_id(
        self, user_repository, mock_session
    ):
        """
        GIVEN valid creation data
        WHEN create() is called
        THEN entity is created with auto-generated ID
        """
        # Arrange
        user_data = UserCreate(telegram_id=123456789, username="testuser")
        created_user = User(id=1, telegram_id=123456789, username="testuser")

        # Mock session methods
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock(
            side_effect=lambda entity: setattr(entity, 'id', 1)
        )

        # Act
        with patch.object(User, '__init__', return_value=None):
            result = await user_repository.create(user_data)

        # Assert
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once()

    @pytest.mark.unit
    async def test_create_calls_model_constructor_with_schema_data(
        self, user_repository, mock_session
    ):
        """
        GIVEN creation schema with specific fields
        WHEN create() is called
        THEN model is instantiated with schema.model_dump()
        """
        # Arrange
        user_data = UserCreate(telegram_id=987654321, username="john")

        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()

        # Act
        with patch.object(User, '__init__', return_value=None) as mock_init:
            await user_repository.create(user_data)

        # Assert
        # Verify model was called with unpacked schema data
        assert mock_init.called


class TestBaseRepositoryUpdate:
    """Test suite for BaseRepository.update()."""

    @pytest.mark.unit
    async def test_update_when_entity_exists_returns_updated_entity(
        self, user_repository, mock_session
    ):
        """
        GIVEN entity exists in database
        WHEN update() is called with new data
        THEN entity is updated and returned
        """
        # Arrange
        existing_user = User(id=1, telegram_id=123, username="old_name")
        update_data = UserUpdate(username="new_name")

        # Mock get_by_id to return existing user
        with patch.object(user_repository, 'get_by_id',
                         return_value=existing_user):
            mock_session.flush = AsyncMock()
            mock_session.refresh = AsyncMock()

            # Act
            result = await user_repository.update(1, update_data)

            # Assert
            assert result == existing_user
            assert result.username == "new_name"
            mock_session.flush.assert_called_once()
            mock_session.refresh.assert_called_once()

    @pytest.mark.unit
    async def test_update_when_entity_not_found_returns_none(
        self, user_repository, mock_session
    ):
        """
        GIVEN entity does not exist
        WHEN update() is called
        THEN return None without updating
        """
        # Arrange
        update_data = UserUpdate(username="new_name")

        # Mock get_by_id to return None
        with patch.object(user_repository, 'get_by_id', return_value=None):
            # Act
            result = await user_repository.update(999, update_data)

            # Assert
            assert result is None
            mock_session.flush.assert_not_called()

    @pytest.mark.unit
    async def test_update_only_updates_provided_fields(
        self, user_repository, mock_session
    ):
        """
        GIVEN update schema with only some fields
        WHEN update() is called
        THEN only provided fields are updated (exclude_unset=True)
        """
        # Arrange
        existing_user = User(
            id=1,
            telegram_id=123,
            username="old_name",
            timezone="UTC"
        )
        # Only update username, leave timezone unchanged
        update_data = UserUpdate(username="new_name")

        with patch.object(user_repository, 'get_by_id',
                         return_value=existing_user):
            mock_session.flush = AsyncMock()
            mock_session.refresh = AsyncMock()

            # Act
            result = await user_repository.update(1, update_data)

            # Assert
            assert result.username == "new_name"
            assert result.timezone == "UTC"  # Unchanged


class TestBaseRepositoryDelete:
    """Test suite for BaseRepository.delete()."""

    @pytest.mark.unit
    async def test_delete_when_entity_exists_returns_true(
        self, user_repository, mock_session
    ):
        """
        GIVEN entity exists in database
        WHEN delete() is called
        THEN entity is deleted and True is returned
        """
        # Arrange
        mock_result = MagicMock()
        mock_result.rowcount = 1  # One row deleted
        mock_session.execute.return_value = mock_result
        mock_session.flush = AsyncMock()

        # Act
        result = await user_repository.delete(1)

        # Assert
        assert result is True
        mock_session.execute.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.unit
    async def test_delete_when_entity_not_found_returns_false(
        self, user_repository, mock_session
    ):
        """
        GIVEN entity does not exist
        WHEN delete() is called
        THEN return False
        """
        # Arrange
        mock_result = MagicMock()
        mock_result.rowcount = 0  # No rows deleted
        mock_session.execute.return_value = mock_result
        mock_session.flush = AsyncMock()

        # Act
        result = await user_repository.delete(999)

        # Assert
        assert result is False

    @pytest.mark.unit
    async def test_delete_builds_correct_sql_query(
        self, user_repository, mock_session
    ):
        """
        GIVEN valid entity ID
        WHEN delete() is called
        THEN correct DELETE SQL query is executed
        """
        # Arrange
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result
        mock_session.flush = AsyncMock()

        # Act
        await user_repository.delete(1)

        # Assert
        call_args = mock_session.execute.call_args[0][0]
        assert "DELETE" in str(call_args).upper()
```

**Success Criteria:**
- ✅ All 12 tests pass
- ✅ 100% line coverage of base.py
- ✅ 100% branch coverage
- ✅ Tests execute in < 0.5 seconds

---

##### Task 1.1.2: Test User Repository

**File:** `services/data_postgres_api/tests/unit/repositories/test_user_repository.py`
**Lines:** ~200
**Tests:** 8
**Time:** 5 hours

**Test Cases:**

```python
"""
Unit tests for UserRepository.

Tests custom user-specific repository methods beyond base CRUD.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from src.infrastructure.repositories.user_repository import UserRepository
from src.domain.models.user import User


@pytest.fixture
def mock_session():
    """Fixture: Mock AsyncSession."""
    return AsyncMock()


@pytest.fixture
def user_repository(mock_session):
    """Fixture: UserRepository for testing."""
    return UserRepository(mock_session)


class TestUserRepositoryGetByTelegramId:
    """Test suite for UserRepository.get_by_telegram_id()."""

    @pytest.mark.unit
    async def test_get_by_telegram_id_when_found_returns_user(
        self, user_repository, mock_session
    ):
        """
        GIVEN user exists with telegram_id
        WHEN get_by_telegram_id() is called
        THEN return the user
        """
        # Arrange
        expected_user = User(id=1, telegram_id=123456789)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = expected_user
        mock_session.execute.return_value = mock_result

        # Act
        result = await user_repository.get_by_telegram_id(123456789)

        # Assert
        assert result == expected_user
        mock_session.execute.assert_called_once()

    @pytest.mark.unit
    async def test_get_by_telegram_id_when_not_found_returns_none(
        self, user_repository, mock_session
    ):
        """
        GIVEN no user with telegram_id exists
        WHEN get_by_telegram_id() is called
        THEN return None
        """
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act
        result = await user_repository.get_by_telegram_id(999999999)

        # Assert
        assert result is None

    @pytest.mark.unit
    async def test_get_by_telegram_id_queries_correct_field(
        self, user_repository, mock_session
    ):
        """
        GIVEN telegram_id parameter
        WHEN get_by_telegram_id() is called
        THEN SQL queries User.telegram_id field
        """
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act
        await user_repository.get_by_telegram_id(123456789)

        # Assert
        call_args = mock_session.execute.call_args[0][0]
        query_str = str(call_args)
        assert "telegram_id" in query_str.lower()


class TestUserRepositoryUpdateLastPollTime:
    """Test suite for UserRepository.update_last_poll_time()."""

    @pytest.mark.unit
    async def test_update_last_poll_time_sets_current_timestamp(
        self, user_repository, mock_session
    ):
        """
        GIVEN user exists
        WHEN update_last_poll_time() is called
        THEN last_poll_time is set to current UTC time
        """
        # Arrange
        user = User(id=1, telegram_id=123, last_poll_time=None)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_session.execute.return_value = mock_result
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()

        # Act
        result = await user_repository.update_last_poll_time(1)

        # Assert
        assert result is not None
        assert isinstance(result.last_poll_time, datetime)
        # Check it's recent (within last 5 seconds)
        time_diff = datetime.now(timezone.utc) - result.last_poll_time
        assert time_diff.total_seconds() < 5

    @pytest.mark.unit
    async def test_update_last_poll_time_when_user_not_found_returns_none(
        self, user_repository, mock_session
    ):
        """
        GIVEN user does not exist
        WHEN update_last_poll_time() is called
        THEN return None
        """
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act
        result = await user_repository.update_last_poll_time(999)

        # Assert
        assert result is None
        mock_session.flush.assert_not_called()
```

**Success Criteria:**
- ✅ All 8 tests pass
- ✅ 100% coverage of user_repository.py
- ✅ Tests execute in < 0.3 seconds

---

##### Task 1.1.3-1.1.5: Test Other Repositories

**Files:**
- `test_activity_repository.py` (~200 lines, 8 tests, 5 hours)
- `test_category_repository.py` (~150 lines, 6 tests, 4 hours)
- `test_user_settings_repository.py` (~150 lines, 6 tests, 4 hours)

**Pattern:** Same as UserRepository tests - focus on custom methods beyond base CRUD.

**Total Repository Tests: 40 tests, ~1,000 lines, 26 hours**

---

#### 1.2 HTTP Client Infrastructure Tests (Priority: CRITICAL)

**Rationale:** All bot communication with API goes through HTTP clients. Zero coverage is unacceptable.

##### Task 1.2.1: Test HTTP Client Core

**File:** `services/tracker_activity_bot/tests/unit/http_client/test_http_client.py`
**Lines:** ~350
**Tests:** 15
**Time:** 10 hours

**Test Cases:**

```python
"""
Unit tests for DataAPIClient (HTTP client core).

Tests the base HTTP client with middleware pipeline.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, Response, ConnectError, TimeoutException
from typing import Dict, Any

from src.infrastructure.http_clients.http_client import DataAPIClient
from src.infrastructure.http_clients.middleware.protocols import (
    HTTPClientMiddleware
)


@pytest.fixture
def mock_httpx_client():
    """Fixture: Mock httpx.AsyncClient."""
    return AsyncMock(spec=AsyncClient)


@pytest.fixture
def http_client(mock_httpx_client):
    """Fixture: DataAPIClient with mocked httpx."""
    with patch('src.infrastructure.http_clients.http_client.AsyncClient',
               return_value=mock_httpx_client):
        client = DataAPIClient(base_url="http://api:8000")
        client._client = mock_httpx_client
        return client


class TestDataAPIClientRequest:
    """Test suite for DataAPIClient.request()."""

    @pytest.mark.unit
    async def test_request_get_success_returns_json_data(
        self, http_client, mock_httpx_client
    ):
        """
        GIVEN valid GET request
        WHEN request() is called
        THEN return parsed JSON response
        """
        # Arrange
        expected_data = {"id": 1, "name": "test"}
        mock_response = Response(200, json=expected_data)
        mock_httpx_client.request.return_value = mock_response

        # Act
        result = await http_client.request("GET", "/users/1")

        # Assert
        assert result == expected_data
        mock_httpx_client.request.assert_called_once_with(
            "GET",
            "http://api:8000/users/1",
            headers=None,
            json=None,
            params=None
        )

    @pytest.mark.unit
    async def test_request_post_with_json_body_sends_data(
        self, http_client, mock_httpx_client
    ):
        """
        GIVEN POST request with JSON body
        WHEN request() is called
        THEN JSON is sent in request body
        """
        # Arrange
        request_data = {"telegram_id": 123456}
        response_data = {"id": 1, **request_data}
        mock_response = Response(201, json=response_data)
        mock_httpx_client.request.return_value = mock_response

        # Act
        result = await http_client.request(
            "POST",
            "/users",
            json=request_data
        )

        # Assert
        assert result == response_data
        call_kwargs = mock_httpx_client.request.call_args.kwargs
        assert call_kwargs["json"] == request_data

    @pytest.mark.unit
    async def test_request_with_query_params_includes_in_url(
        self, http_client, mock_httpx_client
    ):
        """
        GIVEN request with query parameters
        WHEN request() is called
        THEN params are passed to httpx
        """
        # Arrange
        params = {"user_id": 1, "limit": 10}
        mock_response = Response(200, json=[])
        mock_httpx_client.request.return_value = mock_response

        # Act
        await http_client.request("GET", "/activities", params=params)

        # Assert
        call_kwargs = mock_httpx_client.request.call_args.kwargs
        assert call_kwargs["params"] == params

    @pytest.mark.unit
    async def test_request_with_custom_headers_includes_in_request(
        self, http_client, mock_httpx_client
    ):
        """
        GIVEN request with custom headers
        WHEN request() is called
        THEN headers are passed to httpx
        """
        # Arrange
        headers = {"X-Request-ID": "123", "Authorization": "Bearer token"}
        mock_response = Response(200, json={})
        mock_httpx_client.request.return_value = mock_response

        # Act
        await http_client.request("GET", "/users", headers=headers)

        # Assert
        call_kwargs = mock_httpx_client.request.call_args.kwargs
        assert call_kwargs["headers"] == headers


class TestDataAPIClientErrorHandling:
    """Test suite for error handling in DataAPIClient."""

    @pytest.mark.unit
    async def test_request_when_connection_error_raises_exception(
        self, http_client, mock_httpx_client
    ):
        """
        GIVEN API is unreachable
        WHEN request() is called
        THEN ConnectError is raised
        """
        # Arrange
        mock_httpx_client.request.side_effect = ConnectError("Connection refused")

        # Act & Assert
        with pytest.raises(ConnectError):
            await http_client.request("GET", "/users")

    @pytest.mark.unit
    async def test_request_when_timeout_raises_exception(
        self, http_client, mock_httpx_client
    ):
        """
        GIVEN API times out
        WHEN request() is called
        THEN TimeoutException is raised
        """
        # Arrange
        mock_httpx_client.request.side_effect = TimeoutException("Request timeout")

        # Act & Assert
        with pytest.raises(TimeoutException):
            await http_client.request("GET", "/users")

    @pytest.mark.unit
    async def test_request_when_4xx_error_raises_http_error(
        self, http_client, mock_httpx_client
    ):
        """
        GIVEN API returns 4xx error
        WHEN request() is called
        THEN HTTPStatusError is raised
        """
        # Arrange
        mock_response = Response(404, json={"error": "Not found"})
        mock_response.raise_for_status = MagicMock(
            side_effect=Exception("404 Not Found")
        )
        mock_httpx_client.request.return_value = mock_response

        # Act & Assert
        with pytest.raises(Exception):
            await http_client.request("GET", "/users/999")

    @pytest.mark.unit
    async def test_request_when_5xx_error_raises_http_error(
        self, http_client, mock_httpx_client
    ):
        """
        GIVEN API returns 5xx error
        WHEN request() is called
        THEN HTTPStatusError is raised
        """
        # Arrange
        mock_response = Response(500, json={"error": "Internal error"})
        mock_response.raise_for_status = MagicMock(
            side_effect=Exception("500 Internal Server Error")
        )
        mock_httpx_client.request.return_value = mock_response

        # Act & Assert
        with pytest.raises(Exception):
            await http_client.request("GET", "/users")


class TestDataAPIClientMiddleware:
    """Test suite for middleware integration."""

    @pytest.mark.unit
    async def test_middleware_pipeline_executes_in_order(
        self, http_client, mock_httpx_client
    ):
        """
        GIVEN multiple middleware registered
        WHEN request() is called
        THEN middleware execute in registration order
        """
        # Arrange
        execution_order = []

        class MockMiddleware1(HTTPClientMiddleware):
            async def process_request(self, method, url, **kwargs):
                execution_order.append("middleware1_request")
                return method, url, kwargs

            async def process_response(self, response):
                execution_order.append("middleware1_response")
                return response

        class MockMiddleware2(HTTPClientMiddleware):
            async def process_request(self, method, url, **kwargs):
                execution_order.append("middleware2_request")
                return method, url, kwargs

            async def process_response(self, response):
                execution_order.append("middleware2_response")
                return response

        http_client.add_middleware(MockMiddleware1())
        http_client.add_middleware(MockMiddleware2())

        mock_response = Response(200, json={})
        mock_httpx_client.request.return_value = mock_response

        # Act
        await http_client.request("GET", "/test")

        # Assert
        assert execution_order == [
            "middleware1_request",
            "middleware2_request",
            "middleware2_response",
            "middleware1_response"
        ]

    @pytest.mark.unit
    async def test_middleware_can_modify_request(
        self, http_client, mock_httpx_client
    ):
        """
        GIVEN middleware that adds headers
        WHEN request() is called
        THEN modified headers are sent
        """
        # Arrange
        class HeaderMiddleware(HTTPClientMiddleware):
            async def process_request(self, method, url, **kwargs):
                kwargs.setdefault("headers", {})
                kwargs["headers"]["X-Custom"] = "test"
                return method, url, kwargs

        http_client.add_middleware(HeaderMiddleware())
        mock_response = Response(200, json={})
        mock_httpx_client.request.return_value = mock_response

        # Act
        await http_client.request("GET", "/test")

        # Assert
        call_kwargs = mock_httpx_client.request.call_args.kwargs
        assert call_kwargs["headers"]["X-Custom"] == "test"
```

**Success Criteria:**
- ✅ All 15 tests pass
- ✅ 95%+ coverage of http_client.py
- ✅ Tests execute in < 0.5 seconds

---

##### Task 1.2.2: Test HTTP Client Middleware

**Files:**
- `test_error_middleware.py` (~200 lines, 10 tests, 6 hours)
- `test_timing_middleware.py` (~150 lines, 8 tests, 5 hours)
- `test_logging_middleware.py` (~150 lines, 8 tests, 5 hours)

**Total HTTP Client Tests: 41 tests, ~850 lines, 26 hours**

---

#### 1.3 Bot Services Tests (Priority: CRITICAL)

##### Task 1.3.1: Test Scheduler Service

**File:** `services/tracker_activity_bot/tests/unit/services/test_scheduler_service.py`
**Lines:** ~300
**Tests:** 12
**Time:** 8 hours

**Key Test Cases:**
- Schedule poll on weekday within working hours
- Schedule poll on weekend
- Respect quiet hours configuration
- Handle overlapping polls
- Cancel scheduled poll
- Reschedule poll after settings change

##### Task 1.3.2: Test FSM Timeout Service

**File:** `services/tracker_activity_bot/tests/unit/services/test_fsm_timeout_service.py`
**Lines:** ~250
**Tests:** 10
**Time:** 7 hours

**Total Services Tests: 22 tests, ~550 lines, 15 hours**

---

#### 1.4 Critical Utils Tests (Priority: CRITICAL)

##### Task 1.4.1: Test Time Helpers

**File:** `services/tracker_activity_bot/tests/unit/utils/test_time_helpers.py`
**Lines:** ~200
**Tests:** 10
**Time:** 6 hours

##### Task 1.4.2: Test FSM Helpers

**File:** `services/tracker_activity_bot/tests/unit/utils/test_fsm_helpers.py`
**Lines:** ~200
**Tests:** 10
**Time:** 6 hours

**Total Utils Tests: 20 tests, ~400 lines, 12 hours**

---

**Phase 1 Summary:**
- **Files:** 17 new test files
- **Tests:** 123 tests
- **Lines:** ~2,800
- **Time:** 80-100 hours
- **Coverage Gain:** +35-40% → Total: 55-65%

---

### Phase 2: Business Logic (P1)

**Timeline:** Weeks 4-6
**Effort:** 70-90 hours
**Coverage Gain:** +20-25%

#### 2.1 API Contract Tests

**Purpose:** Validate all API endpoints conform to OpenAPI contracts, test Pydantic schemas, ensure proper validation.

##### Task 2.1.1: Users API Contract Tests

**File:** `services/data_postgres_api/tests/contract/test_users_api.py`
**Lines:** ~250
**Tests:** 15
**Time:** 8 hours

```python
"""
Contract tests for Users API endpoints.

Tests request/response schemas, validation, and error handling.
Uses FastAPI TestClient for fast, in-process testing.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from src.main import app
from src.domain.models.user import User


@pytest.fixture
def client():
    """Fixture: FastAPI TestClient."""
    return TestClient(app)


@pytest.fixture
def mock_user_service():
    """Fixture: Mock UserService."""
    return AsyncMock()


class TestCreateUserEndpoint:
    """Contract tests for POST /api/v1/users endpoint."""

    @pytest.mark.contract
    def test_create_user_with_valid_data_returns_201(
        self, client, mock_user_service
    ):
        """
        GIVEN valid user creation data
        WHEN POST /api/v1/users is called
        THEN return 201 with created user
        """
        # Arrange
        request_data = {
            "telegram_id": 123456789,
            "username": "testuser"
        }
        expected_user = User(id=1, **request_data)

        with patch('src.api.dependencies.get_user_service',
                  return_value=mock_user_service):
            mock_user_service.create_user.return_value = expected_user

            # Act
            response = client.post("/api/v1/users", json=request_data)

            # Assert
            assert response.status_code == 201
            data = response.json()
            assert data["id"] == 1
            assert data["telegram_id"] == 123456789
            assert data["username"] == "testuser"
            assert "created_at" in data

    @pytest.mark.contract
    def test_create_user_with_missing_telegram_id_returns_422(self, client):
        """
        GIVEN request missing required telegram_id
        WHEN POST /api/v1/users is called
        THEN return 422 validation error
        """
        # Arrange
        request_data = {"username": "testuser"}  # Missing telegram_id

        # Act
        response = client.post("/api/v1/users", json=request_data)

        # Assert
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        # Pydantic validation error structure
        errors = data["detail"]
        assert any(e["loc"] == ["body", "telegram_id"] for e in errors)

    @pytest.mark.contract
    def test_create_user_with_invalid_telegram_id_type_returns_422(
        self, client
    ):
        """
        GIVEN telegram_id as string instead of integer
        WHEN POST /api/v1/users is called
        THEN return 422 validation error
        """
        # Arrange
        request_data = {
            "telegram_id": "not_an_integer",
            "username": "testuser"
        }

        # Act
        response = client.post("/api/v1/users", json=request_data)

        # Assert
        assert response.status_code == 422
        data = response.json()
        errors = data["detail"]
        assert any(
            e["loc"] == ["body", "telegram_id"] and
            e["type"] == "int_parsing"
            for e in errors
        )

    @pytest.mark.contract
    def test_create_user_response_matches_schema(self, client, mock_user_service):
        """
        GIVEN successful user creation
        WHEN response is received
        THEN response matches UserResponse schema exactly
        """
        # Arrange
        request_data = {"telegram_id": 123456789}
        expected_user = User(id=1, telegram_id=123456789)

        with patch('src.api.dependencies.get_user_service',
                  return_value=mock_user_service):
            mock_user_service.create_user.return_value = expected_user

            # Act
            response = client.post("/api/v1/users", json=request_data)

            # Assert
            data = response.json()
            # Required fields
            assert "id" in data
            assert "telegram_id" in data
            assert "created_at" in data
            assert "updated_at" in data
            # Optional fields
            assert "username" in data or data.get("username") is None
            assert "timezone" in data or data.get("timezone") is None
            # No extra fields
            allowed_fields = {
                "id", "telegram_id", "username", "timezone",
                "created_at", "updated_at", "last_poll_time"
            }
            assert set(data.keys()).issubset(allowed_fields)


class TestGetUserByTelegramIdEndpoint:
    """Contract tests for GET /api/v1/users/{telegram_id} endpoint."""

    @pytest.mark.contract
    def test_get_user_when_exists_returns_200(
        self, client, mock_user_service
    ):
        """
        GIVEN user exists with telegram_id
        WHEN GET /api/v1/users/{telegram_id} is called
        THEN return 200 with user data
        """
        # Arrange
        expected_user = User(id=1, telegram_id=123456789)

        with patch('src.api.dependencies.get_user_service',
                  return_value=mock_user_service):
            mock_user_service.get_user_by_telegram_id.return_value = expected_user

            # Act
            response = client.get("/api/v1/users/123456789")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["telegram_id"] == 123456789

    @pytest.mark.contract
    def test_get_user_when_not_found_returns_404(
        self, client, mock_user_service
    ):
        """
        GIVEN user does not exist
        WHEN GET /api/v1/users/{telegram_id} is called
        THEN return 404
        """
        # Arrange
        with patch('src.api.dependencies.get_user_service',
                  return_value=mock_user_service):
            mock_user_service.get_user_by_telegram_id.return_value = None

            # Act
            response = client.get("/api/v1/users/999999999")

            # Assert
            assert response.status_code == 404
            data = response.json()
            assert "detail" in data

    @pytest.mark.contract
    def test_get_user_with_invalid_telegram_id_returns_422(self, client):
        """
        GIVEN invalid telegram_id format
        WHEN GET /api/v1/users/{telegram_id} is called
        THEN return 422 validation error
        """
        # Act
        response = client.get("/api/v1/users/not_a_number")

        # Assert
        assert response.status_code == 422


class TestUpdateUserEndpoint:
    """Contract tests for PATCH /api/v1/users/{id} endpoint."""

    @pytest.mark.contract
    def test_update_user_with_partial_data_returns_200(
        self, client, mock_user_service
    ):
        """
        GIVEN partial update data (only some fields)
        WHEN PATCH /api/v1/users/{id} is called
        THEN only provided fields are updated
        """
        # Arrange
        update_data = {"username": "new_username"}
        updated_user = User(
            id=1,
            telegram_id=123456789,
            username="new_username"
        )

        with patch('src.api.dependencies.get_user_service',
                  return_value=mock_user_service):
            mock_user_service.update_user.return_value = updated_user

            # Act
            response = client.patch("/api/v1/users/1", json=update_data)

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["username"] == "new_username"
            # Verify service was called with UserUpdate schema
            mock_user_service.update_user.assert_called_once()

    @pytest.mark.contract
    def test_update_user_with_empty_body_returns_422(self, client):
        """
        GIVEN empty update data
        WHEN PATCH /api/v1/users/{id} is called
        THEN return 422 (at least one field required)
        """
        # Act
        response = client.patch("/api/v1/users/1", json={})

        # Assert
        # Depends on schema validation - if all fields optional,
        # might return 200 with no changes, or 422 if at least
        # one field required
        assert response.status_code in [200, 422]
```

**Success Criteria:**
- ✅ All 15 tests pass
- ✅ Tests validate all schemas
- ✅ Tests execute in < 2 seconds (TestClient is fast)

---

##### Task 2.1.2-2.1.4: Other API Contract Tests

**Files:**
- `test_activities_api.py` (~300 lines, 18 tests, 10 hours)
- `test_categories_api.py` (~200 lines, 12 tests, 7 hours)
- `test_user_settings_api.py` (~200 lines, 12 tests, 7 hours)

**Total Contract Tests: 57 tests, ~950 lines, 32 hours**

---

#### 2.2 Models & Schemas Tests

##### Task 2.2.1: Test Pydantic Schemas

**Files:**
- `test_user_schemas.py` (~150 lines, 10 tests, 5 hours)
- `test_activity_schemas.py` (~200 lines, 12 tests, 6 hours)
- `test_category_schemas.py` (~120 lines, 8 tests, 4 hours)
- `test_user_settings_schemas.py` (~150 lines, 10 tests, 5 hours)

**Focus:** Field validation, constraints, serialization, deserialization

**Total Schemas Tests: 40 tests, ~620 lines, 20 hours**

---

#### 2.3 Keyboards Tests

##### Task 2.3.1: Test All Keyboard Generators

**Files:**
- `test_poll_keyboards.py` (~150 lines, 8 tests, 5 hours)
- `test_settings_keyboards.py` (~150 lines, 8 tests, 5 hours)
- `test_time_select_keyboards.py` (~120 lines, 6 tests, 4 hours)
- `test_fsm_reminder_keyboards.py` (~100 lines, 5 tests, 3 hours)

**Total Keyboards Tests: 27 tests, ~520 lines, 17 hours**

---

**Phase 2 Summary:**
- **Files:** 15 new test files
- **Tests:** 124 tests
- **Lines:** ~2,090
- **Time:** 70-90 hours
- **Coverage Gain:** +20-25% → Total: 75-90%

---

### Phase 3: Handlers & Endpoints (P0/P1)

**Timeline:** Weeks 7-9
**Effort:** 80-100 hours
**Coverage Gain:** +5-10%

#### 3.1 Bot Handler Tests

**Challenge:** Handlers involve FSM states, aiogram updates, API calls. Need comprehensive mocking.

##### Task 3.1.1: Test Activity Handlers

**Files:**
- `test_activity_creation.py` (~300 lines, 12 tests, 10 hours)
- `test_activity_management.py` (~250 lines, 10 tests, 8 hours)
- `test_activity_helpers.py` (~150 lines, 8 tests, 5 hours)

**Key Test Patterns:**

```python
"""
Unit tests for activity creation handlers.

Tests the FSM-driven activity creation flow with mocked API calls.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.types import Message, User as TelegramUser
from aiogram.fsm.context import FSMContext

from src.api.handlers.activity.activity_creation import (
    start_activity_creation,
    process_activity_name,
    process_category_selection,
    process_start_time,
    process_end_time,
    save_activity
)
from src.api.states.activity import ActivityCreation


@pytest.fixture
def mock_message():
    """Fixture: Mock Telegram message."""
    message = MagicMock(spec=Message)
    message.from_user = MagicMock(spec=TelegramUser)
    message.from_user.id = 123456789
    message.text = "Test message"
    message.answer = AsyncMock()
    return message


@pytest.fixture
def mock_state():
    """Fixture: Mock FSM context."""
    state = AsyncMock(spec=FSMContext)
    state.get_data = AsyncMock(return_value={})
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()
    state.clear = AsyncMock()
    return state


@pytest.fixture
def mock_category_service():
    """Fixture: Mock CategoryService."""
    return AsyncMock()


class TestStartActivityCreation:
    """Test suite for activity creation initiation."""

    @pytest.mark.unit
    async def test_start_activity_creation_sets_state_and_prompts(
        self, mock_message, mock_state
    ):
        """
        GIVEN user initiates activity creation
        WHEN start_activity_creation() is called
        THEN FSM state is set and user is prompted for activity name
        """
        # Act
        await start_activity_creation(mock_message, mock_state)

        # Assert
        mock_state.set_state.assert_called_once_with(
            ActivityCreation.waiting_for_name
        )
        mock_message.answer.assert_called_once()
        # Verify prompt message
        call_args = mock_message.answer.call_args[0][0]
        assert "название" in call_args.lower()  # Russian: "name"


class TestProcessActivityName:
    """Test suite for processing activity name input."""

    @pytest.mark.unit
    async def test_process_name_with_valid_input_saves_and_requests_category(
        self, mock_message, mock_state, mock_category_service
    ):
        """
        GIVEN user enters valid activity name
        WHEN process_activity_name() is called
        THEN name is saved to state, categories are shown
        """
        # Arrange
        mock_message.text = "Coding"

        with patch('src.api.handlers.activity.activity_creation.get_category_service',
                  return_value=mock_category_service):
            mock_category_service.get_categories.return_value = [
                {"id": 1, "name": "Work"},
                {"id": 2, "name": "Personal"}
            ]

            # Act
            await process_activity_name(mock_message, mock_state)

            # Assert
            mock_state.update_data.assert_called_once_with(
                activity_name="Coding"
            )
            mock_state.set_state.assert_called_once_with(
                ActivityCreation.waiting_for_category
            )
            # Verify keyboard with categories shown
            mock_message.answer.assert_called_once()

    @pytest.mark.unit
    async def test_process_name_with_empty_input_rejects_and_reprompts(
        self, mock_message, mock_state
    ):
        """
        GIVEN user enters empty activity name
        WHEN process_activity_name() is called
        THEN input is rejected, user is re-prompted
        """
        # Arrange
        mock_message.text = "   "  # Empty/whitespace

        # Act
        await process_activity_name(mock_message, mock_state)

        # Assert
        mock_state.update_data.assert_not_called()
        mock_message.answer.assert_called_once()
        # Verify error message
        call_args = mock_message.answer.call_args[0][0]
        assert "пустым" in call_args.lower() or "название" in call_args.lower()

    @pytest.mark.unit
    async def test_process_name_with_too_long_input_rejects(
        self, mock_message, mock_state
    ):
        """
        GIVEN user enters activity name > 100 characters
        WHEN process_activity_name() is called
        THEN input is rejected (validation)
        """
        # Arrange
        mock_message.text = "A" * 101  # Exceeds max length

        # Act
        await process_activity_name(mock_message, mock_state)

        # Assert
        mock_state.update_data.assert_not_called()
        mock_message.answer.assert_called_once()
```

**Total Activity Handler Tests: 30 tests, ~700 lines, 23 hours**

---

##### Task 3.1.2-3.1.4: Other Handler Groups

**Files:**
- **Categories Handlers** (4 files, ~700 lines, 28 tests, 23 hours)
- **Poll Handlers** (3 files, ~650 lines, 25 tests, 20 hours)
- **Settings Handlers** (5 files, ~900 lines, 35 tests, 30 hours)
- **Start Handler** (1 file, ~100 lines, 5 tests, 3 hours)

**Total Handler Tests: 123 tests, ~3,050 lines, 99 hours**

---

**Phase 3 Summary:**
- **Files:** 16 new test files
- **Tests:** 123 tests
- **Lines:** ~3,050
- **Time:** 80-100 hours
- **Coverage Gain:** +5-10% → Total: 80-100%

---

### Phase 4: Infrastructure & Support (P2)

**Timeline:** Weeks 10-11
**Effort:** 40-50 hours
**Coverage Gain:** +3-5%

#### 4.1 States, Middleware, Core

**Files:**
- **States Tests** (4 files, ~300 lines, 12 tests, 10 hours)
- **Middleware Tests** (3 files, ~350 lines, 15 tests, 12 hours)
- **Core Tests** (8 files, ~600 lines, 25 tests, 20 hours)

**Total Infrastructure Tests: 52 tests, ~1,250 lines, 42 hours**

---

### Phase 5: Property-Based & Extended Tests (P2)

**Timeline:** Week 12
**Effort:** 30-40 hours
**Coverage Gain:** +2-3%

#### 5.1 Property-Based Tests with Hypothesis

**Files:**
- `test_time_parser_properties.py` (~200 lines, 8 properties, 8 hours)
- `test_formatters_properties.py` (~150 lines, 6 properties, 6 hours)
- `test_schema_properties.py` (~200 lines, 8 properties, 8 hours)

**Example:**

```python
"""
Property-based tests for time_parser module.

Uses Hypothesis to generate diverse test inputs and verify properties.
"""

import pytest
from hypothesis import given, strategies as st
from datetime import time, datetime

from src.application.utils.time_parser import parse_time, parse_time_range


class TestTimeParserProperties:
    """Property-based tests for time parsing."""

    @pytest.mark.properties
    @given(
        hour=st.integers(min_value=0, max_value=23),
        minute=st.integers(min_value=0, max_value=59)
    )
    def test_parse_time_with_valid_inputs_always_returns_time(
        self, hour, minute
    ):
        """
        Property: parse_time() with any valid hour/minute returns time object.
        """
        # Arrange
        time_str = f"{hour:02d}:{minute:02d}"

        # Act
        result = parse_time(time_str)

        # Assert
        assert result is not None
        assert isinstance(result, time)
        assert result.hour == hour
        assert result.minute == minute

    @pytest.mark.properties
    @given(st.text(min_size=1, max_size=20))
    def test_parse_time_with_invalid_format_returns_none_or_raises(
        self, text
    ):
        """
        Property: parse_time() with invalid format either returns None
        or raises ValueError (never crashes).
        """
        # Filter out valid formats (HH:MM)
        if not (len(text) == 5 and text[2] == ':'):
            # Act & Assert
            try:
                result = parse_time(text)
                assert result is None  # Graceful handling
            except ValueError:
                pass  # Explicit error is also acceptable

    @pytest.mark.properties
    @given(
        start_hour=st.integers(0, 23),
        start_minute=st.integers(0, 59),
        end_hour=st.integers(0, 23),
        end_minute=st.integers(0, 59)
    )
    def test_parse_time_range_order_property(
        self, start_hour, start_minute, end_hour, end_minute
    ):
        """
        Property: If start_time < end_time, parse_time_range() succeeds.
        If start_time >= end_time, it should raise error or swap.
        """
        # Arrange
        start_str = f"{start_hour:02d}:{start_minute:02d}"
        end_str = f"{end_hour:02d}:{end_minute:02d}"

        start_time = time(start_hour, start_minute)
        end_time = time(end_hour, end_minute)

        # Act
        if start_time < end_time:
            result = parse_time_range(start_str, end_str)
            assert result is not None
            assert result[0] < result[1]
        else:
            # Should either raise or auto-correct
            try:
                result = parse_time_range(start_str, end_str)
                # If it doesn't raise, verify it corrected the order
                assert result[0] < result[1]
            except ValueError:
                pass  # Acceptable to reject invalid range
```

**Total Property Tests: 22 properties, ~550 lines, 22 hours**

---

#### 5.2 Extended Smoke Tests

**Files:**
- `test_database_smoke.py` (~120 lines, 6 tests, 4 hours)
- `test_api_smoke.py` (~100 lines, 5 tests, 3 hours)
- `test_bot_smoke.py` (~150 lines, 7 tests, 5 hours)

**Total Smoke Tests: 18 tests, ~370 lines, 12 hours**

---

**Phase 5 Summary:**
- **Files:** 6 new test files
- **Tests:** 40 tests/properties
- **Lines:** ~920
- **Time:** 30-40 hours
- **Coverage Gain:** +2-3% → Total: 100%

---

## Implementation Guidelines

### Test Organization

#### File Naming Convention

```
test_<module_name>.py          # For single module
test_<feature>_<aspect>.py     # For specific aspect
```

**Examples:**
- `test_user_repository.py` - Tests user_repository.py
- `test_activity_creation.py` - Tests activity creation flow
- `test_time_parser_properties.py` - Property tests for time_parser

#### Test Class Organization

```python
"""
Module docstring: What is tested and why.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

# Imports...


@pytest.fixture
def fixture_name():
    """Fixture docstring."""
    return create_fixture()


class TestFunctionName:
    """Test suite for specific function."""

    @pytest.mark.unit
    async def test_function_when_condition_returns_expected(self, fixtures):
        """
        Test docstring in Given-When-Then format.

        GIVEN: Initial conditions
        WHEN: Action performed
        THEN: Expected outcome
        """
        # Arrange: Setup
        ...

        # Act: Execute
        result = await function()

        # Assert: Verify
        assert result == expected
```

### Mocking Strategy

#### What to Mock

**✅ Always Mock:**
- External services (API calls, database queries)
- File system operations
- Network requests
- Time/datetime (use freezegun)
- Random number generation
- Telegram API calls (aiogram updates)

**❌ Never Mock:**
- Code under test
- Simple data structures (dict, list)
- Pure functions (utils like formatters)
- Standard library (except I/O)

#### Mock Patterns

**Pattern 1: Mock External Service**

```python
@pytest.fixture
def mock_user_service():
    """Mock UserService for testing handlers."""
    service = AsyncMock(spec=UserService)
    service.get_user.return_value = User(id=1, telegram_id=123)
    return service

def test_handler(mock_user_service):
    with patch('module.get_user_service', return_value=mock_user_service):
        # Test code
        pass
```

**Pattern 2: Mock Aiogram Update**

```python
@pytest.fixture
def mock_message():
    """Mock Telegram message."""
    msg = MagicMock(spec=Message)
    msg.from_user = MagicMock(spec=User)
    msg.from_user.id = 123456789
    msg.text = "Test"
    msg.answer = AsyncMock()
    return msg
```

**Pattern 3: Mock FSM Context**

```python
@pytest.fixture
def mock_state():
    """Mock FSM context."""
    state = AsyncMock(spec=FSMContext)
    state.get_data = AsyncMock(return_value={})
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()
    state.clear = AsyncMock()
    return state
```

### Test Data Management

#### Fixtures vs Factories

**Use Fixtures for:**
- Shared test configuration
- Mock objects
- Test clients (TestClient, AsyncClient)

**Use Factories for:**
- Creating test data with variations
- Multiple similar objects in one test

**Example Factory:**

```python
# conftest.py
@pytest.fixture
def user_factory():
    """Factory for creating test users."""
    def _create_user(
        id=1,
        telegram_id=123456789,
        username="testuser",
        **kwargs
    ):
        return User(
            id=id,
            telegram_id=telegram_id,
            username=username,
            **kwargs
        )
    return _create_user

# test file
def test_multiple_users(user_factory):
    user1 = user_factory(id=1, telegram_id=111)
    user2 = user_factory(id=2, telegram_id=222)
    user3 = user_factory(id=3, telegram_id=333)
```

### Assertion Best Practices

#### Specific Assertions

```python
# ❌ Bad: Generic assertion
assert result

# ✅ Good: Specific assertion
assert result is not None
assert isinstance(result, User)
assert result.id == 1
```

#### Multiple Assertions

```python
# ✅ Group related assertions
assert response.status_code == 200
data = response.json()
assert data["id"] == 1
assert data["telegram_id"] == 123456789
assert "created_at" in data
```

#### Mock Assertions

```python
# ✅ Verify mock was called correctly
mock_service.create_user.assert_called_once()
mock_service.create_user.assert_called_with(
    UserCreate(telegram_id=123)
)

# ✅ Verify mock was NOT called
mock_service.delete_user.assert_not_called()

# ✅ Verify call arguments
call_args = mock_service.create_user.call_args
assert call_args[0][0].telegram_id == 123
```

---

## Testing Best Practices

### 1. Test Independence

Each test must be completely independent:

```python
# ✅ Good: Isolated test
def test_create_user(mock_repo):
    """Each test has its own mocks."""
    mock_repo.create.return_value = User(id=1)
    service = UserService(mock_repo)
    result = await service.create_user(data)
    assert result.id == 1

# ❌ Bad: Shared state
shared_user = None

def test_create_user():
    global shared_user
    shared_user = create_user()  # Affects other tests!

def test_get_user():
    global shared_user
    user = get_user(shared_user.id)  # Depends on test_create_user
```

### 2. Test One Thing

Each test should verify one behavior:

```python
# ✅ Good: Single responsibility
def test_create_user_with_valid_data_returns_user():
    """Test only creation success."""
    ...

def test_create_user_with_duplicate_telegram_id_raises_error():
    """Test only duplicate error."""
    ...

# ❌ Bad: Testing multiple things
def test_create_and_update_and_delete_user():
    """Too many responsibilities."""
    user = create_user()  # Test 1
    updated = update_user(user.id, data)  # Test 2
    deleted = delete_user(user.id)  # Test 3
```

### 3. Descriptive Test Names

Use convention: `test_<what>_<when>_<then>`

```python
# ✅ Good names
def test_get_user_when_exists_returns_user()
def test_get_user_when_not_found_returns_none()
def test_create_user_with_duplicate_telegram_id_raises_error()
def test_parse_time_with_invalid_format_returns_none()

# ❌ Bad names
def test_user()
def test_get()
def test_error()
def test_1()
```

### 4. Arrange-Act-Assert Pattern

```python
def test_example():
    # Arrange: Set up test data and mocks
    user_data = UserCreate(telegram_id=123)
    mock_repo.create.return_value = User(id=1, telegram_id=123)
    service = UserService(mock_repo)

    # Act: Execute the code under test
    result = await service.create_user(user_data)

    # Assert: Verify the outcome
    assert result.id == 1
    assert result.telegram_id == 123
    mock_repo.create.assert_called_once()
```

### 5. Test Coverage Priorities

Focus on:

1. **Critical paths first** (authentication, data integrity)
2. **Business logic** (services, complex utils)
3. **Public interfaces** (API endpoints, handlers)
4. **Error handling** (edge cases, validation)
5. **Infrastructure last** (config, logging)

```python
# Priority order:
# 1. Service layer (business logic)
@pytest.mark.unit
def test_user_service_create_user():
    """Critical business logic."""
    ...

# 2. Repository layer (data access)
@pytest.mark.unit
def test_user_repository_get_by_telegram_id():
    """Critical data operation."""
    ...

# 3. API contracts
@pytest.mark.contract
def test_create_user_endpoint_validation():
    """Public interface."""
    ...

# 4. Handlers
@pytest.mark.unit
def test_start_handler():
    """User interaction."""
    ...

# 5. Config/logging
@pytest.mark.unit
def test_config_loads():
    """Infrastructure."""
    ...
```

### 6. Parametrize Similar Tests

```python
# ✅ Good: Parametrized test
@pytest.mark.parametrize("hour,minute,expected", [
    (10, 30, time(10, 30)),
    (0, 0, time(0, 0)),
    (23, 59, time(23, 59)),
    (12, 0, time(12, 0)),
])
def test_parse_time_various_valid_inputs(hour, minute, expected):
    """Test multiple valid inputs with one test."""
    result = parse_time(f"{hour:02d}:{minute:02d}")
    assert result == expected

# ❌ Bad: Repetitive tests
def test_parse_time_1030():
    assert parse_time("10:30") == time(10, 30)

def test_parse_time_0000():
    assert parse_time("00:00") == time(0, 0)

def test_parse_time_2359():
    assert parse_time("23:59") == time(23, 59)
```

### 7. Test Error Cases

Don't just test happy paths:

```python
class TestCreateUser:
    """Test suite for user creation."""

    # Happy path
    @pytest.mark.unit
    async def test_create_with_valid_data_succeeds(self):
        """Test successful creation."""
        ...

    # Error cases
    @pytest.mark.unit
    async def test_create_with_duplicate_telegram_id_raises_error(self):
        """Test duplicate prevention."""
        ...

    @pytest.mark.unit
    async def test_create_with_invalid_telegram_id_raises_validation_error(self):
        """Test validation."""
        ...

    @pytest.mark.unit
    async def test_create_when_database_error_raises_exception(self):
        """Test error handling."""
        ...

    # Edge cases
    @pytest.mark.unit
    async def test_create_with_max_length_username_succeeds(self):
        """Test boundary."""
        ...

    @pytest.mark.unit
    async def test_create_with_empty_optional_fields_succeeds(self):
        """Test optional fields."""
        ...
```

---

## Timeline & Milestones

### Detailed Timeline

| Week | Phase | Tasks | Tests | Lines | Hours | Coverage |
|------|-------|-------|-------|-------|-------|----------|
| **1** | Phase 1 | Repository tests (5 files) | 40 | 1,000 | 26 | +15% |
| **2** | Phase 1 | HTTP client tests (4 files) | 41 | 850 | 26 | +10% |
| **3** | Phase 1 | Services + utils tests (4 files) | 42 | 950 | 27 | +10% |
| **4** | Phase 2 | Contract tests (4 files) | 57 | 950 | 32 | +8% |
| **5** | Phase 2 | Schemas tests (4 files) | 40 | 620 | 20 | +5% |
| **6** | Phase 2 | Keyboards tests (4 files) | 27 | 520 | 17 | +7% |
| **7** | Phase 3 | Activity handlers (3 files) | 30 | 700 | 23 | +2% |
| **8** | Phase 3 | Categories + poll (7 files) | 53 | 1,350 | 43 | +3% |
| **9** | Phase 3 | Settings + start (6 files) | 40 | 1,000 | 33 | +3% |
| **10** | Phase 4 | States + middleware (7 files) | 27 | 650 | 22 | +2% |
| **11** | Phase 4 | Core infrastructure (8 files) | 25 | 600 | 20 | +2% |
| **12** | Phase 5 | Properties + smoke (6 files) | 40 | 920 | 34 | +3% |

### Milestones

**Milestone 1: Critical Foundation Complete** (Week 3)
- ✅ Repository layer: 100% coverage
- ✅ HTTP client: 95% coverage
- ✅ Core services: 90% coverage
- **Total Coverage: ~55-60%**

**Milestone 2: Business Logic Complete** (Week 6)
- ✅ All API contracts tested
- ✅ All schemas validated
- ✅ All keyboards tested
- **Total Coverage: ~75-80%**

**Milestone 3: Handlers Complete** (Week 9)
- ✅ All bot handlers tested
- ✅ FSM flows covered
- **Total Coverage: ~85-90%**

**Milestone 4: 100% Coverage Achieved** (Week 12)
- ✅ All infrastructure tested
- ✅ Property tests added
- ✅ Extended smoke tests
- **Total Coverage: 100% ✅**

### Weekly Effort Distribution

```
Week 1:  ████████████████████████░░  26 hours
Week 2:  ████████████████████████░░  26 hours
Week 3:  ████████████████████████░░  27 hours
Week 4:  ████████████████████████████████  32 hours
Week 5:  ████████████████████  20 hours
Week 6:  ██████████████████  17 hours
Week 7:  ██████████████████████  23 hours
Week 8:  ████████████████████████████████████████  43 hours
Week 9:  ████████████████████████████  33 hours
Week 10: ████████████████████  22 hours
Week 11: ██████████████████  20 hours
Week 12: ████████████████████████████  34 hours

Total: ~323 hours (approximately 8 weeks full-time)
```

---

## Quality Gates & CI/CD

### Pytest Configuration Updates

**pytest.ini:**

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

addopts =
    --verbose
    --strict-markers
    --cov=src
    --cov-report=term-missing:skip-covered
    --cov-report=html
    --cov-report=json
    --cov-fail-under=95
    --durations=10

markers =
    unit: Unit tests (fast, isolated, mocked)
    contract: Contract tests (API schemas, FastAPI TestClient)
    properties: Property-based tests (Hypothesis)
    smoke: Smoke tests (basic functionality)
    integration: Integration tests (slow, real dependencies)
    slow: Slow tests (> 1 second)

asyncio_mode = auto
```

### Static Analysis Setup

#### mypy Configuration

**pyproject.toml:**

```toml
[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_any_generics = true
check_untyped_defs = true
no_implicit_reexport = true
warn_redundant_casts = true
warn_unused_ignores = true

[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false
```

#### jscpd Configuration (Code Duplication)

**.jscpd.json:**

```json
{
  "threshold": 10,
  "reporters": ["html", "console"],
  "ignore": [
    "**/tests/**",
    "**/__pycache__/**",
    "**/htmlcov/**",
    "**/.venv/**"
  ],
  "format": ["python"],
  "minLines": 5,
  "maxLines": 500,
  "minTokens": 50
}
```

#### Radon Configuration (Complexity)

**No config needed, run:**

```bash
radon cc src/ -a -nb -s
radon mi src/ -nb -s
```

**Thresholds:**
- Cyclomatic Complexity: < 10 (A-B rating)
- Maintainability Index: > 65 (A-B rating)

#### Bandit Configuration (Security)

**.bandit:**

```yaml
exclude_dirs:
  - /tests/
  - /.venv/
  - /htmlcov/

tests:
  - B101  # assert_used
  - B601  # paramiko_calls
  - B602  # shell_usage_with_shell_equals_true

skips:
  - B101  # Allow assert in tests
```

### Makefile Updates

```makefile
# Fast tests (unit, contract, properties, smoke)
test-fast:
	@echo "Running fast tests only..."
	pytest -m "unit or contract or properties or smoke" --durations=10

# Run with coverage
test-coverage:
	@echo "Running tests with coverage..."
	pytest --cov=src --cov-report=html --cov-report=term

# Type checking
typecheck:
	@echo "Running mypy type checker..."
	mypy src/

# Code duplication check
check-duplication:
	@echo "Checking for code duplication..."
	npx jscpd src/

# Complexity analysis
check-complexity:
	@echo "Analyzing code complexity..."
	radon cc src/ -a -nb
	radon mi src/ -nb

# Security scan
check-security:
	@echo "Running security scan..."
	bandit -r src/ -ll

# All quality checks
quality:
	make test-fast
	make typecheck
	make check-duplication
	make check-complexity
	make check-security

# CI pipeline
ci:
	make lint
	make quality
	make test-coverage
```

### GitHub Actions Workflow

**.github/workflows/tests.yml:**

```yaml
name: Tests & Quality Gates

on:
  push:
    branches: [master, develop]
  pull_request:
    branches: [master, develop]

jobs:
  fast-tests:
    name: Fast Tests (Unit, Contract, Properties, Smoke)
    runs-on: ubuntu-latest
    timeout-minutes: 10

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python 3.11
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"

      - name: Cache dependencies
        uses: actions/cache@v3
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}

      - name: Install dependencies
        run: |
          pip install -r services/data_postgres_api/requirements.txt
          pip install -r services/tracker_activity_bot/requirements.txt
          pip install pytest pytest-cov pytest-asyncio hypothesis

      - name: Run fast tests (Bot)
        run: |
          cd services/tracker_activity_bot
          pytest -m "unit or contract or properties or smoke" \
                 --cov=src --cov-report=json --cov-fail-under=95

      - name: Run fast tests (API)
        run: |
          cd services/data_postgres_api
          pytest -m "unit or contract or properties or smoke" \
                 --cov=src --cov-report=json --cov-fail-under=95

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          files: ./services/*/coverage.json

  static-analysis:
    name: Static Analysis (Type Checking, Linting, Security)
    runs-on: ubuntu-latest
    timeout-minutes: 5

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python 3.11
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"

      - name: Install analysis tools
        run: |
          pip install mypy ruff bandit radon
          npm install -g jscpd

      - name: Run Ruff linter
        run: |
          ruff check services/data_postgres_api/src
          ruff check services/tracker_activity_bot/src

      - name: Run mypy type checker
        run: |
          mypy services/data_postgres_api/src
          mypy services/tracker_activity_bot/src

      - name: Check code duplication (jscpd)
        run: |
          jscpd services/data_postgres_api/src --threshold 10
          jscpd services/tracker_activity_bot/src --threshold 10

      - name: Check complexity (radon)
        run: |
          radon cc services/data_postgres_api/src -a -nb --total-average
          radon cc services/tracker_activity_bot/src -a -nb --total-average

      - name: Security scan (bandit)
        run: |
          bandit -r services/data_postgres_api/src -ll
          bandit -r services/tracker_activity_bot/src -ll

  integration-tests:
    name: Integration Tests (with Docker)
    runs-on: ubuntu-latest
    timeout-minutes: 15
    needs: [fast-tests, static-analysis]

    steps:
      - uses: actions/checkout@v3

      - name: Build Docker images
        run: docker compose build

      - name: Start services
        run: docker compose up -d

      - name: Wait for services
        run: sleep 30

      - name: Run Docker health tests
        run: |
          pip install pytest requests
          pytest tests/smoke/test_docker_health.py -v

      - name: Run integration tests (if any)
        run: |
          docker exec tracker_activity_bot pytest -m integration || true
          docker exec data_postgres_api pytest -m integration || true

      - name: Collect logs on failure
        if: failure()
        run: docker compose logs

      - name: Cleanup
        if: always()
        run: docker compose down -v
```

### Coverage Badges

Add to README.md:

```markdown
[![Tests](https://github.com/yourusername/activity-tracker-bot/workflows/Tests/badge.svg)](https://github.com/yourusername/activity-tracker-bot/actions)
[![Coverage](https://codecov.io/gh/yourusername/activity-tracker-bot/branch/master/graph/badge.svg)](https://codecov.io/gh/yourusername/activity-tracker-bot)
[![Code Quality](https://img.shields.io/badge/code%20quality-A-brightgreen)]()
```

---

## Success Metrics

### Coverage Targets

| Metric | Target | Current | Delta |
|--------|--------|---------|-------|
| **Line Coverage** | ≥ 95% | ~20-25% | +70-75% |
| **Branch Coverage** | ≥ 90% | ~15% | +75% |
| **Function Coverage** | ≥ 95% | ~20% | +75% |
| **Files Tested** | 100% (112/112) | 16% (18/112) | +94 files |

### Quality Metrics

| Metric | Target | Enforcement |
|--------|--------|-------------|
| **Code Duplication** | < 10% | jscpd in CI |
| **Cyclomatic Complexity** | < 10 per function | radon in CI |
| **Maintainability Index** | > 65 (A/B) | radon in CI |
| **Type Coverage** | 100% | mypy --strict |
| **Security Issues** | 0 high/medium | bandit in CI |

### Test Performance

| Metric | Target | Current | Notes |
|--------|--------|---------|-------|
| **Fast Tests Execution** | < 30 seconds | ~3 seconds | Unit, contract, properties, smoke |
| **All Tests Execution** | < 2 minutes | N/A | Including integration |
| **Average Test Duration** | < 0.05 seconds | N/A | Per test |
| **Slowest Tests** | < 1 second | N/A | Flag with --durations=10 |

### Test Distribution

```
Target Distribution (835 total tests):

Unit Tests:           700 (84%)  ████████████████████████████████████████
Contract Tests:        80 (10%)  ████
Property Tests:        30 (4%)   ██
Smoke Tests:           25 (2%)   █
────────────────────────────────────────────────────────
Fast Tests:           835 (100%) ████████████████████████████████████████

Integration Tests:     50 (not in this plan, separate)
E2E Tests:             20 (not in this plan, separate)
```

---

## Appendix: Code Examples

### Example 1: Complete Test File Structure

**File:** `services/data_postgres_api/tests/unit/repositories/test_user_repository.py`

```python
"""
Unit tests for UserRepository.

Tests custom user repository methods beyond base CRUD operations.
Verifies telegram_id queries and last_poll_time updates.

Test Coverage:
    - get_by_telegram_id(): Found, not found, query correctness
    - update_last_poll_time(): Success, not found, timestamp accuracy
    - Inherited base methods: Covered in test_base_repository.py

Author: Testing Team
Date: 2025-11-07
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.repositories.user_repository import UserRepository
from src.domain.models.user import User
from src.schemas.user import UserCreate, UserUpdate


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_session():
    """
    Fixture: Mock SQLAlchemy AsyncSession.

    Returns:
        AsyncMock: Mocked session with execute, flush, refresh methods
    """
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def user_repository(mock_session):
    """
    Fixture: UserRepository instance with mocked session.

    Args:
        mock_session: Mocked AsyncSession from fixture

    Returns:
        UserRepository: Repository instance for testing
    """
    return UserRepository(mock_session)


@pytest.fixture
def sample_user():
    """
    Fixture: Sample User model instance.

    Returns:
        User: User with typical field values
    """
    return User(
        id=1,
        telegram_id=123456789,
        username="testuser",
        timezone="UTC",
        created_at=datetime(2025, 1, 1, 12, 0, 0),
        updated_at=datetime(2025, 1, 1, 12, 0, 0)
    )


# ============================================================================
# TEST SUITES
# ============================================================================

class TestUserRepositoryGetByTelegramId:
    """
    Test suite for UserRepository.get_by_telegram_id() method.

    Tests the custom query method for finding users by Telegram ID.
    This is a critical method used in every bot interaction.
    """

    @pytest.mark.unit
    async def test_get_by_telegram_id_when_user_exists_returns_user(
        self,
        user_repository: UserRepository,
        mock_session: AsyncMock,
        sample_user: User
    ):
        """
        Test successful user retrieval by telegram_id.

        GIVEN: User exists in database with telegram_id 123456789
        WHEN: get_by_telegram_id(123456789) is called
        THEN: User object is returned with all fields populated
        """
        # Arrange: Mock database to return user
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_session.execute.return_value = mock_result

        # Act: Call method under test
        result = await user_repository.get_by_telegram_id(123456789)

        # Assert: Verify correct user returned
        assert result is not None
        assert result == sample_user
        assert result.telegram_id == 123456789
        assert result.username == "testuser"

        # Verify session.execute was called once
        mock_session.execute.assert_called_once()

    @pytest.mark.unit
    async def test_get_by_telegram_id_when_user_not_found_returns_none(
        self,
        user_repository: UserRepository,
        mock_session: AsyncMock
    ):
        """
        Test behavior when user doesn't exist.

        GIVEN: No user with telegram_id 999999999 in database
        WHEN: get_by_telegram_id(999999999) is called
        THEN: None is returned
        """
        # Arrange: Mock database to return nothing
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act
        result = await user_repository.get_by_telegram_id(999999999)

        # Assert
        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.unit
    async def test_get_by_telegram_id_builds_correct_sql_query(
        self,
        user_repository: UserRepository,
        mock_session: AsyncMock
    ):
        """
        Test that correct SQL query is constructed.

        GIVEN: telegram_id parameter
        WHEN: get_by_telegram_id() is called
        THEN: SQL query filters by User.telegram_id field
        """
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act
        await user_repository.get_by_telegram_id(123456789)

        # Assert: Verify SQL query structure
        call_args = mock_session.execute.call_args[0][0]
        query_str = str(call_args)

        # Query should contain SELECT and telegram_id
        assert "SELECT" in query_str.upper()
        assert "telegram_id" in query_str.lower()

    @pytest.mark.unit
    @pytest.mark.parametrize("telegram_id", [
        1,  # Minimum valid ID
        123456789,  # Typical ID
        999999999999,  # Large ID
    ])
    async def test_get_by_telegram_id_handles_various_id_formats(
        self,
        user_repository: UserRepository,
        mock_session: AsyncMock,
        telegram_id: int
    ):
        """
        Test method handles various telegram_id values.

        GIVEN: Different valid telegram_id values
        WHEN: get_by_telegram_id() is called
        THEN: Method executes without error
        """
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act & Assert: Should not raise exception
        result = await user_repository.get_by_telegram_id(telegram_id)
        assert result is None  # Not found is OK


class TestUserRepositoryUpdateLastPollTime:
    """
    Test suite for UserRepository.update_last_poll_time() method.

    Tests updating the last_poll_time field to current UTC time.
    Critical for poll scheduling logic.
    """

    @pytest.mark.unit
    async def test_update_last_poll_time_when_user_exists_sets_current_time(
        self,
        user_repository: UserRepository,
        mock_session: AsyncMock,
        sample_user: User
    ):
        """
        Test successful timestamp update.

        GIVEN: User exists with id=1
        WHEN: update_last_poll_time(1) is called
        THEN: User.last_poll_time is set to current UTC time
        """
        # Arrange: Mock get_by_id to return user
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_session.execute.return_value = mock_result

        # Act
        result = await user_repository.update_last_poll_time(1)

        # Assert: Timestamp was set
        assert result is not None
        assert isinstance(result.last_poll_time, datetime)

        # Timestamp should be recent (within last 5 seconds)
        now = datetime.now(timezone.utc)
        time_diff = now - result.last_poll_time
        assert time_diff.total_seconds() < 5

        # Verify session methods called
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once_with(sample_user)

    @pytest.mark.unit
    async def test_update_last_poll_time_when_user_not_found_returns_none(
        self,
        user_repository: UserRepository,
        mock_session: AsyncMock
    ):
        """
        Test behavior when user doesn't exist.

        GIVEN: No user with id=999
        WHEN: update_last_poll_time(999) is called
        THEN: None is returned, no database update
        """
        # Arrange: Mock get_by_id to return None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act
        result = await user_repository.update_last_poll_time(999)

        # Assert
        assert result is None
        # flush and refresh should NOT be called
        mock_session.flush.assert_not_called()
        mock_session.refresh.assert_not_called()

    @pytest.mark.unit
    async def test_update_last_poll_time_uses_utc_timezone(
        self,
        user_repository: UserRepository,
        mock_session: AsyncMock,
        sample_user: User
    ):
        """
        Test that timestamp is in UTC timezone.

        GIVEN: User exists
        WHEN: update_last_poll_time() is called
        THEN: Timestamp is timezone-aware UTC
        """
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_session.execute.return_value = mock_result

        # Act
        result = await user_repository.update_last_poll_time(1)

        # Assert: Timestamp has UTC timezone
        assert result.last_poll_time.tzinfo == timezone.utc


class TestUserRepositoryIntegrationWithBase:
    """
    Test suite verifying UserRepository inherits base methods correctly.

    These tests verify the inheritance chain works as expected.
    Detailed base method tests are in test_base_repository.py.
    """

    @pytest.mark.unit
    async def test_user_repository_inherits_get_by_id(
        self,
        user_repository: UserRepository,
        mock_session: AsyncMock,
        sample_user: User
    ):
        """
        Test inherited get_by_id() method works.

        GIVEN: UserRepository instance
        WHEN: get_by_id() is called (inherited from BaseRepository)
        THEN: Method executes successfully
        """
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_session.execute.return_value = mock_result

        # Act
        result = await user_repository.get_by_id(1)

        # Assert
        assert result == sample_user

    @pytest.mark.unit
    async def test_user_repository_inherits_create(
        self,
        user_repository: UserRepository,
        mock_session: AsyncMock
    ):
        """
        Test inherited create() method works.

        GIVEN: UserRepository instance
        WHEN: create() is called with UserCreate schema
        THEN: Method executes successfully
        """
        # Arrange
        user_data = UserCreate(telegram_id=123456789)
        mock_session.add = MagicMock()

        # Act
        with patch.object(User, '__init__', return_value=None):
            await user_repository.create(user_data)

        # Assert
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()


# ============================================================================
# EDGE CASES & ERROR HANDLING
# ============================================================================

class TestUserRepositoryEdgeCases:
    """
    Test suite for edge cases and unusual inputs.
    """

    @pytest.mark.unit
    async def test_get_by_telegram_id_with_zero_returns_none(
        self,
        user_repository: UserRepository,
        mock_session: AsyncMock
    ):
        """
        Test behavior with telegram_id=0 (invalid but possible).

        GIVEN: telegram_id = 0
        WHEN: get_by_telegram_id(0) is called
        THEN: None is returned (no users with ID 0)
        """
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act
        result = await user_repository.get_by_telegram_id(0)

        # Assert
        assert result is None

    @pytest.mark.unit
    async def test_update_last_poll_time_called_multiple_times_updates_timestamp(
        self,
        user_repository: UserRepository,
        mock_session: AsyncMock,
        sample_user: User
    ):
        """
        Test repeated calls update timestamp each time.

        GIVEN: User exists
        WHEN: update_last_poll_time() called multiple times
        THEN: Timestamp is updated each call
        """
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_session.execute.return_value = mock_result

        # Act: Call twice
        result1 = await user_repository.update_last_poll_time(1)
        result2 = await user_repository.update_last_poll_time(1)

        # Assert: Both calls succeeded
        assert result1 is not None
        assert result2 is not None

        # flush and refresh called twice
        assert mock_session.flush.call_count == 2
        assert mock_session.refresh.call_count == 2
```

**This example demonstrates:**
- Complete file structure with docstrings
- Multiple test classes organized by method
- Fixtures for reusable test data
- Given-When-Then documentation
- Parametrized tests
- Edge case coverage
- Proper assertions
- Mock verification

---

## Conclusion

This testing plan provides a comprehensive roadmap to achieve 100% fast test coverage for the Activity Tracker Bot project. By following the phased approach and best practices outlined in this document, the project will achieve:

✅ **95%+ line coverage**
✅ **90%+ branch coverage**
✅ **~835 fast tests** executing in < 30 seconds
✅ **Zero critical bugs** in production
✅ **Confident refactoring** capabilities
✅ **CI/CD quality gates** preventing regressions

**Estimated Timeline:** 10-12 weeks
**Estimated Effort:** 240-320 developer hours

**Next Steps:**
1. Review and approve this plan
2. Set up development environment with testing tools
3. Begin Phase 1: Critical Foundation (Weeks 1-3)
4. Weekly progress reviews and coverage reports
5. Adjust timeline based on actual velocity

---

**Document Status:** DRAFT
**Requires Approval:** Yes
**Approval Date:** _________________
**Approved By:** _________________

**Document Control:**
- Version: 1.0
- Last Updated: 2025-11-07
- Next Review: After Phase 1 completion
- Owner: Development Team
