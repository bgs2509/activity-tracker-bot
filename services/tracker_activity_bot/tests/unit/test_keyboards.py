"""
Unit tests for keyboard builders.

Tests TASK 4: Keyboard generation without empty lists.
This test suite ensures keyboards are properly structured without
empty list items that could break the UI.
"""
import pytest
from src.api.keyboards.settings import (
    get_quiet_hours_main_keyboard,
    get_reminders_keyboard,
)


class TestQuietHoursKeyboard:
    """Test quiet hours keyboard structure (TASK 4)."""

    @pytest.mark.unit
    def test_keyboard_when_enabled(self):
        """Test keyboard when quiet hours are enabled."""
        keyboard = get_quiet_hours_main_keyboard(enabled=True)

        # Should have 3 rows: toggle, change time, back
        assert len(keyboard.inline_keyboard) == 3

        # Row 1: Toggle button (should say "Отключить")
        assert "Отключить" in keyboard.inline_keyboard[0][0].text

        # Row 2: Change time button (should be present when enabled)
        assert "Изменить время" in keyboard.inline_keyboard[1][0].text

        # Row 3: Back button
        assert "Назад" in keyboard.inline_keyboard[2][0].text

        # Verify no empty lists
        for row in keyboard.inline_keyboard:
            assert len(row) > 0, "Keyboard should not contain empty rows"

    @pytest.mark.unit
    def test_keyboard_when_disabled(self):
        """Test keyboard when quiet hours are disabled."""
        keyboard = get_quiet_hours_main_keyboard(enabled=False)

        # Should have 2 rows: toggle, back (NO change time button)
        assert len(keyboard.inline_keyboard) == 2

        # Row 1: Toggle button (should say "Включить")
        assert "Включить" in keyboard.inline_keyboard[0][0].text

        # Row 2: Back button
        assert "Назад" in keyboard.inline_keyboard[1][0].text

        # Verify "Изменить время" button is NOT present
        button_texts = [
            btn.text for row in keyboard.inline_keyboard for btn in row
        ]
        assert "Изменить время" not in button_texts

        # Verify no empty lists
        for row in keyboard.inline_keyboard:
            assert len(row) > 0, "Keyboard should not contain empty rows"

    @pytest.mark.unit
    def test_keyboard_no_empty_lists_when_toggled(self):
        """Test that toggling doesn't create empty list items."""
        # Test both states
        for enabled in [True, False]:
            keyboard = get_quiet_hours_main_keyboard(enabled=enabled)

            # Check every row has at least one button
            for i, row in enumerate(keyboard.inline_keyboard):
                assert len(row) > 0, f"Row {i} is empty when enabled={enabled}"
                assert isinstance(row, list), f"Row {i} should be a list"
                assert all(hasattr(btn, 'text') for btn in row), "All items should be buttons"


class TestRemindersKeyboard:
    """Test reminders keyboard structure (TASK 4)."""

    @pytest.mark.unit
    def test_keyboard_when_enabled(self):
        """Test keyboard when reminders are enabled."""
        keyboard = get_reminders_keyboard(enabled=True)

        # Should have 3 rows: toggle, change delay, back
        assert len(keyboard.inline_keyboard) == 3

        # Row 1: Toggle button (should say "Отключить")
        assert "Отключить" in keyboard.inline_keyboard[0][0].text

        # Row 2: Change delay button (should be present when enabled)
        assert "Изменить задержку" in keyboard.inline_keyboard[1][0].text

        # Row 3: Back button
        assert "Назад" in keyboard.inline_keyboard[2][0].text

        # Verify no empty lists
        for row in keyboard.inline_keyboard:
            assert len(row) > 0, "Keyboard should not contain empty rows"

    @pytest.mark.unit
    def test_keyboard_when_disabled(self):
        """Test keyboard when reminders are disabled."""
        keyboard = get_reminders_keyboard(enabled=False)

        # Should have 2 rows: toggle, back (NO change delay button)
        assert len(keyboard.inline_keyboard) == 2

        # Row 1: Toggle button (should say "Включить")
        assert "Включить" in keyboard.inline_keyboard[0][0].text

        # Row 2: Back button
        assert "Назад" in keyboard.inline_keyboard[1][0].text

        # Verify "Изменить задержку" button is NOT present
        button_texts = [
            btn.text for row in keyboard.inline_keyboard for btn in row
        ]
        assert "Изменить задержку" not in button_texts

        # Verify no empty lists
        for row in keyboard.inline_keyboard:
            assert len(row) > 0, "Keyboard should not contain empty rows"

    @pytest.mark.unit
    def test_keyboard_no_empty_lists_when_toggled(self):
        """Test that toggling doesn't create empty list items."""
        # Test both states
        for enabled in [True, False]:
            keyboard = get_reminders_keyboard(enabled=enabled)

            # Check every row has at least one button
            for i, row in enumerate(keyboard.inline_keyboard):
                assert len(row) > 0, f"Row {i} is empty when enabled={enabled}"
                assert isinstance(row, list), f"Row {i} should be a list"
                assert all(hasattr(btn, 'text') for btn in row), "All items should be buttons"


class TestKeyboardStructureConsistency:
    """Test keyboard structure consistency across different states."""

    @pytest.mark.unit
    def test_quiet_hours_keyboard_structure_is_valid(self):
        """Test that quiet hours keyboard always has valid structure."""
        for enabled in [True, False]:
            keyboard = get_quiet_hours_main_keyboard(enabled=enabled)

            # Should be InlineKeyboardMarkup
            assert hasattr(keyboard, 'inline_keyboard')
            assert isinstance(keyboard.inline_keyboard, list)

            # Every row should be a list of buttons
            for row in keyboard.inline_keyboard:
                assert isinstance(row, list)
                assert len(row) > 0  # No empty rows

    @pytest.mark.unit
    def test_reminders_keyboard_structure_is_valid(self):
        """Test that reminders keyboard always has valid structure."""
        for enabled in [True, False]:
            keyboard = get_reminders_keyboard(enabled=enabled)

            # Should be InlineKeyboardMarkup
            assert hasattr(keyboard, 'inline_keyboard')
            assert isinstance(keyboard.inline_keyboard, list)

            # Every row should be a list of buttons
            for row in keyboard.inline_keyboard:
                assert isinstance(row, list)
                assert len(row) > 0  # No empty rows


# Total: 8 tests
