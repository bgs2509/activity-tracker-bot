"""
Unit tests for poll handlers.

Tests TASK 1: "I was doing something" poll option.
This test suite covers the new poll activity recording functionality
including category selection and activity creation with automatic duration.
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
    """Provide mock bot instance."""
    bot = Bot(token="TEST_TOKEN")
    bot.session = AsyncMock()
    return bot


@pytest.fixture
async def state():
    """Provide FSM context with memory storage."""
    storage = MemoryStorage()
    ctx = FSMContext(storage=storage, key="test:123:456")
    yield ctx
    await ctx.clear()


@pytest.fixture
def callback(bot):
    """Factory for creating mock CallbackQuery objects."""
    def _make(data: str, user_id: int = 123):
        user = types.User(id=user_id, is_bot=False, first_name="Test")
        chat = types.Chat(id=user_id, type="private")
        msg = types.Message(
            message_id=1,
            date=1234567890,
            chat=chat,
            from_user=user,
            text="Test",
            bot=bot
        )
        cb = types.CallbackQuery(
            id="cb_123",
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
    """Test poll activity recording flow (TASK 1)."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch('src.api.handlers.poll.UserService')
    @patch('src.api.handlers.poll.CategoryService')
    async def test_start_poll_activity_success(
        self, mock_cat_svc, mock_user_svc, callback, state
    ):
        """Test starting activity recording from poll with categories."""
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

        # Verify FSM state set correctly
        assert await state.get_state() == PollStates.waiting_for_poll_category.state

        # Verify user_id stored in state
        data = await state.get_data()
        assert data["user_id"] == "u1"

        # Verify message sent to user
        cb.message.answer.assert_called_once()
        call_text = cb.message.answer.call_args[0][0]
        assert "Чем ты занимался?" in call_text
        assert "Выбери категорию" in call_text

        # Verify callback answered
        cb.answer.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch('src.api.handlers.poll.UserService')
    @patch('src.api.handlers.poll.CategoryService')
    async def test_start_poll_activity_no_categories(
        self, mock_cat_svc, mock_user_svc, callback, state
    ):
        """Test starting activity when user has no categories."""
        # Mock user exists but has no categories
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

        # Should show error message
        call_text = cb.message.answer.call_args[0][0]
        assert "нет категорий" in call_text.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch('src.api.handlers.poll.UserService')
    @patch('src.api.handlers.poll.CategoryService')
    async def test_start_poll_activity_user_not_found(
        self, mock_cat_svc, mock_user_svc, callback, state
    ):
        """Test starting activity when user not found."""
        mock_user_svc.return_value.get_by_telegram_id = AsyncMock(
            return_value=None
        )

        cb = callback("poll_activity")
        await handle_poll_activity_start(cb, state)

        # Should NOT set FSM state
        assert await state.get_state() is None

        # Should show error
        call_text = cb.message.answer.call_args[0][0]
        assert "не найден" in call_text.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch('src.api.handlers.poll.UserService')
    @patch('src.api.handlers.poll.UserSettingsService')
    @patch('src.api.handlers.poll.ActivityService')
    @patch('src.api.handlers.poll.scheduler_service')
    async def test_category_select_creates_activity_weekday(
        self, mock_sched, mock_act_svc, mock_set_svc, mock_user_svc, callback, state
    ):
        """Test category selection creates activity with correct weekday duration."""
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

        # Mock weekday (Monday)
        with patch('src.api.handlers.poll.datetime') as mock_dt:
            mock_now = datetime(2025, 11, 10, 12, 0, 0, tzinfo=timezone.utc)  # Monday
            mock_dt.now.return_value = mock_now
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

            await handle_poll_category_select(cb, state)

        # Verify activity created
        mock_act_svc.return_value.create_activity.assert_called_once()
        call_kwargs = mock_act_svc.return_value.create_activity.call_args[1]

        assert call_kwargs["category_id"] == 1
        assert call_kwargs["description"] == "Активность"

        # Verify duration is poll_interval (weekday = 60 min)
        start_time = call_kwargs["start_time"]
        end_time = call_kwargs["end_time"]
        duration = (end_time - start_time).total_seconds() / 60
        assert 59 <= duration <= 61  # Allow 1 min tolerance

        # Verify poll rescheduled
        mock_sched.schedule_poll.assert_called_once()

        # Verify FSM cleared
        assert await state.get_state() is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch('src.api.handlers.poll.UserService')
    @patch('src.api.handlers.poll.UserSettingsService')
    @patch('src.api.handlers.poll.ActivityService')
    @patch('src.api.handlers.poll.scheduler_service')
    async def test_category_select_creates_activity_weekend(
        self, mock_sched, mock_act_svc, mock_set_svc, mock_user_svc, callback, state
    ):
        """Test category selection uses weekend interval on Saturday."""
        await state.set_state(PollStates.waiting_for_poll_category)

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

        # Mock Saturday
        with patch('src.api.handlers.poll.datetime') as mock_dt:
            mock_now = datetime(2025, 11, 15, 12, 0, 0, tzinfo=timezone.utc)  # Saturday
            mock_dt.now.return_value = mock_now
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

            await handle_poll_category_select(cb, state)

        # Verify duration is weekend interval (120 min)
        call_kwargs = mock_act_svc.return_value.create_activity.call_args[1]
        start_time = call_kwargs["start_time"]
        end_time = call_kwargs["end_time"]
        duration = (end_time - start_time).total_seconds() / 60
        assert 119 <= duration <= 121  # Weekend interval

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_poll_cancel(self, callback, state):
        """Test canceling poll activity recording clears FSM."""
        await state.set_state(PollStates.waiting_for_poll_category)

        cb = callback("poll_cancel")
        await handle_poll_cancel(cb, state)

        # Verify FSM cleared
        assert await state.get_state() is None

        # Verify confirmation message
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
        """Test 'I slept' creates sleep activity with correct duration (TASK 5)."""
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

        # Mock weekday
        with patch('src.api.handlers.poll.datetime') as mock_dt:
            mock_now = datetime(2025, 11, 10, 12, 0, 0, tzinfo=timezone.utc)
            mock_dt.now.return_value = mock_now
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

            await handle_poll_sleep(cb, state)

        # Verify sleep activity created
        mock_act.return_value.create_activity.assert_called_once()
        call_kwargs = mock_act.return_value.create_activity.call_args[1]

        assert call_kwargs["category_id"] == 999

        # Duration should be poll_interval (NOT default 8 hours!)
        start = call_kwargs["start_time"]
        end = call_kwargs["end_time"]
        duration_min = (end - start).total_seconds() / 60
        assert 59 <= duration_min <= 61  # Should be ~60 min, not 480 min (8 hours)


# Total: 8 tests
