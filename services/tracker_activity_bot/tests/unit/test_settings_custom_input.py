"""
Unit tests for settings custom input handlers.

Tests TASK 2: Custom time input for intervals and reminder delay.
This test suite validates user input, updates settings, and reschedules polls.
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
    def _make(text: str, user_id: int = 123):
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


class TestWeekdayCustomInput:
    """Test weekday interval custom input and validation."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch('src.api.handlers.settings.UserService')
    @patch('src.api.handlers.settings.UserSettingsService')
    @patch('src.api.handlers.settings.scheduler_service')
    async def test_valid_weekday_input(
        self, mock_sched, mock_set, mock_user, message, state
    ):
        """Test valid weekday interval input updates settings and reschedules poll."""
        await state.set_state(SettingsStates.waiting_for_weekday_interval_custom)

        # Setup mocks
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

        # Verify settings updated with correct value
        mock_set.return_value.update_settings.assert_called_once()
        call_kwargs = mock_set.return_value.update_settings.call_args[1]
        assert call_kwargs["poll_interval_weekday"] == 90

        # Verify poll rescheduled
        mock_sched.schedule_poll.assert_called_once()

        # Verify FSM cleared
        assert await state.get_state() is None

        # Verify confirmation message with formatted time
        call_text = msg.answer.call_args[0][0]
        assert "1ч 30м" in call_text

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_weekday_input_too_low(self, message, state):
        """Test validation rejects interval below minimum (5 minutes)."""
        await state.set_state(SettingsStates.waiting_for_weekday_interval_custom)

        msg = message("3")
        await process_weekday_custom_input(msg, state)

        # FSM should NOT be cleared (allow retry)
        current_state = await state.get_state()
        assert current_state == SettingsStates.waiting_for_weekday_interval_custom.state

        # Error message shown
        call_text = msg.answer.call_args[0][0]
        assert "от 5 до 480" in call_text.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_weekday_input_too_high(self, message, state):
        """Test validation rejects interval above maximum (480 minutes)."""
        await state.set_state(SettingsStates.waiting_for_weekday_interval_custom)

        msg = message("500")
        await process_weekday_custom_input(msg, state)

        # FSM should NOT be cleared
        current_state = await state.get_state()
        assert current_state == SettingsStates.waiting_for_weekday_interval_custom.state

        # Error message
        call_text = msg.answer.call_args[0][0]
        assert "от 5 до 480" in call_text.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_weekday_input_not_a_number(self, message, state):
        """Test validation rejects non-numeric input."""
        await state.set_state(SettingsStates.waiting_for_weekday_interval_custom)

        msg = message("abc")
        await process_weekday_custom_input(msg, state)

        # FSM should NOT be cleared
        current_state = await state.get_state()
        assert current_state == SettingsStates.waiting_for_weekday_interval_custom.state

        # Error message
        call_text = msg.answer.call_args[0][0]
        assert "неверный формат" in call_text.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_weekday_input_negative(self, message, state):
        """Test validation rejects negative values."""
        await state.set_state(SettingsStates.waiting_for_weekday_interval_custom)

        msg = message("-10")
        await process_weekday_custom_input(msg, state)

        current_state = await state.get_state()
        assert current_state == SettingsStates.waiting_for_weekday_interval_custom.state

        call_text = msg.answer.call_args[0][0]
        assert "от 5 до 480" in call_text.lower()


class TestWeekendCustomInput:
    """Test weekend interval custom input and validation."""

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

        # Verify settings updated
        call_kwargs = mock_set.return_value.update_settings.call_args[1]
        assert call_kwargs["poll_interval_weekend"] == 210

        # Verify confirmation message
        call_text = msg.answer.call_args[0][0]
        assert "3ч 30м" in call_text

        # Verify FSM cleared
        assert await state.get_state() is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_weekend_input_too_low(self, message, state):
        """Test validation rejects weekend interval below minimum."""
        await state.set_state(SettingsStates.waiting_for_weekend_interval_custom)

        msg = message("3")
        await process_weekend_custom_input(msg, state)

        # FSM should NOT be cleared
        current_state = await state.get_state()
        assert current_state == SettingsStates.waiting_for_weekend_interval_custom.state

        call_text = msg.answer.call_args[0][0]
        assert "от 5 до 600" in call_text.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_weekend_input_too_high(self, message, state):
        """Test validation rejects weekend interval above maximum (600 minutes)."""
        await state.set_state(SettingsStates.waiting_for_weekend_interval_custom)

        msg = message("700")
        await process_weekend_custom_input(msg, state)

        current_state = await state.get_state()
        assert current_state == SettingsStates.waiting_for_weekend_interval_custom.state

        call_text = msg.answer.call_args[0][0]
        assert "от 5 до 600" in call_text.lower()


class TestReminderDelayCustomInput:
    """Test reminder delay custom input and validation."""

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

        # Verify settings updated
        call_kwargs = mock_set.return_value.update_settings.call_args[1]
        assert call_kwargs["reminder_delay_minutes"] == 45

        # Verify confirmation message
        call_text = msg.answer.call_args[0][0]
        assert "45 минут" in call_text

        # Verify FSM cleared
        assert await state.get_state() is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_reminder_delay_too_low(self, message, state):
        """Test validation rejects delay below minimum (5 minutes)."""
        await state.set_state(SettingsStates.waiting_for_reminder_delay_custom)

        msg = message("2")
        await process_reminder_delay_custom(msg, state)

        # FSM should NOT be cleared
        current_state = await state.get_state()
        assert current_state == SettingsStates.waiting_for_reminder_delay_custom.state

        call_text = msg.answer.call_args[0][0]
        assert "от 5 до 120" in call_text.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_reminder_delay_too_high(self, message, state):
        """Test validation rejects delay above maximum (120 minutes)."""
        await state.set_state(SettingsStates.waiting_for_reminder_delay_custom)

        msg = message("150")
        await process_reminder_delay_custom(msg, state)

        current_state = await state.get_state()
        assert current_state == SettingsStates.waiting_for_reminder_delay_custom.state

        call_text = msg.answer.call_args[0][0]
        assert "от 5 до 120" in call_text.lower()


# Total: 12 tests
