"""Activity creation and recording handlers.

This module handles all activity recording functionality including:
- Manual activity recording (user-initiated)
- Time period selection
- Category selection
- Activity description input
- Activity saving

State machine flow:
    waiting_for_period -> waiting_for_category -> waiting_for_description
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Callable, Awaitable

from aiogram import Router, F, types, Bot
from aiogram.fsm.context import FSMContext

from src.api.dependencies import ServiceContainer
from src.api.keyboards.main_menu import get_main_menu_keyboard
from src.api.keyboards.time_select import (
    get_period_keyboard,
    get_start_time_keyboard,
    get_end_time_keyboard,
    get_period_keyboard_with_auto
)
from src.api.keyboards.poll import get_poll_category_keyboard
from src.api.messages.activity_messages import get_category_selection_message
from src.api.states.activity import ActivityStates
from src.application.utils.formatters import format_time, format_duration, extract_tags
from src.application.services import fsm_timeout_service as fsm_timeout_module
from src.application.utils.decorators import with_typing_action

logger = logging.getLogger(__name__)

router = Router()


@router.message(F.text == "📝 Записать активность")
@with_typing_action
async def start_add_activity(message: types.Message, state: FSMContext):
    """Start activity recording - MANUAL trigger.

    This is the entry point for MANUAL activity recording (user clicked button).
    It presents the user with period selection options.

    Flow:
        Start -> Period Selection -> Category -> Description -> Save
    """
    telegram_id = message.from_user.id

    # Set FSM state
    await state.set_state(ActivityStates.waiting_for_period)

    # Mark this as manual flow (not automatic poll)
    await state.update_data(trigger_source="manual")

    # Schedule FSM timeout
    if fsm_timeout_module.fsm_timeout_service:
        fsm_timeout_module.fsm_timeout_service.schedule_timeout(
            user_id=telegram_id,
            state=ActivityStates.waiting_for_period,
            bot=message.bot
        )

    # Send period selection keyboard with auto-calculate option
    text = (
        "📝 Записываем активность\n\n"
        "Автоматически рассчитать период от последней активности или выбрать вручную?\n\n"
        "⏰ Выбери период:"
    )

    await message.answer(text, reply_markup=get_period_keyboard_with_auto())


@router.callback_query(ActivityStates.waiting_for_period, F.data == "noop")
async def handle_noop(callback: types.CallbackQuery):
    """Handle no-op callback (visual dividers in keyboards).

    Some keyboards have visual divider buttons that don't perform actions.
    This handler simply acknowledges them without doing anything.
    """
    await callback.answer()


@router.callback_query(ActivityStates.waiting_for_period, F.data == "period_auto")
@with_typing_action
async def auto_calculate_period(
    callback: types.CallbackQuery,
    state: FSMContext,
    services: ServiceContainer
):
    """Auto-calculate period from last activity (manual flow).

    Uses the same logic as automatic polls to calculate the time range
    based on the user's last recorded activity end time.

    Flow:
        User clicks "Auto" -> Calculate period -> Category selection
    """
    telegram_id = callback.from_user.id

    try:
        # Get user data
        user = await services.user.get_by_telegram_id(telegram_id)
        if not user:
            await callback.message.answer(
                "⚠️ Пользователь не найден.",
                reply_markup=get_main_menu_keyboard()
            )
            await state.clear()
            await callback.answer()
            return

        # Get settings for poll interval calculation
        settings = await services.settings.get_settings(user["id"])
        if not settings:
            logger.warning(
                "Settings not found for user, using defaults",
                extra={"user_id": user["id"]}
            )
            settings = {}

        # Auto-calculate period using same logic as polls
        from src.application.utils.time_helpers import calculate_poll_period

        start_time, end_time = await calculate_poll_period(
            services.activity,
            user["id"],
            settings
        )

        logger.info(
            "Auto-calculated period for manual flow",
            extra={
                "user_id": user["id"],
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_minutes": int((end_time - start_time).total_seconds() / 60)
            }
        )

        # Store period and user_id in state
        await state.update_data(
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            user_id=user["id"]
        )

        # Move to category selection
        await state.set_state(ActivityStates.waiting_for_category)

        # Schedule FSM timeout
        if fsm_timeout_module.fsm_timeout_service:
            fsm_timeout_module.fsm_timeout_service.schedule_timeout(
                user_id=telegram_id,
                state=ActivityStates.waiting_for_category,
                bot=callback.bot
            )

        # Get user categories
        categories = await services.category.get_user_categories(user["id"])

        if not categories:
            await callback.message.answer(
                "⚠️ У тебя нет категорий. Сначала создай категорию.",
                reply_markup=get_main_menu_keyboard()
            )
            await state.clear()
            await callback.answer()
            return

        # Format time for display
        start_str = format_time(start_time)
        end_str = format_time(end_time)
        duration_minutes = int((end_time - start_time).total_seconds() / 60)
        duration_str = format_duration(duration_minutes)

        # Build category selection message
        text = get_category_selection_message(
            source="manual",  # This is manual flow
            start_time=start_str,
            end_time=end_str,
            duration=duration_str,
            add_motivation=False
        )

        # Send category selection message
        await callback.message.answer(
            text,
            reply_markup=get_poll_category_keyboard(categories)
        )
        await callback.answer()

    except Exception as e:
        logger.error(
            "Error auto-calculating period",
            extra={
                "telegram_user_id": telegram_id,
                "error": str(e)
            },
            exc_info=True
        )
        await callback.message.answer(
            "⚠️ Ошибка при расчёте периода.",
            reply_markup=get_main_menu_keyboard()
        )
        await state.clear()
        await callback.answer()


@router.callback_query(ActivityStates.waiting_for_period, F.data.startswith("period_"))
@with_typing_action
async def quick_period_selection(callback: types.CallbackQuery, state: FSMContext, services: ServiceContainer):
    """Handle quick period selection (15m, 30m, 1h, etc).

    User selected a predefined period - calculate start and end times,
    then move to category selection.
    """
    period = callback.data.replace("period_", "")
    telegram_id = callback.from_user.id

    # Defensive: Ensure trigger_source is set (should be "manual")
    data = await state.get_data()
    if "trigger_source" not in data:
        await state.update_data(trigger_source="manual")

    # Parse period and calculate times
    now = datetime.now(timezone.utc)

    period_map = {
        "15m": timedelta(minutes=15),
        "30m": timedelta(minutes=30),
        "1h": timedelta(hours=1),
        "3h": timedelta(hours=3),
        "8h": timedelta(hours=8),
        "12h": timedelta(hours=12),
    }

    delta = period_map.get(period)
    if not delta:
        await callback.answer("⚠️ Неверный период")
        return

    end_time = now
    start_time = now - delta

    # Get user
    user = await services.user.get_by_telegram_id(telegram_id)
    if not user:
        await callback.message.answer(
            "⚠️ Пользователь не найден.",
            reply_markup=get_main_menu_keyboard()
        )
        await state.clear()
        await callback.answer()
        return

    # Store times and user_id
    await state.update_data(
        start_time=start_time.isoformat(),
        end_time=end_time.isoformat(),
        user_id=user["id"]
    )

    # Move to category selection
    await state.set_state(ActivityStates.waiting_for_category)

    # Schedule FSM timeout
    if fsm_timeout_module.fsm_timeout_service:
        fsm_timeout_module.fsm_timeout_service.schedule_timeout(
            user_id=telegram_id,
            state=ActivityStates.waiting_for_category,
            bot=callback.bot
        )

    # Get categories
    categories = await services.category.get_user_categories(user["id"])

    if not categories:
        await callback.message.answer(
            "⚠️ У тебя нет категорий. Сначала создай категорию.",
            reply_markup=get_main_menu_keyboard()
        )
        await state.clear()
        await callback.answer()
        return

    # Format time and duration
    start_time_str = format_time(start_time)
    end_time_str = format_time(end_time)
    duration_minutes = int(delta.total_seconds() / 60)
    duration_str = format_duration(duration_minutes)

    # Build category selection message
    text = get_category_selection_message(
        source="manual",
        start_time=start_time_str,
        end_time=end_time_str,
        duration=duration_str,
        add_motivation=False
    )

    await callback.message.answer(
        text,
        reply_markup=get_poll_category_keyboard(categories)
    )
    await callback.answer()


@router.message(ActivityStates.waiting_for_period)
@with_typing_action
async def process_period_input(message: types.Message, state: FSMContext, services: ServiceContainer):
    """Handle custom period input (text message).

    User typed a custom period instead of using quick buttons.
    Parse the input and move to category selection.
    """
    # This is a placeholder - in the future we can add text parsing for custom periods
    # For now, just show a helpful message
    telegram_id = message.from_user.id

    # Defensive: Ensure trigger_source is set (should be "manual")
    data = await state.get_data()
    if "trigger_source" not in data:
        await state.update_data(trigger_source="manual")

    await message.answer(
        "⚠️ Используй кнопки для выбора периода.",
        reply_markup=get_period_keyboard_with_auto()
    )


@router.callback_query(ActivityStates.waiting_for_category, F.data.startswith("poll_category_"))
@router.callback_query(ActivityStates.waiting_for_category, F.data.startswith("activity_category_"))
@with_typing_action
async def process_category_callback(
    callback: types.CallbackQuery,
    state: FSMContext,
    services: ServiceContainer
):
    """Handle category selection - SHARED by manual and automatic flows.

    This handler works for both manual activity recording and automatic
    poll responses. Flow differentiation is done via trigger_source in state.

    Callback data formats:
        - poll_category_{id} - from automatic polls
        - activity_category_{id} - from manual recording

    Flow:
        Category selected -> Fetch recent activities -> Description prompt
    """
    telegram_id = callback.from_user.id
    callback_data = callback.data

    # Parse category ID from both callback formats
    if callback_data.startswith("poll_category_"):
        category_id = int(callback_data.replace("poll_category_", ""))
    elif callback_data.startswith("activity_category_"):
        category_id = int(callback_data.replace("activity_category_", ""))
    else:
        await callback.answer("⚠️ Неверный формат данных")
        return

    try:
        # Get data from state
        data = await state.get_data()
        user_id = data.get("user_id")
        start_time_str = data.get("start_time")
        end_time_str = data.get("end_time")
        trigger_source = data.get("trigger_source", "manual")

        # Validate required data
        if not all([user_id, start_time_str, end_time_str]):
            logger.warning(
                "Missing required data for category selection",
                extra={
                    "has_user_id": user_id is not None,
                    "has_start_time": start_time_str is not None,
                    "has_end_time": end_time_str is not None
                }
            )
            await callback.message.answer(
                "⚠️ Недостаточно данных. Начни заново.",
                reply_markup=get_main_menu_keyboard()
            )
            await state.clear()
            await callback.answer()
            return

        # Parse times
        start_time = datetime.fromisoformat(start_time_str)
        end_time = datetime.fromisoformat(end_time_str)

        # Store category_id in state
        await state.update_data(category_id=category_id)

        # Move to description input
        await state.set_state(ActivityStates.waiting_for_description)

        # Schedule FSM timeout
        if fsm_timeout_module.fsm_timeout_service:
            fsm_timeout_module.fsm_timeout_service.schedule_timeout(
                user_id=telegram_id,
                state=ActivityStates.waiting_for_description,
                bot=callback.bot
            )

        # Use shared function to build description prompt
        from src.api.handlers.activity.shared import fetch_and_build_description_prompt

        text, keyboard = await fetch_and_build_description_prompt(
            services=services,
            user_id=user_id,
            category_id=category_id,
            start_time=start_time,
            end_time=end_time,
            limit=20
        )

        logger.info(
            "Category selected, prompting for description",
            extra={
                "user_id": user_id,
                "category_id": category_id,
                "trigger_source": trigger_source,
                "has_suggestions": keyboard is not None
            }
        )

        # Send description prompt
        await callback.message.answer(text, reply_markup=keyboard)
        await callback.answer()

    except Exception as e:
        logger.error(
            "Error processing category selection",
            extra={
                "telegram_user_id": telegram_id,
                "error": str(e)
            },
            exc_info=True
        )
        await callback.message.answer(
            "⚠️ Ошибка при обработке категории.",
            reply_markup=get_main_menu_keyboard()
        )
        await state.clear()
        await callback.answer()


@router.callback_query(ActivityStates.waiting_for_description, F.data.startswith("activity_desc_"))
@with_typing_action
async def select_recent_activity(
    callback: types.CallbackQuery,
    state: FSMContext,
    services: ServiceContainer
):
    """Handle selection of recent activity - SHARED by manual and automatic flows.

    User clicked on one of the recent activity buttons - use that description
    to save the activity. This handler works for both flows.

    Flow:
        Recent activity clicked -> Extract description -> Save activity
    """
    telegram_id = callback.from_user.id

    # Extract activity_id from callback data
    activity_id_str = callback.data.replace("activity_desc_", "")

    try:
        activity_id = int(activity_id_str)
    except ValueError:
        await callback.message.answer("⚠️ Ошибка при обработке выбора.")
        await callback.answer()
        return

    try:
        # Get data from state
        data = await state.get_data()
        user_id = data.get("user_id")
        category_id = data.get("category_id")
        trigger_source = data.get("trigger_source", "manual")

        # Fetch the selected activity to get its description
        if category_id:
            response = await services.activity.get_user_activities_by_category(
                user_id=user_id,
                category_id=category_id,
                limit=20
            )
        else:
            response = await services.activity.get_user_activities(
                user_id=user_id,
                limit=20
            )

        recent_activities = (
            response.get("activities", [])
            if isinstance(response, dict)
            else response
        )

        # Find the activity with matching ID
        selected_activity = next(
            (act for act in recent_activities if act.get("id") == activity_id),
            None
        )

        if not selected_activity:
            await callback.message.answer("⚠️ Активность не найдена.")
            await callback.answer()
            return

        description = selected_activity.get("description", "")
        tags = extract_tags(description)

        logger.info(
            "Recent activity selected",
            extra={
                "user_id": user_id,
                "activity_id": activity_id,
                "trigger_source": trigger_source,
                "description_length": len(description)
            }
        )

        # Create post-save callback if this is automatic flow
        post_save_callback = None
        if trigger_source == "automatic":
            post_save_callback = _create_poll_scheduling_callback(
                telegram_id, callback.bot, services
            )

        # Use shared function to save activity
        from src.api.handlers.activity.shared import create_and_save_activity

        await create_and_save_activity(
            message=callback.message,
            state=state,
            services=services,
            telegram_user_id=telegram_id,
            description=description,
            tags=tags,
            post_save_callback=post_save_callback
        )

        await callback.answer()

    except Exception as e:
        logger.error(
            "Error selecting recent activity",
            extra={
                "telegram_user_id": telegram_id,
                "error": str(e)
            },
            exc_info=True
        )
        await callback.message.answer(
            "⚠️ Ошибка при сохранении активности.",
            reply_markup=get_main_menu_keyboard()
        )
        await state.clear()
        await callback.answer()


@router.message(ActivityStates.waiting_for_description)
@with_typing_action
async def process_description(
    message: types.Message,
    state: FSMContext,
    services: ServiceContainer
):
    """Process activity description - SHARED by manual and automatic flows.

    User entered activity description as text. Validate it and save the activity.
    This handler works for both manual and automatic flows.

    Flow:
        Description entered -> Validate -> Extract tags -> Save activity
    """
    telegram_id = message.from_user.id
    description = message.text.strip()

    # Validate description using shared function
    from src.api.handlers.activity.shared import validate_description

    is_valid, error_msg = validate_description(description, min_length=3)
    if not is_valid:
        await message.answer(error_msg)
        return

    # Extract tags from description
    tags = extract_tags(description)

    # Get trigger source to determine if we need post-save callback
    data = await state.get_data()
    trigger_source = data.get("trigger_source", "manual")

    logger.info(
        "Description entered",
        extra={
            "telegram_user_id": telegram_id,
            "trigger_source": trigger_source,
            "description_length": len(description),
            "tags_count": len(tags)
        }
    )

    # Create post-save callback if this is automatic flow
    post_save_callback = None
    if trigger_source == "automatic":
        post_save_callback = _create_poll_scheduling_callback(
            telegram_id, message.bot, services
        )

    # Use shared function to save activity
    from src.api.handlers.activity.shared import create_and_save_activity

    await create_and_save_activity(
        message=message,
        state=state,
        services=services,
        telegram_user_id=telegram_id,
        description=description,
        tags=tags,
        post_save_callback=post_save_callback
    )


@router.callback_query(F.data == "cancel")
async def handle_cancel(callback: types.CallbackQuery, state: FSMContext):
    """Handle cancel button in any state."""
    telegram_id = callback.from_user.id

    await state.clear()

    # Cancel FSM timeout
    if fsm_timeout_module.fsm_timeout_service:
        fsm_timeout_module.fsm_timeout_service.cancel_timeout(telegram_id)

    await callback.message.answer(
        "❌ Отменено.",
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer()


# Old save_activity function - kept for reference, will be removed after testing
async def save_activity(
    message: types.Message,
    state: FSMContext,
    user_id: int,
    category_id: int | None,
    telegram_user_id: int,
    services: ServiceContainer,
    description: str | None = None,
    tags: list[str] | None = None
):
    """Save activity to database.

    Args:
        message: Telegram message object
        state: FSM context
        user_id: Internal user ID
        category_id: Category ID or None
        telegram_user_id: Telegram user ID
        services: Service container
        description: Activity description (if not provided, will get from state)
        tags: Activity tags (if not provided, will get from state)
    """
    data = await state.get_data()
    start_time_str = data.get("start_time")
    end_time_str = data.get("end_time")

    # Use provided description/tags or get from state
    if description is None:
        description = data.get("description")
    if tags is None:
        tags = data.get("tags", [])

    if not all([start_time_str, end_time_str, description]):
        await message.answer(
            "⚠️ Недостаточно данных для сохранения.",
            reply_markup=get_main_menu_keyboard()
        )
        await state.clear()
        return

    try:
        start_time = datetime.fromisoformat(start_time_str)
        end_time = datetime.fromisoformat(end_time_str)

        # Create activity
        await services.activity.create_activity(
            user_id=user_id,
            category_id=category_id,
            description=description,
            tags=tags,
            start_time=start_time,
            end_time=end_time
        )

        duration_minutes = int((end_time - start_time).total_seconds() / 60)
        duration_str = format_duration(duration_minutes)

        await message.answer(
            f"✅ Активность сохранена!\n\n"
            f"{description}\n"
            f"Продолжительность: {duration_str}",
            reply_markup=get_main_menu_keyboard()
        )
        await state.clear()
        # Cancel FSM timeout
        if fsm_timeout_module.fsm_timeout_service:
            fsm_timeout_module.fsm_timeout_service.cancel_timeout(telegram_user_id)

    except Exception as e:
        logger.error(f"Error saving activity: {e}")
        await message.answer(
            "⚠️ Ошибка при сохранении активности.",
            reply_markup=get_main_menu_keyboard()
        )
        await state.clear()
        # Cancel FSM timeout
        if fsm_timeout_module.fsm_timeout_service:
            fsm_timeout_module.fsm_timeout_service.cancel_timeout(telegram_user_id)


# Helper functions

def _create_poll_scheduling_callback(
    telegram_id: int,
    bot: Bot,
    services: ServiceContainer
) -> Callable[[dict], Awaitable[None]]:
    """Create post-save callback for scheduling next poll.

    Returns an async callback function that schedules the next automatic poll
    after activity is saved. Used only for automatic poll flow.

    Args:
        telegram_id: Telegram user ID
        bot: Bot instance for scheduling
        services: Service container with scheduler access

    Returns:
        Async callback function that takes state_data dict

    Example:
        >>> callback = _create_poll_scheduling_callback(123, bot, services)
        >>> await create_and_save_activity(..., post_save_callback=callback)
    """
    async def schedule_next_poll(state_data: dict) -> None:
        """Schedule next poll after activity save.

        Args:
            state_data: FSM state data containing settings and user_timezone
        """
        try:
            from src.api.handlers.poll.poll_sender import send_automatic_poll

            settings = state_data.get("settings", {})
            user_timezone = state_data.get("user_timezone", "Europe/Moscow")

            await services.scheduler.schedule_poll(
                user_id=telegram_id,
                settings=settings,
                user_timezone=user_timezone,
                send_poll_callback=send_automatic_poll,
                bot=bot
            )

            logger.debug(
                "Scheduled next poll after activity save",
                extra={"telegram_user_id": telegram_id}
            )

        except Exception as e:
            logger.error(
                "Error scheduling next poll in post-save callback",
                extra={
                    "telegram_user_id": telegram_id,
                    "error": str(e)
                },
                exc_info=True
            )

    return schedule_next_poll
