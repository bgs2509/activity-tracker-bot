# File Structure Refactoring Plan

**Date:** 2025-11-07
**Type:** Structural Refactoring
**Focus:** Breaking down large files into smaller, focused modules
**Author:** Claude Code Analysis

---

## Executive Summary

This document outlines a comprehensive plan to refactor the Activity Tracker Bot codebase by breaking down large files (>350 lines) into smaller, focused modules that adhere to the Single Responsibility Principle (SRP). The current codebase has **4 files exceeding 400 lines** and **8 files exceeding 300 lines**, which impacts maintainability and readability.

**Key Goals:**
- Reduce maximum file size from 555 lines to ~300 lines
- Improve code organization and discoverability
- Maintain high cohesion within modules
- Reduce coupling between modules
- Follow established architectural patterns

**Impact:**
- 4 critical files requiring refactoring
- 4 high-priority files requiring refactoring
- Estimated effort: 16-24 hours
- Risk level: Medium (FSM state management requires careful handling)

---

## Table of Contents

1. [Current State Analysis](#current-state-analysis)
2. [Problem Statement](#problem-statement)
3. [Design Principles](#design-principles)
4. [Target Architecture](#target-architecture)
5. [Detailed Refactoring Plans](#detailed-refactoring-plans)
6. [Implementation Phases](#implementation-phases)
7. [Risk Assessment](#risk-assessment)
8. [Testing Strategy](#testing-strategy)
9. [Metrics & Success Criteria](#metrics--success-criteria)
10. [References](#references)

---

## Current State Analysis

### File Size Distribution

```
Total Python Files: 91
Total Lines of Code: 10,174
Average File Size: 112 lines

Size Distribution:
  0-100 lines:   56 files (61.5%) ✅ Excellent
  100-200 lines: 21 files (23.1%) ✅ Good
  200-300 lines: 10 files (11.0%) ⚠️  Acceptable
  300-400 lines:  0 files ( 0.0%)
  >400 lines:     4 files ( 4.4%) ❌ Critical
```

### Critical Files Requiring Refactoring

| File | Lines | Functions | Status | Priority |
|------|-------|-----------|--------|----------|
| `activity_creation.py` | 555 | 11 | ❌ Critical | P1 |
| `categories.py` | 538 | 11 | ❌ Critical | P0 |
| `quiet_hours_settings.py` | 522 | ~10 | ❌ Critical | P2 |
| `interval_settings.py` | 446 | ~9 | ❌ Critical | P2 |
| `main_menu.py` (settings) | 395 | ~8 | ⚠️ High | P3 |
| `poll_activity.py` | 382 | ~7 | ⚠️ High | P3 |
| `poll_handlers.py` | 352 | ~6 | ⚠️ High | P3 |
| `logging_middleware.py` | 325 | ~5 | ⚠️ Medium | P4 |

### Current Directory Structure

```
services/tracker_activity_bot/src/api/handlers/
├── activity/
│   ├── activity_creation.py      555 lines ❌
│   ├── activity_management.py    193 lines ✅
│   └── helpers.py                 86 lines ✅
├── categories.py                 538 lines ❌ (NOT structured!)
├── poll/
│   ├── poll_handlers.py          352 lines ⚠️
│   ├── poll_activity.py          382 lines ⚠️
│   ├── poll_sender.py            294 lines ✅
│   └── helpers.py                101 lines ✅
├── settings/
│   ├── main_menu.py              395 lines ⚠️
│   ├── quiet_hours_settings.py   522 lines ❌
│   ├── interval_settings.py      446 lines ❌
│   ├── reminder_settings.py      299 lines ⚠️
│   └── helpers.py                 74 lines ✅
└── start.py                       94 lines ✅
```

### Data API Service (Reference - Good Structure)

```
services/data_postgres_api/src/
├── api/v1/
│   ├── users.py              59 lines ✅
│   ├── categories.py         56 lines ✅
│   ├── activities.py         78 lines ✅
│   └── user_settings.py      55 lines ✅
├── application/services/
│   ├── user_service.py       100 lines ✅
│   ├── category_service.py   109 lines ✅
│   ├── activity_service.py    98 lines ✅
│   └── user_settings_service.py 135 lines ✅
├── infrastructure/repositories/
│   ├── base.py               124 lines ✅ (Generic)
│   ├── user_repository.py     21 lines ✅
│   ├── category_repository.py 47 lines ✅
│   └── activity_repository.py 81 lines ✅
└── domain/models/
    ├── user.py                56 lines ✅
    ├── category.py            48 lines ✅
    ├── activity.py            57 lines ✅
    └── user_settings.py       52 lines ✅
```

**Key Observation:** Data API service has excellent structure with files averaging 50-100 lines. Bot service should follow similar patterns.

---

## Problem Statement

### Primary Issues

1. **Large Monolithic Files**
   - `categories.py` (538 lines) handles 3 different business processes (list, create, delete)
   - Settings files (400-500 lines each) mix multiple FSM flows
   - Difficult to locate specific functionality
   - High cognitive load when reading code

2. **Inconsistent Structure**
   - `activity/` and `poll/` are properly structured into subdirectories
   - `categories.py` remains monolithic despite handling multiple concerns
   - Settings files are split but each is still too large

3. **Technical Debt**
   - Old backup files (`.old`) consuming space:
     - `activity.py.old` (28,513 lines)
     - `poll.py.old` (24,165 lines)
     - `settings.py.old` (36,166 lines)

### Impact on Development

- **Discoverability:** Hard to find where specific functionality is implemented
- **Maintainability:** Large files are harder to understand and modify
- **Testing:** Difficult to test large files with multiple responsibilities
- **Code Review:** Reviewing changes in 500+ line files is time-consuming
- **Collaboration:** Merge conflicts more likely in large files

---

## Design Principles

### When to Split a File

✅ **DO split when:**

1. **Multiple Business Processes**
   ```python
   # categories.py contains:
   - Category listing (read)
   - Category creation (FSM: name → emoji)
   - Category deletion (FSM: select → confirm)
   # → Split into separate files
   ```

2. **File Exceeds 350 Lines** AND has logical boundaries
   ```python
   # quiet_hours_settings.py (522 lines):
   - Main menu handlers
   - Start time FSM flow
   - End time FSM flow
   # → Split into separate flows
   ```

3. **Low Cohesion**
   ```python
   # Multiple unrelated functions in one file
   # → Group by responsibility
   ```

❌ **DON'T split when:**

1. **Single FSM Flow** (high cohesion)
   ```python
   # activity_creation.py (555 lines):
   # start_time → end_time → description → category → save
   # All steps are tightly coupled
   # → Keep together for readability
   ```

2. **File Under 250 Lines** (acceptable size)

3. **High Cohesion** (all functions relate to one concept)
   ```python
   # time_helpers.py - all time-related utilities
   # → Keep together
   ```

### Optimal File Sizes

```
 50-150 lines: ✅ Ideal
150-250 lines: ✅ Acceptable
250-350 lines: ⚠️  Consider splitting if low cohesion
    >350 lines: ❌ Must split (unless single FSM flow)
```

### Architecture Patterns to Follow

1. **Single Responsibility Principle (SRP)**
   - Each file has one clear purpose
   - Easy to name and describe in one sentence

2. **High Cohesion, Low Coupling**
   - Code within a file is tightly related
   - Files have minimal dependencies on each other

3. **Consistent Structure**
   - Follow patterns from `activity/` and `poll/` directories
   - Match Data API service organization where applicable

4. **Clear Naming**
   - File names clearly indicate their purpose
   - `category_creation.py` > `category_add.py`
   - `category_list.py` > `category_view.py`

---

## Target Architecture

### Categories Module Restructure

**Current:**
```
handlers/
└── categories.py          538 lines (3 business processes)
```

**Target:**
```
handlers/categories/
├── __init__.py            ~20 lines  (router exports)
├── category_list.py       ~90 lines  (view list, navigation)
├── category_creation.py   ~230 lines (FSM: name → emoji → save)
├── category_deletion.py   ~180 lines (FSM: select → confirm → delete)
└── helpers.py             ~50 lines  (keyboard builders, validation)
```

**Rationale:**
- Matches existing `activity/` and `poll/` structure
- Each file has single business process
- Easy to locate functionality
- Files are appropriately sized (90-230 lines)

### Settings Module Restructure

#### Option A: Deep Nesting (by feature)

```
handlers/settings/
├── __init__.py
├── main_menu.py           ~150 lines (settings entry, navigation)
├── intervals/
│   ├── __init__.py
│   ├── menu.py            ~80 lines
│   ├── weekday_flow.py    ~180 lines
│   └── weekend_flow.py    ~180 lines
├── quiet_hours/
│   ├── __init__.py
│   ├── menu.py            ~80 lines
│   ├── start_time_flow.py ~220 lines
│   └── end_time_flow.py   ~220 lines
└── reminders/
    ├── __init__.py
    ├── menu.py            ~80 lines
    └── reminder_flow.py   ~180 lines
```

**Pros:** Clear feature separation
**Cons:** Deep nesting, more directories

#### Option B: Flat Structure (by flow) ✅ **RECOMMENDED**

```
handlers/settings/
├── __init__.py                     ~30 lines
├── main_menu.py                    ~150 lines (reduce from 395)
├── interval_weekday_settings.py    ~200 lines
├── interval_weekend_settings.py    ~200 lines
├── quiet_hours_start_settings.py   ~240 lines
├── quiet_hours_end_settings.py     ~240 lines
├── reminder_settings.py            ~280 lines (keep as is)
└── helpers.py                      ~100 lines
```

**Pros:**
- Flatter structure, easier navigation
- Each file is one FSM flow
- Consistent with project style

**Cons:**
- More files in one directory (7 files)

**Decision:** Use Option B for consistency with existing structure.

### Poll Module Optimization

**Current (3 files with unclear boundaries):**
```
handlers/poll/
├── poll_handlers.py       352 lines (response handling)
├── poll_activity.py       382 lines (activity creation from poll)
├── poll_sender.py         294 lines (sending polls)
└── helpers.py             101 lines
```

**Issue:** Unclear separation between `poll_handlers` and `poll_activity`

**Target:**
```
handlers/poll/
├── __init__.py            ~30 lines
├── poll_sender.py         ~300 lines (scheduling + sending)
├── poll_response.py       ~600 lines (response handling + activity creation)
└── helpers.py             ~100 lines (time calculations, keyboards)
```

**Rationale:**
- Clear separation: "sending" vs "responding"
- Combines related logic (response handling + activity creation)
- Reduces cognitive load: 2 main files instead of 3
- 600 lines is acceptable for complex response handling

**Alternative (if 600 lines feels too large):**
```
handlers/poll/
├── __init__.py
├── poll_sender.py         ~300 lines
├── poll_response.py       ~400 lines (button callbacks, FSM)
├── poll_activity.py       ~250 lines (activity creation logic)
└── helpers.py             ~100 lines
```

### Activity Module Assessment

**Current:**
```
handlers/activity/
├── activity_creation.py   555 lines ⚠️
├── activity_management.py 193 lines ✅
└── helpers.py              86 lines ✅
```

**Recommendation:** **KEEP AS IS**

**Rationale:**
- `activity_creation.py` is a single FSM flow with 11 tightly coupled steps
- Splitting would reduce readability (harder to follow the flow)
- 555 lines is on the edge but acceptable for FSM flows
- Clear, logical progression: start → end → description → category → save

**Minor Optimization (Optional):**
```
handlers/activity/
├── activity_creation.py   ~450 lines (FSM handlers)
├── activity_management.py ~193 lines (existing)
├── helpers.py             ~100 lines (validation, keyboard builders)
└── formatters.py          ~80 lines  (time formatting, moved from helpers)
```

---

## Detailed Refactoring Plans

### 1. Categories Module (Priority: P0)

**Estimated Effort:** 4-6 hours
**Risk Level:** Low
**Dependencies:** None

#### Current Structure Analysis

```python
# categories.py (538 lines) contains:

# Section 1: CATEGORY LIST VIEW (50 lines)
@router.callback_query(F.data == "categories")
async def show_categories_list(...)

# Section 2: ADD CATEGORY (270 lines)
@router.callback_query(F.data == "add_category")
async def add_category_start(...)  # Entry point

@router.message(CategoryStates.waiting_for_category_name)
async def add_category_name(...)   # FSM step 1

@router.callback_query(CategoryStates.waiting_for_emoji)
async def add_category_emoji_button(...)  # FSM step 2a

@router.message(CategoryStates.waiting_for_emoji)
async def add_category_emoji_text(...)  # FSM step 2b

async def create_category_final(...)  # Helper

# Section 3: DELETE CATEGORY (170 lines)
@router.callback_query(F.data == "delete_category")
async def delete_category_select(...)  # Entry

@router.callback_query(F.data.startswith("delete_cat_"))
async def delete_category_confirm(...)  # Confirm

@router.callback_query(F.data.startswith("confirm_delete_cat_"))
async def delete_category_execute(...)  # Execute

# Section 4: COMMON (48 lines)
@router.message(CategoryStates.waiting_for_category_name)
async def cancel_category_fsm(...)

@router.callback_query(F.data == "back_to_main")
async def show_main_menu(...)
```

#### Target Structure

##### File 1: `categories/__init__.py`

```python
"""Category management handlers.

This package provides handlers for:
- Viewing category list
- Creating new categories
- Deleting existing categories
"""

from aiogram import Router

from .category_list import router as list_router
from .category_creation import router as creation_router
from .category_deletion import router as deletion_router

# Combine all routers
router = Router()
router.include_router(list_router)
router.include_router(creation_router)
router.include_router(deletion_router)

__all__ = ["router"]
```

**Lines:** ~20

##### File 2: `categories/category_list.py`

```python
"""Category list view handler.

Displays user's categories with options to add or delete.
"""

import logging
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext

from src.api.dependencies import ServiceContainer
from src.api.decorators import require_user
from src.api.keyboards.main_menu import get_main_menu_keyboard
from src.application.utils.decorators import with_typing_action
from src.core.logging_middleware import log_user_action

from .helpers import build_category_list_keyboard

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "categories")
@with_typing_action
@log_user_action("categories_button_clicked")
@require_user
async def show_categories_list(
    callback: types.CallbackQuery,
    services: ServiceContainer,
    user: dict
):
    """Show list of user's categories.

    Triggered by: Main menu "📂 Категории" button

    Args:
        callback: Callback query from button press
        services: Service container for API access
        user: Current user data
    """
    logger.debug(
        "User opened categories list",
        extra={"user_id": callback.from_user.id}
    )

    # Get categories
    categories = await services.category.get_user_categories(user["id"])

    # Build keyboard
    keyboard = build_category_list_keyboard(categories)

    # Format message
    if categories:
        text = "📂 Твои категории:\n\n"
        for cat in categories:
            emoji = cat.get("emoji", "")
            text += f"{emoji} {cat['name']}\n"
        text += "\n💡 Выбери действие:"
    else:
        text = (
            "📂 У тебя пока нет категорий\n\n"
            "Категории помогают группировать активности.\n"
            "Например: 💼 Работа, 📚 Учёба, 🎮 Отдых\n\n"
            "Добавь первую категорию! 👇"
        )

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "back_to_main")
async def back_to_main_menu(callback: types.CallbackQuery):
    """Return to main menu from categories."""
    keyboard = get_main_menu_keyboard()
    await callback.message.edit_text(
        "Главное меню:",
        reply_markup=keyboard
    )
    await callback.answer()
```

**Lines:** ~90

##### File 3: `categories/category_creation.py`

```python
"""Category creation FSM flow.

Handles the multi-step process of creating a new category:
1. User initiates creation
2. User enters category name
3. User selects or enters emoji
4. Category is saved via API
"""

import logging
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext

from src.api.dependencies import ServiceContainer
from src.api.decorators import require_user
from src.api.states.category import CategoryStates
from src.application.services import fsm_timeout_service as fsm_timeout_module
from src.application.utils.fsm_helpers import (
    schedule_fsm_timeout,
    clear_state_and_timeout
)
from src.application.utils.decorators import with_typing_action
from src.core.logging_middleware import log_user_action

from .helpers import (
    build_emoji_selection_keyboard,
    validate_category_name,
    extract_emoji
)

router = Router()
logger = logging.getLogger(__name__)

MAX_CATEGORY_NAME_LENGTH = 100


@router.callback_query(F.data == "add_category")
@with_typing_action
@log_user_action("add_category_initiated")
async def start_category_creation(callback: types.CallbackQuery, state: FSMContext):
    """Start category creation flow.

    Entry point for adding a new category.
    Sets FSM state and prompts for category name.
    """
    logger.debug(
        "User started category creation",
        extra={"user_id": callback.from_user.id}
    )

    await state.set_state(CategoryStates.waiting_for_category_name)

    # Schedule FSM timeout
    await schedule_fsm_timeout(
        callback.from_user.id,
        CategoryStates.waiting_for_category_name,
        callback.bot
    )

    text = (
        "📝 Введи название категории\n\n"
        f"Максимум {MAX_CATEGORY_NAME_LENGTH} символов.\n"
        "Например: Работа, Учёба, Спорт\n\n"
        "Отправь /cancel для отмены"
    )

    await callback.message.edit_text(text)
    await callback.answer()


@router.message(CategoryStates.waiting_for_category_name)
@with_typing_action
async def process_category_name(
    message: types.Message,
    state: FSMContext,
    services: ServiceContainer
):
    """Process category name input.

    Validates the name and proceeds to emoji selection.

    Args:
        message: User's message with category name
        state: FSM context
        services: Service container
    """
    user_id = message.from_user.id
    category_name = message.text.strip()

    # Cancel command
    if category_name == "/cancel":
        await clear_state_and_timeout(state, user_id)
        await message.answer("❌ Создание категории отменено")
        return

    # Validate name
    error = validate_category_name(category_name)
    if error:
        await message.answer(
            f"❌ {error}\n\n"
            f"Попробуй снова или отправь /cancel для отмены"
        )
        return

    # Check for duplicates
    try:
        user = await services.user.get_by_telegram_id(user_id)
        if not user:
            await message.answer("❌ Ошибка: пользователь не найден")
            await clear_state_and_timeout(state, user_id)
            return

        existing_categories = await services.category.get_user_categories(user["id"])

        # Check if name already exists (case-insensitive)
        if any(cat["name"].lower() == category_name.lower() for cat in existing_categories):
            await message.answer(
                f"❌ Категория '{category_name}' уже существует\n\n"
                "Введи другое название или /cancel для отмены"
            )
            return

    except Exception as e:
        logger.error(f"Error checking category duplicates: {e}", exc_info=True)
        await message.answer("❌ Ошибка при проверке категории")
        await clear_state_and_timeout(state, user_id)
        return

    # Save name to FSM data
    await state.update_data(category_name=category_name)
    await state.set_state(CategoryStates.waiting_for_emoji)

    # Reschedule timeout for new state
    await schedule_fsm_timeout(
        user_id,
        CategoryStates.waiting_for_emoji,
        message.bot
    )

    # Show emoji selection
    keyboard = build_emoji_selection_keyboard()
    text = (
        f"✅ Название: {category_name}\n\n"
        "😊 Выбери эмодзи для категории\n\n"
        "Можешь:\n"
        "• Выбрать из предложенных ниже\n"
        "• Отправить своё эмодзи\n"
        "• Отправить '-' для пропуска\n\n"
        "/cancel для отмены"
    )

    await message.answer(text, reply_markup=keyboard)


@router.callback_query(
    CategoryStates.waiting_for_emoji,
    F.data.startswith("emoji_")
)
@with_typing_action
async def process_emoji_button(
    callback: types.CallbackQuery,
    state: FSMContext,
    services: ServiceContainer
):
    """Process emoji selection from inline keyboard.

    Args:
        callback: Callback with emoji selection
        state: FSM context
        services: Service container
    """
    user_id = callback.from_user.id

    # Extract emoji from callback data
    emoji = callback.data.replace("emoji_", "")
    if emoji == "skip":
        emoji = None

    # Get category name from FSM data
    data = await state.get_data()
    category_name = data.get("category_name")

    if not category_name:
        logger.error("Category name not found in FSM data")
        await callback.answer("❌ Ошибка: данные утеряны", show_alert=True)
        await clear_state_and_timeout(state, user_id)
        return

    # Create category
    await create_category_final(
        category_name=category_name,
        emoji=emoji,
        user_id=user_id,
        services=services,
        state=state,
        callback_or_message=callback
    )


@router.message(CategoryStates.waiting_for_emoji)
@with_typing_action
async def process_emoji_text(
    message: types.Message,
    state: FSMContext,
    services: ServiceContainer
):
    """Process emoji entered as text message.

    Args:
        message: User's message with emoji
        state: FSM context
        services: Service container
    """
    user_id = message.from_user.id
    text = message.text.strip()

    # Cancel command
    if text == "/cancel":
        await clear_state_and_timeout(state, user_id)
        await message.answer("❌ Создание категории отменено")
        return

    # Skip emoji
    if text == "-":
        emoji = None
    else:
        # Extract emoji from text
        emoji = extract_emoji(text)
        if not emoji:
            await message.answer(
                "❌ Не найдено эмодзи в сообщении\n\n"
                "Отправь эмодзи или '-' для пропуска\n"
                "/cancel для отмены"
            )
            return

    # Get category name from FSM data
    data = await state.get_data()
    category_name = data.get("category_name")

    if not category_name:
        logger.error("Category name not found in FSM data")
        await message.answer("❌ Ошибка: данные утеряны")
        await clear_state_and_timeout(state, user_id)
        return

    # Create category
    await create_category_final(
        category_name=category_name,
        emoji=emoji,
        user_id=user_id,
        services=services,
        state=state,
        callback_or_message=message
    )


async def create_category_final(
    category_name: str,
    emoji: str | None,
    user_id: int,
    services: ServiceContainer,
    state: FSMContext,
    callback_or_message
):
    """Save category to database and finish FSM flow.

    Args:
        category_name: Category name
        emoji: Optional emoji
        user_id: Telegram user ID
        services: Service container
        state: FSM context
        callback_or_message: Either CallbackQuery or Message for response
    """
    try:
        # Get user
        user = await services.user.get_by_telegram_id(user_id)
        if not user:
            error_text = "❌ Ошибка: пользователь не найден"
            if isinstance(callback_or_message, types.CallbackQuery):
                await callback_or_message.answer(error_text, show_alert=True)
            else:
                await callback_or_message.answer(error_text)
            await clear_state_and_timeout(state, user_id)
            return

        # Create category via API
        category_data = {
            "user_id": user["id"],
            "name": category_name,
            "emoji": emoji,
            "is_default": False
        }

        category = await services.category.create_category(category_data)

        # Clear FSM
        await clear_state_and_timeout(state, user_id)

        # Success message
        emoji_display = f"{emoji} " if emoji else ""
        success_text = (
            f"✅ Категория создана!\n\n"
            f"{emoji_display}{category_name}\n\n"
            "Теперь её можно использовать при добавлении активностей"
        )

        logger.info(
            "Category created",
            extra={
                "user_id": user_id,
                "category_id": category["id"],
                "category_name": category_name
            }
        )

        if isinstance(callback_or_message, types.CallbackQuery):
            await callback_or_message.message.edit_text(success_text)
            await callback_or_message.answer()
        else:
            await callback_or_message.answer(success_text)

    except Exception as e:
        logger.error(f"Error creating category: {e}", exc_info=True)

        error_text = (
            f"❌ Ошибка при создании категории\n\n"
            f"Попробуй позже или обратись к администратору"
        )

        if isinstance(callback_or_message, types.CallbackQuery):
            await callback_or_message.answer(error_text, show_alert=True)
        else:
            await callback_or_message.answer(error_text)

        await clear_state_and_timeout(state, user_id)
```

**Lines:** ~230

##### File 4: `categories/category_deletion.py`

```python
"""Category deletion FSM flow.

Handles the multi-step process of deleting a category:
1. User selects category to delete
2. User confirms deletion
3. Category is deleted via API (activities set to no category)
"""

import logging
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext

from src.api.dependencies import ServiceContainer
from src.api.decorators import require_user
from src.application.utils.decorators import with_typing_action
from src.core.logging_middleware import log_user_action

from .helpers import build_category_delete_keyboard

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "delete_category")
@with_typing_action
@log_user_action("delete_category_initiated")
@require_user
async def start_category_deletion(
    callback: types.CallbackQuery,
    services: ServiceContainer,
    user: dict
):
    """Show category selection for deletion.

    Entry point for deleting a category.
    Displays list of categories with delete buttons.

    Args:
        callback: Callback query from button press
        services: Service container
        user: Current user data
    """
    logger.debug(
        "User started category deletion",
        extra={"user_id": callback.from_user.id}
    )

    # Get categories
    categories = await services.category.get_user_categories(user["id"])

    if not categories:
        await callback.answer(
            "❌ У тебя нет категорий для удаления",
            show_alert=True
        )
        return

    # Build keyboard
    keyboard = build_category_delete_keyboard(categories)

    text = (
        "🗑️ Выбери категорию для удаления:\n\n"
        "⚠️ Внимание:\n"
        "• Активности с этой категорией останутся\n"
        "• Но категория у них станет 'Без категории'\n"
    )

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("delete_cat_"))
@with_typing_action
async def confirm_category_deletion(
    callback: types.CallbackQuery,
    services: ServiceContainer
):
    """Show deletion confirmation.

    Args:
        callback: Callback with category ID to delete
        services: Service container
    """
    user_id = callback.from_user.id

    # Extract category ID
    try:
        category_id = int(callback.data.replace("delete_cat_", ""))
    except ValueError:
        logger.error(f"Invalid category ID in callback: {callback.data}")
        await callback.answer("❌ Ошибка: неверный ID категории", show_alert=True)
        return

    # Get category details
    try:
        category = await services.category.get_category(category_id)
        if not category:
            await callback.answer(
                "❌ Категория не найдена",
                show_alert=True
            )
            return

        # Verify ownership
        user = await services.user.get_by_telegram_id(user_id)
        if not user or category["user_id"] != user["id"]:
            await callback.answer(
                "❌ Это не твоя категория",
                show_alert=True
            )
            return

        # Build confirmation keyboard
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="✅ Да, удалить",
                    callback_data=f"confirm_delete_cat_{category_id}"
                ),
                types.InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="categories"
                )
            ]
        ])

        emoji = category.get("emoji", "")
        text = (
            f"🗑️ Удалить категорию?\n\n"
            f"{emoji} {category['name']}\n\n"
            f"⚠️ Это действие нельзя отменить!"
        )

        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()

    except Exception as e:
        logger.error(f"Error confirming category deletion: {e}", exc_info=True)
        await callback.answer(
            "❌ Ошибка при загрузке категории",
            show_alert=True
        )


@router.callback_query(F.data.startswith("confirm_delete_cat_"))
@with_typing_action
async def execute_category_deletion(
    callback: types.CallbackQuery,
    services: ServiceContainer
):
    """Execute category deletion.

    Args:
        callback: Callback with confirmed category ID
        services: Service container
    """
    user_id = callback.from_user.id

    # Extract category ID
    try:
        category_id = int(callback.data.replace("confirm_delete_cat_", ""))
    except ValueError:
        logger.error(f"Invalid category ID in callback: {callback.data}")
        await callback.answer("❌ Ошибка: неверный ID", show_alert=True)
        return

    try:
        # Get category for logging
        category = await services.category.get_category(category_id)
        if not category:
            await callback.answer("❌ Категория не найдена", show_alert=True)
            return

        # Verify ownership again
        user = await services.user.get_by_telegram_id(user_id)
        if not user or category["user_id"] != user["id"]:
            await callback.answer("❌ Это не твоя категория", show_alert=True)
            return

        # Delete category
        success = await services.category.delete_category(category_id)

        if success:
            logger.info(
                "Category deleted",
                extra={
                    "user_id": user_id,
                    "category_id": category_id,
                    "category_name": category["name"]
                }
            )

            await callback.answer("✅ Категория удалена", show_alert=True)

            # Show updated list
            categories = await services.category.get_user_categories(user["id"])

            if categories:
                text = "📂 Твои категории:\n\n"
                for cat in categories:
                    emoji = cat.get("emoji", "")
                    text += f"{emoji} {cat['name']}\n"
                text += "\n💡 Выбери действие:"

                from .helpers import build_category_list_keyboard
                keyboard = build_category_list_keyboard(categories)
            else:
                text = (
                    "📂 У тебя больше нет категорий\n\n"
                    "Добавь новую категорию! 👇"
                )
                keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                    [types.InlineKeyboardButton(
                        text="➕ Добавить категорию",
                        callback_data="add_category"
                    )],
                    [types.InlineKeyboardButton(
                        text="🔙 Главное меню",
                        callback_data="back_to_main"
                    )]
                ])

            await callback.message.edit_text(text, reply_markup=keyboard)
        else:
            await callback.answer(
                "❌ Не удалось удалить категорию",
                show_alert=True
            )

    except Exception as e:
        logger.error(f"Error deleting category: {e}", exc_info=True)
        await callback.answer(
            "❌ Ошибка при удалении категории",
            show_alert=True
        )
```

**Lines:** ~180

##### File 5: `categories/helpers.py`

```python
"""Helper functions for category handlers.

Contains keyboard builders, validators, and utility functions.
"""

import re
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def build_category_list_keyboard(categories: list) -> InlineKeyboardMarkup:
    """Build keyboard for category list view.

    Args:
        categories: List of user's categories

    Returns:
        Inline keyboard with add/delete buttons
    """
    buttons = []

    # Add category button
    buttons.append([
        InlineKeyboardButton(
            text="➕ Добавить категорию",
            callback_data="add_category"
        )
    ])

    # Delete category button (if categories exist)
    if categories:
        buttons.append([
            InlineKeyboardButton(
                text="🗑️ Удалить категорию",
                callback_data="delete_category"
            )
        ])

    # Back button
    buttons.append([
        InlineKeyboardButton(
            text="🔙 Главное меню",
            callback_data="back_to_main"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_emoji_selection_keyboard() -> InlineKeyboardMarkup:
    """Build keyboard with common emoji options.

    Returns:
        Inline keyboard with emoji buttons
    """
    common_emojis = [
        ("💼", "work"), ("📚", "study"), ("🎮", "gaming"),
        ("🏃", "sport"), ("🍳", "cooking"), ("🎬", "movies"),
        ("🎵", "music"), ("✈️", "travel"), ("🛒", "shopping"),
    ]

    buttons = []
    row = []

    for emoji, code in common_emojis:
        row.append(
            InlineKeyboardButton(
                text=emoji,
                callback_data=f"emoji_{emoji}"
            )
        )
        # 3 emojis per row
        if len(row) == 3:
            buttons.append(row)
            row = []

    # Add remaining emojis
    if row:
        buttons.append(row)

    # Skip button
    buttons.append([
        InlineKeyboardButton(
            text="⏭️ Пропустить",
            callback_data="emoji_skip"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_category_delete_keyboard(categories: list) -> InlineKeyboardMarkup:
    """Build keyboard for category deletion selection.

    Args:
        categories: List of categories to show

    Returns:
        Inline keyboard with category delete buttons
    """
    buttons = []

    for category in categories:
        emoji = category.get("emoji", "")
        name = category["name"]
        display_text = f"{emoji} {name}" if emoji else name

        buttons.append([
            InlineKeyboardButton(
                text=display_text,
                callback_data=f"delete_cat_{category['id']}"
            )
        ])

    # Cancel button
    buttons.append([
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="categories"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def validate_category_name(name: str) -> str | None:
    """Validate category name.

    Args:
        name: Category name to validate

    Returns:
        Error message if invalid, None if valid
    """
    if not name:
        return "Название не может быть пустым"

    if len(name) > 100:
        return "Название слишком длинное (максимум 100 символов)"

    if len(name) < 2:
        return "Название слишком короткое (минимум 2 символа)"

    # Check for invalid characters (optional)
    # Allow letters, numbers, spaces, dashes, underscores
    if not re.match(r'^[\w\s\-]+$', name, re.UNICODE):
        return "Название содержит недопустимые символы"

    return None


def extract_emoji(text: str) -> str | None:
    """Extract first emoji from text.

    Args:
        text: Text potentially containing emoji

    Returns:
        First emoji found or None
    """
    # Simple emoji detection using Unicode ranges
    # This is a simplified version; full emoji detection is complex
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE
    )

    match = emoji_pattern.search(text)
    return match.group(0) if match else None
```

**Lines:** ~50

#### Migration Steps

1. **Create directory structure**
   ```bash
   mkdir -p services/tracker_activity_bot/src/api/handlers/categories
   ```

2. **Create `__init__.py`** with router exports

3. **Extract code into separate files:**
   - Move list view → `category_list.py`
   - Move creation FSM → `category_creation.py`
   - Move deletion FSM → `category_deletion.py`
   - Move helpers → `helpers.py`

4. **Update imports** in each file

5. **Update main handler registration:**
   ```python
   # In src/main.py or router configuration
   from src.api.handlers.categories import router as categories_router
   dp.include_router(categories_router)
   ```

6. **Test each flow:**
   - Category list view
   - Category creation FSM
   - Category deletion FSM

7. **Remove old file:**
   ```bash
   git rm services/tracker_activity_bot/src/api/handlers/categories.py
   ```

#### Testing Checklist

- [ ] Category list displays correctly
- [ ] "Add category" button works
- [ ] Category name FSM step works
- [ ] Emoji selection (buttons) works
- [ ] Emoji selection (text input) works
- [ ] Skip emoji works
- [ ] Category creation succeeds
- [ ] Duplicate name validation works
- [ ] Delete category shows list
- [ ] Delete confirmation works
- [ ] Delete execution works
- [ ] Back to main menu works
- [ ] FSM timeout works
- [ ] Cancel command works

---

### 2. Settings Module (Priority: P2)

**Estimated Effort:** 8-12 hours
**Risk Level:** Medium (complex FSM flows)
**Dependencies:** None

#### Current Issues

1. **quiet_hours_settings.py** (522 lines)
   - Handles both start time and end time settings
   - Each is a separate FSM flow
   - Mixing concerns

2. **interval_settings.py** (446 lines)
   - Handles both weekday and weekend intervals
   - Similar but separate flows
   - Could be split

3. **main_menu.py** (395 lines)
   - Entry point + multiple setting displays
   - Somewhat acceptable but could be optimized

#### Refactoring Decision

**Option A: Deep Split** (Not recommended)
```
settings/
├── intervals/
│   ├── weekday.py
│   └── weekend.py
├── quiet_hours/
│   ├── start_time.py
│   └── end_time.py
```

**Option B: Flat Split** ✅ (Recommended)
```
settings/
├── main_menu.py                    ~200 lines (reduce)
├── interval_weekday.py             ~220 lines
├── interval_weekend.py             ~220 lines
├── quiet_hours_start.py            ~260 lines
├── quiet_hours_end.py              ~260 lines
├── reminder_settings.py            ~280 lines (keep as is)
└── helpers.py                      ~100 lines
```

**Rationale:**
- Maintains flat structure consistent with project
- Each file = one FSM flow
- Clear naming
- Easy to navigate

#### Implementation Notes

1. **Extract common validation** to `helpers.py`:
   - Time validation
   - Interval validation
   - Keyboard builders

2. **Each flow file should contain:**
   - Entry handler (callback_query)
   - FSM steps (message handlers)
   - Save handler (final step)
   - Back/cancel handlers

3. **Ensure FSM state naming** is clear:
   ```python
   # Good
   SettingsStates.waiting_for_weekday_interval
   SettingsStates.waiting_for_weekend_interval
   SettingsStates.waiting_for_quiet_hours_start
   SettingsStates.waiting_for_quiet_hours_end
   ```

**Note:** This refactoring is P2 priority. Should be done after categories.py refactoring.

---

### 3. Poll Module Optimization (Priority: P3)

**Estimated Effort:** 4-6 hours
**Risk Level:** Low
**Dependencies:** None

#### Current Structure Issues

```
poll/
├── poll_handlers.py       352 lines (response handling)
├── poll_activity.py       382 lines (activity creation)
├── poll_sender.py         294 lines (poll sending)
└── helpers.py             101 lines
```

**Problem:** Unclear boundary between `poll_handlers` and `poll_activity`

#### Proposed Refactoring

**Option A: Two-File Structure** ✅ (Recommended)

```
poll/
├── __init__.py            ~30 lines
├── poll_sender.py         ~300 lines (scheduling + sending)
├── poll_response.py       ~630 lines (responses + activity creation)
└── helpers.py             ~100 lines
```

**Justification:**
- Clear separation: "sending polls" vs "responding to polls"
- 630 lines is acceptable for complex response handling
- Reduces cognitive load (2 main files vs 3)

**Option B: Three-File Structure** (Current with rename)

```
poll/
├── __init__.py
├── poll_sender.py         ~300 lines
├── poll_response.py       ~350 lines (rename from poll_handlers)
├── poll_activity.py       ~380 lines (activity creation logic)
└── helpers.py             ~100 lines
```

**Decision:** Implement Option A (combine handlers + activity)

#### Migration Steps

1. Rename `poll_handlers.py` → `poll_response.py`
2. Move activity creation logic from `poll_activity.py` → `poll_response.py`
3. Test all poll flows
4. Remove `poll_activity.py`

---

### 4. Activity Module (Priority: P4 - Optional)

**Recommendation:** **DO NOT REFACTOR**

**Current State:**
```
activity/
├── activity_creation.py   555 lines ⚠️
├── activity_management.py 193 lines ✅
└── helpers.py              86 lines ✅
```

**Rationale for NOT splitting:**

1. **Single FSM Flow:** All 11 functions form one cohesive flow:
   ```
   start → start_time → end_time → description → category → save
   ```

2. **High Cohesion:** Steps are tightly coupled, splitting would harm readability

3. **555 lines is acceptable** for FSM flows with multiple steps

4. **User flow is sequential:** Developers need to see the full flow

5. **Testing is easier** with all steps in one file

**Minor Optimization (Optional, Low Priority):**

If 555 lines is still concerning, can extract helpers:

```
activity/
├── activity_creation.py       ~450 lines (FSM handlers only)
├── activity_management.py     ~193 lines
├── creation_helpers.py        ~100 lines (time validation, keyboards)
└── helpers.py                  ~86 lines
```

**Decision:** Keep as is. 555 lines is on the edge but acceptable.

---

### 5. Other Files

#### logging_middleware.py (325 lines) - Priority P4

**Current:** One large file with middleware + decorators + formatters

**Proposed:**
```
core/logging/
├── __init__.py
├── middleware.py      ~120 lines (middleware class)
├── decorators.py      ~100 lines (@log_user_action)
├── formatters.py      ~100 lines (log formatting)
```

**Priority:** Low - not blocking, nice to have

---

## Implementation Phases

### Phase 1: Quick Wins (Week 1)

**Goal:** Address highest-priority items with low risk

```
Priority 0 - Must Do
├─ Delete .old backup files                    [1 hour]
└─ Refactor categories.py → categories/        [6 hours]

Priority 1 - Should Do
└─ Optimize poll/ module                       [4 hours]

Total: ~11 hours
Risk: Low
```

**Deliverables:**
- [ ] Remove `activity.py.old`, `poll.py.old`, `settings.py.old`
- [ ] New `categories/` directory structure
- [ ] All category tests passing
- [ ] Optimized `poll/` structure

### Phase 2: Settings Refactoring (Week 2-3)

**Goal:** Break down large settings files

```
Priority 2 - Important
├─ Split quiet_hours_settings.py               [8 hours]
├─ Split interval_settings.py                  [6 hours]
└─ Optimize main_menu.py                       [4 hours]

Total: ~18 hours
Risk: Medium (complex FSM flows)
```

**Deliverables:**
- [ ] `quiet_hours_start.py` and `quiet_hours_end.py`
- [ ] `interval_weekday.py` and `interval_weekend.py`
- [ ] Reduced `main_menu.py` (~200 lines)
- [ ] All settings tests passing

### Phase 3: Polish (Week 4)

**Goal:** Optional improvements

```
Priority 3-4 - Nice to Have
├─ Split logging_middleware.py                 [4 hours]
├─ Optional: Extract activity creation helpers [3 hours]
└─ Code review and documentation               [4 hours]

Total: ~11 hours
Risk: Low
```

**Deliverables:**
- [ ] Cleaner logging structure
- [ ] Updated documentation
- [ ] Code review feedback addressed

---

## Risk Assessment

### High Risks

#### 1. FSM State Management

**Risk:** Breaking FSM flows during refactoring

**Mitigation:**
- Test each FSM flow thoroughly after refactoring
- Use git branches for each refactoring
- Keep FSM state definitions unchanged
- Ensure router includes maintain order

**Test Cases:**
```python
# For each FSM flow, test:
1. Entry point (starting the flow)
2. Each state transition
3. Data persistence across states
4. Cancel/timeout scenarios
5. Error handling
```

#### 2. Import Circular Dependencies

**Risk:** Creating circular imports when splitting files

**Mitigation:**
- Use clear import hierarchy
- Move shared code to `helpers.py`
- Import from `__init__.py` at package level
- Use TYPE_CHECKING for type hints if needed

**Example:**
```python
# Good
from .helpers import validate_time

# Avoid
from .other_handler import some_function
```

#### 3. Router Registration Order

**Risk:** Handler registration order matters in Aiogram

**Mitigation:**
- Document router include order in `__init__.py`
- Test that more specific handlers come before general ones
- Use explicit router priorities if needed

### Medium Risks

#### 4. Keyboard Import Changes

**Risk:** Keyboard builders split across files

**Mitigation:**
- Centralize keyboard builders in `helpers.py`
- Use clear naming conventions
- Document which keyboards are used where

#### 5. Testing Coverage

**Risk:** Breaking existing functionality without tests

**Mitigation:**
- Run smoke tests after each refactoring step
- Test both happy paths and error cases
- Manual testing of user flows

### Low Risks

#### 6. Documentation Drift

**Risk:** Documentation becoming outdated

**Mitigation:**
- Update ARCHITECTURE.md after major changes
- Add docstrings to new files
- Update README if needed

---

## Testing Strategy

### Unit Tests

Focus on business logic and validation:

```python
# Test validation functions
def test_validate_category_name():
    assert validate_category_name("Work") is None
    assert validate_category_name("") == "Название не может быть пустым"
    assert validate_category_name("A" * 101) == "Название слишком длинное"

# Test emoji extraction
def test_extract_emoji():
    assert extract_emoji("🎮") == "🎮"
    assert extract_emoji("Test 🎮 text") == "🎮"
    assert extract_emoji("No emoji") is None
```

### Integration Tests

Test handler flows:

```python
@pytest.mark.asyncio
async def test_category_creation_flow():
    """Test full category creation FSM flow."""
    # 1. Start creation
    # 2. Send category name
    # 3. Select emoji
    # 4. Verify category created
    # 5. Verify FSM cleared
```

### Manual Testing Checklist

For each refactored module:

**Categories:**
- [ ] View empty category list
- [ ] View category list with categories
- [ ] Add category with emoji (button selection)
- [ ] Add category with emoji (text input)
- [ ] Add category without emoji
- [ ] Try to add duplicate category name
- [ ] Delete category
- [ ] Cancel category creation
- [ ] FSM timeout works

**Settings:**
- [ ] View settings menu
- [ ] Change weekday interval
- [ ] Change weekend interval
- [ ] Set quiet hours start
- [ ] Set quiet hours end
- [ ] Toggle reminders
- [ ] Invalid input handling
- [ ] Cancel flow works

**Poll:**
- [ ] Receive automatic poll
- [ ] Select category from poll
- [ ] Confirm activity from poll
- [ ] Skip poll
- [ ] Poll respects quiet hours
- [ ] Poll respects intervals

### Smoke Tests

Quick tests to run after each change:

```bash
# 1. Bot starts without errors
docker-compose up -d
docker-compose logs tracker_activity_bot | grep ERROR

# 2. Basic commands work
/start
Main menu appears

# 3. Each refactored flow works
Categories → View list → Success
Categories → Add → Complete flow → Success
Categories → Delete → Complete flow → Success
```

---

## Metrics & Success Criteria

### Before Refactoring

```
Files >400 lines: 4
Files >300 lines: 8
Largest file: 555 lines (activity_creation.py)
Average file size: 112 lines

Technical Debt:
- .old files: 88,844 lines
- Monolithic handlers: 2,042 lines (categories + settings)
```

### After Refactoring (Target)

```
Files >400 lines: 0
Files >300 lines: 2 (activity_creation, poll_response - acceptable)
Largest file: ~600 lines (poll_response - acceptable)
Average file size: ~95 lines

Technical Debt Reduction:
- .old files: 0 lines (deleted)
- Largest handler: ~300 lines
- Improved organization: 4+ new structured modules
```

### Success Criteria

✅ **Must Have:**
1. All files <400 lines (except FSM flows with good reason)
2. Zero `.old` backup files
3. All existing tests pass
4. No new bugs introduced
5. Consistent directory structure

✅ **Should Have:**
1. Improved code discoverability
2. Better separation of concerns
3. Easier to navigate codebase
4. Clearer file naming

✅ **Nice to Have:**
1. Reduced average file size
2. More granular git history
3. Easier code reviews
4. Better documentation

### Measurement

Track metrics before and after:

```bash
# File size distribution
find services -name "*.py" -type f ! -path "*/__pycache__/*" -exec wc -l {} + | sort -rn

# Largest files
find services -name "*.py" -exec wc -l {} + | sort -rn | head -20

# Total lines of code
find services -name "*.py" -exec wc -l {} + | tail -1

# Number of files
find services -name "*.py" -type f ! -path "*/__pycache__/*" | wc -l
```

---

## References

### Internal Documentation

- [ARCHITECTURE.md](../../ARCHITECTURE.md) - Current architecture patterns
- [ADR-20251107-001](../../docs/adr/ADR-20251107-001/) - Core architecture decisions
- Previous refactoring reports:
  - [refactoring-2025-11-07-(1).md](./refactoring-2025-11-07-(1).md)
  - [refactoring-2025-11-07-(2).md](./refactoring-2025-11-07-(2).md)
  - [refactoring-2025-11-07-(3).md](./refactoring-2025-11-07-(3).md)

### Design Principles

1. **SOLID Principles**
   - Single Responsibility Principle
   - Open/Closed Principle
   - Dependency Inversion Principle

2. **DRY/KISS/YAGNI**
   - Don't Repeat Yourself
   - Keep It Simple, Stupid
   - You Aren't Gonna Need It

3. **Code Organization**
   - High Cohesion, Low Coupling
   - Clear naming conventions
   - Consistent structure

### External Resources

- [Aiogram 3.x Documentation](https://docs.aiogram.dev/en/latest/)
- [FSM Best Practices](https://docs.aiogram.dev/en/latest/dispatcher/finite_state_machine/index.html)
- [Python Project Structure](https://docs.python-guide.org/writing/structure/)
- [Clean Code Principles](https://github.com/ryanmcdermott/clean-code-python)

---

## Appendix A: File Size Reference

### Complete File Listing with Line Counts

```
# Critical (>400 lines)
activity_creation.py           555
categories.py                  538
quiet_hours_settings.py        522
interval_settings.py           446

# High (300-400 lines)
main_menu.py (settings)        395
poll_activity.py               382
poll_handlers.py               352
logging_middleware.py          325

# Medium (200-300 lines)
reminder_settings.py           299
poll_sender.py                 294
http_client.py                 286
fsm_timeout_service.py         275

# Good (100-200 lines)
main.py (data_api)             201
dependencies.py (bot)          200
activity_management.py         193
keyboards/settings.py          184
scheduler_service.py           157
dependencies.py (data_api)     147
main.py (bot)                  138
user_settings_service.py       135
time_parser.py                 128
protocols.py                   127
base.py (repository)           124
formatters.py                  118
error_handler.py               116
category_service.py            109
scheduler.py (protocol)        107
fsm_helpers.py                 105
migration_001.py               104
poll/helpers.py                101
user_service.py                100
env.py (alembic)               100

# Excellent (<100 lines)
activity_service.py             98
start.py                        94
decorators.py                   94
logging.py (middleware)         90
logging.py (core, bot)          86
activity/helpers.py             86
logging.py (core, api)          86
error_middleware.py             85
activity_repository.py          81
activities.py (api)             78
timing_middleware.py            76
timezone_helper.py              74
settings/helpers.py             74
time_select.py                  73
logging_middleware.py (http)    67
time_helpers.py                 66
poll.py (keyboard)              61
users.py (api)                  59
activity.py (model)             56
categories.py (api)             56
service_injection.py            56
user.py (model)                 56
user_settings.py (api)          55
user.py (model)                 55
correlation.py                  54
user_settings.py (model)        51
user_service.py (http)          50
category_service.py (http)      49
poll/__init__.py                48
activity.py (schema)            48
connection.py                   48
category_repository.py          47
category.py (model)             47
user_settings_repository.py     46
middleware/__init__.py          42
user_settings.py (schema)       42
activity_service.py (http)      39
decorators.py (utils)           38
user_settings_service.py (http) 36
settings/__init__.py            35
main_menu.py (keyboard)         34
user.py (schema)                33
migration_002.py                31
activity/__init__.py            29
config.py (bot)                 27
category.py (schema)            26
constants.py                    26
config.py (api)                 25
protocols/__init__.py           22
user_repository.py              21
services/__init__.py            18
settings.py (states)            17
fsm_reminder.py                 16
activity.py (states)            11
poll.py (states)                10
category.py (states)             9
middleware/__init__.py (api)     8
base.py (model)                  7
```

---

## Appendix B: Refactoring Checklist Template

### Pre-Refactoring

- [ ] Create git branch for refactoring
- [ ] Document current file structure
- [ ] Run existing tests to establish baseline
- [ ] Identify all imports of target file
- [ ] Review FSM states and handlers

### During Refactoring

- [ ] Create new directory structure
- [ ] Create `__init__.py` with router exports
- [ ] Split code into logical files
- [ ] Update imports in new files
- [ ] Update router registration
- [ ] Test each new file independently
- [ ] Run full test suite

### Post-Refactoring

- [ ] Delete old file(s)
- [ ] Update documentation
- [ ] Update ARCHITECTURE.md if needed
- [ ] Run smoke tests
- [ ] Manual testing of user flows
- [ ] Code review
- [ ] Merge to main branch
- [ ] Monitor for issues in production

---

## Appendix C: Command Reference

### Useful Commands for Refactoring

```bash
# Find large files
find services -name "*.py" -type f ! -path "*/__pycache__/*" \
  -exec wc -l {} + | sort -rn | head -20

# Count functions in a file
grep -c "^async def\|^def" file.py

# Find all imports of a specific module
grep -r "from.*categories import" services/

# Check for circular imports
python -c "import services.tracker_activity_bot.src.api.handlers.categories"

# Run specific test
pytest services/tracker_activity_bot/tests/unit/test_categories.py -v

# Check git diff for a file
git diff services/tracker_activity_bot/src/api/handlers/categories.py

# Create directory structure
mkdir -p services/tracker_activity_bot/src/api/handlers/categories

# Remove old file
git rm services/tracker_activity_bot/src/api/handlers/categories.py

# Count lines in directory
find services/tracker_activity_bot/src/api/handlers/categories -name "*.py" \
  -exec wc -l {} + | tail -1
```

---

**Document Version:** 1.0
**Last Updated:** 2025-11-07
**Status:** Draft - Ready for Review
**Next Review Date:** After Phase 1 completion
