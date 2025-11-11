# Integration Tests Implementation Plan
## Created: 2025-11-11

---

## 📋 Overview

This plan describes the implementation of 90 integration tests across 3 levels:
- **Level 1**: Handler → Service (30 tests, mocked API/DB)
- **Level 2**: Service → API (40 tests, real API/DB)
- **Level 3**: Full Stack (20 tests, complete flows)

**Target execution time**: 18-20 seconds with optimizations
**Target coverage**: 85% integration coverage

---

## 🎯 Implementation Tasks

### Phase 1: Infrastructure Setup

#### Task 1.1: Create Directory Structure
- [ ] Create `tests/integration/` directory
- [ ] Create `tests/integration/level1_handlers/` directory
- [ ] Create `tests/integration/level2_services/` directory
- [ ] Create `tests/integration/level3_flows/` directory
- [ ] Create `__init__.py` files in all directories

**Files to create:**
```
tests/integration/
├── __init__.py
├── conftest.py (will create in Task 1.3)
├── level1_handlers/
│   └── __init__.py
├── level2_services/
│   └── __init__.py
└── level3_flows/
    └── __init__.py
```

#### Task 1.2: Update Requirements
- [ ] Add testcontainers[postgres]==3.7.1
- [ ] Add pytest-xdist==3.5.0
- [ ] Add fakeredis==2.20.1
- [ ] Ensure pytest-asyncio is present
- [ ] Update services/tracker_activity_bot/requirements-test.txt
- [ ] Update services/data_postgres_api/requirements-test.txt

#### Task 1.3: Create Session-Scoped Fixtures
- [ ] Create `tests/integration/conftest.py`
- [ ] Implement `postgres_container` fixture (session-scoped)
- [ ] Implement `redis_container` fixture (session-scoped)
- [ ] Implement `database_url` fixture
- [ ] Implement `api_client` fixture (httpx AsyncClient)
- [ ] Implement `db_session` fixture (SQLAlchemy AsyncSession)
- [ ] Implement `test_user_factory` fixture
- [ ] Implement `fake_redis_storage` fixture for Level 1
- [ ] Implement `mock_bot` fixture (aiogram MockBot)

#### Task 1.4: Configure Pytest
- [ ] Update `pytest.ini` with integration markers
- [ ] Add level1, level2, level3 markers
- [ ] Configure asyncio_mode = auto
- [ ] Add testpaths configuration

#### Task 1.5: Update Makefile
- [ ] Add `test-integration-level1` command
- [ ] Add `test-integration-level2` command
- [ ] Add `test-integration-level3` command
- [ ] Add `test-integration-optimized` command (with -n 4)
- [ ] **Update `test-all-docker` to run unit + integration + smoke**
- [ ] Ensure all commands use proper pytest markers

---

### Phase 2: Level 1 Tests (Handler → Service)

#### Task 2.1: Activity Handlers Tests (8 tests)
- [ ] Create `tests/integration/level1_handlers/test_activity_handlers.py`
- [ ] Test: `test_add_activity_handler_initiates_creation_flow`
- [ ] Test: `test_add_activity_handler_shows_category_keyboard`
- [ ] Test: `test_category_selected_changes_state_to_start_time`
- [ ] Test: `test_start_time_entered_validates_format`
- [ ] Test: `test_end_time_entered_validates_format`
- [ ] Test: `test_end_time_before_start_time_shows_error`
- [ ] Test: `test_activity_confirmation_calls_service`
- [ ] Test: `test_cancel_resets_fsm_state`

#### Task 2.2: Category Handlers Tests (6 tests)
- [ ] Create `tests/integration/level1_handlers/test_category_handlers.py`
- [ ] Test: `test_manage_categories_shows_category_list`
- [ ] Test: `test_add_category_button_initiates_flow`
- [ ] Test: `test_category_name_entered_calls_service`
- [ ] Test: `test_delete_category_shows_confirmation`
- [ ] Test: `test_delete_confirm_calls_service`
- [ ] Test: `test_delete_cancel_returns_to_list`

#### Task 2.3: Poll Handlers Tests (8 tests)
- [ ] Create `tests/integration/level1_handlers/test_poll_handlers.py`
- [ ] Test: `test_enable_polls_shows_interval_keyboard`
- [ ] Test: `test_disable_polls_updates_settings`
- [ ] Test: `test_set_poll_interval_validates_value`
- [ ] Test: `test_set_quiet_hours_shows_time_keyboard`
- [ ] Test: `test_poll_response_saves_activity`
- [ ] Test: `test_poll_skip_records_skip`
- [ ] Test: `test_poll_category_selection_updates_activity`
- [ ] Test: `test_poll_invalid_response_shows_error`

#### Task 2.4: Settings Handlers Tests (5 tests)
- [ ] Create `tests/integration/level1_handlers/test_settings_handlers.py`
- [ ] Test: `test_settings_menu_shows_options`
- [ ] Test: `test_change_weekday_interval_shows_keyboard`
- [ ] Test: `test_change_weekend_interval_shows_keyboard`
- [ ] Test: `test_set_reminder_delay_validates_value`
- [ ] Test: `test_back_to_main_menu_resets_state`

#### Task 2.5: Start Handlers Tests (3 tests)
- [ ] Create `tests/integration/level1_handlers/test_start_handlers.py`
- [ ] Test: `test_start_command_creates_user_if_not_exists`
- [ ] Test: `test_start_command_shows_main_menu`
- [ ] Test: `test_help_command_shows_help_text`

---

### Phase 3: Level 2 Tests (Service → API)

#### Task 3.1: Activity Service Tests (12 tests)
- [ ] Create `tests/integration/level2_services/test_activity_service.py`
- [ ] Test: `test_create_activity_stores_in_database`
- [ ] Test: `test_create_activity_returns_correct_data`
- [ ] Test: `test_get_activity_by_id_returns_activity`
- [ ] Test: `test_get_activity_by_id_not_found_returns_none`
- [ ] Test: `test_update_activity_changes_data`
- [ ] Test: `test_delete_activity_removes_from_database`
- [ ] Test: `test_list_activities_returns_all_user_activities`
- [ ] Test: `test_list_activities_filters_by_date_range`
- [ ] Test: `test_list_activities_filters_by_category`
- [ ] Test: `test_get_activity_stats_calculates_totals`
- [ ] Test: `test_get_daily_stats_groups_by_category`
- [ ] Test: `test_activity_overlapping_validation`

#### Task 3.2: Category Service Tests (8 tests)
- [ ] Create `tests/integration/level2_services/test_category_service.py`
- [ ] Test: `test_create_category_stores_in_database`
- [ ] Test: `test_get_category_by_id_returns_category`
- [ ] Test: `test_get_all_categories_by_user_returns_list`
- [ ] Test: `test_update_category_changes_name`
- [ ] Test: `test_delete_category_removes_from_database`
- [ ] Test: `test_delete_category_with_activities_fails`
- [ ] Test: `test_category_name_uniqueness_per_user`
- [ ] Test: `test_default_categories_created_for_new_user`

#### Task 3.3: User Service Tests (6 tests)
- [ ] Create `tests/integration/level2_services/test_user_service.py`
- [ ] Test: `test_create_user_stores_in_database`
- [ ] Test: `test_get_user_by_telegram_id_returns_user`
- [ ] Test: `test_get_or_create_user_creates_if_not_exists`
- [ ] Test: `test_get_or_create_user_returns_existing`
- [ ] Test: `test_update_user_settings_changes_data`
- [ ] Test: `test_get_user_settings_returns_settings`

#### Task 3.4: Poll Service Tests (8 tests)
- [ ] Create `tests/integration/level2_services/test_poll_service.py`
- [ ] Test: `test_schedule_poll_creates_scheduler_job`
- [ ] Test: `test_send_poll_creates_activity_draft`
- [ ] Test: `test_save_poll_response_completes_activity`
- [ ] Test: `test_skip_poll_records_skip`
- [ ] Test: `test_quiet_hours_prevents_poll`
- [ ] Test: `test_poll_interval_respected`
- [ ] Test: `test_get_poll_statistics_calculates_response_rate`
- [ ] Test: `test_disable_polls_removes_scheduler_job`

#### Task 3.5: Stats Service Tests (6 tests)
- [ ] Create `tests/integration/level2_services/test_stats_service.py`
- [ ] Test: `test_get_daily_stats_groups_by_category`
- [ ] Test: `test_get_weekly_stats_aggregates_days`
- [ ] Test: `test_get_category_stats_calculates_totals`
- [ ] Test: `test_stats_with_no_activities_returns_empty`
- [ ] Test: `test_stats_respects_date_range`
- [ ] Test: `test_stats_calculates_percentages`

---

### Phase 4: Level 3 Tests (Full Stack Flows)

#### Task 4.1: Activity Flow Tests (6 tests)
- [ ] Create `tests/integration/level3_flows/test_activity_flow.py`
- [ ] Test: `test_complete_activity_creation_flow`
- [ ] Test: `test_complete_activity_edit_flow`
- [ ] Test: `test_complete_activity_delete_flow`
- [ ] Test: `test_view_activity_history_flow`
- [ ] Test: `test_filter_activities_by_category_flow`
- [ ] Test: `test_view_statistics_flow`

#### Task 4.2: Poll Flow Tests (5 tests)
- [ ] Create `tests/integration/level3_flows/test_poll_flow.py`
- [ ] Test: `test_enable_polls_receive_respond_flow`
- [ ] Test: `test_quiet_hours_enforcement_flow`
- [ ] Test: `test_poll_skip_and_statistics_flow`
- [ ] Test: `test_change_poll_interval_flow`
- [ ] Test: `test_disable_polls_flow`

#### Task 4.3: Settings Flow Tests (4 tests)
- [ ] Create `tests/integration/level3_flows/test_settings_flow.py`
- [ ] Test: `test_change_weekday_interval_flow`
- [ ] Test: `test_change_weekend_interval_flow`
- [ ] Test: `test_set_quiet_hours_flow`
- [ ] Test: `test_set_reminder_delay_flow`

#### Task 4.4: Category Management Flow Tests (5 tests)
- [ ] Create `tests/integration/level3_flows/test_category_flow.py`
- [ ] Test: `test_create_category_flow`
- [ ] Test: `test_use_new_category_in_activity_flow`
- [ ] Test: `test_edit_category_name_flow`
- [ ] Test: `test_delete_unused_category_flow`
- [ ] Test: `test_prevent_delete_category_with_activities_flow`

---

### Phase 5: Optimization & Verification

#### Task 5.1: Configure Parallel Execution
- [ ] Ensure pytest-xdist is configured
- [ ] Test parallel execution with -n 4
- [ ] Verify session-scoped fixtures work with parallelization
- [ ] Measure execution time

#### Task 5.2: Run All Tests
- [ ] Run `make test-all-docker`
- [ ] Verify all unit tests pass
- [ ] Verify all integration tests pass
- [ ] Verify all smoke tests pass
- [ ] Measure total execution time

#### Task 5.3: Fix Any Issues
- [ ] Fix import errors
- [ ] Fix fixture issues
- [ ] Fix database connection issues
- [ ] Fix API client issues
- [ ] Fix timing issues

#### Task 5.4: Documentation
- [ ] Update README with new test commands
- [ ] Document test structure
- [ ] Document how to add new tests
- [ ] Document troubleshooting tips

---

## 📊 Success Criteria

- ✅ All 90 integration tests created
- ✅ All tests pass successfully
- ✅ Total execution time: 18-22 seconds
- ✅ Integration coverage: 85%+
- ✅ `make test-all-docker` runs all tests (unit + integration + smoke)
- ✅ CI/CD ready (Test Containers work in any environment)

---

## 🚀 Execution Timeline

- **Phase 1**: Infrastructure (1-2 hours)
- **Phase 2**: Level 1 Tests (2-3 hours)
- **Phase 3**: Level 2 Tests (3-4 hours)
- **Phase 4**: Level 3 Tests (2-3 hours)
- **Phase 5**: Optimization (1 hour)

**Total**: 9-13 hours

---

## 📝 Notes

- All mocks for Telegram Bot API (use aiogram MockBot)
- Always mock APScheduler
- Never mock PostgreSQL (use Test Containers)
- Never mock HTTP Client (use real httpx AsyncClient)
- Never mock Business Logic Services
- Redis: Use fakeredis for L1/L2, real Redis for L3

---

## ✅ Checklist Before Completion

- [ ] All 90 tests created and passing
- [ ] `make test-all-docker` works correctly
- [ ] Execution time is within target (18-22 seconds)
- [ ] No flaky tests (run 3 times to verify)
- [ ] Documentation updated
- [ ] Git commit with descriptive message
- [ ] Git push to master branch

---

**Status**: 🚧 In Progress
**Last Updated**: 2025-11-11
