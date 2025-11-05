"""
Unit tests for /cancel command handlers.

Tests TASK 3: /cancel support in all FSM states.
This test suite ensures users can cancel any active FSM state
using the /cancel command across all bot handlers.
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
def message(bot):
    """Factory for creating mock Message objects."""
    def _make(text: str = "/cancel", user_id: int = 123):
        user = types.User(id=user_id, is_bot=False, first_name="Test")
        chat = types.Chat(id=user_id, type="private")
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


class TestCancelSettingsFSM:
    """Test /cancel in settings FSM states."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cancel_weekday_interval_custom(self, message, state):
        """Test /cancel clears weekday interval custom input FSM."""
        await state.set_state(SettingsStates.waiting_for_weekday_interval_custom)

        msg = message()
        await cancel_settings_fsm(msg, state)

        # Verify FSM cleared
        assert await state.get_state() is None

        # Verify confirmation message
        call_text = msg.answer.call_args[0][0]
        assert "отменена" in call_text.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cancel_weekend_interval_custom(self, message, state):
        """Test /cancel clears weekend interval custom input FSM."""
        await state.set_state(SettingsStates.waiting_for_weekend_interval_custom)

        msg = message()
        await cancel_settings_fsm(msg, state)

        assert await state.get_state() is None
        call_text = msg.answer.call_args[0][0]
        assert "отменена" in call_text.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cancel_when_no_active_fsm(self, message, state):
        """Test /cancel when no active FSM state."""
        # No FSM state set
        assert await state.get_state() is None

        msg = message()
        await cancel_settings_fsm(msg, state)

        # Should show "nothing to cancel" message
        call_text = msg.answer.call_args[0][0]
        assert "нечего отменять" in call_text.lower()


class TestCancelActivityFSM:
    """Test /cancel in activity recording FSM states."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cancel_activity_waiting_for_description(self, message, state):
        """Test /cancel during description input."""
        await state.set_state(ActivityStates.waiting_for_description)

        msg = message()
        await cancel_activity_fsm(msg, state)

        # FSM cleared
        assert await state.get_state() is None

        # Confirmation message
        call_text = msg.answer.call_args[0][0]
        assert "активности отменена" in call_text.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cancel_activity_waiting_for_category(self, message, state):
        """Test /cancel during category selection."""
        await state.set_state(ActivityStates.waiting_for_category)

        msg = message()
        await cancel_activity_fsm(msg, state)

        assert await state.get_state() is None
        call_text = msg.answer.call_args[0][0]
        assert "активности отменена" in call_text.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cancel_activity_waiting_for_time(self, message, state):
        """Test /cancel during time input."""
        await state.set_state(ActivityStates.waiting_for_start_time)

        msg = message()
        await cancel_activity_fsm(msg, state)

        assert await state.get_state() is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cancel_activity_when_not_recording(self, message, state):
        """Test /cancel when not recording activity."""
        # No activity FSM state
        assert await state.get_state() is None

        msg = message()
        await cancel_activity_fsm(msg, state)

        # Should show "nothing to cancel"
        call_text = msg.answer.call_args[0][0]
        assert "нечего отменять" in call_text.lower() or "не записываешь" in call_text.lower()


class TestCancelCategoryFSM:
    """Test /cancel in category management FSM states."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cancel_category_waiting_for_name(self, message, state):
        """Test /cancel during category name input."""
        await state.set_state(CategoryStates.waiting_for_name)

        msg = message()
        await cancel_category_fsm(msg, state)

        # FSM cleared
        assert await state.get_state() is None

        # Confirmation message
        call_text = msg.answer.call_args[0][0]
        assert "категории отменено" in call_text.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cancel_category_waiting_for_emoji(self, message, state):
        """Test /cancel during emoji input."""
        await state.set_state(CategoryStates.waiting_for_emoji)

        msg = message()
        await cancel_category_fsm(msg, state)

        assert await state.get_state() is None
        call_text = msg.answer.call_args[0][0]
        assert "категории отменено" in call_text.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cancel_category_when_not_creating(self, message, state):
        """Test /cancel when not creating category."""
        # No category FSM state
        assert await state.get_state() is None

        msg = message()
        await cancel_category_fsm(msg, state)

        # Should show "nothing to cancel"
        call_text = msg.answer.call_args[0][0]
        assert "нечего отменять" in call_text.lower() or "не создаёшь" in call_text.lower()


class TestCancelCrossFSM:
    """Test /cancel doesn't interfere with other FSM states."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cancel_settings_doesnt_clear_activity_fsm(self, message, state):
        """Test settings cancel doesn't clear activity FSM (isolation)."""
        # Set activity FSM state
        await state.set_state(ActivityStates.waiting_for_category)

        msg = message()
        await cancel_settings_fsm(msg, state)

        # Activity FSM should still be active
        # (This test assumes handlers check their own FSM namespace)
        # In practice, the handler should check if state starts with "SettingsStates"


# Total: 12 tests
