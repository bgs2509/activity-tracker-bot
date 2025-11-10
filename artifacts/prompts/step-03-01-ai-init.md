# AI Integration Implementation Plan
# Activity Tracker Bot - LangChain + OpenRouter Integration

**Status**: 🔵 Planning
**Started**: 2025-11-08
**Estimated Time**: 12-18 hours (1.5-2 working days)
**Complexity**: High

---

## Architecture Overview

**Core Concept**: AI as Intelligent Intent Router
- User sends arbitrary text → AI classifies intent → Execute corresponding action
- Actions: FSM flows, inline menus, direct responses
- Full access to user activity history for contextual responses

**Tech Stack**:
- LangChain for AI orchestration
- OpenRouter API (free tier) for LLM access
- Existing aiogram FSM infrastructure
- Redis-backed state storage

**Integration Point**:
- New router registered LAST in handler chain
- Uses `StateFilter(None)` to avoid FSM conflicts
- Follows existing DI/middleware patterns

---

## Phase 1: Infrastructure Setup (2-3 hours)

### Task 1.1: Dependencies and Environment

**Priority**: P0 (Critical)
**Time**: 30 min

#### Subtasks:

- [ ] **1.1.1** Update `pyproject.toml` dependencies
  ```toml
  [tool.poetry.dependencies]
  langchain = "^0.1.0"
  langchain-openai = "^0.0.5"
  openai = "^1.12.0"
  langchain-community = "^0.0.20"  # For additional integrations
  tiktoken = "^0.5.2"  # Token counting
  ```
  - **Location**: `/services/tracker_activity_bot/pyproject.toml`
  - **After line**: Current dependencies section
  - **Validation**: Run `poetry lock` to check compatibility

- [ ] **1.1.2** Add environment variables to `.env`
  ```bash
  # AI Configuration
  OPENROUTER_API_KEY=sk-or-v1-xxxxx
  OPENROUTER_MODEL=openai/gpt-3.5-turbo  # Free tier model
  OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
  AI_REQUEST_TIMEOUT=10  # seconds
  AI_MAX_CONTEXT_ACTIVITIES=20  # Max activities to send in context
  AI_RATE_LIMIT_PER_MINUTE=10  # Max AI requests per user per minute
  ```
  - **Location**: `.env` (create from `.env.example`)
  - **Security**: Add `.env` to `.gitignore` if not already

- [ ] **1.1.3** Document environment variables
  - **Location**: `.env.example`
  - **Add section**: "# AI Service Configuration"
  - **Include**: Comments explaining each variable

- [ ] **1.1.4** Install dependencies
  ```bash
  poetry install
  ```
  - **Validation**: Check no conflicts in lock file
  - **Restart**: Rebuild Docker containers if using Docker Compose

**Acceptance Criteria**:
- ✅ Dependencies installed without conflicts
- ✅ `.env` configured with valid OpenRouter key
- ✅ `.env.example` documented
- ✅ Application starts without errors

---

### Task 1.2: Intent Classification System

**Priority**: P0 (Critical)
**Time**: 45 min

#### Subtasks:

- [ ] **1.2.1** Create intent enum and definitions
  - **File**: `src/api/handlers/ai/intents.py` (NEW)
  - **Content**:
    ```python
    """
    Intent classification system for AI-powered message handling.

    This module defines user intent types and their corresponding actions.
    """
    from enum import Enum
    from dataclasses import dataclass
    from typing import Optional, Dict, Any


    class UserIntent(str, Enum):
        """User intent categories for AI classification."""

        CREATE_ACTIVITY = "create_activity"
        """User wants to log an activity (e.g., 'worked 2 hours on project')"""

        VIEW_STATS = "view_stats"
        """User wants to see statistics (e.g., 'show my stats', 'what did I do today')"""

        MANAGE_CATEGORIES = "manage_categories"
        """User wants to create/edit categories (e.g., 'create category', 'my categories')"""

        SETTINGS = "settings"
        """User wants to change settings (e.g., 'change interval', 'settings')"""

        GENERAL_CHAT = "general_chat"
        """General conversation (e.g., 'hello', 'how are you')"""

        HELP = "help"
        """User needs help (e.g., 'help', 'how to use this bot')"""

        UNKNOWN = "unknown"
        """Unable to classify intent"""


    @dataclass
    class IntentClassification:
        """Result of intent classification."""

        intent: UserIntent
        confidence: float  # 0.0 to 1.0
        parameters: Dict[str, Any]  # Extracted parameters (time, description, etc.)
        reasoning: Optional[str] = None  # AI's reasoning (for debugging)

        def is_confident(self, threshold: float = 0.7) -> bool:
            """Check if classification confidence is above threshold."""
            return self.confidence >= threshold


    @dataclass
    class ActivityParameters:
        """Extracted parameters for CREATE_ACTIVITY intent."""

        start_time: Optional[str] = None  # ISO format or relative ('14:30', '30m ago')
        end_time: Optional[str] = None
        duration: Optional[str] = None  # '2h', '30m', '1h 30m'
        description: Optional[str] = None
        category: Optional[str] = None

        def has_time_info(self) -> bool:
            """Check if any time information was extracted."""
            return any([self.start_time, self.end_time, self.duration])


    # Intent to Russian description mapping (for user interface)
    INTENT_DESCRIPTIONS_RU = {
        UserIntent.CREATE_ACTIVITY: "Записать активность",
        UserIntent.VIEW_STATS: "Посмотреть статистику",
        UserIntent.MANAGE_CATEGORIES: "Управление категориями",
        UserIntent.SETTINGS: "Настройки",
        UserIntent.GENERAL_CHAT: "Общение",
        UserIntent.HELP: "Справка",
        UserIntent.UNKNOWN: "Неизвестное намерение",
    }
    ```

- [ ] **1.2.2** Create intent configuration
  - **File**: `src/api/handlers/ai/config.py` (NEW)
  - **Purpose**: Centralize AI configuration constants
  - **Content**: System prompts, model settings, timeouts

**Acceptance Criteria**:
- ✅ Intent enum with all 7 types defined
- ✅ IntentClassification dataclass with validation
- ✅ ActivityParameters for structured extraction
- ✅ Russian UI mappings
- ✅ Type hints and docstrings (English)

---

### Task 1.3: AI Service Implementation

**Priority**: P0 (Critical)
**Time**: 1-1.5 hours

#### Subtasks:

- [ ] **1.3.1** Create AIService base class
  - **File**: `src/application/services/ai_service.py` (NEW)
  - **Methods to implement**:
    1. `__init__(api_key, model, base_url)` - Initialize LangChain client
    2. `classify_intent(message: str, user_context: dict) -> IntentClassification`
    3. `extract_activity_params(message: str) -> ActivityParameters`
    4. `generate_response(message: str, context: dict) -> str`
    5. `_build_system_prompt(intent_type: str) -> str`
    6. `_count_tokens(text: str) -> int` - For context limiting

  - **Error handling**:
    - Timeout after 10 seconds
    - Retry logic (1 retry with exponential backoff)
    - Fallback to UNKNOWN intent on failure
    - Log all API errors

- [ ] **1.3.2** Implement intent classification
  ```python
  async def classify_intent(
      self,
      message: str,
      user_context: Optional[Dict[str, Any]] = None
  ) -> IntentClassification:
      """
      Classify user intent using LLM.

      Args:
          message: User's message text
          user_context: Optional user statistics and activity history

      Returns:
          IntentClassification with intent type and parameters

      Raises:
          AIServiceError: If API call fails after retries
      """
      # Implementation:
      # 1. Build classification prompt with context
      # 2. Call OpenRouter via LangChain
      # 3. Parse JSON response
      # 4. Validate and return IntentClassification
  ```

- [ ] **1.3.3** Implement parameter extraction
  ```python
  async def extract_activity_params(
      self,
      message: str
  ) -> ActivityParameters:
      """
      Extract activity parameters from natural language.

      Examples:
          'worked 2 hours on project' -> duration='2h', description='project'
          'meeting from 14:00 to 15:30' -> start='14:00', end='15:30'

      Returns:
          ActivityParameters with extracted fields
      """
  ```

- [ ] **1.3.4** Implement response generation
  ```python
  async def generate_response(
      self,
      message: str,
      user_context: Dict[str, Any],
      intent: UserIntent
  ) -> str:
      """
      Generate contextual response for GENERAL_CHAT and VIEW_STATS intents.

      Response should be in Russian, friendly, and include action suggestions.
      """
  ```

- [ ] **1.3.5** Add unit tests
  - **File**: `tests/unit/services/test_ai_service.py` (NEW)
  - **Test cases**:
    - Mock OpenRouter responses
    - Test each intent classification
    - Test parameter extraction accuracy
    - Test error handling and fallbacks
    - Test timeout behavior

**Acceptance Criteria**:
- ✅ AIService class with all methods implemented
- ✅ LangChain integration working with OpenRouter
- ✅ Proper error handling and logging
- ✅ Unit tests with >80% coverage
- ✅ All docstrings in English

---

### Task 1.4: Context Provider

**Priority**: P0 (Critical)
**Time**: 45 min

#### Subtasks:

- [ ] **1.4.1** Create ContextProvider service
  - **File**: `src/api/handlers/ai/context_provider.py` (NEW)
  - **Purpose**: Gather user data for AI context
  - **Methods**:
    ```python
    async def get_user_context(
        user_id: int,
        services: ServiceContainer,
        max_activities: int = 20
    ) -> Dict[str, Any]:
        """
        Gather comprehensive user context for AI.

        Returns:
            {
                'recent_activities': [...],  # Last N activities
                'today_stats': {...},  # Today's summary
                'week_stats': {...},  # Week summary
                'categories': [...],  # User's categories
                'settings': {...},  # Current settings
                'timezone': 'UTC+3'
            }
        """
    ```

- [ ] **1.4.2** Implement activity history fetching
  - Query last N activities from database
  - Format for AI consumption (simplified JSON)
  - Include: id, description, start_time, end_time, category, duration

- [ ] **1.4.3** Implement statistics calculation
  - Today's total time by category
  - Week's total time by category
  - Most used categories
  - Average activities per day

- [ ] **1.4.4** Implement context formatting
  - Convert to human-readable format for prompt
  - Limit token count (~2000 tokens max)
  - Prioritize recent activities over old ones

- [ ] **1.4.5** Add caching (optional optimization)
  - Cache user context for 5 minutes
  - Invalidate on activity creation
  - Use Redis for cache storage

**Acceptance Criteria**:
- ✅ ContextProvider fetches all required data
- ✅ Token count stays under limit
- ✅ Data formatted for AI consumption
- ✅ Performance: <500ms to gather context

---

### Task 1.5: ServiceContainer Integration

**Priority**: P0 (Critical)
**Time**: 15 min

#### Subtasks:

- [ ] **1.5.1** Add AIService to ServiceContainer
  - **File**: `src/application/services/service_container.py`
  - **Changes**:
    ```python
    from application.services.ai_service import AIService

    class ServiceContainer:
        def __init__(self, ...):
            # ... existing services ...
            self.ai = AIService(
                api_key=settings.openrouter_api_key,
                model=settings.openrouter_model,
                base_url=settings.openrouter_base_url
            )
    ```

- [ ] **1.5.2** Add settings to config
  - **File**: `src/infrastructure/config/settings.py`
  - **Add**:
    ```python
    openrouter_api_key: str = Field(..., env="OPENROUTER_API_KEY")
    openrouter_model: str = Field(default="openai/gpt-3.5-turbo", env="OPENROUTER_MODEL")
    openrouter_base_url: str = Field(default="https://openrouter.ai/api/v1", env="OPENROUTER_BASE_URL")
    ai_request_timeout: int = Field(default=10, env="AI_REQUEST_TIMEOUT")
    ```

- [ ] **1.5.3** Validate dependency injection
  - Test that `services.ai` is accessible in handlers
  - Verify middleware injects ServiceContainer correctly

**Acceptance Criteria**:
- ✅ AIService accessible via `services.ai`
- ✅ Settings loaded from environment
- ✅ No breaking changes to existing code

---

## Phase 2: AI Router and Handler (3-4 hours)

### Task 2.1: AI Router Structure

**Priority**: P0 (Critical)
**Time**: 30 min

#### Subtasks:

- [ ] **2.1.1** Create AI handler module
  - **Directory**: `src/api/handlers/ai/` (NEW)
  - **Files**:
    - `__init__.py` - Router export
    - `chat_handler.py` - Main message handler
    - `actions.py` - Action executors
    - `intents.py` - Already created in 1.2.1
    - `context_provider.py` - Already created in 1.4.1
    - `config.py` - Configuration constants

- [ ] **2.1.2** Create router instance
  - **File**: `src/api/handlers/ai/__init__.py`
  - **Content**:
    ```python
    """
    AI-powered message handling with intent classification.

    This router handles arbitrary text messages using AI to determine
    user intent and execute corresponding actions.
    """
    from aiogram import Router
    from .chat_handler import router as chat_router

    # Main AI router
    router = Router(name="ai")
    router.include_router(chat_router)

    __all__ = ["router"]
    ```

**Acceptance Criteria**:
- ✅ Directory structure created
- ✅ Router properly exported
- ✅ Follows existing handler patterns

---

### Task 2.2: Catch-All Message Handler

**Priority**: P0 (Critical)
**Time**: 1.5 hours

#### Subtasks:

- [ ] **2.2.1** Implement base handler
  - **File**: `src/api/handlers/ai/chat_handler.py` (NEW)
  - **Handler signature**:
    ```python
    from aiogram import Router, types, F
    from aiogram.filters import StateFilter
    from application.services.service_container import ServiceContainer

    router = Router(name="ai_chat")

    @router.message(
        StateFilter(None),  # Only when NOT in FSM state
        F.text,  # Only text messages
        F.text.func(lambda text: not text.startswith('/'))  # Exclude commands
    )
    async def handle_ai_message(
        message: types.Message,
        services: ServiceContainer
    ) -> None:
        """
        Handle arbitrary text messages with AI classification.

        Flow:
        1. Show typing indicator
        2. Gather user context
        3. Classify intent via AI
        4. Execute corresponding action
        5. Handle errors gracefully
        """
    ```

- [ ] **2.2.2** Implement handler logic
  ```python
  async def handle_ai_message(message: types.Message, services: ServiceContainer):
      # 1. Rate limiting check
      if not await check_rate_limit(message.from_user.id, services):
          await message.answer("⏳ Слишком много запросов. Попробуйте через минуту.")
          return

      # 2. Show typing indicator
      await message.bot.send_chat_action(message.chat.id, "typing")

      # 3. Gather user context
      context = await get_user_context(message.from_user.id, services)

      # 4. Classify intent
      try:
          classification = await services.ai.classify_intent(
              message.text,
              context
          )
      except AIServiceError as e:
          logger.error(f"AI classification failed: {e}")
          await message.answer(
              "😔 Извините, AI временно недоступен.\n"
              "Используйте /start для меню."
          )
          return

      # 5. Log classification
      logger.info(
          f"Intent classified: {classification.intent}",
          extra={
              "user_id": message.from_user.id,
              "confidence": classification.confidence,
              "parameters": classification.parameters
          }
      )

      # 6. Execute action
      await execute_intent_action(message, classification, services)
  ```

- [ ] **2.2.3** Add rate limiting
  - **Function**: `check_rate_limit(user_id: int, services: ServiceContainer) -> bool`
  - **Implementation**: Redis-based sliding window (10 req/min)
  - **Key format**: `ai:ratelimit:{user_id}`

- [ ] **2.2.4** Add typing indicator helper
  - Use `ChatActionSender` context manager for continuous typing
  - Auto-cancel on response sent

**Acceptance Criteria**:
- ✅ Handler only triggers when NOT in FSM state
- ✅ Excludes commands (starting with `/`)
- ✅ Rate limiting works correctly
- ✅ Typing indicator shows while processing
- ✅ Graceful error handling

---

### Task 2.3: Action Executors

**Priority**: P0 (Critical)
**Time**: 1.5 hours

#### Subtasks:

- [ ] **2.3.1** Create action executor dispatcher
  - **File**: `src/api/handlers/ai/actions.py` (NEW)
  - **Main function**:
    ```python
    async def execute_intent_action(
        message: types.Message,
        classification: IntentClassification,
        services: ServiceContainer
    ) -> None:
        """
        Execute action based on classified intent.

        Routes to appropriate executor based on intent type.
        """
        executor_map = {
            UserIntent.CREATE_ACTIVITY: execute_create_activity,
            UserIntent.VIEW_STATS: execute_view_stats,
            UserIntent.MANAGE_CATEGORIES: execute_manage_categories,
            UserIntent.SETTINGS: execute_settings,
            UserIntent.GENERAL_CHAT: execute_general_response,
            UserIntent.HELP: execute_help,
            UserIntent.UNKNOWN: execute_unknown,
        }

        executor = executor_map.get(classification.intent)
        await executor(message, classification, services)
    ```

- [ ] **2.3.2** Implement CREATE_ACTIVITY executor
  ```python
  async def execute_create_activity(
      message: types.Message,
      classification: IntentClassification,
      services: ServiceContainer
  ) -> None:
      """
      Handle activity creation intent.

      Options:
      1. If parameters extracted -> prefill and start FSM
      2. If no parameters -> show activity creation button
      """
      params = ActivityParameters(**classification.parameters)

      if params.has_time_info():
          # Start FSM with prefilled data
          await start_activity_fsm_with_prefill(message, params, services)
      else:
          # Show quick action button
          keyboard = InlineKeyboardMarkup(inline_keyboard=[[
              InlineKeyboardButton(
                  text="📝 Записать активность",
                  callback_data="add_activity"
              )
          ]])
          await message.answer(
              "Понял, вы хотите записать активность.\n"
              "Нажмите кнопку ниже чтобы начать:",
              reply_markup=keyboard
          )
  ```

- [ ] **2.3.3** Implement VIEW_STATS executor
  ```python
  async def execute_view_stats(
      message: types.Message,
      classification: IntentClassification,
      services: ServiceContainer
  ) -> None:
      """
      Show user statistics with AI-generated summary.

      Combines structured data display with natural language summary.
      """
      # 1. Get user stats
      user = await services.user.get_by_telegram_id(message.from_user.id)
      stats = await calculate_user_stats(user["id"], services)

      # 2. Generate AI summary
      context = await get_user_context(message.from_user.id, services)
      summary = await services.ai.generate_response(
          message.text,
          context,
          UserIntent.VIEW_STATS
      )

      # 3. Format and send
      response = f"{summary}\n\n📊 **Статистика:**\n{format_stats(stats)}"
      await message.answer(response, parse_mode="Markdown")
  ```

- [ ] **2.3.4** Implement MANAGE_CATEGORIES executor
  ```python
  async def execute_manage_categories(
      message: types.Message,
      classification: IntentClassification,
      services: ServiceContainer
  ) -> None:
      """Show categories management menu."""
      # Reuse existing categories keyboard
      from api.handlers.categories import get_categories_keyboard

      keyboard = await get_categories_keyboard(message.from_user.id, services)
      await message.answer(
          "📁 Управление категориями:",
          reply_markup=keyboard
      )
  ```

- [ ] **2.3.5** Implement SETTINGS executor
  ```python
  async def execute_settings(
      message: types.Message,
      classification: IntentClassification,
      services: ServiceContainer
  ) -> None:
      """Show settings menu."""
      from api.handlers.settings import get_settings_menu

      keyboard = get_settings_menu()
      await message.answer(
          "⚙️ Настройки бота:",
          reply_markup=keyboard
      )
  ```

- [ ] **2.3.6** Implement GENERAL_CHAT executor
  ```python
  async def execute_general_response(
      message: types.Message,
      classification: IntentClassification,
      services: ServiceContainer
  ) -> None:
      """Generate conversational response."""
      context = await get_user_context(message.from_user.id, services)
      response = await services.ai.generate_response(
          message.text,
          context,
          UserIntent.GENERAL_CHAT
      )

      # Add helpful action buttons
      keyboard = InlineKeyboardMarkup(inline_keyboard=[
          [InlineKeyboardButton(text="📝 Записать", callback_data="add_activity")],
          [InlineKeyboardButton(text="📊 Статистика", callback_data="view_stats")],
      ])

      await message.answer(response, reply_markup=keyboard)
  ```

- [ ] **2.3.7** Implement HELP and UNKNOWN executors
  - HELP: Show bot features and commands
  - UNKNOWN: Apologize and show main menu

**Acceptance Criteria**:
- ✅ All 7 intent types have executors
- ✅ Executors reuse existing keyboards/menus
- ✅ Error handling in each executor
- ✅ Russian user messages

---

## Phase 3: FSM Integration (2-3 hours)

### Task 3.1: FSM Programmatic Triggering

**Priority**: P1 (High)
**Time**: 1 hour

#### Subtasks:

- [ ] **3.1.1** Create FSM starter utilities
  - **File**: `src/api/handlers/ai/fsm_helpers.py` (NEW)
  - **Functions**:
    ```python
    async def start_activity_fsm_with_prefill(
        message: types.Message,
        params: ActivityParameters,
        services: ServiceContainer
    ) -> None:
        """
        Start activity creation FSM with AI-extracted parameters.

        Flow:
        1. Set initial FSM state
        2. Store prefilled data in FSM context
        3. Send first prompt (skip already filled fields)
        """
        from api.states.activity import ActivityStates
        from aiogram.fsm.context import FSMContext

        state = FSMContext(...)  # Get from message

        # Determine starting state based on extracted params
        if params.start_time and params.end_time and params.description:
            # All filled -> go to category selection
            await state.set_state(ActivityStates.waiting_for_category)
            await state.update_data(
                start_time=params.start_time,
                end_time=params.end_time,
                description=params.description
            )
            # Show category keyboard
            ...
        elif params.start_time and params.duration:
            # Start + duration -> go to description
            await state.set_state(ActivityStates.waiting_for_description)
            ...
        # ... other combinations
    ```

- [ ] **3.1.2** Implement smart field skipping
  - If start_time extracted -> skip to end_time state
  - If description extracted -> skip to category state
  - Show confirmation message: "Я понял: ..."

- [ ] **3.1.3** Add validation for extracted params
  - Validate time formats
  - Validate duration parsing
  - Validate description length
  - Fallback to manual input if invalid

**Acceptance Criteria**:
- ✅ FSM starts from appropriate state
- ✅ Extracted data stored in FSM context
- ✅ Invalid data handled gracefully
- ✅ User sees confirmation of understood parameters

---

### Task 3.2: Natural Language Parsing

**Priority**: P1 (High)
**Time**: 1 hour

#### Subtasks:

- [ ] **3.2.1** Enhance parameter extraction prompts
  - **File**: Update `src/application/services/ai_service.py`
  - **Improve**: Time parsing (relative and absolute)
  - **Examples**:
    - "час назад" -> 1 hour ago from now
    - "с 14:00 до 15:30" -> start=14:00, end=15:30
    - "2 часа" -> duration=2h
    - "полчаса" -> duration=30m

- [ ] **3.2.2** Add time parsing utilities
  - **File**: `src/api/handlers/ai/time_parser.py` (NEW)
  - **Functions**:
    - `parse_relative_time(text: str) -> datetime`
    - `parse_duration(text: str) -> timedelta`
    - `parse_absolute_time(text: str) -> time`

- [ ] **3.2.3** Test extraction accuracy
  - **File**: `tests/unit/test_time_parser.py`
  - **Test cases**:
    - Various Russian time formats
    - Relative times
    - Durations in different units
    - Edge cases (midnight, noon, etc.)

**Acceptance Criteria**:
- ✅ Accurate parsing of Russian time expressions
- ✅ Support for relative and absolute times
- ✅ Duration parsing in hours/minutes
- ✅ 90%+ accuracy on test cases

---

### Task 3.3: Confirmation Flow

**Priority**: P2 (Medium)
**Time**: 45 min

#### Subtasks:

- [ ] **3.3.1** Add confirmation before saving
  - When all params extracted, show summary:
    ```
    Я понял:
    🕐 Начало: 14:00
    🕑 Окончание: 16:00
    📝 Описание: работа над проектом
    📁 Категория: Работа

    Всё верно?
    [✅ Сохранить] [✏️ Изменить] [❌ Отмена]
    ```

- [ ] **3.3.2** Implement edit flow
  - If user clicks "Изменить" -> show inline keyboard to select field
  - Allow editing specific field
  - Return to confirmation after edit

- [ ] **3.3.3** Handle cancellation
  - Clear FSM state
  - Return to idle mode (AI catch-all active)

**Acceptance Criteria**:
- ✅ Clear confirmation message
- ✅ Easy to edit specific fields
- ✅ Cancellation works correctly

---

## Phase 4: Prompts and Classification (2-3 hours)

### Task 4.1: System Prompts

**Priority**: P0 (Critical)
**Time**: 1 hour

#### Subtasks:

- [ ] **4.1.1** Create classification system prompt
  - **File**: `src/api/handlers/ai/prompts.py` (NEW)
  - **Prompt template**:
    ```python
    CLASSIFICATION_PROMPT = """
    You are an intent classifier for a Telegram activity tracking bot.

    User context:
    - Recent activities: {recent_activities}
    - Today's stats: {today_stats}
    - Categories: {categories}
    - Timezone: {timezone}

    User message: "{user_message}"

    Classify the intent into ONE of these categories:
    1. CREATE_ACTIVITY: User wants to log an activity
       Examples: "worked 2 hours", "meeting from 14:00", "я поработал"

    2. VIEW_STATS: User wants to see statistics
       Examples: "show stats", "what did I do today", "покажи статистику"

    3. MANAGE_CATEGORIES: User wants to manage categories
       Examples: "create category", "my categories", "категории"

    4. SETTINGS: User wants to change settings
       Examples: "settings", "change interval", "настройки"

    5. GENERAL_CHAT: General conversation
       Examples: "hello", "how are you", "привет"

    6. HELP: User needs help
       Examples: "help", "how to use", "помощь"

    7. UNKNOWN: Cannot determine intent

    Respond with JSON:
    {
        "intent": "intent_name",
        "confidence": 0.0-1.0,
        "reasoning": "why you classified this way",
        "parameters": {}
    }

    Be concise. Always respond in valid JSON.
    """
    ```

- [ ] **4.1.2** Create parameter extraction prompt
  ```python
  EXTRACTION_PROMPT = """
  Extract activity parameters from this message: "{message}"

  Extract if present:
  - start_time: When activity started (ISO time or relative)
  - end_time: When activity ended
  - duration: How long it lasted (e.g., "2h", "30m")
  - description: What the activity was about
  - category: Category name if mentioned

  Current time: {current_time}
  Current date: {current_date}
  Timezone: {timezone}

  Examples:
  "worked 2 hours on project" -> {
      "duration": "2h",
      "description": "работа над проектом"
  }

  "meeting from 14:00 to 15:30" -> {
      "start_time": "14:00",
      "end_time": "15:30"
  }

  Respond with JSON only. Use null for missing fields.
  """
  ```

- [ ] **4.1.3** Create response generation prompt
  ```python
  RESPONSE_PROMPT = """
  You are a friendly activity tracking assistant.

  User context:
  {user_context}

  User message: "{user_message}"
  Intent: {intent}

  Generate a helpful response in Russian that:
  1. Acknowledges the user's message
  2. Provides relevant information from context
  3. Suggests helpful actions (if applicable)

  Be concise (2-3 sentences max), friendly, and helpful.
  Use emojis sparingly.

  Response:
  """
  ```

**Acceptance Criteria**:
- ✅ All prompts defined with clear templates
- ✅ JSON schema specified for structured outputs
- ✅ Examples included in prompts
- ✅ Timezone-aware time handling

---

### Task 4.2: Prompt Testing and Refinement

**Priority**: P1 (High)
**Time**: 1 hour

#### Subtasks:

- [ ] **4.2.1** Create test dataset
  - **File**: `tests/data/ai_test_messages.json`
  - **Content**: 50+ test messages with expected intents
  - **Coverage**:
    - 10 CREATE_ACTIVITY messages
    - 10 VIEW_STATS messages
    - 10 GENERAL_CHAT messages
    - 10 edge cases
    - 10 ambiguous messages

- [ ] **4.2.2** Run classification accuracy tests
  - **Script**: `tests/integration/test_ai_classification.py`
  - **Metrics**:
    - Overall accuracy (target: >85%)
    - Per-intent precision/recall
    - Confidence score distribution

- [ ] **4.2.3** Tune prompts based on results
  - Adjust examples in prompts
  - Add edge case handling
  - Improve parameter extraction

- [ ] **4.2.4** Test with real Russian messages
  - Colloquial language
  - Typos and informal speech
  - Mixed Russian/English

**Acceptance Criteria**:
- ✅ 85%+ classification accuracy on test set
- ✅ No critical misclassifications (e.g., DELETE as CREATE)
- ✅ Robust to typos and informal language

---

## Phase 5: Error Handling and Safety (1-2 hours)

### Task 5.1: Error Handling

**Priority**: P0 (Critical)
**Time**: 45 min

#### Subtasks:

- [ ] **5.1.1** Implement comprehensive error handling
  - **File**: Update `src/application/services/ai_service.py`
  - **Error types**:
    ```python
    class AIServiceError(Exception):
        """Base exception for AI service errors."""
        pass

    class AITimeoutError(AIServiceError):
        """AI request timed out."""
        pass

    class AIQuotaExceededError(AIServiceError):
        """API quota/rate limit exceeded."""
        pass

    class AIInvalidResponseError(AIServiceError):
        """AI returned invalid/unparseable response."""
        pass
    ```

- [ ] **5.1.2** Add retry logic
  ```python
  async def _call_with_retry(
      self,
      prompt: str,
      max_retries: int = 1
  ) -> str:
      """Call AI with exponential backoff retry."""
      for attempt in range(max_retries + 1):
          try:
              return await self._call_ai(prompt)
          except (Timeout, APIError) as e:
              if attempt == max_retries:
                  raise AIServiceError(f"Failed after {max_retries} retries") from e
              await asyncio.sleep(2 ** attempt)  # Exponential backoff
  ```

- [ ] **5.1.3** Add fallback messages
  - **File**: `src/api/handlers/ai/config.py`
  - **Fallback responses**:
    ```python
    FALLBACK_MESSAGES_RU = {
        "ai_unavailable": (
            "😔 Извините, AI временно недоступен.\n"
            "Используйте /start для меню или попробуйте позже."
        ),
        "classification_failed": (
            "🤔 Не уверен, что вы имеете в виду.\n"
            "Попробуйте переформулировать или используйте /start."
        ),
        "rate_limit": (
            "⏳ Слишком много запросов.\n"
            "Подождите минуту и попробуйте снова."
        ),
    }
    ```

**Acceptance Criteria**:
- ✅ All error types properly caught
- ✅ Retry logic works correctly
- ✅ User-friendly fallback messages
- ✅ Errors logged for debugging

---

### Task 5.2: Security and Safety

**Priority**: P0 (Critical)
**Time**: 30 min

#### Subtasks:

- [ ] **5.2.1** Add input validation
  - **Max message length**: 1000 characters
  - **Sanitize input**: Remove control characters
  - **Check for prompt injection attempts**: Log suspicious patterns

- [ ] **5.2.2** Add output validation
  - **Validate JSON structure** from AI
  - **Sanitize AI responses** before sending to user
  - **Check for sensitive data** in responses

- [ ] **5.2.3** Add rate limiting
  - **Per user**: 10 requests/minute
  - **Global**: 100 requests/minute (optional)
  - **Implementation**: Redis sliding window

- [ ] **5.2.4** Add monitoring
  - Log all AI interactions
  - Track error rates
  - Alert on unusual patterns

**Acceptance Criteria**:
- ✅ Input validation prevents abuse
- ✅ Rate limiting works correctly
- ✅ All interactions logged
- ✅ No sensitive data leaks

---

### Task 5.3: Cost Management

**Priority**: P2 (Medium)
**Time**: 15 min

#### Subtasks:

- [ ] **5.3.1** Add token counting
  - Count tokens before API call
  - Truncate context if exceeds limit
  - Log token usage per request

- [ ] **5.3.2** Add cost tracking
  - Log approximate cost per request
  - Daily/weekly usage reports
  - Alert on excessive usage

- [ ] **5.3.3** Optimize prompts
  - Remove unnecessary context
  - Use shorter system prompts
  - Cache common responses (optional)

**Acceptance Criteria**:
- ✅ Token usage monitored
- ✅ Context stays under limits
- ✅ Cost tracking implemented

---

## Phase 6: Testing (2-3 hours)

### Task 6.1: Unit Tests

**Priority**: P0 (Critical)
**Time**: 1 hour

#### Subtasks:

- [ ] **6.1.1** Test AIService methods
  - **File**: `tests/unit/services/test_ai_service.py`
  - **Coverage**:
    - Mock OpenRouter API responses
    - Test all intent classifications
    - Test parameter extraction
    - Test error handling
    - Test retry logic

- [ ] **6.1.2** Test intent classification
  - **File**: `tests/unit/handlers/ai/test_intents.py`
  - **Test**: Each UserIntent enum value
  - **Test**: IntentClassification validation
  - **Test**: ActivityParameters parsing

- [ ] **6.1.3** Test context provider
  - **File**: `tests/unit/handlers/ai/test_context_provider.py`
  - **Mock**: Database queries
  - **Test**: Token limit enforcement
  - **Test**: Data formatting

**Target**: >80% code coverage

**Acceptance Criteria**:
- ✅ All services have unit tests
- ✅ Mock external dependencies
- ✅ Fast execution (<5 seconds)

---

### Task 6.2: Integration Tests

**Priority**: P0 (Critical)
**Time**: 1 hour

#### Subtasks:

- [ ] **6.2.1** Test full AI handler flow
  - **File**: `tests/integration/test_ai_handler.py`
  - **Test scenarios**:
    1. User sends text -> AI classifies -> Action executed
    2. User sends text in FSM state -> AI ignored
    3. User sends command -> AI ignored
    4. Rate limit exceeded -> Error message
    5. AI service down -> Fallback message

- [ ] **6.2.2** Test FSM integration
  - **File**: `tests/integration/test_ai_fsm_integration.py`
  - **Scenarios**:
    1. AI starts FSM with prefilled data
    2. User completes FSM started by AI
    3. User cancels AI-started FSM
    4. Invalid parameters -> Manual FSM

- [ ] **6.2.3** Test handler registration order
  - Verify AI router is registered last
  - Verify FSM handlers take priority
  - Verify commands not intercepted

**Acceptance Criteria**:
- ✅ Full flow tested end-to-end
- ✅ FSM integration works correctly
- ✅ No regression in existing tests

---

### Task 6.3: Manual Testing

**Priority**: P1 (High)
**Time**: 1 hour

#### Subtasks:

- [ ] **6.3.1** Test natural language activity creation
  - **Scenarios**:
    - "я работал 2 часа над проектом"
    - "встреча с 14:00 до 15:30"
    - "час назад начал читать книгу"
    - "позавчера тренировался 45 минут"

- [ ] **6.3.2** Test statistics queries
  - "что я делал сегодня?"
  - "покажи статистику за неделю"
  - "сколько времени на работу?"
  - "мои категории"

- [ ] **6.3.3** Test general conversation
  - "привет"
  - "спасибо"
  - "как дела?"
  - "расскажи о боте"

- [ ] **6.3.4** Test edge cases
  - Empty messages
  - Very long messages (>1000 chars)
  - Messages with special characters
  - Mixed language messages

- [ ] **6.3.5** Test error scenarios
  - AI service down (disconnect internet)
  - Invalid API key
  - Rate limit exceeded (send 15 messages quickly)

**Acceptance Criteria**:
- ✅ All scenarios work as expected
- ✅ No crashes or unhandled errors
- ✅ User experience is smooth

---

## Phase 7: Registration and Deployment (30 min)

### Task 7.1: Router Registration

**Priority**: P0 (Critical)
**Time**: 10 min

#### Subtasks:

- [ ] **7.1.1** Register AI router in main.py
  - **File**: `src/main.py`
  - **Location**: After all existing routers (line ~81)
  - **Code**:
    ```python
    from api.handlers import (
        start_router,
        activity_router,
        categories_router,
        settings_router,
        poll_router,
        ai_router  # ← Add import
    )

    # Router registration (ORDER MATTERS!)
    dp.include_router(start_router)
    dp.include_router(activity_router)
    dp.include_router(categories_router)
    dp.include_router(settings_router)
    dp.include_router(poll_router)
    dp.include_router(ai_router)  # ← Add LAST
    ```

- [ ] **7.1.2** Verify import path
  - Ensure `ai_router` exported from `api.handlers.__init__.py`

**Acceptance Criteria**:
- ✅ AI router registered last
- ✅ Application starts without errors
- ✅ Existing routes still work

---

### Task 7.2: Configuration Documentation

**Priority**: P1 (High)
**Time**: 15 min

#### Subtasks:

- [ ] **7.2.1** Update README
  - **File**: `README.md`
  - **Add section**: "AI Integration"
  - **Content**:
    ```markdown
    ## AI Integration

    This bot uses AI (via OpenRouter) to understand natural language
    and help users log activities conversationally.

    ### Setup

    1. Get OpenRouter API key: https://openrouter.ai/
    2. Add to `.env`:
       ```
       OPENROUTER_API_KEY=your-key-here
       OPENROUTER_MODEL=openai/gpt-3.5-turbo
       ```
    3. Restart bot

    ### Features

    - Natural language activity logging
    - Intent classification
    - Smart parameter extraction
    - Contextual responses

    ### Examples

    - "я работал 2 часа над проектом" → Creates activity
    - "покажи статистику" → Shows stats
    - "настройки" → Opens settings
    ```

- [ ] **7.2.2** Update .env.example
  - Already done in Task 1.1.3

- [ ] **7.2.3** Add troubleshooting guide
  - **File**: `docs/AI_TROUBLESHOOTING.md` (NEW)
  - **Content**: Common issues and solutions

**Acceptance Criteria**:
- ✅ Clear setup instructions
- ✅ Examples provided
- ✅ Troubleshooting documented

---

### Task 7.3: Logging and Monitoring

**Priority**: P1 (High)
**Time**: 10 min

#### Subtasks:

- [ ] **7.3.1** Add AI-specific logging
  - **File**: Update `src/infrastructure/logging/logger.py` (if exists)
  - **Add logger**: `ai_service` logger
  - **Log levels**:
    - INFO: Successful classifications
    - WARNING: Low confidence classifications
    - ERROR: API failures, timeouts

- [ ] **7.3.2** Add metrics (optional)
  - Track classification success rate
  - Track average confidence score
  - Track API latency
  - Track error rate

**Acceptance Criteria**:
- ✅ All AI interactions logged
- ✅ Easy to debug classification issues
- ✅ Performance metrics available

---

## Phase 8: Optimization and Enhancements (Optional)

### Task 8.1: Response Caching

**Priority**: P3 (Low)
**Time**: 30 min

#### Subtasks:

- [ ] **8.1.1** Implement classification cache
  - Cache common phrases for 24 hours
  - Key: `ai:cache:{hash(message)}`
  - Store: IntentClassification JSON

- [ ] **8.1.2** Implement context cache
  - Cache user context for 5 minutes
  - Invalidate on activity creation
  - Reduce DB queries

**Acceptance Criteria**:
- ✅ Response time improved for cached queries
- ✅ Cache hit rate >30%

---

### Task 8.2: Advanced Features

**Priority**: P3 (Low)
**Time**: 2+ hours

#### Subtasks:

- [ ] **8.2.1** Multi-activity creation
  - Support: "я работал 2 часа, потом встреча час"
  - Create multiple activities from one message

- [ ] **8.2.2** Activity editing via AI
  - "измени последнюю активность"
  - "удали запись про встречу"

- [ ] **8.2.3** Smart suggestions
  - Suggest categories based on description
  - Detect patterns (e.g., recurring meetings)
  - Remind about unfinished activities

- [ ] **8.2.4** Voice message support
  - Transcribe voice to text
  - Process with AI

**Acceptance Criteria**:
- ✅ Advanced features work reliably
- ✅ No impact on basic functionality

---

## Verification Checklist

Before marking project as complete, verify:

### Functionality
- [ ] AI handler responds to arbitrary text messages
- [ ] Intent classification works with >85% accuracy
- [ ] Activity creation from natural language works
- [ ] Statistics queries answered correctly
- [ ] Existing FSM flows not affected
- [ ] Commands still work normally

### Code Quality
- [ ] All code follows existing patterns (DI, middleware)
- [ ] Type hints on all functions
- [ ] Docstrings (English) on all public methods
- [ ] User-facing messages in Russian
- [ ] No hardcoded strings (use config/constants)

### Testing
- [ ] Unit tests pass (>80% coverage)
- [ ] Integration tests pass
- [ ] Manual testing completed
- [ ] No regression in existing tests

### Performance
- [ ] AI responses within 3 seconds (p95)
- [ ] Rate limiting works
- [ ] No memory leaks
- [ ] Token usage within limits

### Security
- [ ] Input validation implemented
- [ ] Output sanitization implemented
- [ ] Rate limiting active
- [ ] API keys not exposed in logs

### Documentation
- [ ] README updated
- [ ] .env.example updated
- [ ] API documented (if public)
- [ ] Troubleshooting guide created

### Deployment
- [ ] Works in Docker environment
- [ ] Environment variables documented
- [ ] Rollback plan prepared
- [ ] Monitoring/logging active

---

## Rollback Plan

If AI integration causes issues:

1. **Quick Disable**:
   ```python
   # In main.py, comment out:
   # dp.include_router(ai_router)
   ```

2. **Revert Commits**:
   ```bash
   git revert <commit-hash>
   ```

3. **Emergency Fix**:
   - Add feature flag: `AI_ENABLED=false`
   - Check in handler: `if not settings.ai_enabled: return`

---

## Success Metrics

### Week 1
- [ ] 90%+ of natural language activity creations succeed
- [ ] AI response time <3s (p95)
- [ ] Error rate <5%
- [ ] User satisfaction (survey or feedback)

### Week 2
- [ ] Refine prompts based on real usage
- [ ] Add most-requested features
- [ ] Optimize performance

---

## Notes and Considerations

### OpenRouter Free Tier Limits
- Check current free tier limits
- Monitor usage daily
- Plan for paid tier if needed

### Future Enhancements
- Multi-language support
- Voice input
- Batch activity import
- AI-powered analytics
- Predictive suggestions

### Known Limitations
- AI may misclassify ambiguous messages
- Russian language parsing may have edge cases
- API latency depends on OpenRouter performance
- Free tier may have rate limits

---

## Timeline Summary

| Phase | Duration | Priority | Dependencies |
|-------|----------|----------|--------------|
| 1. Infrastructure | 2-3h | P0 | None |
| 2. AI Router | 3-4h | P0 | Phase 1 |
| 3. FSM Integration | 2-3h | P1 | Phase 2 |
| 4. Prompts | 2-3h | P0 | Phase 1 |
| 5. Error Handling | 1-2h | P0 | Phase 2 |
| 6. Testing | 2-3h | P0 | All above |
| 7. Deployment | 30min | P0 | Phase 6 |
| 8. Optimization | 2+ h | P3 | Phase 7 |

**Total Estimated Time**: 12-18 hours
**Critical Path**: Phases 1, 2, 4, 5, 6, 7

---

## Contact and Support

- **Documentation**: See `docs/` directory
- **Issues**: Check existing integration tests for examples
- **Questions**: Review similar handlers in codebase

---

**End of Implementation Plan**

Good luck with the integration! 🚀
