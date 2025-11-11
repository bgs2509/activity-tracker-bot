"""
Unit tests for category inline button keyboards.

Tests TASK 8: Inline buttons for category selection.
This test suite validates that category selection keyboards are generated
correctly with proper structure and button layout.
"""
import pytest
from aiogram.types import InlineKeyboardMarkup

from src.api.keyboards.poll import get_poll_category_keyboard


class TestCategoryInlineKeyboard:
    """Test category inline keyboard generation."""

    @pytest.mark.unit
    def test_keyboard_structure_2_categories(self):
        """Test keyboard with 2 categories (1 row + cancel)."""
        categories = [
            {"id": 1, "name": "Work", "emoji": "💼"},
            {"id": 2, "name": "Sport", "emoji": "🏃"},
        ]

        keyboard = get_poll_category_keyboard(categories)

        assert isinstance(keyboard, InlineKeyboardMarkup)

        # Should have 1 row (2 cats) + 1 remind later row + 1 cancel row = 3 rows total
        assert len(keyboard.inline_keyboard) == 3

        # First row: 2 buttons (categories)
        assert len(keyboard.inline_keyboard[0]) == 2

        # Check button format and data
        btn1 = keyboard.inline_keyboard[0][0]
        assert btn1.text == "💼 Work"
        assert btn1.callback_data == "poll_category_1"

        btn2 = keyboard.inline_keyboard[0][1]
        assert btn2.text == "🏃 Sport"
        assert btn2.callback_data == "poll_category_2"

        # Second-to-last row: remind later button
        remind_row = keyboard.inline_keyboard[-2]
        assert len(remind_row) == 1
        assert remind_row[0].text == "⏸ Напомнить позже"
        assert remind_row[0].callback_data == "poll_category_remind_later"

        # Last row: cancel button
        cancel_row = keyboard.inline_keyboard[-1]
        assert len(cancel_row) == 1
        assert cancel_row[0].text == "❌ Отменить"
        assert cancel_row[0].callback_data == "poll_cancel"

    @pytest.mark.unit
    def test_keyboard_structure_1_category(self):
        """Test keyboard with single category."""
        categories = [
            {"id": 1, "name": "Work", "emoji": "💼"},
        ]

        keyboard = get_poll_category_keyboard(categories)

        # Should have 1 row (1 cat) + 1 remind later row + 1 cancel row = 3 rows
        assert len(keyboard.inline_keyboard) == 3

        # First row: 1 button
        assert len(keyboard.inline_keyboard[0]) == 1

    @pytest.mark.unit
    def test_keyboard_structure_5_categories(self):
        """Test keyboard with 5 categories (3 rows + remind later + cancel)."""
        categories = [
            {"id": i, "name": f"Cat{i}", "emoji": "📁"}
            for i in range(1, 6)
        ]

        keyboard = get_poll_category_keyboard(categories)

        # 5 cats = 3 rows (2+2+1) + 1 remind later row + 1 cancel row = 5 rows
        assert len(keyboard.inline_keyboard) == 5

        # Row 1: 2 buttons
        assert len(keyboard.inline_keyboard[0]) == 2
        # Row 2: 2 buttons
        assert len(keyboard.inline_keyboard[1]) == 2
        # Row 3: 1 button
        assert len(keyboard.inline_keyboard[2]) == 1
        # Row 4: remind later
        assert len(keyboard.inline_keyboard[3]) == 1
        # Row 5: cancel
        assert len(keyboard.inline_keyboard[4]) == 1

    @pytest.mark.unit
    def test_keyboard_structure_10_categories(self):
        """Test keyboard with 10 categories (max pagination)."""
        categories = [
            {"id": i, "name": f"Category {i}", "emoji": "📁"}
            for i in range(1, 11)
        ]

        keyboard = get_poll_category_keyboard(categories)

        # 10 cats = 5 rows (2 per row) + 1 remind later row + 1 cancel row = 7 rows
        assert len(keyboard.inline_keyboard) == 7

        # Each category row should have 2 buttons
        for i in range(5):
            assert len(keyboard.inline_keyboard[i]) == 2

        # Second-to-last row: remind later
        assert len(keyboard.inline_keyboard[-2]) == 1

        # Last row: cancel
        assert len(keyboard.inline_keyboard[-1]) == 1

    @pytest.mark.unit
    def test_keyboard_empty_categories(self):
        """Test keyboard with no categories (remind later + cancel)."""
        categories = []

        keyboard = get_poll_category_keyboard(categories)

        # Should have remind later + cancel buttons (2 rows)
        assert len(keyboard.inline_keyboard) == 2

        # First row: remind later
        assert keyboard.inline_keyboard[0][0].text == "⏸ Напомнить позже"
        assert keyboard.inline_keyboard[0][0].callback_data == "poll_category_remind_later"

        # Second row: cancel
        assert keyboard.inline_keyboard[1][0].text == "❌ Отменить"
        assert keyboard.inline_keyboard[1][0].callback_data == "poll_cancel"

    @pytest.mark.unit
    def test_keyboard_callback_data_format(self):
        """Test callback data format for category buttons."""
        categories = [
            {"id": 42, "name": "Test", "emoji": "🧪"},
        ]

        keyboard = get_poll_category_keyboard(categories)

        # Check callback data format: poll_category_{id}
        btn = keyboard.inline_keyboard[0][0]
        assert btn.callback_data == "poll_category_42"

    @pytest.mark.unit
    def test_keyboard_category_without_emoji(self):
        """Test category button when emoji is missing."""
        categories = [
            {"id": 1, "name": "NoEmoji", "emoji": ""},
        ]

        keyboard = get_poll_category_keyboard(categories)

        # Button should show name even without emoji
        btn = keyboard.inline_keyboard[0][0]
        # Could be " NoEmoji" or "NoEmoji" depending on implementation
        assert "NoEmoji" in btn.text


# Total: 7 tests
