# 🧪 КОМПЛЕКСНЫЙ ПЛАН ТЕСТИРОВАНИЯ
**Дата создания:** 2025-11-05
**Версия:** 1.0
**Статус:** Ready for Execution

---

## 📋 EXECUTIVE SUMMARY

Данный план включает **комплексное тестирование** проекта Activity Tracker Bot после реализации всех UI исправлений и улучшений из `ui-fixes-todo-2025-11-05-142922.md`.

**Уровни тестирования:**
1. ✅ Manual E2E Testing (UI scenarios)
2. ✅ Automated Unit Tests
3. ✅ Automated Service Tests
4. ✅ Automated Integration Tests
5. ✅ Regression Testing
6. ✅ Performance Testing

**Целевые метрики:**
- Coverage: 80%+
- Critical paths: 100% tested
- Zero critical bugs
- P95 response time < 2s

---

## 🎯 ЗАДАЧА 15: КОМПЛЕКСНОЕ ТЕСТИРОВАНИЕ

**Приоритет:** КРИТИЧНО (выполнить ПОСЛЕ задач 1-14)
**Время выполнения:** 8-12 часов
**Ответственный:** QA Engineer + Developer

---

## ЧАСТЬ 1: РУЧНОЕ E2E ТЕСТИРОВАНИЕ UI

### 📱 Раздел 1.1: Регистрация и Onboarding

**Test Case TC-001: Регистрация нового пользователя**

```
Prerequisite: Бот запущен, пользователь не зарегистрирован

Steps:
1. Открыть бота в Telegram
2. Отправить /start
3. Проверить приветственное сообщение
4. Проверить создание пользователя в БД

Expected Result:
✓ Показано приветственное сообщение
✓ Показана главная клавиатура
✓ Пользователь создан с дефолтными настройками
✓ Запланирован первый автоопрос

Pass/Fail: [ ]
Notes: _______________
```

---

### 📝 Раздел 1.2: Запись Активности (ЗАДАЧА 8)

**Test Case TC-002: Запись активности с inline кнопками для категорий**

```
Prerequisite: Пользователь зарегистрирован, есть категории

Steps:
1. Нажать "✏️ Записать активность"
2. Ввести описание: "Работа над проектом"
3. Проверить что категории показаны как inline кнопки (по 2 в ряду)
4. Нажать на категорию "💼 Работа"
5. Выбрать время начала кнопкой "⏰ 1ч назад"
6. Выбрать время окончания кнопкой "⏱ 30м"
7. Проверить сохранение

Expected Result:
✓ Категории показаны как inline кнопки
✓ Есть кнопка "❌ Отменить"
✓ После выбора категории показано время начала
✓ Активность сохранена корректно
✓ Показано главное меню

Pass/Fail: [ ]
Notes: _______________
```

**Test Case TC-003: Отмена выбора категории**

```
Prerequisite: В процессе записи активности на шаге выбора категории

Steps:
1. Начать запись активности
2. Ввести описание
3. На экране выбора категории нажать "❌ Отменить"
4. Проверить очистку FSM

Expected Result:
✓ Показано сообщение "❌ Запись активности отменена."
✓ FSM state очищен
✓ Показано главное меню

Pass/Fail: [ ]
Notes: _______________
```

**Test Case TC-004: Пропуск категории через "0"**

```
Prerequisite: В процессе записи активности на шаге выбора категории

Steps:
1. Начать запись активности
2. Ввести описание
3. На экране выбора категории ввести текстом "0"
4. Проверить что процесс продолжился без категории

Expected Result:
✓ Категория пропущена (category_id = null)
✓ Показан выбор времени начала
✓ Процесс записи продолжен

Pass/Fail: [ ]
Notes: _______________
```

**Test Case TC-005: Запись активности с текстовым вводом времени (ЗАДАЧА 6)**

```
Prerequisite: Пользователь зарегистрирован, есть категории

Steps:
1. Нажать "✏️ Записать активность"
2. Ввести описание
3. Выбрать категорию кнопкой
4. Выбрать время начала кнопкой "⏰ 2ч назад"
5. Ввести время окончания ТЕКСТОМ: "30м"
6. Проверить что показано главное меню

Expected Result:
✓ Время окончания распознано корректно
✓ Активность сохранена
✓ ВАЖНО: Показано главное меню (reply_markup добавлен)

Pass/Fail: [ ]
Notes: _______________
```

---

### 📂 Раздел 1.3: Категории

**Test Case TC-006: Создание категории**

```
Prerequisite: Пользователь зарегистрирован

Steps:
1. Нажать "📂 Категории"
2. Нажать "➕ Создать категорию"
3. Ввести название: "Спорт"
4. Ввести эмодзи: "🏃"
5. Проверить создание

Expected Result:
✓ Категория создана
✓ Показана в списке
✓ Сохранена в БД

Pass/Fail: [ ]
Notes: _______________
```

**Test Case TC-007: Удаление категории**

```
Prerequisite: Есть категория без активностей

Steps:
1. Открыть "📂 Категории"
2. Выбрать категорию
3. Нажать "🗑 Удалить"
4. Подтвердить удаление

Expected Result:
✓ Показано подтверждение
✓ Категория удалена из БД
✓ Обновлен список категорий

Pass/Fail: [ ]
Notes: _______________
```

---

### ⏰ Раздел 1.4: Автоматические Опросы (ЗАДАЧИ 1, 5, 7, 13)

**Test Case TC-008: Автоопрос - вариант "Занимался чем-то" (ЗАДАЧА 1)**

```
Prerequisite: Пользователь зарегистрирован, есть категории, настроен интервал опроса

Steps:
1. Дождаться автоматического опроса (или запустить вручную для теста)
2. Проверить текст опроса (должен быть обновлен согласно ЗАДАЧЕ 13)
3. Нажать кнопку "✏️ Занимался чем-то"
4. Выбрать категорию из inline кнопок
5. Проверить создание активности
6. Проверить планирование следующего опроса

Expected Result:
✓ Показан опрос с кнопкой "✏️ Занимался чем-то"
✓ Текст опроса корректен (с указанием времени интервала)
✓ Показаны категории как inline кнопки
✓ Активность создана с duration = poll_interval
✓ Следующий опрос запланирован
✓ Показано сообщение с подтверждением и временем следующего опроса

Pass/Fail: [ ]
Notes: _______________
```

**Test Case TC-009: Автоопрос - вариант "Спал" (ЗАДАЧА 5)**

```
Prerequisite: Дождаться автоопроса

Steps:
1. Получить автоопрос
2. Нажать "😴 Спал"
3. Проверить длительность сна в сообщении

Expected Result:
✓ Категория "сон" создана автоматически
✓ Длительность сна = интервал опроса (НЕ дефолтные 8 часов!)
✓ last_poll_time обновлён (если API поддерживает)
✓ Следующий опрос запланирован

Pass/Fail: [ ]
Notes: _______________
```

**Test Case TC-010: Автоопрос - откладывание при конфликте FSM (ЗАДАЧА 7)**

```
Prerequisite: Пользователь в процессе записи активности

Steps:
1. Начать запись активности (FSM активен)
2. Запустить автоопрос вручную (или дождаться времени)
3. Проверить что опрос НЕ прислан
4. Проверить логи - должна быть запись о postpone на 10 минут
5. Завершить запись активности
6. Через 10 минут проверить что опрос пришёл

Expected Result:
✓ Опрос не прислан во время активного FSM
✓ В логах: "User X is in FSM state Y, postponing poll by 10 minutes"
✓ Job rescheduled на +10 минут
✓ После завершения FSM опрос приходит корректно

Pass/Fail: [ ]
Notes: _______________
```

**Test Case TC-011: Автоопрос - напоминание**

```
Prerequisite: Пользователь пропустил опрос

Steps:
1. Получить автоопрос
2. Нажать "⏰ Напомни позже"
3. Дождаться напоминания (или проверить job в scheduler)
4. Получить напоминание
5. Нажать "✅ Хорошо, расскажу"

Expected Result:
✓ Показано сообщение о напоминании
✓ Job запланирован на +reminder_delay минут
✓ Напоминание приходит вовремя
✓ После "Хорошо" показаны те же опции что в оригинальном опросе

Pass/Fail: [ ]
Notes: _______________
```

---

### ⚙️ Раздел 1.5: Настройки (ЗАДАЧА 2, 4)

**Test Case TC-012: Настройка интервала будних дней - кастомный ввод (ЗАДАЧА 2)**

```
Prerequisite: Пользователь зарегистрирован

Steps:
1. Открыть "⚙️ Настройки"
2. Выбрать "⏱ Интервалы опросов"
3. Выбрать "📅 Будние дни"
4. Нажать "✏️ Указать своё время"
5. Ввести "90"
6. Проверить обновление настроек
7. Проверить пересчёт расписания опросов

Expected Result:
✓ Показан промпт для ввода
✓ Валидация работает (30-480 минут)
✓ Настройки обновлены в БД
✓ Показано подтверждение "каждые 1ч 30м"
✓ Poll job rescheduled
✓ В логах: "Rescheduled poll for user X with custom weekday interval 90"

Pass/Fail: [ ]
Notes: _______________
```

**Test Case TC-013: Настройка интервала выходных - кастомный ввод (ЗАДАЧА 2)**

```
Prerequisite: Пользователь зарегистрирован

Steps:
1. Настройки → Интервалы → Выходные
2. Нажать "✏️ Указать своё время"
3. Ввести "210"
4. Проверить обновление

Expected Result:
✓ Валидация работает (30-600 минут)
✓ Настройки обновлены
✓ Показано "каждые 3ч 30м"
✓ Poll rescheduled

Pass/Fail: [ ]
Notes: _______________
```

**Test Case TC-014: Настройка задержки напоминаний - кастомный ввод (ЗАДАЧА 2)**

```
Prerequisite: Пользователь зарегистрирован

Steps:
1. Настройки → Напоминания
2. Нажать "⏱ Изменить задержку"
3. Нажать "✏️ Указать своё время"
4. Ввести "45"
5. Проверить обновление

Expected Result:
✓ Валидация работает (5-120 минут)
✓ Настройки обновлены
✓ Показано подтверждение "напомнить через 45 минут"

Pass/Fail: [ ]
Notes: _______________
```

**Test Case TC-015: Валидация кастомного ввода - неверные значения**

```
Prerequisite: В процессе кастомного ввода интервала

Steps:
1. Настройки → Интервалы → Будние → Кастомный
2. Ввести "15" (меньше минимума 30)
3. Проверить ошибку валидации
4. Ввести "500" (больше максимума 480)
5. Проверить ошибку валидации
6. Ввести "abc" (не число)
7. Проверить ошибку валидации

Expected Result:
✓ Для 15: "⚠️ Интервал должен быть от 30 до 480 минут"
✓ Для 500: "⚠️ Интервал должен быть от 30 до 480 минут"
✓ Для abc: "⚠️ Неверный формат! Введи целое число"
✓ FSM state НЕ очищен, можно ввести заново

Pass/Fail: [ ]
Notes: _______________
```

**Test Case TC-016: Тихие часы - включение/выключение (ЗАДАЧА 4)**

```
Prerequisite: Тихие часы выключены

Steps:
1. Настройки → Тихие часы
2. Проверить что кнопка "⏰ Изменить время" ОТСУТСТВУЕТ
3. Нажать "✅ Включить тихие часы"
4. Проверить что кнопка "⏰ Изменить время" ПОЯВИЛАСЬ
5. Нажать "❌ Отключить тихие часы"
6. Проверить что кнопка исчезла

Expected Result:
✓ Клавиатура формируется корректно (без пустых списков)
✓ Кнопки показываются/скрываются в зависимости от состояния
✓ Настройки обновляются в БД

Pass/Fail: [ ]
Notes: _______________
```

**Test Case TC-017: Напоминания - включение/выключение (ЗАДАЧА 4)**

```
Prerequisite: Напоминания включены

Steps:
1. Настройки → Напоминания
2. Проверить что кнопка "⏱ Изменить задержку" ПРИСУТСТВУЕТ
3. Нажать "❌ Отключить"
4. Проверить что кнопка "⏱ Изменить задержку" ИСЧЕЗЛА
5. Включить обратно

Expected Result:
✓ Клавиатура формируется корректно
✓ Кнопки показываются/скрываются правильно
✓ Настройки обновляются

Pass/Fail: [ ]
Notes: _______________
```

---

### 🚫 Раздел 1.6: Команда /cancel (ЗАДАЧА 3)

**Test Case TC-018: /cancel в процессе записи активности**

```
Prerequisite: В процессе записи активности

Steps:
1. Начать запись активности
2. Ввести описание
3. На любом шаге (выбор категории, времени) отправить /cancel
4. Проверить очистку FSM
5. Проверить возврат в главное меню

Expected Result:
✓ FSM state очищен
✓ Показано "❌ Запись активности отменена."
✓ Показано главное меню
✓ Можно начать новую активность

Pass/Fail: [ ]
Notes: _______________
```

**Test Case TC-019: /cancel в процессе создания категории**

```
Prerequisite: В процессе создания категории

Steps:
1. Начать создание категории
2. На шаге ввода названия отправить /cancel
3. Проверить очистку FSM

Expected Result:
✓ FSM cleared
✓ Показано "❌ Создание категории отменено."
✓ Главное меню

Pass/Fail: [ ]
Notes: _______________
```

**Test Case TC-020: /cancel в процессе настроек**

```
Prerequisite: В процессе кастомного ввода интервала

Steps:
1. Настройки → Интервалы → Будние → Кастомный
2. Отправить /cancel
3. Проверить очистку FSM

Expected Result:
✓ FSM cleared
✓ Показано "❌ Настройка отменена."
✓ Главное меню

Pass/Fail: [ ]
Notes: _______________
```

**Test Case TC-021: /cancel когда FSM не активен**

```
Prerequisite: Пользователь в главном меню (FSM не активен)

Steps:
1. Отправить /cancel
2. Проверить сообщение

Expected Result:
✓ Показано "Нечего отменять. Ты сейчас не в процессе настройки."
✓ Главное меню

Pass/Fail: [ ]
Notes: _______________
```

---

### ✨ Раздел 1.7: UX Улучшения (ЗАДАЧА 9)

**Test Case TC-022: Индикатор "печатает..." при нажатии кнопок**

```
Prerequisite: Пользователь в главном меню

Steps:
1. Нажать любую inline кнопку (например "✏️ Записать активность")
2. СРАЗУ после клика проверить индикатор
3. Повторить для других кнопок:
   - "📂 Категории"
   - "⚙️ Настройки"
   - Кнопки в настройках
   - Кнопки в опросах

Expected Result:
✓ СРАЗУ после клика появляется индикатор "печатает..."
✓ Индикатор показывается ~1-2 секунды
✓ Затем приходит ответ бота
✓ UX улучшен - нет ощущения "зависшего" бота

Pass/Fail: [ ]
Notes: _______________
```

---

### 📊 Раздел 1.8: Просмотр Активностей

**Test Case TC-023: Просмотр последних активностей**

```
Prerequisite: У пользователя есть 5+ активностей

Steps:
1. Нажать "📊 Мои активности"
2. Проверить список
3. Проверить формат вывода

Expected Result:
✓ Показаны последние 10 активностей
✓ Формат: "🏃 Спорт: Бег в парке (1ч 30м)"
✓ Сортировка от новых к старым
✓ Показано главное меню

Pass/Fail: [ ]
Notes: _______________
```

---

## ЧАСТЬ 2: РЕГРЕССИОННОЕ ТЕСТИРОВАНИЕ

### 🔄 Раздел 2.1: Smoke Tests

**Test Case TC-024: Запуск всех контейнеров**

```
Steps:
1. docker compose down
2. docker compose up -d
3. docker compose ps
4. Проверить health checks

Expected Result:
✓ Все 4 контейнера запущены (postgres, redis, data_api, bot)
✓ Health checks: healthy
✓ Нет ошибок в логах

Pass/Fail: [ ]
Command: docker compose ps --format "table {{.Names}}\t{{.Status}}"
```

**Test Case TC-025: Health endpoint API**

```
Steps:
1. curl http://localhost:8080/health

Expected Result:
✓ HTTP 200
✓ {"status": "healthy"}

Pass/Fail: [ ]
```

---

### 🔄 Раздел 2.2: Критические Flow

**Test Case TC-026: Полный цикл: регистрация → активность → опрос**

```
Steps:
1. Новый пользователь → /start
2. Создать категорию
3. Записать активность
4. Дождаться автоопроса
5. Ответить на опрос

Expected Result:
✓ Все шаги проходят без ошибок
✓ Данные корректно сохранены в БД
✓ Scheduler работает

Pass/Fail: [ ]
```

---

## ЧАСТЬ 3: АВТОМАТИЗИРОВАННОЕ ТЕСТИРОВАНИЕ

### 🧪 Раздел 3.1: Unit Tests для Poll Handlers (ЗАДАЧА 1)

**Test File:** `services/tracker_activity_bot/tests/unit/test_poll_handlers.py`

```python
"""
Unit tests for poll handlers.

Tests new functionality from TASK 1: "I was doing something" poll option.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from aiogram import types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

from src.api.handlers.poll import (
    handle_poll_activity_start,
    handle_poll_category_select,
    handle_poll_cancel
)
from src.api.states.poll import PollStates


@pytest.fixture
def bot():
    """Mock bot instance."""
    bot = Bot(token="TEST_TOKEN")
    bot.session = AsyncMock()
    return bot


@pytest.fixture
async def fsm_context():
    """Provide FSM context with memory storage."""
    storage = MemoryStorage()
    context = FSMContext(
        storage=storage,
        key="test_user_123:test_chat_456"
    )
    yield context
    await context.clear()


@pytest.fixture
def callback_factory(bot):
    """Factory for creating mock CallbackQuery."""
    def _create(data: str, user_id: int = 123):
        user = types.User(id=user_id, is_bot=False, first_name="Test")
        chat = types.Chat(id=user_id, type="private")
        message = types.Message(
            message_id=1,
            date=1234567890,
            chat=chat,
            from_user=user,
            text="Test",
            bot=bot
        )
        callback = types.CallbackQuery(
            id="cb_123",
            from_user=user,
            message=message,
            data=data,
            chat_instance="test"
        )
        callback.answer = AsyncMock()
        callback.message.answer = AsyncMock()
        return callback
    return _create


class TestPollActivityFlow:
    """Test poll activity recording flow (TASK 1)."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handle_poll_activity_start_success(
        self,
        callback_factory,
        fsm_context,
        mocker
    ):
        """Test starting activity recording from poll."""
        # Mock services
        mock_user_service = mocker.patch(
            'src.api.handlers.poll.UserService'
        )
        mock_user_service.return_value.get_by_telegram_id = AsyncMock(
            return_value={"id": "user_123", "telegram_id": 123}
        )

        mock_category_service = mocker.patch(
            'src.api.handlers.poll.CategoryService'
        )
        mock_category_service.return_value.get_user_categories = AsyncMock(
            return_value=[
                {"id": 1, "name": "Work", "emoji": "💼"},
                {"id": 2, "name": "Sport", "emoji": "🏃"}
            ]
        )

        # Create callback
        callback = callback_factory("poll_activity")

        # Call handler
        await handle_poll_activity_start(callback, fsm_context)

        # Assertions
        assert await fsm_context.get_state() == PollStates.waiting_for_poll_category.state
        data = await fsm_context.get_data()
        assert data["user_id"] == "user_123"

        callback.message.answer.assert_called_once()
        call_text = callback.message.answer.call_args[0][0]
        assert "Чем ты занимался?" in call_text
        assert "Выбери категорию" in call_text

        callback.answer.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handle_poll_activity_start_no_categories(
        self,
        callback_factory,
        fsm_context,
        mocker
    ):
        """Test starting activity when user has no categories."""
        # Mock user exists but has no categories
        mocker.patch(
            'src.api.handlers.poll.UserService'
        ).return_value.get_by_telegram_id = AsyncMock(
            return_value={"id": "user_123"}
        )
        mocker.patch(
            'src.api.handlers.poll.CategoryService'
        ).return_value.get_user_categories = AsyncMock(
            return_value=[]
        )

        callback = callback_factory("poll_activity")

        await handle_poll_activity_start(callback, fsm_context)

        # Should show error and not set FSM state
        assert await fsm_context.get_state() is None
        call_text = callback.message.answer.call_args[0][0]
        assert "нет категорий" in call_text.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handle_poll_category_select_creates_activity(
        self,
        callback_factory,
        fsm_context,
        mocker
    ):
        """Test category selection creates activity with correct duration."""
        from datetime import datetime, timezone

        # Set up FSM state
        await fsm_context.set_state(PollStates.waiting_for_poll_category)

        # Mock services
        mocker.patch(
            'src.api.handlers.poll.UserService'
        ).return_value.get_by_telegram_id = AsyncMock(
            return_value={"id": "user_123", "timezone": "Europe/Moscow"}
        )

        mocker.patch(
            'src.api.handlers.poll.UserSettingsService'
        ).return_value.get_settings = AsyncMock(
            return_value={
                "poll_interval_weekday": 60,  # 1 hour
                "poll_interval_weekend": 120
            }
        )

        mock_activity_service = mocker.patch(
            'src.api.handlers.poll.ActivityService'
        )
        mock_activity_service.return_value.create_activity = AsyncMock()

        mock_scheduler = mocker.patch(
            'src.api.handlers.poll.scheduler_service'
        )
        mock_scheduler.schedule_poll = AsyncMock()

        # Create callback
        callback = callback_factory("poll_category_1")

        # Call handler
        await handle_poll_category_select(callback, fsm_context)

        # Verify activity created
        mock_activity_service.return_value.create_activity.assert_called_once()
        call_kwargs = mock_activity_service.return_value.create_activity.call_args[1]

        assert call_kwargs["category_id"] == 1
        assert call_kwargs["description"] == "Активность"

        # Verify duration is poll_interval (weekday = 60 min)
        start_time = call_kwargs["start_time"]
        end_time = call_kwargs["end_time"]
        duration = (end_time - start_time).total_seconds() / 60
        assert 59 <= duration <= 61  # Allow 1 min tolerance

        # Verify poll rescheduled
        mock_scheduler.schedule_poll.assert_called_once()

        # Verify FSM cleared
        assert await fsm_context.get_state() is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handle_poll_cancel(
        self,
        callback_factory,
        fsm_context
    ):
        """Test canceling poll activity recording."""
        # Set FSM state
        await fsm_context.set_state(PollStates.waiting_for_poll_category)

        callback = callback_factory("poll_cancel")

        await handle_poll_cancel(callback, fsm_context)

        # Verify FSM cleared
        assert await fsm_context.get_state() is None

        # Verify message
        call_text = callback.message.answer.call_args[0][0]
        assert "отменена" in call_text.lower()


# TODO: Add more tests for:
# - Weekend vs weekday interval calculation
# - Timezone handling
# - Error handling when API fails
# - Scheduler errors
```

**Coverage target:** 80%+

---

### 🧪 Раздел 3.2: Unit Tests для Settings Handlers (ЗАДАЧА 2)

**Test File:** `services/tracker_activity_bot/tests/unit/test_settings_custom_input.py`

```python
"""
Unit tests for settings custom input handlers.

Tests new functionality from TASK 2: custom time input for intervals.
"""
import pytest
from unittest.mock import AsyncMock
from aiogram import types, Bot
from aiogram.fsm.context import FSMContext

from src.api.handlers.settings import (
    show_weekday_custom_input,
    process_weekday_custom_input,
    show_weekend_custom_input,
    process_weekend_custom_input,
    process_reminder_delay_custom
)
from src.api.states.settings import SettingsStates


class TestCustomIntervalInput:
    """Test custom interval input for settings."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_weekday_custom_input_valid(self, message_factory, fsm_context, mocker):
        """Test valid weekday custom interval input."""
        # Mock services
        mocker.patch(
            'src.api.handlers.settings.UserService'
        ).return_value.get_by_telegram_id = AsyncMock(
            return_value={"id": "user_123", "timezone": "Europe/Moscow"}
        )

        mocker.patch(
            'src.api.handlers.settings.UserSettingsService'
        ).return_value.get_settings = AsyncMock(
            return_value={"id": "settings_123", "poll_interval_weekday": 120}
        )
        mocker.patch(
            'src.api.handlers.settings.UserSettingsService'
        ).return_value.update_settings = AsyncMock()

        mock_scheduler = mocker.patch('src.api.handlers.settings.scheduler_service')
        mock_scheduler.schedule_poll = AsyncMock()

        # Set FSM state
        await fsm_context.set_state(SettingsStates.waiting_for_weekday_interval_custom)

        # Create message with valid input
        message = message_factory("90")

        # Call handler
        await process_weekday_custom_input(message, fsm_context)

        # Verify settings updated
        # Verify scheduler called
        # Verify confirmation message
        assert await fsm_context.get_state() is None
        call_text = message.answer.call_args[0][0]
        assert "1ч 30м" in call_text

    @pytest.mark.unit
    @pytest.mark.parametrize("invalid_value,expected_error", [
        ("15", "от 30 до 480"),
        ("500", "от 30 до 480"),
        ("abc", "Неверный формат"),
        ("-10", "от 30 до 480"),
    ])
    async def test_weekday_custom_input_validation(
        self,
        message_factory,
        fsm_context,
        invalid_value,
        expected_error
    ):
        """Test validation of weekday custom input."""
        await fsm_context.set_state(SettingsStates.waiting_for_weekday_interval_custom)

        message = message_factory(invalid_value)

        await process_weekday_custom_input(message, fsm_context)

        # FSM should NOT be cleared (allow retry)
        assert await fsm_context.get_state() == SettingsStates.waiting_for_weekday_interval_custom.state

        # Error message shown
        call_text = message.answer.call_args[0][0]
        assert expected_error.lower() in call_text.lower()

    # TODO: Similar tests for weekend and reminder delay
```

**Coverage target:** 90%+

---

### 🧪 Раздел 3.3: Unit Tests для /cancel Handler (ЗАДАЧА 3)

**Test File:** `services/tracker_activity_bot/tests/unit/test_cancel_command.py`

```python
"""
Unit tests for /cancel command handlers.

Tests new functionality from TASK 3: /cancel support in all FSM states.
"""
import pytest
from src.api.handlers.settings import cancel_settings_fsm
from src.api.handlers.activity import cancel_activity_fsm
from src.api.handlers.categories import cancel_category_fsm


class TestCancelCommand:
    """Test /cancel command in different FSM states."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cancel_in_settings_fsm(self, message_factory, fsm_context):
        """Test /cancel clears settings FSM."""
        from src.api.states.settings import SettingsStates

        # Set active FSM state
        await fsm_context.set_state(SettingsStates.waiting_for_weekday_interval_custom)

        message = message_factory("/cancel")

        await cancel_settings_fsm(message, fsm_context)

        # FSM cleared
        assert await fsm_context.get_state() is None

        # Confirmation shown
        call_text = message.answer.call_args[0][0]
        assert "отменена" in call_text.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cancel_when_no_fsm(self, message_factory, fsm_context):
        """Test /cancel when FSM is not active."""
        # No FSM state
        assert await fsm_context.get_state() is None

        message = message_factory("/cancel")

        await cancel_settings_fsm(message, fsm_context)

        # Should show "nothing to cancel"
        call_text = message.answer.call_args[0][0]
        assert "нечего отменять" in call_text.lower()

    # TODO: Tests for cancel in activity and category FSM
```

---

### 🧪 Раздел 3.4: Integration Tests для Inline Keyboards

**Test File:** `services/tracker_activity_bot/tests/integration/test_category_inline_buttons.py`

```python
"""
Integration tests for category inline button selection.

Tests new functionality from TASK 8: inline buttons for category selection.
"""
import pytest
from src.api.keyboards.poll import get_poll_category_keyboard


class TestCategoryInlineButtons:
    """Test category selection with inline buttons."""

    @pytest.mark.integration
    def test_get_poll_category_keyboard_structure(self):
        """Test keyboard structure for category selection."""
        categories = [
            {"id": 1, "name": "Work", "emoji": "💼"},
            {"id": 2, "name": "Sport", "emoji": "🏃"},
            {"id": 3, "name": "Study", "emoji": "📚"},
        ]

        keyboard = get_poll_category_keyboard(categories)

        # Should have 2 rows (2 categories per row) + 1 cancel button row
        assert len(keyboard.inline_keyboard) == 2  # 2 categories rows + cancel

        # First row should have 2 buttons
        assert len(keyboard.inline_keyboard[0]) == 2

        # Check button data format
        first_button = keyboard.inline_keyboard[0][0]
        assert first_button.text == "💼 Work"
        assert first_button.callback_data == "poll_category_1"

        # Last row should have cancel button
        cancel_row = keyboard.inline_keyboard[-1]
        assert len(cancel_row) == 1
        assert cancel_row[0].text == "❌ Отменить"
        assert cancel_row[0].callback_data == "poll_cancel"

    # TODO: Test keyboard with 1, 5, 10 categories
    # TODO: Test keyboard with empty categories list
```

---

### 🧪 Раздел 3.5: Service Tests для API Endpoints

**Test File:** `services/data_postgres_api/tests/service/test_activity_endpoints.py`

```python
"""
Service tests for activity endpoints.

Tests full request/response cycle using TestClient.
"""
import pytest
from fastapi.testclient import TestClient
from src.main import app


@pytest.fixture
def test_client():
    """Provide TestClient."""
    return TestClient(app)


class TestActivityEndpoints:
    """Test activity API endpoints."""

    @pytest.mark.service
    def test_create_activity(self, test_client, mocker):
        """Test POST /api/v1/activities."""
        # Mock database session
        # Create test data
        # Send request
        # Verify response

        payload = {
            "user_id": "user_123",
            "category_id": 1,
            "description": "Test activity",
            "start_time": "2025-11-05T10:00:00Z",
            "end_time": "2025-11-05T11:00:00Z",
            "tags": []
        }

        response = test_client.post("/api/v1/activities", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["description"] == "Test activity"
        assert "id" in data

    @pytest.mark.service
    def test_get_user_activities(self, test_client):
        """Test GET /api/v1/activities."""
        response = test_client.get(
            "/api/v1/activities",
            params={"user_id": "user_123", "limit": 10}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 10

    # TODO: Test validation errors (422)
    # TODO: Test not found (404)
    # TODO: Test unauthorized access
```

---

## ЧАСТЬ 4: PERFORMANCE ТЕСТИРОВАНИЕ

### ⚡ Раздел 4.1: Response Time Tests

**Test Case TC-027: API Response Time**

```
Test: Measure response time for critical endpoints

Endpoints:
- POST /api/v1/activities
- GET /api/v1/activities?user_id=X&limit=10
- GET /api/v1/categories?user_id=X
- POST /api/v1/users

Method:
1. Use Apache Bench or similar tool
2. Send 100 requests
3. Measure P50, P95, P99

Expected Result:
✓ P50 < 200ms
✓ P95 < 500ms
✓ P99 < 1000ms

Pass/Fail: [ ]
Command: ab -n 100 -c 10 http://localhost:8080/health
```

---

### ⚡ Раздел 4.2: Load Tests

**Test Case TC-028: Concurrent Users**

```
Test: Simulate 10 concurrent users

Scenario:
1. 10 users simultaneously:
   - Register (/start)
   - Create category
   - Create activity
   - Receive poll

Method: Use locust or similar

Expected Result:
✓ All operations succeed
✓ No deadlocks
✓ No memory leaks
✓ Response time < 2s for 95%

Pass/Fail: [ ]
```

---

## ЧАСТЬ 5: COVERAGE REPORT

### 📊 Раздел 5.1: Coverage Targets

**Run coverage:**
```bash
# Bot service
cd services/tracker_activity_bot
pytest tests/ -v --cov=src --cov-report=html --cov-report=term

# API service
cd services/data_postgres_api
pytest tests/ -v --cov=src --cov-report=html --cov-report=term
```

**Targets:**

| Component | Current | Target | Priority |
|-----------|---------|--------|----------|
| **tracker_activity_bot** | ~5% | 80% | HIGH |
| - handlers/poll.py | 0% | 90% | CRITICAL |
| - handlers/settings.py | 0% | 85% | HIGH |
| - handlers/activity.py | 0% | 85% | HIGH |
| - keyboards/* | 0% | 70% | MEDIUM |
| - states/* | 100% | 100% | ✓ |
| **data_postgres_api** | ~20% | 80% | HIGH |
| - api/v1/activities.py | 0% | 90% | CRITICAL |
| - api/v1/users.py | 0% | 90% | CRITICAL |
| - repositories/* | 0% | 85% | HIGH |

---

## КОНТРОЛЬНЫЙ СПИСОК ВЫПОЛНЕНИЯ

### ✅ Manual E2E Tests

- [ ] TC-001: Регистрация
- [ ] TC-002: Запись активности с inline кнопками
- [ ] TC-003: Отмена выбора категории
- [ ] TC-004: Пропуск категории через "0"
- [ ] TC-005: Текстовый ввод времени + keyboard
- [ ] TC-006: Создание категории
- [ ] TC-007: Удаление категории
- [ ] TC-008: Опрос "Занимался чем-то"
- [ ] TC-009: Опрос "Спал" (с правильной duration)
- [ ] TC-010: Откладывание опроса при FSM конфликте
- [ ] TC-011: Напоминание
- [ ] TC-012: Кастомный ввод будних дней
- [ ] TC-013: Кастомный ввод выходных
- [ ] TC-014: Кастомный ввод задержки напоминаний
- [ ] TC-015: Валидация кастомного ввода
- [ ] TC-016: Тихие часы (клавиатура без пустых списков)
- [ ] TC-017: Напоминания (клавиатура)
- [ ] TC-018: /cancel в активности
- [ ] TC-019: /cancel в категории
- [ ] TC-020: /cancel в настройках
- [ ] TC-021: /cancel без FSM
- [ ] TC-022: Индикатор "печатает..."
- [ ] TC-023: Просмотр активностей

### ✅ Regression Tests

- [ ] TC-024: Smoke tests (контейнеры)
- [ ] TC-025: Health endpoint
- [ ] TC-026: Полный цикл

### ✅ Automated Tests

- [ ] test_poll_handlers.py (ЗАДАЧА 1)
- [ ] test_settings_custom_input.py (ЗАДАЧА 2)
- [ ] test_cancel_command.py (ЗАДАЧА 3)
- [ ] test_category_inline_buttons.py (ЗАДАЧА 8)
- [ ] test_activity_endpoints.py (API)
- [ ] test_user_endpoints.py (API)
- [ ] test_category_endpoints.py (API)

### ✅ Performance Tests

- [ ] TC-027: Response time
- [ ] TC-028: Concurrent users

### ✅ Coverage

- [ ] tracker_activity_bot: 80%+
- [ ] data_postgres_api: 80%+
- [ ] HTML reports generated
- [ ] Critical paths: 100%

---

## ОТЧЕТНОСТЬ

### Формат отчета:

```markdown
# Test Execution Report
**Date:** YYYY-MM-DD
**Executed by:** Name
**Build:** #version

## Summary
- Total tests: XX
- Passed: XX
- Failed: XX
- Blocked: XX
- Coverage: XX%

## Failed Tests
| TC ID | Name | Reason | Severity |
|-------|------|--------|----------|
| TC-XXX | ... | ... | Critical |

## Coverage Report
[Link to htmlcov/index.html]

## Recommendations
- ...
```

---

## КРИТЕРИИ ГОТОВНОСТИ К PRODUCTION

**Все должно быть ✅:**

- [ ] All critical TC (TC-001 to TC-021) passed
- [ ] Zero critical bugs
- [ ] Coverage ≥ 80%
- [ ] Performance: P95 < 1s
- [ ] Load test: 10 concurrent users OK
- [ ] Docker health checks: all healthy
- [ ] No memory leaks
- [ ] Logs clean (no ERROR level in normal flow)

---

## ИНСТРУМЕНТЫ

### Testing Tools:
```bash
# Unit/Service tests
pytest

# Coverage
pytest-cov

# API testing
httpx, requests

# Load testing
locust, ab (Apache Bench)

# Mocking
pytest-mock, unittest.mock
```

### Monitoring:
```bash
# Docker stats
docker compose ps
docker compose logs -f

# DB queries
docker exec -it tracker_db psql -U tracker_user -d tracker_db

# Redis
docker exec -it tracker_redis redis-cli
```

---

## ПРИЛОЖЕНИЯ

### Приложение A: Test Data

**Test Users:**
```json
{
  "telegram_id": 123456789,
  "name": "Test User",
  "timezone": "Europe/Moscow"
}
```

**Test Categories:**
```json
[
  {"name": "Work", "emoji": "💼"},
  {"name": "Sport", "emoji": "🏃"},
  {"name": "Study", "emoji": "📚"}
]
```

### Приложение B: Useful Commands

```bash
# Reset test database
docker compose down -v
docker compose up -d

# Clear Redis (FSM states)
docker exec -it tracker_redis redis-cli FLUSHALL

# View logs
docker compose logs -f tracker_activity_bot | grep ERROR

# Run specific test
pytest tests/unit/test_poll_handlers.py::TestPollActivityFlow::test_handle_poll_activity_start_success -v

# Coverage report
pytest --cov=src --cov-report=html
open htmlcov/index.html
```

---

**Конец плана тестирования v1.0**
