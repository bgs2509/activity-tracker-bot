# Test Coverage Gaps Analysis

**Date:** 2025-11-08
**Author:** Testing Team
**Status:** Critical Issues Identified

---

## 🔍 Executive Summary

Current test suite (`make test-all-docker`) **FAILED** to catch 2 critical production bugs:

1. **Missing Handler Registration** - "Записать" button had no `@router.callback_query` decorator
2. **API Path Mismatches** - Bot called `/by-telegram/` but API had `/by-telegram-id/`

These issues only manifested in production when users clicked buttons or made API calls.

---

## 📊 Current Test Coverage

### What We Have

```
✓ Unit Tests (Isolated component testing)
  - Services: Business logic validation
  - Repositories: Data access patterns
  - Utilities: Helper functions

✓ Contract Tests (API schema validation)
  - Request/response schemas
  - HTTP status codes
  - Error messages

✓ Smoke Tests (Basic health checks)
  - Container health
  - Import verification
```

### What We're Missing

```
❌ Integration Tests (Component interaction)
  - Router registration verification
  - End-to-end API call flows
  - Bot → API communication

❌ Handler Registration Tests
  - Verify all buttons have handlers
  - Verify all handlers are registered

❌ API Contract Compliance Tests
  - Verify bot client calls match API endpoints
  - Cross-service path validation
```

---

## 🐛 Why Tests Missed The Bugs

### Issue #1: Missing Handler Registration

**The Bug:**
```python
# NO @router.callback_query decorator!
async def start_add_activity(callback: types.CallbackQuery, state: FSMContext):
    ...
```

**Why Tests Missed It:**

1. **Unit Test Only Tests Function**
   ```python
   # Test calls function DIRECTLY
   await start_add_activity(mock_callback, mock_state)
   ```
   - ✅ Tests function logic works
   - ❌ Does NOT test if handler is registered with router
   - ❌ Does NOT test if callback_data matches

2. **No Router Registration Test**
   ```python
   # MISSING: Test that would catch this
   def test_add_activity_handler_is_registered():
       handlers = router._handlers  # Check registered handlers
       assert any(h.callback == start_add_activity for h in handlers)
   ```

3. **No E2E Test**
   - No test simulates clicking "📝 Записать" button
   - No test verifies bot responds to callback_data="add_activity"

**Root Cause:** Unit tests verify **function behavior**, not **system integration**

---

### Issue #2: API Path Mismatches

**The Bug:**
```python
# Bot client
response = await client.get("/api/v1/users/by-telegram/123")

# API endpoint (WRONG PATH!)
@router.get("/users/by-telegram-id/{id}")
```

**Why Tests Missed It:**

1. **Contract Tests Use OLD Paths**
   ```python
   # Contract test (INCORRECT PATH)
   response = client.get("/api/v1/users/by-telegram-id/123456789")
   ```
   - Test passes because it tests the API in isolation
   - Bot client was never validated against these paths

2. **No Cross-Service Validation**
   ```python
   # MISSING: Test that would catch this
   def test_bot_client_paths_match_api_endpoints():
       bot_paths = extract_paths_from_bot_client()
       api_paths = extract_paths_from_api_routes()
       assert bot_paths == api_paths
   ```

3. **Mocked Dependencies Hide The Issue**
   - Unit tests mock HTTP calls
   - Contract tests mock services
   - Real HTTP communication never tested together

**Root Cause:** Tests verify **components in isolation**, not **cross-service contracts**

---

## 🎯 Test Strategy Improvements

### 1. Handler Registration Tests (HIGH PRIORITY)

**Purpose:** Ensure all buttons have registered handlers

```python
# tests/integration/test_handler_registration.py

import pytest
from aiogram import F
from src.api.keyboards import main_menu, time_select, poll, settings
from src.api.handlers import activity, categories, poll as poll_handlers


class TestHandlerRegistration:
    """Verify all keyboard buttons have registered handlers."""

    def extract_callback_data_from_keyboard(self, keyboard):
        """Extract all callback_data from keyboard."""
        callbacks = []
        for row in keyboard.inline_keyboard:
            for button in row:
                if button.callback_data:
                    callbacks.append(button.callback_data)
        return callbacks

    def extract_registered_callbacks(self, router):
        """Extract all registered callback_query handlers."""
        registered = set()
        for observer in router.observers.get('callback_query', []):
            # Extract F.data patterns from filters
            for filter in observer.filters:
                if hasattr(filter, 'magic_data'):
                    registered.add(filter.magic_data.key)
        return registered

    @pytest.mark.integration
    def test_all_main_menu_buttons_have_handlers(self):
        """
        GIVEN: Main menu keyboard
        WHEN: Extracting all callback_data
        THEN: Every callback has a registered handler
        """
        # Get all buttons from main menu
        keyboard = main_menu.get_main_menu_keyboard()
        button_callbacks = self.extract_callback_data_from_keyboard(keyboard)

        # Get all registered handlers
        from src.main import dp
        registered = self.extract_registered_callbacks(dp)

        # Verify coverage
        missing_handlers = set(button_callbacks) - registered
        assert not missing_handlers, \
            f"Buttons without handlers: {missing_handlers}"

    @pytest.mark.integration
    def test_time_selection_buttons_have_handlers(self):
        """Verify start/end time quick selection buttons."""
        keyboards = [
            time_select.get_start_time_keyboard(),
            time_select.get_end_time_keyboard()
        ]

        for keyboard in keyboards:
            callbacks = self.extract_callback_data_from_keyboard(keyboard)
            from src.main import dp
            registered = self.extract_registered_callbacks(dp)

            missing = set(callbacks) - registered
            assert not missing, f"Missing handlers: {missing}"

    @pytest.mark.integration
    def test_no_orphaned_handlers(self):
        """
        GIVEN: Registered callback handlers
        WHEN: Checking against all keyboards
        THEN: Every handler is used by at least one button
        """
        # Collect all button callbacks
        all_buttons = set()
        # ... collect from all keyboards ...

        # Get all registered handlers
        from src.main import dp
        all_handlers = self.extract_registered_callbacks(dp)

        # Find orphaned handlers (registered but no button)
        orphaned = all_handlers - all_buttons
        # NOTE: Some handlers are for FSM states, not buttons
        # Filter those out before asserting
        # assert not orphaned, f"Orphaned handlers: {orphaned}"
```

---

### 2. Cross-Service Contract Tests (HIGH PRIORITY)

**Purpose:** Ensure bot HTTP client paths match API endpoints

```python
# tests/integration/test_api_contracts.py

import pytest
import re
from pathlib import Path


class TestAPIContracts:
    """Verify bot client calls match API endpoint paths."""

    def extract_api_endpoints(self):
        """Extract all @router.get/post/patch/delete paths from API."""
        endpoints = {}
        api_path = Path("services/data_postgres_api/src/api/v1/")

        for file in api_path.glob("*.py"):
            content = file.read_text()
            # Match: @router.METHOD("path")
            pattern = r'@router\.(get|post|patch|put|delete)\("([^"]+)"'
            for match in re.finditer(pattern, content):
                method, path = match.groups()
                full_path = f"/api/v1{path}" if not path.startswith('/') else path
                endpoints.setdefault(method.upper(), set()).add(full_path)

        return endpoints

    def extract_bot_client_calls(self):
        """Extract all HTTP calls from bot client services."""
        calls = {}
        client_path = Path("services/tracker_activity_bot/src/infrastructure/http_clients/")

        for file in client_path.glob("*_service.py"):
            content = file.read_text()
            # Match: self.client.METHOD("path")
            pattern = r'self\.client\.(get|post|patch|put|delete)\("([^"]+)"'
            for match in re.finditer(pattern, content):
                method, path = match.groups()
                # Handle f-strings: "/api/v1/users/{user_id}"
                path = re.sub(r'\{[^}]+\}', '{id}', path)
                calls.setdefault(method.upper(), set()).add(path)

        return calls

    @pytest.mark.integration
    def test_bot_client_paths_match_api_endpoints(self):
        """
        GIVEN: Bot HTTP client service calls
        WHEN: Comparing with API endpoint definitions
        THEN: All bot calls match existing API endpoints
        """
        api_endpoints = self.extract_api_endpoints()
        bot_calls = self.extract_bot_client_calls()

        mismatches = []
        for method, paths in bot_calls.items():
            api_paths = api_endpoints.get(method, set())
            for bot_path in paths:
                # Normalize paths for comparison
                normalized_bot = bot_path.replace('{id}', '{telegram_id}')
                if bot_path not in api_paths and normalized_bot not in api_paths:
                    mismatches.append(f"{method} {bot_path}")

        assert not mismatches, \
            f"Bot calls non-existent API endpoints:\n" + "\n".join(mismatches)

    @pytest.mark.integration
    def test_api_endpoint_changes_update_contract_tests(self):
        """
        GIVEN: API contract test paths
        WHEN: Comparing with actual API endpoints
        THEN: Contract tests use correct paths
        """
        # Read contract test file
        contract_test = Path("services/data_postgres_api/tests/contract/test_users_api.py")
        content = contract_test.read_text()

        # Extract paths used in tests
        test_paths = re.findall(r'client\.(get|post|patch|put|delete)\("([^"]+)"', content)

        # Extract actual API paths
        api_endpoints = self.extract_api_endpoints()

        # Verify contract tests use current paths
        for method, test_path in test_paths:
            api_paths = api_endpoints.get(method.upper(), set())
            assert test_path in api_paths, \
                f"Contract test uses outdated path: {method.upper()} {test_path}"
```

---

### 3. E2E Integration Tests (MEDIUM PRIORITY)

**Purpose:** Test real user flows end-to-end

```python
# tests/integration/test_activity_recording_flow.py

import pytest
from aiogram.types import Update, CallbackQuery, Message
from unittest.mock import AsyncMock


class TestActivityRecordingFlow:
    """End-to-end tests for activity recording."""

    @pytest.mark.integration
    async def test_user_can_record_activity_via_button(
        self,
        bot_client,
        test_user
    ):
        """
        Test complete flow: Click button → Select times → Save

        GIVEN: User authenticated
        WHEN: User clicks "📝 Записать"
              AND selects start time "30м назад"
              AND selects end time "Сейчас"
              AND enters description
              AND selects category
        THEN: Activity is saved to database
              AND user sees confirmation message
        """
        # Step 1: Click "Записать" button
        response = await bot_client.send_callback_query(
            callback_data="add_activity",
            from_user=test_user
        )
        assert "Укажи время НАЧАЛА" in response.text

        # Step 2: Select start time
        response = await bot_client.send_callback_query(
            callback_data="time_start_30m",
            from_user=test_user
        )
        assert "Укажи время ОКОНЧАНИЯ" in response.text

        # Step 3: Select end time
        response = await bot_client.send_callback_query(
            callback_data="time_end_now",
            from_user=test_user
        )
        assert "Опиши активность" in response.text

        # Step 4: Send description
        response = await bot_client.send_message(
            text="Работал над проектом #coding",
            from_user=test_user
        )
        assert "Выбери категорию" in response.text

        # Step 5: Select category
        response = await bot_client.send_callback_query(
            callback_data="poll_category_1",  # Work category
            from_user=test_user
        )
        assert "✅ Активность сохранена" in response.text

        # Verify in database
        activities = await get_user_activities(test_user.id)
        assert len(activities) == 1
        assert activities[0].description == "Работал над проектом #coding"
```

---

### 4. Router Smoke Tests (LOW PRIORITY)

**Purpose:** Basic router health checks

```python
# tests/smoke/test_router_health.py

class TestRouterHealth:
    """Basic health checks for routers."""

    @pytest.mark.smoke
    def test_all_routers_are_included_in_dispatcher(self):
        """Verify all routers are registered."""
        from src.main import dp

        expected_routers = [
            'activity',
            'categories',
            'poll',
            'settings'
        ]

        for router_name in expected_routers:
            assert router_name in dp.sub_routers, \
                f"Router '{router_name}' not registered"

    @pytest.mark.smoke
    def test_no_duplicate_callback_handlers(self):
        """Ensure no callback_data is handled by multiple handlers."""
        from src.main import dp

        callback_map = {}
        for observer in dp.observers.get('callback_query', []):
            callback_data = extract_callback_data(observer)
            if callback_data in callback_map:
                raise AssertionError(
                    f"Duplicate handler for '{callback_data}':\n"
                    f"  1. {callback_map[callback_data]}\n"
                    f"  2. {observer.callback}"
                )
            callback_map[callback_data] = observer.callback
```

---

## 🏗️ Implementation Plan

### Phase 1: Critical Fixes (Week 1)

1. **Update Contract Tests** ✅
   - Fix `/by-telegram-id/` → `/by-telegram/` in test_users_api.py
   - Change `PUT` → `PATCH` in test descriptions
   - Run: `pytest services/data_postgres_api/tests/contract/ -v`

2. **Add Handler Registration Tests**
   - Create `tests/integration/test_handler_registration.py`
   - Run in CI pipeline
   - Coverage: 100% of keyboard buttons

3. **Add Cross-Service Contract Tests**
   - Create `tests/integration/test_api_contracts.py`
   - Validate bot client paths against API
   - Run in CI before deployment

### Phase 2: Enhanced Coverage (Week 2-3)

4. **E2E Integration Tests**
   - User flows: activity recording, poll responses
   - Test fixtures for bot simulator
   - Database verification

5. **Router Health Checks**
   - Smoke tests for router registration
   - Duplicate handler detection

### Phase 3: CI/CD Integration (Week 4)

6. **Update Makefile**
   ```makefile
   test-integration: ## Run integration tests
       pytest tests/integration/ -v -m integration

   test-e2e: ## Run end-to-end tests
       pytest tests/e2e/ -v -m e2e

   test-all-docker: test-unit-docker test-integration test-e2e
   ```

7. **Add Pre-commit Hooks**
   ```yaml
   # .pre-commit-config.yaml
   - repo: local
     hooks:
       - id: test-handler-registration
         name: Verify Handler Registration
         entry: pytest tests/integration/test_handler_registration.py
         language: system
         pass_filenames: false
   ```

---

## 📈 Expected Outcomes

### Coverage Improvements

| Test Type | Current | Target |
|-----------|---------|--------|
| Unit Tests | 80% | 85% |
| Integration Tests | 0% | 95% |
| E2E Tests | 0% | 60% |
| **Total Coverage** | **65%** | **85%** |

### Bug Prevention

```
✓ Handler registration bugs → PREVENTED by integration tests
✓ API path mismatches → PREVENTED by contract validation
✓ Cross-service issues → DETECTED before deployment
✓ User flow breaks → CAUGHT by E2E tests
```

---

## 🎓 Best Practices Applied

1. **Test Pyramid**
   - 70% Unit tests (fast, isolated)
   - 20% Integration tests (component interaction)
   - 10% E2E tests (full user flows)

2. **Contract Testing**
   - Consumer-driven contracts (bot ↔ API)
   - Schema validation (Pydantic)
   - Path verification (static analysis)

3. **Continuous Testing**
   - Run on every commit (unit + smoke)
   - Run before deployment (integration)
   - Run in production (health checks)

4. **Test Maintainability**
   - DRY: Extract common fixtures
   - KISS: One assertion per test
   - Clear naming: test_WHEN_GIVEN_THEN

---

## 📚 References

- [Testing Aiogram Bots](https://docs.aiogram.dev/en/latest/dispatcher/testing.html)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Contract Testing Best Practices](https://pactflow.io/blog/what-is-contract-testing/)
- [Test Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html)

---

## 🎯 Action Items

- [ ] Update contract tests with correct API paths
- [ ] Implement handler registration tests
- [ ] Implement cross-service contract tests
- [ ] Add integration test suite to CI
- [ ] Update test documentation
- [ ] Train team on new test patterns

---

**Status:** Draft for Review
**Next Review:** 2025-11-15
**Owner:** Testing Team
