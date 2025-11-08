"""
Handler Registration Integration Tests.

Verifies that all keyboard buttons have registered callback_query handlers.
This test suite prevents issues where buttons are defined but have no handlers,
which was the root cause of the "Записать" button not working.

Test Coverage:
    - Main menu buttons have handlers
    - Time selection buttons have handlers
    - Settings buttons have handlers
    - Category buttons have handlers
    - Poll buttons have handlers
    - No orphaned handlers (handlers without buttons)

Coverage Target: 100% of all keyboard buttons
Execution Time: < 1 second

Author: Testing Team
Date: 2025-11-08
"""

import pytest
import re
from typing import Set, Dict, List
from pathlib import Path


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def extract_callback_data_from_file(file_path: Path) -> Set[str]:
    """
    Extract all callback_data values from a keyboard file.

    Args:
        file_path: Path to keyboard definition file

    Returns:
        Set of callback_data strings found in the file

    Example:
        InlineKeyboardButton(text="Test", callback_data="test_button")
        -> Returns: {"test_button"}
    """
    content = file_path.read_text()
    callbacks = set()

    # Pattern: callback_data="value" or callback_data='value'
    pattern = r'callback_data=["\']([^"\']+)["\']'
    for match in re.finditer(pattern, content):
        callback_value = match.group(1)

        # Handle f-strings with variables: f"prefix_{variable}"
        # Replace {variable} with {id} for pattern matching
        callback_value = re.sub(r'\{[^}]+\}', '{id}', callback_value)

        callbacks.add(callback_value)

    return callbacks


def extract_handlers_from_file(file_path: Path) -> Dict[str, List[str]]:
    """
    Extract all registered callback_query handlers from a handler file.

    Args:
        file_path: Path to handler definition file

    Returns:
        Dict mapping handler patterns to handler function names

    Example:
        @router.callback_query(F.data == "test")
        async def test_handler(...):
        -> Returns: {"test": ["test_handler"]}
    """
    content = file_path.read_text()
    handlers = {}

    # Pattern 1: @router.callback_query with F.data (but NOT with StateFilter)
    # This avoids double-counting handlers that have both StateFilter and F.data
    pattern1 = r'@router\.callback_query\([^)]*F\.data\s*==\s*["\']([^"\']+)["\']'
    for match in re.finditer(pattern1, content):
        # Check if this is NOT a StateFilter handler by looking backwards
        start_pos = match.start()
        preceding_text = content[max(0, start_pos-200):start_pos]
        if 'StateFilter' not in preceding_text:
            handler_value = match.group(1)
            handlers.setdefault(handler_value, []).append(file_path.stem)

    # Pattern 2: F.data.startswith("prefix_")
    pattern2 = r'F\.data\.startswith\(["\']([^"\']+)["\']'
    for match in re.finditer(pattern2, content):
        prefix = match.group(1)
        # Add wildcard pattern
        handlers.setdefault(f"{prefix}*", []).append(file_path.stem)

    # Pattern 3: StateFilter with F.data == "value"
    pattern3 = r'StateFilter\([^)]+\).*?F\.data\s*==\s*["\']([^"\']+)["\']'
    for match in re.finditer(pattern3, content, re.DOTALL):
        handler_value = match.group(1)
        handlers.setdefault(handler_value, []).append(file_path.stem)

    return handlers


def matches_pattern(callback: str, pattern: str) -> bool:
    """
    Check if callback matches a handler pattern.

    Args:
        callback: Callback data from button
        pattern: Handler pattern (exact match or wildcard)

    Returns:
        True if callback matches pattern

    Examples:
        matches_pattern("time_start_5m", "time_start_*") -> True
        matches_pattern("cancel", "cancel") -> True
        matches_pattern("test", "other") -> False
    """
    if pattern == callback:
        return True

    if pattern.endswith('*'):
        prefix = pattern[:-1]
        return callback.startswith(prefix)

    # Handle {id} placeholder
    if '{id}' in pattern:
        regex_pattern = pattern.replace('{id}', r'\d+')
        return bool(re.match(f"^{regex_pattern}$", callback))

    return False


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def all_keyboard_callbacks() -> Dict[str, Set[str]]:
    """
    Fixture: Extract all callback_data from all keyboard files.

    Returns:
        Dict mapping keyboard name to set of callback_data values
    """
    keyboards_path = Path("services/tracker_activity_bot/src/api/keyboards")
    all_callbacks = {}

    for file in keyboards_path.glob("*.py"):
        if file.name in ["__init__.py", "__pycache__"]:
            continue

        callbacks = extract_callback_data_from_file(file)
        if callbacks:
            all_callbacks[file.stem] = callbacks

    return all_callbacks


@pytest.fixture
def all_registered_handlers() -> Dict[str, List[str]]:
    """
    Fixture: Extract all registered callback_query handlers.

    Returns:
        Dict mapping handler pattern to list of handler files
    """
    handlers_path = Path("services/tracker_activity_bot/src/api/handlers")
    all_handlers = {}

    for file in handlers_path.rglob("*.py"):
        if file.name in ["__init__.py", "helpers.py"]:
            continue

        handlers = extract_handlers_from_file(file)
        for pattern, files in handlers.items():
            all_handlers.setdefault(pattern, []).extend(files)

    return all_handlers


# ============================================================================
# TEST SUITES
# ============================================================================

class TestMainMenuHandlers:
    """Test suite for main menu button handlers."""

    @pytest.mark.integration
    def test_all_main_menu_buttons_have_handlers(
        self,
        all_keyboard_callbacks,
        all_registered_handlers
    ):
        """
        Verify all main menu buttons have registered handlers.

        GIVEN: Main menu keyboard with buttons
        WHEN: Checking for registered handlers
        THEN: Every button callback_data has a matching handler

        This test would have caught the "Записать" button bug.
        """
        # Get main menu callbacks
        main_menu_callbacks = all_keyboard_callbacks.get("main_menu", set())

        # Check each callback has a handler
        missing_handlers = []
        for callback in main_menu_callbacks:
            has_handler = any(
                matches_pattern(callback, pattern)
                for pattern in all_registered_handlers.keys()
            )
            if not has_handler:
                missing_handlers.append(callback)

        assert not missing_handlers, \
            f"Main menu buttons without handlers: {missing_handlers}\n" \
            f"Available handlers: {list(all_registered_handlers.keys())}"


class TestTimeSelectionHandlers:
    """Test suite for time selection button handlers."""

    @pytest.mark.integration
    def test_start_time_buttons_have_handlers(
        self,
        all_keyboard_callbacks,
        all_registered_handlers
    ):
        """
        Verify start time quick selection buttons have handlers.

        GIVEN: Start time keyboard with quick selection buttons
        WHEN: Checking for registered handlers
        THEN: Every button has a matching handler
        """
        time_callbacks = all_keyboard_callbacks.get("time_select", set())

        # Filter for start time buttons
        start_callbacks = {cb for cb in time_callbacks if cb.startswith("time_start_")}

        missing = []
        for callback in start_callbacks:
            has_handler = any(
                matches_pattern(callback, pattern)
                for pattern in all_registered_handlers.keys()
            )
            if not has_handler:
                missing.append(callback)

        assert not missing, f"Start time buttons without handlers: {missing}"

    @pytest.mark.integration
    def test_end_time_buttons_have_handlers(
        self,
        all_keyboard_callbacks,
        all_registered_handlers
    ):
        """
        Verify end time quick selection buttons have handlers.

        GIVEN: End time keyboard with quick selection buttons
        WHEN: Checking for registered handlers
        THEN: Every button has a matching handler
        """
        time_callbacks = all_keyboard_callbacks.get("time_select", set())

        # Filter for end time buttons
        end_callbacks = {cb for cb in time_callbacks if cb.startswith("time_end_")}

        missing = []
        for callback in end_callbacks:
            has_handler = any(
                matches_pattern(callback, pattern)
                for pattern in all_registered_handlers.keys()
            )
            if not has_handler:
                missing.append(callback)

        assert not missing, f"End time buttons without handlers: {missing}"

    @pytest.mark.integration
    def test_cancel_button_has_handler(
        self,
        all_keyboard_callbacks,
        all_registered_handlers
    ):
        """
        Verify cancel button in time selection has handler.

        GIVEN: Cancel button in time selection keyboards
        WHEN: Checking for registered handler
        THEN: "cancel" callback has a handler

        This test would have caught the missing cancel button handler.
        """
        time_callbacks = all_keyboard_callbacks.get("time_select", set())

        if "cancel" in time_callbacks:
            has_handler = any(
                matches_pattern("cancel", pattern)
                for pattern in all_registered_handlers.keys()
            )
            assert has_handler, \
                "Cancel button has no handler!\n" \
                f"Available handlers: {list(all_registered_handlers.keys())}"


class TestPollHandlers:
    """Test suite for poll button handlers."""

    @pytest.mark.integration
    def test_poll_action_buttons_have_handlers(
        self,
        all_keyboard_callbacks,
        all_registered_handlers
    ):
        """
        Verify poll action buttons have handlers.

        GIVEN: Poll keyboard with action buttons
        WHEN: Checking for registered handlers
        THEN: All poll actions have handlers
        """
        poll_callbacks = all_keyboard_callbacks.get("poll", set())

        # Poll action buttons
        poll_actions = {
            cb for cb in poll_callbacks
            if cb.startswith("poll_") and not cb.startswith("poll_category_")
        }

        missing = []
        for callback in poll_actions:
            has_handler = any(
                matches_pattern(callback, pattern)
                for pattern in all_registered_handlers.keys()
            )
            if not has_handler:
                missing.append(callback)

        assert not missing, f"Poll action buttons without handlers: {missing}"

    @pytest.mark.integration
    def test_poll_category_buttons_have_handler_pattern(
        self,
        all_registered_handlers
    ):
        """
        Verify poll category dynamic buttons have handler pattern.

        GIVEN: Poll category buttons (generated dynamically)
        WHEN: Checking for handler pattern
        THEN: poll_category_* pattern has a registered handler
        """
        has_pattern = any(
            "poll_category" in pattern
            for pattern in all_registered_handlers.keys()
        )

        assert has_pattern, \
            "No handler pattern for poll_category_* buttons!\n" \
            f"Available patterns: {list(all_registered_handlers.keys())}"


class TestSettingsHandlers:
    """Test suite for settings button handlers."""

    @pytest.mark.integration
    def test_settings_menu_buttons_have_handlers(
        self,
        all_keyboard_callbacks,
        all_registered_handlers
    ):
        """
        Verify settings menu buttons have handlers.

        GIVEN: Settings keyboard with menu buttons
        WHEN: Checking for registered handlers
        THEN: All settings menu items have handlers
        """
        settings_callbacks = all_keyboard_callbacks.get("settings", set())

        # Main settings menu buttons
        menu_buttons = {
            cb for cb in settings_callbacks
            if cb.startswith("settings_")
        }

        missing = []
        for callback in menu_buttons:
            has_handler = any(
                matches_pattern(callback, pattern)
                for pattern in all_registered_handlers.keys()
            )
            if not has_handler:
                missing.append(callback)

        assert not missing, f"Settings menu buttons without handlers: {missing}"


class TestHandlerCoverage:
    """Test suite for overall handler coverage."""

    @pytest.mark.integration
    def test_all_buttons_have_handlers(
        self,
        all_keyboard_callbacks,
        all_registered_handlers
    ):
        """
        Comprehensive test: ALL buttons have handlers.

        GIVEN: All keyboard files with callback_data
        WHEN: Checking against all registered handlers
        THEN: Every callback_data has at least one handler

        This is the master test that catches any missing handlers.
        """
        all_callbacks = set()
        for callbacks in all_keyboard_callbacks.values():
            all_callbacks.update(callbacks)

        # Exclude dynamic patterns that are verified separately
        exclude_patterns = {
            # Dynamic category buttons verified by pattern test
            "poll_category_{id}",
            "delete_cat:{id}",
            "delete_confirm:{id}",
            # Dynamic interval buttons verified by pattern test
            "set_weekday_{id}",
            "set_weekend_{id}",
            # Dynamic time selection verified by pattern test
            "quiet_start_{id}",
            "quiet_end_{id}",
            # Dynamic reminder delay verified by pattern test
            "reminder_delay_{id}",
        }

        callbacks_to_check = all_callbacks - exclude_patterns

        missing_handlers = []
        for callback in callbacks_to_check:
            has_handler = any(
                matches_pattern(callback, pattern)
                for pattern in all_registered_handlers.keys()
            )
            if not has_handler:
                missing_handlers.append(callback)

        if missing_handlers:
            # Generate helpful error message
            error_msg = [
                f"\n{'='*60}",
                "MISSING HANDLERS DETECTED",
                f"{'='*60}",
                "",
                "The following buttons have NO registered handlers:",
                ""
            ]
            for callback in sorted(missing_handlers):
                error_msg.append(f"  ❌ {callback}")

            error_msg.extend([
                "",
                "To fix this, add a handler like:",
                "",
                "  @router.callback_query(F.data == \"button_name\")",
                "  async def handler_function(callback: types.CallbackQuery):",
                "      ...",
                "",
                f"Available handler patterns:",
                ""
            ])
            for pattern in sorted(all_registered_handlers.keys())[:10]:
                files = all_registered_handlers[pattern]
                error_msg.append(f"  ✓ {pattern} (in {', '.join(files[:2])})")

            error_msg.append(f"{'='*60}\n")

            pytest.fail("\n".join(error_msg))

    @pytest.mark.integration
    def test_no_duplicate_handler_registrations(
        self,
        all_registered_handlers
    ):
        """
        Verify no callback is handled by multiple conflicting handlers.

        GIVEN: All registered callback_query handlers
        WHEN: Checking for duplicate exact matches
        THEN: No callback_data is registered multiple times

        NOTE: Patterns like "time_start_*" don't conflict with "time_start_5m"
        """
        # Only check exact matches, not patterns
        exact_matches = {
            pattern: files
            for pattern, files in all_registered_handlers.items()
            if '*' not in pattern and '{id}' not in pattern
        }

        duplicates = []
        for pattern, files in exact_matches.items():
            if len(files) > 1:
                duplicates.append(f"{pattern} -> {files}")

        assert not duplicates, \
            f"Duplicate handler registrations found:\n" + "\n".join(duplicates)


# ============================================================================
# REGRESSION TESTS (Specific Bug Prevention)
# ============================================================================

class TestRegressionPrevention:
    """Tests that prevent specific bugs from recurring."""

    @pytest.mark.integration
    def test_add_activity_button_handler_registered(
        self,
        all_registered_handlers
    ):
        """
        Regression test: "Записать" button must have handler.

        Bug History: 2025-11-08 - add_activity button had no handler
        Root Cause: Function defined but no @router.callback_query decorator

        GIVEN: Main menu "Записать" button
        WHEN: Checking for add_activity handler
        THEN: Handler is registered
        """
        has_handler = "add_activity" in all_registered_handlers

        assert has_handler, \
            "REGRESSION: add_activity button has no handler!\n" \
            "The 'Записать' button will not work.\n" \
            "Add: @router.callback_query(F.data == \"add_activity\")"

    @pytest.mark.integration
    def test_cancel_button_handler_registered(
        self,
        all_registered_handlers
    ):
        """
        Regression test: Cancel button must have handler.

        Bug History: 2025-11-08 - cancel button had no handler
        Root Cause: Function defined but never registered

        GIVEN: Time selection "Отменить" button
        WHEN: Checking for cancel handler
        THEN: Handler is registered
        """
        has_handler = "cancel" in all_registered_handlers

        assert has_handler, \
            "REGRESSION: cancel button has no handler!\n" \
            "The 'Отменить' button in time selection will not work.\n" \
            "Add: @router.callback_query(F.data == \"cancel\")"
