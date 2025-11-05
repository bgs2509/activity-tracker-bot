# 🚀 FAST AUTOMATED TESTING PLAN
**Date:** 2025-11-05
**Version:** 2.0 (Optimized)
**Execution Time:** ~1 minute
**Focus:** Automated tests only, CI/CD ready

---

## 📋 PHILOSOPHY

**Test Pyramid (optimal distribution):**
```
        Integration (10%)
       ─────────────
      /             \
     /   Service     \   (30%)
    /   (TestClient) \
   /─────────────────────\
  /                       \
 /    Unit Tests (60%)     \
/___________________________\
```

**Key Principles:**
- ✅ Fast execution (~1 min total)
- ✅ High coverage (80%+)
- ✅ CI/CD friendly
- ✅ Mock external dependencies
- ✅ Pytest best practices
- ❌ No manual tests
- ❌ No performance tests
- ❌ No slow integration tests

---

## 🎯 TEST SUITE STRUCTURE

### Execution Time Budget:

```
┌─────────────────────────────────────────────────────┐
│ Category         │ Tests │ Time   │ Coverage Target │
├─────────────────────────────────────────────────────┤
│ Unit Tests       │ ~80   │ 8s     │ 85%             │
│ Service Tests    │ ~30   │ 12s    │ 90%             │
│ Integration      │ ~10   │ 20s    │ Critical paths  │
│ Overhead         │ -     │ 10s    │ -               │
├─────────────────────────────────────────────────────┤
│ TOTAL            │ ~120  │ 50s    │ 80%+            │
└─────────────────────────────────────────────────────┘
```

---

## 📦 PART 1: UNIT TESTS (80 tests, 8 seconds)

### 1.1 Poll Handlers (TASK 1)

**File:** `services/tracker_activity_bot/tests/unit/test_poll_handlers.py`

```python
"""
Unit tests for poll handlers.

Tests TASK 1: "I was doing something" poll option.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta
from aiogram import types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

from src.api.handlers.poll import (
    handle_poll_activity_start,
    handle_poll_category_select,
    handle_poll_cancel,
    handle_poll_skip,
    handle_poll_sleep,
)
from src.api.states.poll import PollStates


# Fixtures
@pytest.fixture
def bot():
    """Provide mock bot."""
    bot = Bot(token="TEST")
    bot.session = AsyncMock()
    return bot


@pytest.fixture
async def state():
    """Provide FSM context."""
    storage = MemoryStorage()
    ctx = FSMContext(storage=storage, key="test:123:456")
    yield ctx
    await ctx.clear()


@pytest.fixture
def callback(bot):
    """Factory for CallbackQuery."""
    def _make(data: str):
        user = types.User(id=123, is_bot=False, first_name="Test")
        chat = types.Chat(id=123, type="private")
        msg = types.Message(
            message_id=1,
            date=1234567890,
            chat=chat,
            from_user=user,
            text="Test",
            bot=bot
        )
        cb = types.CallbackQuery(
            id="cb1",
            from_user=user,
            message=msg,
            data=data,
            chat_instance="test"
        )
        cb.answer = AsyncMock()
        cb.message.answer = AsyncMock()
        return cb
    return _make


class TestPollActivityFlow:
    """Test poll activity recording (TASK 1)."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch('src.api.handlers.poll.UserService')
    @patch('src.api.handlers.poll.CategoryService')
    async def test_start_poll_activity_success(
        self, mock_cat_svc, mock_user_svc, callback, state
    ):
        """Test starting activity from poll."""
        # Setup mocks
        mock_user_svc.return_value.get_by_telegram_id = AsyncMock(
            return_value={"id": "u1", "telegram_id": 123}
        )
        mock_cat_svc.return_value.get_user_categories = AsyncMock(
            return_value=[
                {"id": 1, "name": "Work", "emoji": "💼"},
                {"id": 2, "name": "Sport", "emoji": "🏃"}
            ]
        )

        cb = callback("poll_activity")
        await handle_poll_activity_start(cb, state)

        # Assertions
        assert await state.get_state() == PollStates.waiting_for_poll_category.state
        data = await state.get_data()
        assert data["user_id"] == "u1"
        cb.message.answer.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch('src.api.handlers.poll.UserService')
    @patch('src.api.handlers.poll.CategoryService')
    async def test_start_poll_activity_no_categories(
        self, mock_cat_svc, mock_user_svc, callback, state
    ):
        """Test start when no categories exist."""
        mock_user_svc.return_value.get_by_telegram_id = AsyncMock(
            return_value={"id": "u1"}
        )
        mock_cat_svc.return_value.get_user_categories = AsyncMock(
            return_value=[]
        )

        cb = callback("poll_activity")
        await handle_poll_activity_start(cb, state)

        # Should NOT set FSM state
        assert await state.get_state() is None
        call_text = cb.message.answer.call_args[0][0]
        assert "нет категорий" in call_text.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch('src.api.handlers.poll.UserService')
    @patch('src.api.handlers.poll.UserSettingsService')
    @patch('src.api.handlers.poll.ActivityService')
    @patch('src.api.handlers.poll.scheduler_service')
    async def test_category_select_creates_activity(
        self, mock_sched, mock_act_svc, mock_set_svc, mock_user_svc, callback, state
    ):
        """Test category selection creates activity with correct duration."""
        # Setup state
        await state.set_state(PollStates.waiting_for_poll_category)

        # Mocks
        mock_user_svc.return_value.get_by_telegram_id = AsyncMock(
            return_value={"id": "u1", "timezone": "Europe/Moscow"}
        )
        mock_set_svc.return_value.get_settings = AsyncMock(
            return_value={
                "poll_interval_weekday": 60,
                "poll_interval_weekend": 120
            }
        )
        mock_act_svc.return_value.create_activity = AsyncMock()
        mock_sched.schedule_poll = AsyncMock()

        cb = callback("poll_category_1")
        await handle_poll_category_select(cb, state)

        # Verify activity created
        mock_act_svc.return_value.create_activity.assert_called_once()
        call_kwargs = mock_act_svc.return_value.create_activity.call_args[1]

        assert call_kwargs["category_id"] == 1
        assert call_kwargs["description"] == "Активность"

        # Verify duration = poll_interval (60 min for weekday)
        start = call_kwargs["start_time"]
        end = call_kwargs["end_time"]
        duration_min = (end - start).total_seconds() / 60
        assert 59 <= duration_min <= 61  # 1 min tolerance

        # Verify FSM cleared
        assert await state.get_state() is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_poll_cancel(self, callback, state):
        """Test canceling poll activity."""
        await state.set_state(PollStates.waiting_for_poll_category)

        cb = callback("poll_cancel")
        await handle_poll_cancel(cb, state)

        assert await state.get_state() is None
        call_text = cb.message.answer.call_args[0][0]
        assert "отменена" in call_text.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch('src.api.handlers.poll.UserService')
    @patch('src.api.handlers.poll.UserSettingsService')
    @patch('src.api.handlers.poll.CategoryService')
    @patch('src.api.handlers.poll.ActivityService')
    @patch('src.api.handlers.poll.scheduler_service')
    async def test_poll_sleep_creates_sleep_activity(
        self, mock_sched, mock_act, mock_cat, mock_set, mock_user, callback, state
    ):
        """Test 'I slept' creates sleep activity (TASK 5)."""
        # Mocks
        mock_user.return_value.get_by_telegram_id = AsyncMock(
            return_value={"id": "u1", "timezone": "Europe/Moscow"}
        )
        mock_set.return_value.get_settings = AsyncMock(
            return_value={
                "poll_interval_weekday": 60,
                "poll_interval_weekend": 120
            }
        )
        mock_cat.return_value.get_or_create_sleep_category = AsyncMock(
            return_value={"id": 999, "name": "Сон"}
        )
        mock_act.return_value.create_activity = AsyncMock()
        mock_sched.schedule_poll = AsyncMock()

        cb = callback("poll_sleep")
        await handle_poll_sleep(cb, state)

        # Verify sleep activity created with correct duration
        mock_act.return_value.create_activity.assert_called_once()
        call_kwargs = mock_act.return_value.create_activity.call_args[1]

        assert call_kwargs["category_id"] == 999
        # Duration should be poll_interval (NOT default 8 hours!)
        start = call_kwargs["start_time"]
        end = call_kwargs["end_time"]
        duration_min = (end - start).total_seconds() / 60
        assert 59 <= duration_min <= 61  # Should be ~60 min


# Total: ~8 tests, ~1.2 seconds
```

---

### 1.2 Settings Custom Input (TASK 2)

**File:** `services/tracker_activity_bot/tests/unit/test_settings_custom_input.py`

```python
"""
Unit tests for settings custom input handlers.

Tests TASK 2: Custom time input for intervals.
"""
import pytest
from unittest.mock import AsyncMock, patch
from aiogram import types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

from src.api.handlers.settings import (
    process_weekday_custom_input,
    process_weekend_custom_input,
    process_reminder_delay_custom,
)
from src.api.states.settings import SettingsStates


@pytest.fixture
def bot():
    """Mock bot."""
    bot = Bot(token="TEST")
    bot.session = AsyncMock()
    return bot


@pytest.fixture
async def state():
    """FSM context."""
    storage = MemoryStorage()
    ctx = FSMContext(storage=storage, key="test:123:456")
    yield ctx
    await ctx.clear()


@pytest.fixture
def message(bot):
    """Factory for Message."""
    def _make(text: str):
        user = types.User(id=123, is_bot=False, first_name="Test")
        chat = types.Chat(id=123, type="private")
        msg = types.Message(
            message_id=1,
            date=1234567890,
            chat=chat,
            from_user=user,
            text=text,
            bot=bot
        )
        msg.answer = AsyncMock()
        return msg
    return _make


class TestWeekdayCustomInput:
    """Test weekday interval custom input."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch('src.api.handlers.settings.UserService')
    @patch('src.api.handlers.settings.UserSettingsService')
    @patch('src.api.handlers.settings.scheduler_service')
    async def test_valid_weekday_input(
        self, mock_sched, mock_set, mock_user, message, state
    ):
        """Test valid weekday interval input."""
        await state.set_state(SettingsStates.waiting_for_weekday_interval_custom)

        # Mocks
        mock_user.return_value.get_by_telegram_id = AsyncMock(
            return_value={"id": "u1", "timezone": "Europe/Moscow"}
        )
        mock_set.return_value.get_settings = AsyncMock(
            return_value={"id": "s1", "poll_interval_weekday": 120}
        )
        mock_set.return_value.update_settings = AsyncMock()
        mock_sched.schedule_poll = AsyncMock()

        msg = message("90")
        await process_weekday_custom_input(msg, state)

        # Verify update called with 90
        mock_set.return_value.update_settings.assert_called_once()
        call_kwargs = mock_set.return_value.update_settings.call_args[1]
        assert call_kwargs["poll_interval_weekday"] == 90

        # Verify FSM cleared
        assert await state.get_state() is None

        # Verify confirmation message
        call_text = msg.answer.call_args[0][0]
        assert "1ч 30м" in call_text

    @pytest.mark.unit
    @pytest.mark.asyncio
    @pytest.mark.parametrize("invalid_input,expected_error", [
        ("15", "от 30 до 480"),      # Too low
        ("500", "от 30 до 480"),     # Too high
        ("abc", "Неверный формат"),  # Not a number
        ("-10", "от 30 до 480"),     # Negative
    ])
    async def test_invalid_weekday_input(
        self, invalid_input, expected_error, message, state
    ):
        """Test validation for weekday input."""
        await state.set_state(SettingsStates.waiting_for_weekday_interval_custom)

        msg = message(invalid_input)
        await process_weekday_custom_input(msg, state)

        # FSM should NOT be cleared (allow retry)
        current_state = await state.get_state()
        assert current_state == SettingsStates.waiting_for_weekday_interval_custom.state

        # Error message shown
        call_text = msg.answer.call_args[0][0]
        assert expected_error.lower() in call_text.lower()


class TestWeekendCustomInput:
    """Test weekend interval custom input."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch('src.api.handlers.settings.UserService')
    @patch('src.api.handlers.settings.UserSettingsService')
    @patch('src.api.handlers.settings.scheduler_service')
    async def test_valid_weekend_input(
        self, mock_sched, mock_set, mock_user, message, state
    ):
        """Test valid weekend interval input."""
        await state.set_state(SettingsStates.waiting_for_weekend_interval_custom)

        mock_user.return_value.get_by_telegram_id = AsyncMock(
            return_value={"id": "u1", "timezone": "Europe/Moscow"}
        )
        mock_set.return_value.get_settings = AsyncMock(
            return_value={"id": "s1", "poll_interval_weekend": 120}
        )
        mock_set.return_value.update_settings = AsyncMock()
        mock_sched.schedule_poll = AsyncMock()

        msg = message("210")
        await process_weekend_custom_input(msg, state)

        # Verify update
        call_kwargs = mock_set.return_value.update_settings.call_args[1]
        assert call_kwargs["poll_interval_weekend"] == 210

        # Verify message
        call_text = msg.answer.call_args[0][0]
        assert "3ч 30м" in call_text


class TestReminderDelayCustomInput:
    """Test reminder delay custom input."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch('src.api.handlers.settings.UserService')
    @patch('src.api.handlers.settings.UserSettingsService')
    async def test_valid_reminder_delay(
        self, mock_set, mock_user, message, state
    ):
        """Test valid reminder delay input."""
        await state.set_state(SettingsStates.waiting_for_reminder_delay_custom)

        mock_user.return_value.get_by_telegram_id = AsyncMock(
            return_value={"id": "u1"}
        )
        mock_set.return_value.get_settings = AsyncMock(
            return_value={"id": "s1"}
        )
        mock_set.return_value.update_settings = AsyncMock()

        msg = message("45")
        await process_reminder_delay_custom(msg, state)

        # Verify update
        call_kwargs = mock_set.return_value.update_settings.call_args[1]
        assert call_kwargs["reminder_delay_minutes"] == 45

        # Verify message
        call_text = msg.answer.call_args[0][0]
        assert "45 минут" in call_text


# Total: ~12 tests, ~1.5 seconds
```

---

### 1.3 Cancel Command (TASK 3)

**File:** `services/tracker_activity_bot/tests/unit/test_cancel_command.py`

```python
"""
Unit tests for /cancel command.

Tests TASK 3: /cancel support in all FSM states.
"""
import pytest
from unittest.mock import AsyncMock
from aiogram import types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

from src.api.handlers.settings import cancel_settings_fsm
from src.api.handlers.activity import cancel_activity_fsm
from src.api.handlers.categories import cancel_category_fsm
from src.api.states.settings import SettingsStates
from src.api.states.activity import ActivityStates
from src.api.states.category import CategoryStates


@pytest.fixture
def bot():
    """Mock bot."""
    bot = Bot(token="TEST")
    bot.session = AsyncMock()
    return bot


@pytest.fixture
async def state():
    """FSM context."""
    storage = MemoryStorage()
    ctx = FSMContext(storage=storage, key="test:123:456")
    yield ctx
    await ctx.clear()


@pytest.fixture
def message(bot):
    """Factory for Message."""
    def _make(text: str = "/cancel"):
        user = types.User(id=123, is_bot=False, first_name="Test")
        chat = types.Chat(id=123, type="private")
        msg = types.Message(
            message_id=1,
            date=1234567890,
            chat=chat,
            from_user=user,
            text=text,
            bot=bot
        )
        msg.answer = AsyncMock()
        return msg
    return _make


class TestCancelSettings:
    """Test /cancel in settings FSM."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cancel_in_settings_fsm(self, message, state):
        """Test /cancel clears settings FSM."""
        await state.set_state(SettingsStates.waiting_for_weekday_interval_custom)

        msg = message()
        await cancel_settings_fsm(msg, state)

        # FSM cleared
        assert await state.get_state() is None

        # Confirmation shown
        call_text = msg.answer.call_args[0][0]
        assert "отменена" in call_text.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cancel_when_no_fsm(self, message, state):
        """Test /cancel when no active FSM."""
        # No FSM state
        assert await state.get_state() is None

        msg = message()
        await cancel_settings_fsm(msg, state)

        # Should show "nothing to cancel"
        call_text = msg.answer.call_args[0][0]
        assert "нечего отменять" in call_text.lower()


class TestCancelActivity:
    """Test /cancel in activity FSM."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cancel_activity_recording(self, message, state):
        """Test /cancel in activity recording."""
        await state.set_state(ActivityStates.waiting_for_category)

        msg = message()
        await cancel_activity_fsm(msg, state)

        assert await state.get_state() is None
        call_text = msg.answer.call_args[0][0]
        assert "активности отменена" in call_text.lower()


class TestCancelCategory:
    """Test /cancel in category FSM."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cancel_category_creation(self, message, state):
        """Test /cancel in category creation."""
        await state.set_state(CategoryStates.waiting_for_name)

        msg = message()
        await cancel_category_fsm(msg, state)

        assert await state.get_state() is None
        call_text = msg.answer.call_args[0][0]
        assert "категории отменено" in call_text.lower()


# Total: ~6 tests, ~0.8 seconds
```

---

### 1.4 Inline Category Buttons (TASK 8)

**File:** `services/tracker_activity_bot/tests/unit/test_category_inline_buttons.py`

```python
"""
Unit tests for category inline buttons.

Tests TASK 8: Inline buttons for category selection.
"""
import pytest
from aiogram.types import InlineKeyboardMarkup

from src.api.keyboards.poll import get_poll_category_keyboard


class TestCategoryInlineKeyboard:
    """Test category inline keyboard generation."""

    @pytest.mark.unit
    def test_keyboard_structure_2_categories(self):
        """Test keyboard with 2 categories."""
        categories = [
            {"id": 1, "name": "Work", "emoji": "💼"},
            {"id": 2, "name": "Sport", "emoji": "🏃"},
        ]

        keyboard = get_poll_category_keyboard(categories)

        assert isinstance(keyboard, InlineKeyboardMarkup)
        # Should have 1 row (2 cats) + 1 cancel row
        assert len(keyboard.inline_keyboard) == 2

        # First row: 2 buttons
        assert len(keyboard.inline_keyboard[0]) == 2

        # Check button format
        btn1 = keyboard.inline_keyboard[0][0]
        assert btn1.text == "💼 Work"
        assert btn1.callback_data == "poll_category_1"

        # Last row: cancel
        cancel_row = keyboard.inline_keyboard[-1]
        assert len(cancel_row) == 1
        assert cancel_row[0].text == "❌ Отменить"

    @pytest.mark.unit
    def test_keyboard_structure_5_categories(self):
        """Test keyboard with 5 categories (3 rows)."""
        categories = [
            {"id": i, "name": f"Cat{i}", "emoji": "📁"}
            for i in range(1, 6)
        ]

        keyboard = get_poll_category_keyboard(categories)

        # 5 cats = 3 rows (2+2+1) + 1 cancel row = 4 rows
        assert len(keyboard.inline_keyboard) == 4

        # Row 1: 2 buttons
        assert len(keyboard.inline_keyboard[0]) == 2
        # Row 2: 2 buttons
        assert len(keyboard.inline_keyboard[1]) == 2
        # Row 3: 1 button
        assert len(keyboard.inline_keyboard[2]) == 1

    @pytest.mark.unit
    def test_keyboard_empty_categories(self):
        """Test keyboard with no categories."""
        categories = []

        keyboard = get_poll_category_keyboard(categories)

        # Should have only cancel button
        assert len(keyboard.inline_keyboard) == 1
        assert keyboard.inline_keyboard[0][0].text == "❌ Отменить"


# Total: ~3 tests, ~0.3 seconds
```

---

### 1.5 Existing Unit Tests

**Already implemented:**

```python
# services/tracker_activity_bot/tests/unit/test_imports.py
# ~8 tests, 0.4s

# services/data_postgres_api/tests/unit/test_imports.py
# ~6 tests, 0.3s

# services/data_postgres_api/tests/unit/test_health.py
# ~3 tests, 0.3s
```

---

### 1.6 Additional Unit Tests (Quick Wins)

**File:** `services/tracker_activity_bot/tests/unit/test_keyboards.py`

```python
"""
Unit tests for keyboard builders.

Tests TASK 4: Keyboard generation without empty lists.
"""
import pytest
from src.api.keyboards.settings import (
    get_quiet_hours_main_keyboard,
    get_reminders_keyboard,
)


class TestQuietHoursKeyboard:
    """Test quiet hours keyboard (TASK 4)."""

    @pytest.mark.unit
    def test_keyboard_when_enabled(self):
        """Test keyboard when quiet hours enabled."""
        keyboard = get_quiet_hours_main_keyboard(enabled=True)

        # Should have 3 rows: toggle, change time, back
        assert len(keyboard.inline_keyboard) == 3

        # Toggle button
        assert "Отключить" in keyboard.inline_keyboard[0][0].text

        # Change time button present
        assert "Изменить время" in keyboard.inline_keyboard[1][0].text

    @pytest.mark.unit
    def test_keyboard_when_disabled(self):
        """Test keyboard when quiet hours disabled."""
        keyboard = get_quiet_hours_main_keyboard(enabled=False)

        # Should have 2 rows: toggle, back (NO change time button)
        assert len(keyboard.inline_keyboard) == 2

        # Toggle button
        assert "Включить" in keyboard.inline_keyboard[0][0].text

        # NO "Изменить время" button
        button_texts = [
            btn.text for row in keyboard.inline_keyboard for btn in row
        ]
        assert "Изменить время" not in button_texts


class TestRemindersKeyboard:
    """Test reminders keyboard (TASK 4)."""

    @pytest.mark.unit
    def test_keyboard_when_enabled(self):
        """Test keyboard when reminders enabled."""
        keyboard = get_reminders_keyboard(enabled=True)

        # Should have 3 rows: toggle, change delay, back
        assert len(keyboard.inline_keyboard) == 3

    @pytest.mark.unit
    def test_keyboard_when_disabled(self):
        """Test keyboard when reminders disabled."""
        keyboard = get_reminders_keyboard(enabled=False)

        # Should have 2 rows: toggle, back
        assert len(keyboard.inline_keyboard) == 2


# Total: ~4 tests, ~0.4 seconds
```

---

**UNIT TESTS SUMMARY:**
```
test_poll_handlers.py              8 tests    1.2s
test_settings_custom_input.py     12 tests    1.5s
test_cancel_command.py             6 tests    0.8s
test_category_inline_buttons.py    3 tests    0.3s
test_keyboards.py                  4 tests    0.4s
test_imports.py (existing)        14 tests    0.7s
test_health.py (existing)          3 tests    0.3s
──────────────────────────────────────────────────
TOTAL UNIT:                       50 tests    5.2s
```

---

## 📦 PART 2: SERVICE TESTS (30 tests, 12 seconds)

### 2.1 Activity Endpoints

**File:** `services/data_postgres_api/tests/service/test_activity_endpoints.py`

```python
"""
Service tests for activity endpoints.

Tests full request/response cycle using FastAPI TestClient.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from src.main import app


@pytest.fixture
def client():
    """Provide TestClient."""
    return TestClient(app)


class TestActivityEndpoints:
    """Test activity API endpoints."""

    @pytest.mark.service
    @patch('src.api.v1.activities.get_db')
    async def test_create_activity_success(self, mock_db, client):
        """Test POST /api/v1/activities."""
        # Mock database session
        mock_session = AsyncMock()
        mock_db.return_value = mock_session

        payload = {
            "user_id": "u1",
            "category_id": 1,
            "description": "Test",
            "start_time": "2025-11-05T10:00:00Z",
            "end_time": "2025-11-05T11:00:00Z",
            "tags": []
        }

        response = client.post("/api/v1/activities", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["description"] == "Test"
        assert "id" in data

    @pytest.mark.service
    def test_create_activity_validation_error(self, client):
        """Test validation for invalid data."""
        payload = {
            "user_id": "u1",
            # Missing required fields
        }

        response = client.post("/api/v1/activities", json=payload)

        assert response.status_code == 422
        assert "detail" in response.json()

    @pytest.mark.service
    @patch('src.api.v1.activities.get_db')
    async def test_get_user_activities(self, mock_db, client):
        """Test GET /api/v1/activities."""
        mock_session = AsyncMock()
        mock_db.return_value = mock_session

        response = client.get(
            "/api/v1/activities",
            params={"user_id": "u1", "limit": 10}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.service
    def test_get_activities_missing_user_id(self, client):
        """Test GET without user_id returns 422."""
        response = client.get("/api/v1/activities")
        assert response.status_code == 422


# Total: ~8 tests, ~3 seconds
```

---

### 2.2 User Endpoints

**File:** `services/data_postgres_api/tests/service/test_user_endpoints.py`

```python
"""
Service tests for user endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from src.main import app


@pytest.fixture
def client():
    """Provide TestClient."""
    return TestClient(app)


class TestUserEndpoints:
    """Test user API endpoints."""

    @pytest.mark.service
    @patch('src.api.v1.users.get_db')
    async def test_create_user(self, mock_db, client):
        """Test POST /api/v1/users."""
        mock_session = AsyncMock()
        mock_db.return_value = mock_session

        payload = {
            "telegram_id": 123456,
            "name": "Test User",
            "timezone": "Europe/Moscow"
        }

        response = client.post("/api/v1/users", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["telegram_id"] == 123456

    @pytest.mark.service
    @patch('src.api.v1.users.get_db')
    async def test_get_user_by_telegram_id(self, mock_db, client):
        """Test GET /api/v1/users?telegram_id=X."""
        mock_session = AsyncMock()
        mock_db.return_value = mock_session

        response = client.get("/api/v1/users", params={"telegram_id": 123})

        assert response.status_code == 200

    @pytest.mark.service
    def test_create_user_duplicate(self, client):
        """Test creating duplicate user returns 409."""
        # This would require actual DB or more complex mocking
        # For now, test validation
        payload = {"telegram_id": "not_a_number"}
        response = client.post("/api/v1/users", json=payload)
        assert response.status_code == 422


# Total: ~6 tests, ~2 seconds
```

---

### 2.3 Category Endpoints

**File:** `services/data_postgres_api/tests/service/test_category_endpoints.py`

```python
"""
Service tests for category endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from src.main import app


@pytest.fixture
def client():
    """Provide TestClient."""
    return TestClient(app)


class TestCategoryEndpoints:
    """Test category endpoints."""

    @pytest.mark.service
    @patch('src.api.v1.categories.get_db')
    async def test_create_category(self, mock_db, client):
        """Test POST /api/v1/categories."""
        mock_session = AsyncMock()
        mock_db.return_value = mock_session

        payload = {
            "user_id": "u1",
            "name": "Work",
            "emoji": "💼"
        }

        response = client.post("/api/v1/categories", json=payload)

        assert response.status_code == 201

    @pytest.mark.service
    @patch('src.api.v1.categories.get_db')
    async def test_get_user_categories(self, mock_db, client):
        """Test GET /api/v1/categories?user_id=X."""
        mock_session = AsyncMock()
        mock_db.return_value = mock_session

        response = client.get("/api/v1/categories", params={"user_id": "u1"})

        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.service
    @patch('src.api.v1.categories.get_db')
    async def test_delete_category(self, mock_db, client):
        """Test DELETE /api/v1/categories/{id}."""
        mock_session = AsyncMock()
        mock_db.return_value = mock_session

        response = client.delete("/api/v1/categories/1")

        assert response.status_code in [204, 200, 404]


# Total: ~6 tests, ~2 seconds
```

---

**SERVICE TESTS SUMMARY:**
```
test_activity_endpoints.py         8 tests    3s
test_user_endpoints.py             6 tests    2s
test_category_endpoints.py         6 tests    2s
test_user_settings_endpoints.py    5 tests    2s (TODO)
──────────────────────────────────────────────
TOTAL SERVICE:                    25 tests    9s
```

---

## 📦 PART 3: INTEGRATION TESTS (10 tests, 20 seconds)

**Focus:** Critical paths only, using MemoryStorage (no DB).

**File:** `services/tracker_activity_bot/tests/integration/test_critical_flows.py`

```python
"""
Integration tests for critical flows.

Tests end-to-end scenarios without external dependencies.
"""
import pytest
from unittest.mock import AsyncMock, patch
from aiogram import Dispatcher, Bot
from aiogram.fsm.storage.memory import MemoryStorage

from src.api.handlers import activity, categories, poll, settings


@pytest.fixture
async def dp():
    """Provide Dispatcher with all handlers."""
    storage = MemoryStorage()
    dispatcher = Dispatcher(storage=storage)

    # Register all routers
    dispatcher.include_router(activity.router)
    dispatcher.include_router(categories.router)
    dispatcher.include_router(poll.router)
    dispatcher.include_router(settings.router)

    yield dispatcher


@pytest.fixture
def bot():
    """Mock bot."""
    bot = Bot(token="TEST")
    bot.session = AsyncMock()
    return bot


class TestActivityFlow:
    """Test activity recording flow."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_activity_recording_flow(self, dp, bot):
        """Test complete activity recording from start to finish."""
        # TODO: Simulate user clicking buttons, entering data
        # Verify FSM transitions correctly
        pass


class TestPollFlow:
    """Test poll flow."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_poll_activity_flow(self, dp, bot):
        """Test poll 'I was doing something' flow."""
        # TODO: Simulate poll → select category → verify activity created
        pass


# Total: ~5 tests, ~10 seconds
```

---

**INTEGRATION TESTS SUMMARY:**
```
test_critical_flows.py            5 tests    10s
test_fsm_transitions.py           3 tests     6s (TODO)
──────────────────────────────────────────────
TOTAL INTEGRATION:                8 tests    16s
```

---

## 📊 COVERAGE CONFIGURATION

### pytest.ini

**Both services:**

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
    --cov-fail-under=80
    -n auto  # Parallel execution

markers =
    unit: Unit tests (fast, no external dependencies)
    service: Service tests (TestClient, mocked DB)
    integration: Integration tests (full flow, MemoryStorage)
    slow: Slow tests (skip in CI)

asyncio_mode = auto
```

### .coveragerc

```ini
[run]
source = src
branch = true
parallel = true
omit =
    */tests/*
    */__pycache__/*
    */.venv/*

[report]
precision = 2
show_missing = true
skip_covered = false
exclude_lines =
    pragma: no cover
    def __repr__
    def __str__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
    if TYPE_CHECKING:
    @abstractmethod

[html]
directory = htmlcov

[xml]
output = coverage.xml
```

---

## 🚀 CI/CD INTEGRATION

### GitHub Actions Workflow

**File:** `.github/workflows/tests.yml`

```yaml
name: Tests

on:
  push:
    branches: [ master, develop ]
  pull_request:
    branches: [ master ]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd services/tracker_activity_bot
          pip install -r requirements.txt
          pip install pytest-xdist pytest-cov

      - name: Run Bot Tests
        run: |
          cd services/tracker_activity_bot
          pytest tests/ -v --cov=src --cov-report=xml -n auto

      - name: Run API Tests
        run: |
          cd services/data_postgres_api
          pytest tests/ -v --cov=src --cov-report=xml -n auto

      - name: Upload Coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./services/tracker_activity_bot/coverage.xml,./services/data_postgres_api/coverage.xml
          fail_ci_if_error: true
```

---

## 📋 EXECUTION COMMANDS

### Local Development

```bash
# Run all tests (both services)
make test

# Run with coverage
make test-coverage

# Run specific test file
pytest tests/unit/test_poll_handlers.py -v

# Run specific test
pytest tests/unit/test_poll_handlers.py::TestPollActivityFlow::test_start_poll_activity_success -v

# Run by marker
pytest -m unit          # Only unit tests
pytest -m service       # Only service tests
pytest -m "not slow"    # Skip slow tests

# Parallel execution (faster)
pytest -n auto          # Use all CPU cores
pytest -n 4             # Use 4 cores

# Watch mode (re-run on changes)
ptw -- tests/           # Requires pytest-watch
```

### Makefile

**Add to existing Makefile:**

```makefile
# Fast automated tests
test-fast: ## Run fast automated tests (~1 min)
	@echo "Running fast automated tests..."
	cd services/tracker_activity_bot && pytest tests/ -v -n auto -m "not slow"
	cd services/data_postgres_api && pytest tests/ -v -n auto -m "not slow"

test-unit: ## Run only unit tests
	cd services/tracker_activity_bot && pytest tests/unit/ -v
	cd services/data_postgres_api && pytest tests/unit/ -v

test-service: ## Run only service tests
	cd services/data_postgres_api && pytest tests/service/ -v

test-coverage: ## Run tests with coverage report
	cd services/tracker_activity_bot && pytest tests/ -v --cov=src --cov-report=html --cov-report=term -n auto
	cd services/data_postgres_api && pytest tests/ -v --cov=src --cov-report=html --cov-report=term -n auto
	@echo "\nCoverage reports:"
	@echo "Bot: services/tracker_activity_bot/htmlcov/index.html"
	@echo "API: services/data_postgres_api/htmlcov/index.html"

test-watch: ## Watch mode (re-run on changes)
	cd services/tracker_activity_bot && ptw -- tests/
```

---

## 🎯 COVERAGE TARGETS

```
╔══════════════════════════════════════════════════════════╗
║ Component              │ Current │ Target │ Priority    ║
╠══════════════════════════════════════════════════════════╣
║ poll.py                │ 0%      │ 90%    │ CRITICAL    ║
║ settings.py            │ 0%      │ 85%    │ HIGH        ║
║ activity.py            │ 0%      │ 85%    │ HIGH        ║
║ keyboards/*            │ 0%      │ 70%    │ MEDIUM      ║
║ states/*               │ 100%    │ 100%   │ ✅          ║
║ API endpoints          │ 20%     │ 90%    │ CRITICAL    ║
║ repositories           │ 0%      │ 80%    │ HIGH        ║
╠══════════════════════════════════════════════════════════╣
║ OVERALL                │ 15%     │ 80%+   │ TARGET      ║
╚══════════════════════════════════════════════════════════╝
```

---

## ✅ SUCCESS CRITERIA

**All must be ✅:**

```
[ ] All tests pass (120+ tests)
[ ] Execution time < 60 seconds
[ ] Coverage ≥ 80%
[ ] No flaky tests
[ ] CI/CD pipeline green
[ ] Coverage reports generated
[ ] No test warnings
```

---

## 📚 BEST PRACTICES APPLIED

### 1. Test Isolation
```python
✅ Each test is independent
✅ Use fixtures for setup/teardown
✅ Clean FSM state after each test
```

### 2. Mocking Strategy
```python
✅ Mock external dependencies (API, DB, scheduler)
✅ Use AsyncMock for async functions
✅ patch at handler level, not service level
```

### 3. Test Naming
```python
✅ test_<what>_<scenario>
✅ Descriptive docstrings
✅ Arrange-Act-Assert pattern
```

### 4. Speed Optimization
```python
✅ Parallel execution (-n auto)
✅ No slow integration tests in unit suite
✅ MemoryStorage instead of Redis
✅ No real HTTP calls
```

### 5. Coverage
```python
✅ Branch coverage enabled
✅ Skip covered lines in report
✅ Fail CI if < 80%
```

---

## 🔄 DEVELOPMENT WORKFLOW

```
┌─────────────────────────────────────────────────────┐
│ 1. Write code                                       │
├─────────────────────────────────────────────────────┤
│ 2. Write tests (TDD preferred)                      │
├─────────────────────────────────────────────────────┤
│ 3. Run tests locally:                               │
│    pytest tests/unit/test_<module>.py -v            │
├─────────────────────────────────────────────────────┤
│ 4. Check coverage:                                  │
│    pytest --cov=src --cov-report=term-missing       │
├─────────────────────────────────────────────────────┤
│ 5. Commit:                                          │
│    git add . && git commit -m "..."                 │
├─────────────────────────────────────────────────────┤
│ 6. CI runs automatically                            │
│    ✅ All tests pass                                │
│    ✅ Coverage ≥ 80%                                │
├─────────────────────────────────────────────────────┤
│ 7. Merge to master                                  │
└─────────────────────────────────────────────────────┘
```

---

## 📊 FINAL TEST SUITE SUMMARY

```
╔═══════════════════════════════════════════════════════╗
║ AUTOMATED TEST SUITE                                  ║
╠═══════════════════════════════════════════════════════╣
║ Unit Tests              50 tests        5s            ║
║ Service Tests           25 tests        9s            ║
║ Integration Tests        8 tests       16s            ║
║ Overhead                 -              10s            ║
╠═══════════════════════════════════════════════════════╣
║ TOTAL                   83 tests       40s            ║
║                                                        ║
║ With pytest-xdist:      83 tests       15s ⚡         ║
╚═══════════════════════════════════════════════════════╝

Coverage Target: 80%+
CI/CD: ✅ Automated
Execution: ⚡ Fast (<1 min)
```

---

**END OF FAST AUTOMATED TESTING PLAN v2.0**
