# Requirements Intake - Activity Tracker Bot (Step 01)

> **Дата**: 2025-10-30
> **Версия промпта**: step-01-v01.md
> **Maturity Level**: Level 1 (PoC - Proof of Concept)
> **Расчётное время**: ~5-7 минут
> **Статус**: Анализ существующей реализации

---

## 📋 Executive Summary

**Бизнес-цель**: Создать MVP Telegram-бота для отслеживания личной активности пользователей в течение дня.

**Target аудитория**: Solo разработчик, валидация идеи

**Ключевые возможности**:
- ✅ Регистрация через Telegram бот
- ✅ Запись активностей с временными метками
- ✅ Управление категориями активностей
- ✅ Просмотр истории записей
- ✅ Гибкий парсинг времени (14:30, 30м, 2ч)

---

## 🎯 Functional Requirements

### REQ-F-001: User Registration & Onboarding

**Priority**: MUST HAVE
**ID**: REQ-F-001

**Description**: Пользователь регистрируется через команду `/start` в Telegram боте.

**Acceptance Criteria**:
- ✅ При первом запуске создаётся пользователь в БД
- ✅ Автоматически создаются 6 базовых категорий:
  - 💼 Работа
  - 🏃 Спорт
  - 🎮 Отдых
  - 📚 Обучение
  - 😴 Сон
  - 🍽️ Еда
- ✅ При повторном запуске показывается главное меню (без регистрации)
- ✅ Данные пользователя: telegram_id, username, first_name, timezone (default: Europe/Moscow)

**HTTP API Dependencies**:
- `GET /api/v1/users/by-telegram/{telegram_id}` — проверка существования
- `POST /api/v1/users` — создание пользователя
- `POST /api/v1/categories/bulk-create` — создание базовых категорий

---

### REQ-F-002: Activity Recording (FSM Workflow)

**Priority**: MUST HAVE
**ID**: REQ-F-002

**Description**: Пользователь записывает активность через многошаговый диалог (5 шагов FSM).

**FSM States**:
1. `waiting_for_start_time` — ввод времени начала
2. `waiting_for_end_time` — ввод времени окончания
3. `waiting_for_description` — ввод описания
4. `waiting_for_category` — выбор категории

**Step 1: Start Time**
**Input Formats**:
- Точное время: `14:30`, `14-30` → сегодня 14:30 (в timezone пользователя)
- Минуты назад: `30м`, `30` → текущее время минус 30 минут
- Часы назад: `2ч`, `2h` → текущее время минус 2 часа

**Validation**:
- ❌ Время НЕ должно быть в будущем
- ❌ Время НЕ должно быть раньше чем 24 часа назад

**Quick buttons**: `[30м назад]` `[1ч назад]` `[2ч назад]` `[❌ Отменить]`

**Step 2: End Time**
**Input Formats**:
- Точное время: `16:00`, `16-00` → сегодня 16:00
- Продолжительность: `30м` → **start_time + 30 минут**
- Сейчас: `сейчас`, `now`, `0` → текущее время

**Validation**:
- ✅ `end_time > start_time`
- ❌ `end_time` НЕ должно быть в будущем

**Quick buttons**: `[Сейчас]` `[30м длилось]` `[1ч длилось]` `[2ч длилось]` `[❌ Отменить]`

**Step 3: Description**
**Input**: Текстовое описание активности

**Tag Extraction**: Извлечение тегов из текста (всё после `#`)
**Example**: `Работал над отчётом #проект_X #срочно` → `tags: ["проект_X", "срочно"]`

**Validation**:
- Минимум 3 символа

**Step 4: Category Selection**
**Input**: Выбор категории из inline-кнопок (2 колонки)

**Options**:
- Все категории пользователя (из `GET /api/v1/categories?user_id={user_id}`)
- Кнопка `[➖ Без категории]` → `category_id = null`

**Step 5: Save & Confirmation**
**Action**: Отправка HTTP запроса к data API

**API Call**: `POST /api/v1/activities`
**Payload**:
```json
{
  "user_id": 1,
  "category_id": 1,
  "description": "Работал над отчётом для клиента",
  "tags": ["проект_X", "срочно"],
  "start_time": "2025-10-29T14:30:00Z",  // UTC
  "end_time": "2025-10-29T16:00:00Z"      // UTC
}
```

**Important**:
- ✅ Все даты отправляются в **UTC** (конвертация из user timezone)
- ✅ `duration_minutes` вычисляется на сервере автоматически
- ✅ FSM state очищается после успешного сохранения

**Confirmation Message**:
```
✅ Активность записана!

💼 Работа
Работал над отчётом для клиента
🏷 #проект_X #срочно

⏰ 14:30 — 16:00
⏱ Продолжительность: 1ч 30м

[➕ Добавить ещё активность]
[📋 Показать мои записи]
[🏠 Главное меню]
```

**HTTP API Dependencies**:
- `GET /api/v1/categories?user_id={user_id}` — получить категории для выбора
- `POST /api/v1/activities` — сохранить активность

---

### REQ-F-003: Category Management

**Priority**: MUST HAVE
**ID**: REQ-F-003

#### REQ-F-003.1: List Categories

**Description**: Просмотр списка всех категорий пользователя

**Trigger**: Кнопка `📂 Категории`

**API Call**: `GET /api/v1/categories?user_id={user_id}`

**Display Format**:
```
📂 Твои категории активностей:

💼 Работа
🏃 Спорт
🎮 Отдых
📚 Обучение
😴 Сон
🍽️ Еда
🎨 Хобби

[➕ Добавить категорию]
[❌ Удалить категорию]
[🏠 Главное меню]
```

#### REQ-F-003.2: Add Category (FSM)

**FSM States**:
- `waiting_for_name` — ввод названия
- `waiting_for_emoji` — выбор эмодзи

**Step 1: Category Name**
**Validation**:
- Минимум 2 символа
- Максимум 50 символов

**Step 2: Category Emoji**
**Options**:
- Inline-кнопки с популярными эмодзи (4 колонки)
- Или ввод любого эмодзи текстом
- Кнопка `[➖ Без эмодзи]` → `emoji = null`

**API Call**: `POST /api/v1/categories`
**Payload**:
```json
{
  "user_id": 1,
  "name": "Хобби",
  "emoji": "🎨",
  "is_default": false
}
```

**Error Handling**:
- `409 Conflict` → Категория с таким именем уже существует
- Показать сообщение: "⚠️ Категория с названием 'Хобби' уже существует. Введи другое название."

#### REQ-F-003.3: Delete Category

**Step 1**: Показать список с inline-кнопками
**Callback data**: `delete_category:{category_id}`

**Step 2**: Подтверждение удаления
```
⚠️ Ты уверен, что хочешь удалить категорию "🎨 Хобби"?

Все активности с этой категорией останутся, но без категории.

[✅ Да, удалить]
[❌ Нет, отменить]
```

**API Call**: `DELETE /api/v1/categories/{category_id}`

**Error Handling**:
- `400 Bad Request` → Попытка удалить последнюю категорию
- Показать сообщение: "⚠️ Нельзя удалить последнюю категорию. Должна остаться хотя бы одна."

**HTTP API Dependencies**:
- `GET /api/v1/categories?user_id={user_id}` — список категорий
- `POST /api/v1/categories` — создать категорию
- `DELETE /api/v1/categories/{category_id}` — удалить категорию

---

### REQ-F-004: Activity List View

**Priority**: MUST HAVE
**ID**: REQ-F-004

**Description**: Просмотр последних 10 активностей, сгруппированных по датам

**Trigger**: Кнопка `📋 Мои записи`

**API Call**: `GET /api/v1/activities?user_id={user_id}&limit=10&offset=0`

**Display Format** (группировка по датам):
```
📋 Твои последние активности:

━━━━━━━━━━━━━━━━━━
📅 29 октября 2025
━━━━━━━━━━━━━━━━━━

💼 Работа | 14:30 — 16:00 (1ч 30м)
Работал над отчётом для клиента
🏷 #проект_X #срочно

🍽️ Еда | 13:00 — 13:30 (30м)
Обед в кафе
🏷 #обед

━━━━━━━━━━━━━━━━━━
📅 28 октября 2025
━━━━━━━━━━━━━━━━━━

🏃 Спорт | 19:00 — 20:00 (1ч)
Пробежка в парке

[➕ Добавить активность]
[🔄 Обновить список]
[🏠 Главное меню]
```

**Important**:
- ✅ Даты/время конвертируются из UTC в timezone пользователя
- ✅ Группировка по датам (в локальном времени)
- ✅ Максимум 10 записей
- ✅ Сортировка: от новых к старым (`start_time DESC`)

**Empty State**:
```
📋 У тебя пока нет записанных активностей.

Начни отслеживать свою активность!

[➕ Записать первую активность]
[🏠 Главное меню]
```

**HTTP API Dependencies**:
- `GET /api/v1/activities?user_id={user_id}&limit=10&offset=0`

---

### REQ-F-005: Help & Documentation

**Priority**: SHOULD HAVE
**ID**: REQ-F-005

**Description**: Справка по использованию бота

**Trigger**: Кнопка `❓ Справка`

**Display**:
```
📖 Как пользоваться ботом:

📝 Записать активность
Добавь новую активность с точным временем и описанием

📋 Мои записи
Посмотри последние 10 записанных активностей

📂 Категории
Управляй своими категориями: добавляй или удаляй

💡 Про теги:
В описании активности можно использовать теги через #
Например: "Работал над проектом #важное #дедлайн"

⏰ Форматы времени:
• 14:30 — точное время
• 30м — 30 минут назад
• 2ч — 2 часа назад
• сейчас — прямо сейчас

[🏠 Главное меню]
```

---

## 🏗️ Technical Requirements

### REQ-T-001: Service Architecture

**Priority**: MUST HAVE
**ID**: REQ-T-001

**Architectural Principle**: **Improved Hybrid Approach** (согласно `.framework/docs/atomic/architecture/improved-hybrid-overview.md`)

**Services**:

#### 1. `tracker_activity_bot` (Aiogram Business Service)
- **Type**: Business service (Telegram bot)
- **Technology**: Aiogram 3.x, Python 3.11+
- **Container**: Docker
- **Data Access**: **ТОЛЬКО через HTTP** к `data_postgres_api`
- **FSM Storage**: Redis
- **Naming**: 3-part convention `{context}_{domain}_{type}` → `tracker_activity_bot`

**CRITICAL CONSTRAINTS**:
- ❌ **НЕ может напрямую обращаться к PostgreSQL**
- ✅ **Все запросы к БД через HTTP API**
- ✅ Использует FSM (Finite State Machine) для многошаговых диалогов

#### 2. `data_postgres_api` (FastAPI Data Service)
- **Type**: Data service (HTTP API для PostgreSQL)
- **Technology**: FastAPI, SQLAlchemy 2.0 async, Python 3.11+
- **Container**: Docker
- **Endpoints**: REST API для CRUD над users, categories, activities
- **Naming**: 3-part convention → `data_postgres_api`

**CRITICAL CONSTRAINTS**:
- ✅ Единственный сервис с прямым доступом к PostgreSQL
- ✅ Предоставляет HTTP endpoints для всех операций с данными
- ✅ Repository Pattern (изоляция БД логики)

#### 3. PostgreSQL 15+ (Database)
- **Access**: ТОЛЬКО для `data_postgres_api`
- **Container**: `postgres:15-alpine`

#### 4. Redis 7+ (FSM Storage)
- **Access**: ТОЛЬКО для `tracker_activity_bot`
- **Container**: `redis:7-alpine`

**Source**: `.framework/docs/atomic/architecture/service-separation-principles.md`

---

### REQ-T-002: DDD/Hexagonal Architecture (MANDATORY)

**Priority**: MUST HAVE
**ID**: REQ-T-002

**Requirement**: Оба сервиса ДОЛЖНЫ использовать **обязательную `src/` директорию** с DDD/Hexagonal структурой.

**Согласно**: `.framework/docs/atomic/architecture/project-structure-patterns.md` (Level 1 requirement)

#### Structure: `tracker_activity_bot/`
```
services/tracker_activity_bot/
├── src/                             # ⚠️ ОБЯЗАТЕЛЬНАЯ src/ директория
│   ├── api/                         # Transport adapters (handlers, keyboards, states)
│   ├── application/                 # Use cases, orchestrators
│   ├── domain/                      # Entities, value objects
│   ├── infrastructure/              # External adapters
│   │   └── http_clients/            # HTTP clients для data API
│   ├── schemas/                     # Pydantic DTOs
│   └── core/                        # Config, logging
│       ├── config.py
│       └── logging.py               # ⚠️ ОБЯЗАТЕЛЬНО для Level 1
├── main.py
├── requirements.txt
└── Dockerfile
```

#### Structure: `data_postgres_api/`
```
services/data_postgres_api/
├── src/                             # ⚠️ ОБЯЗАТЕЛЬНАЯ src/ директория
│   ├── api/v1/                      # HTTP routers (users, categories, activities)
│   ├── models/                      # SQLAlchemy models
│   ├── repositories/                # Repository Pattern
│   ├── schemas/                     # Pydantic schemas (DTOs)
│   └── core/                        # Config, database, logging
│       ├── config.py
│       ├── database.py
│       └── logging.py               # ⚠️ ОБЯЗАТЕЛЬНО для Level 1
├── main.py
├── requirements.txt
└── Dockerfile
```

**Rationale**: Подготовка к эволюции без рефакторинга при переходе на Level 2/3/4.

---

### REQ-T-003: Structured JSON Logging (MANDATORY)

**Priority**: MUST HAVE
**ID**: REQ-T-003

**Requirement**: Все сервисы ДОЛЖНЫ использовать **structured JSON logging** через `python-json-logger`.

**Согласно**: `.framework/docs/reference/maturity-levels.md` (Level 1, строки 48-52)

**Implementation**:

**File**: `src/core/logging.py` (для ОБОИХ сервисов)

```python
"""Structured JSON logging setup."""
import logging
import sys
from pythonjsonlogger import jsonlogger


def setup_logging(service_name: str, log_level: str = "INFO"):
    """Setup structured JSON logging for the service."""
    logger = logging.getLogger()
    logger.setLevel(log_level)
    logger.handlers = []

    handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(name)s %(levelname)s %(message)s",
        rename_fields={"asctime": "timestamp", "name": "logger"},
        static_fields={"service": service_name}
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    logger.info(f"Structured JSON logging initialized for {service_name}")
```

**Usage in `main.py`**:
```python
from src.core.logging import setup_logging

# Initialize ПЕРВЫМ делом
setup_logging(service_name="tracker_activity_bot", log_level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

logger.info("Bot started", extra={"telegram_id": bot_id})
```

**Output Example** (JSON to stdout):
```json
{"timestamp": "2025-10-30T12:00:00Z", "logger": "main", "levelname": "INFO", "message": "Bot started", "service": "tracker_activity_bot", "telegram_id": 123456789}
```

**Dependencies** (добавить в requirements.txt):
```
python-json-logger==2.0.7
```

**Why Mandatory for Level 1?**
1. JSON легко парсится log aggregators (даже без ELK на PoC)
2. Structured data: `extra={}` добавляет поля автоматически
3. Production-ready: Console logs НЕ подходят для production

**NOT Required for Level 1**:
- ❌ Request ID tracking (добавится в Level 2)

---

### REQ-T-004: HTTP-Only Data Access

**Priority**: MUST HAVE
**ID**: REQ-T-004

**Requirement**: Business service (`tracker_activity_bot`) НЕ может напрямую обращаться к PostgreSQL. Все операции с данными ТОЛЬКО через HTTP API (`data_postgres_api`).

**Согласно**: `.framework/docs/atomic/architecture/data-access-architecture.md`

**Implementation**: HTTP clients в `tracker_activity_bot/src/infrastructure/http_clients/`

**Files**:
- `data_api_client.py` — Base async HTTP client (httpx)
- `user_client.py` — Users API calls
- `category_client.py` — Categories API calls
- `activity_client.py` — Activities API calls

**Example**:
```python
# Base client
class DataAPIClient:
    def __init__(self):
        self.base_url = settings.DATA_API_URL  # http://data_postgres_api:8000
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=10.0)

    async def get(self, path: str, **kwargs):
        response = await self.client.get(path, **kwargs)
        response.raise_for_status()
        return response.json()
```

**Validation**:
- ❌ НЕ должно быть прямых импортов PostgreSQL драйверов в `tracker_activity_bot`
- ❌ НЕ должно быть `DATABASE_URL` в environment variables бота
- ✅ Только `DATA_API_URL` для HTTP общения

---

### REQ-T-005: Database Schema

**Priority**: MUST HAVE
**ID**: REQ-T-005

**Database**: PostgreSQL 15+

**Tables**:

#### Table: `users`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | SERIAL | PRIMARY KEY | Auto-increment ID |
| `telegram_id` | BIGINT | NOT NULL, UNIQUE | Telegram user ID |
| `username` | VARCHAR(255) | NULLABLE | @username |
| `first_name` | VARCHAR(255) | NULLABLE | Имя из Telegram |
| `timezone` | VARCHAR(50) | NOT NULL, DEFAULT 'Europe/Moscow' | Часовой пояс |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Дата регистрации |

**Indexes**:
- `UNIQUE INDEX idx_users_telegram_id ON users(telegram_id)`

#### Table: `categories`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | SERIAL | PRIMARY KEY | Auto-increment ID |
| `user_id` | INTEGER | NOT NULL, FK → users(id) | Владелец категории |
| `name` | VARCHAR(100) | NOT NULL | Название категории |
| `emoji` | VARCHAR(10) | NULLABLE | Эмодзи (1-2 символа) |
| `is_default` | BOOLEAN | NOT NULL, DEFAULT FALSE | Базовая категория |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Дата создания |

**Indexes**:
- `INDEX idx_categories_user_id ON categories(user_id)`
- `UNIQUE INDEX idx_categories_user_name ON categories(user_id, name)`

**Constraints**:
- `FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE`

#### Table: `activities`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | SERIAL | PRIMARY KEY | Auto-increment ID |
| `user_id` | INTEGER | NOT NULL, FK → users(id) | Владелец активности |
| `category_id` | INTEGER | NULLABLE, FK → categories(id) | Категория |
| `description` | TEXT | NOT NULL | Описание |
| `tags` | TEXT | NULLABLE | Теги (JSON array или строка) |
| `start_time` | TIMESTAMP | NOT NULL | Начало (UTC) |
| `end_time` | TIMESTAMP | NOT NULL | Окончание (UTC) |
| `duration_minutes` | INTEGER | NOT NULL | Продолжительность |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Дата создания |

**Indexes**:
- `INDEX idx_activities_user_id ON activities(user_id)`
- `INDEX idx_activities_user_start_time ON activities(user_id, start_time DESC)`

**Constraints**:
- `FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE`
- `FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL`
- `CHECK (end_time > start_time)`

---

### REQ-T-006: Timezone Management

**Priority**: MUST HAVE
**ID**: REQ-T-006

**Requirement**: Корректная работа с временными зонами

**Rules**:
1. **В БД**: Всё хранится в **UTC** (TIMESTAMP)
2. **От пользователя** (ввод): Считаем время в **его timezone** (default: `Europe/Moscow`)
3. **Для пользователя** (вывод): Конвертируем UTC → его timezone

**Implementation**: Utility функция `parse_user_time()` в `src/application/utils/time_parser.py`

**Example**:
```python
import pytz
from datetime import datetime

def parse_user_time(time_str: str, user_timezone: str = "Europe/Moscow") -> datetime:
    """Парсит время от пользователя и возвращает datetime в UTC."""
    tz = pytz.timezone(user_timezone)

    # Парсинг: "14:30", "30м", "2ч"
    local_dt = ...  # parsed datetime в user timezone

    # Возвращаем в UTC
    return local_dt.astimezone(pytz.UTC)
```

**Dependencies**:
```
pytz>=2024.1
```

---

### REQ-T-007: FSM Storage (Redis)

**Priority**: MUST HAVE
**ID**: REQ-T-007

**Requirement**: Aiogram FSM использует Redis для хранения состояний диалогов

**Configuration** (в `tracker_activity_bot/main.py`):
```python
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage

storage = RedisStorage.from_url(settings.REDIS_URL)  # redis://redis:6379/0
dp = Dispatcher(storage=storage)
```

**FSM Data Format**:
```python
await state.update_data(
    start_time=start_time_utc,
    end_time=end_time_utc,
    description="...",
    tags=["tag1", "tag2"],
    category_id=1
)
```

**Environment Variable**:
```
REDIS_URL=redis://redis:6379/0
```

---

### REQ-T-008: Docker Compose Setup

**Priority**: MUST HAVE
**ID**: REQ-T-008

**Requirement**: Local development через Docker Compose (PoC Level)

**Services**:
- `postgres` — PostgreSQL 15-alpine
- `redis` — Redis 7-alpine
- `data_postgres_api` — FastAPI service
- `tracker_activity_bot` — Aiogram bot

**Key Points**:
- ✅ Health checks для PostgreSQL и Redis
- ✅ `depends_on` с `condition: service_healthy`
- ✅ Volumes для PostgreSQL data persistence
- ✅ Environment variables из `.env` file

**File**: `docker-compose.yml`

---

## 📊 HTTP API Specification

### Base URL
```
http://data_postgres_api:8000/api/v1
```

### Endpoints

#### Users API
- `POST /api/v1/users` — создать пользователя
- `GET /api/v1/users/by-telegram/{telegram_id}` — получить по Telegram ID

#### Categories API
- `POST /api/v1/categories` — создать категорию
- `POST /api/v1/categories/bulk-create` — создать несколько категорий
- `GET /api/v1/categories?user_id={user_id}` — список категорий
- `DELETE /api/v1/categories/{category_id}` — удалить категорию

#### Activities API
- `POST /api/v1/activities` — создать активность
- `GET /api/v1/activities?user_id={user_id}&limit={limit}&offset={offset}` — список активностей

**См. полную спецификацию**: `artifacts/prompts/step-01-v01.md`, строки 256-508

---

## ✅ Quality Gates (Level 1 - PoC)

### Linting (Ruff)
```bash
ruff check services/tracker_activity_bot
ruff check services/data_postgres_api
```

### Type Checking (Mypy)
```bash
mypy services/tracker_activity_bot --strict
mypy services/data_postgres_api --strict
```

### Unit Tests (Pytest)
```bash
pytest services/tracker_activity_bot/tests --cov=src --cov-report=term-missing
pytest services/data_postgres_api/tests --cov=src --cov-report=term-missing
```

**Coverage target**: ≥ 60% (допустимо для PoC)

### Deployment Validation
- ✅ `docker-compose up -d` запускает все сервисы
- ✅ Health checks проходят
- ✅ Бот отвечает на `/start`
- ✅ Можно записать активность и увидеть её в списке

---

## 🚫 Out of Scope (для Step 01)

**NOT included в Level 1 PoC**:
- ❌ Редактирование активностей (будет в Step 2)
- ❌ Удаление активностей (будет в Step 2)
- ❌ Статистика и аналитика (будет в Step 3)
- ❌ Экспорт данных (CSV, JSON) (будет в Step 3)
- ❌ Визуализация (графики) (будет в Step 4)
- ❌ Request ID tracking (Level 2+)
- ❌ Health endpoints `/health`, `/ready` (Level 2+)
- ❌ Prometheus/Grafana (Level 3+)
- ❌ Nginx API Gateway (Level 3+)
- ❌ SSL/TLS (Level 3+)
- ❌ OAuth/JWT (Level 4)

---

## 📎 References

**Framework Documentation**:
- `.framework/docs/guides/architecture-guide.md` — Архитектурные принципы
- `.framework/docs/atomic/architecture/improved-hybrid-overview.md` — Improved Hybrid Approach
- `.framework/docs/atomic/architecture/data-access-architecture.md` — HTTP-only data access
- `.framework/docs/atomic/architecture/service-separation-principles.md` — Сервисная сепарация
- `.framework/docs/atomic/architecture/naming/README.md` — Naming conventions
- `.framework/docs/reference/maturity-levels.md` — 4 уровня зрелости

**Source Prompt**:
- `artifacts/prompts/step-01-v01.md` — Полный промпт для Step 01

---

**Статус**: ✅ Готово для Stage 3 (Architecture Planning)
