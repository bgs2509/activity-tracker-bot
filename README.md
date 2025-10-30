# Activity Tracker Bot

Telegram bot for personal activity tracking with microservices architecture.

## 🎯 Overview

This project implements a **Proof of Concept (Level 1)** Telegram bot for tracking daily activities using the **Improved Hybrid Approach** architecture.

### Architecture

```
┌──────────────────┐       HTTP REST API        ┌──────────────────┐
│                  │  ────────────────────────►  │                  │
│  tracker_        │   GET /api/v1/users          │  data_          │
│  activity_       │   POST /api/v1/activities    │  postgres_      │
│  bot             │   GET /api/v1/categories     │  api            │
│                  │  ◄──────────────────────────  │                  │
│  (Aiogram)       │       JSON responses         │  (FastAPI)      │
└──────────────────┘                              └──────────────────┘
       │                                                  │
       │ FSM Storage                                      │ SQL Queries
       ▼                                                  ▼
┌──────────────────┐                              ┌──────────────────┐
│     Redis        │                              │   PostgreSQL     │
└──────────────────┘                              └──────────────────┘
```

### Key Principles

- ✅ **HTTP-only data access** - Bot communicates with database ONLY through REST API
- ✅ **Service separation** - Each service in separate Docker container
- ✅ **3-part naming** - `tracker_activity_bot`, `data_postgres_api`
- ✅ **Maturity Level 1 (PoC)** - ~5-7 minutes to deploy

## 🚀 Quick Start

### Prerequisites

- Docker 24.0+
- Docker Compose 2.20+
- Telegram Bot Token (get from [@BotFather](https://t.me/botfather))

### Installation

1. **Clone repository**:
   ```bash
   git clone --recurse-submodules <repository-url>
   cd activity-tracker-bot
   ```

2. **Initialize environment**:
   ```bash
   make init
   ```

3. **Edit `.env` file** and add your Telegram bot token:
   ```bash
   nano .env
   # Set TELEGRAM_BOT_TOKEN=your_actual_token_here
   ```

4. **Build and start services**:
   ```bash
   make build
   make up
   ```

5. **Check logs**:
   ```bash
   make logs
   ```

6. **Start using bot**:
   - Open Telegram
   - Send `/start` to your bot
   - Follow inline keyboard instructions

## 📁 Project Structure

```
activity-tracker-bot/
├── .framework/                        # Framework submodule (read-only)
│   └── docs/                          # Framework documentation
│
├── services/
│   ├── data_postgres_api/             # FastAPI data service
│   │   ├── routers/                   # API endpoints
│   │   ├── models/                    # SQLAlchemy models
│   │   ├── repositories/              # Repository pattern
│   │   ├── schemas/                   # Pydantic DTOs
│   │   ├── database/                  # DB connection
│   │   └── main.py                    # Entry point
│   │
│   └── tracker_activity_bot/          # Aiogram bot service
│       ├── handlers/                  # Message handlers
│       ├── keyboards/                 # Inline keyboards
│       ├── states/                    # FSM states
│       ├── services/                  # HTTP clients
│       ├── utils/                     # Utilities
│       └── main.py                    # Entry point
│
├── docker-compose.yml                 # Docker configuration
├── .env.example                       # Environment template
├── Makefile                           # Development commands
└── README.md                          # This file
```

## 🛠️ Development Commands

```bash
# Start services
make up

# View logs
make logs              # All services
make logs-bot          # Bot only
make logs-api          # API only

# Restart services
make restart           # All services
make restart-bot       # Bot only
make restart-api       # API only

# Stop services
make down

# Clean up (remove volumes)
make clean

# Open shells
make shell-bot         # Bot container
make shell-api         # API container
make shell-db          # PostgreSQL shell

# Code quality
make lint              # Run Ruff linting
make format            # Format code
```

## 📋 Features

### Current (PoC Level 1)

- ✅ User registration via `/start`
- ✅ 6 default categories auto-created
- ✅ Activity recording with FSM (multi-step dialog)
- ✅ Time parsing (14:30, 30м, 2ч, сейчас)
- ✅ Inline keyboards for all actions
- ✅ HTTP-only data access
- ✅ Docker Compose deployment

### Planned (Future Levels)

- ⏳ **Level 2** (Development): Structured logging, health checks, integration tests
- ⏳ **Level 3** (Pre-Production): Nginx, SSL/TLS, Prometheus metrics
- ⏳ **Level 4** (Production): OAuth, RBAC, ELK stack, CI/CD

## 🔌 API Endpoints

### Users API

- `POST /api/v1/users` - Create user
- `GET /api/v1/users/by-telegram/{id}` - Get user by Telegram ID

### Categories API

- `POST /api/v1/categories` - Create category
- `POST /api/v1/categories/bulk-create` - Create multiple categories
- `GET /api/v1/categories?user_id={id}` - Get user categories
- `DELETE /api/v1/categories/{id}` - Delete category

### Activities API

- `POST /api/v1/activities` - Create activity
- `GET /api/v1/activities?user_id={id}&limit={n}` - Get user activities

**API Documentation**: http://localhost:8000/docs (Swagger UI)

## 🗄️ Database Schema

### Users Table
- id, telegram_id (unique), username, first_name, timezone, created_at

### Categories Table
- id, user_id, name, emoji, is_default, created_at
- **Unique constraint**: (user_id, name)

### Activities Table
- id, user_id, category_id, description, tags, start_time, end_time, duration_minutes, created_at
- **Check constraint**: end_time > start_time

## 🔐 Environment Variables

See `.env.example` for all available variables:

- `TELEGRAM_BOT_TOKEN` - **Required**: Your Telegram bot token
- `POSTGRES_USER` - PostgreSQL username
- `POSTGRES_PASSWORD` - PostgreSQL password
- `POSTGRES_DB` - Database name
- `LOG_LEVEL` - Logging level (default: INFO)

## 🧪 Testing

```bash
# Unit tests (when implemented)
cd services/data_postgres_api && pytest
cd services/tracker_activity_bot && pytest

# Integration tests
# 1. Start services: make up
# 2. Send /start to bot
# 3. Test activity recording flow
```

## 📚 Documentation

- **Framework docs**: `.framework/docs/INDEX.md`
- **Prompt**: `artifacts/prompts/step-01-v01.md`
- **Architecture guide**: `.framework/docs/guides/architecture-guide.md`
- **Naming conventions**: `.framework/docs/atomic/architecture/naming/README.md`

## 🐛 Troubleshooting

### Bot not responding

```bash
# Check bot logs
make logs-bot

# Check bot token in .env
cat .env | grep TELEGRAM_BOT_TOKEN

# Restart bot
make restart-bot
```

### API errors

```bash
# Check API logs
make logs-api

# Check database connection
make shell-db

# Restart API
make restart-api
```

### Database connection issues

```bash
# Check PostgreSQL is running
make ps

# Check database logs
docker-compose logs postgres

# Recreate database
make clean && make up
```

## 📄 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- Built with [doc4microservices framework](https://github.com/...)
- Uses **Improved Hybrid Approach** architecture
- Follows `.framework/` best practices

---

**Status**: ✅ PoC Level 1 - Ready for local testing
**Next Step**: Level 2 (Development Ready) - Add observability and integration tests
