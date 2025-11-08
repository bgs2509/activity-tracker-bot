# First-Time Setup

**Time**: 15 minutes

**Goal**: Get the project running locally.

## Step 1: Clone Repository

Clone with submodules (important!):

```bash
git clone --recurse-submodules https://github.com/your-username/activity-tracker-bot.git
cd activity-tracker-bot
```

**Note**: The project uses `.ai-framework` as a git submodule for shared documentation.

If you forgot `--recurse-submodules`:
```bash
git submodule update --init --recursive
```

## Step 2: Create Environment File

The project uses `.env` file for configuration:

```bash
# Copy example file
cp .env.example .env

# Edit with your bot token
nano .env  # or use your favorite editor
```

**Required Changes in .env**:

```bash
# Replace this with your actual bot token from @BotFather
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

**Example .env**:
```bash
# Telegram Bot
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# PostgreSQL
POSTGRES_USER=tracker_user
POSTGRES_PASSWORD=tracker_password
POSTGRES_DB=tracker_db

# Data API
DATABASE_URL=postgresql+asyncpg://tracker_user:tracker_password@postgres:5432/tracker_db

# Redis
REDIS_URL=redis://redis:6379/0

# Internal Services
DATA_API_URL=http://data_postgres_api:8000

# Application
LOG_LEVEL=INFO
```

**Security**: NEVER commit `.env` to git! It's in `.gitignore`.

## Step 3: Build Docker Images

Build all service images:

```bash
make build
```

**Expected Output**:
```
[+] Building 45.2s (28/28) FINISHED
 => [tracker_activity_bot internal] load build definition
 => [data_postgres_api internal] load build definition
 ...
 => => naming to docker.io/library/activity-tracker-bot-tracker_activity_bot
 => => naming to docker.io/library/activity-tracker-bot-data_postgres_api
```

**Time**: ~2-5 minutes (depending on internet speed)

## Step 4: Start Services

Start all containers:

```bash
make up
```

**Expected Output**:
```
[+] Running 5/5
 ✔ Network activity-tracker-bot_tracker_network  Created
 ✔ Container activity-tracker-bot-postgres-1                Started
 ✔ Container activity-tracker-bot-redis-1                   Started
 ✔ Container activity-tracker-bot-data_postgres_api-1       Started
 ✔ Container activity-tracker-bot-tracker_activity_bot-1    Started
```

## Step 5: Verify Services

Check all containers are running:

```bash
docker ps
```

**Expected Output** (4 containers running):
```
CONTAINER ID   IMAGE                                        STATUS
abc123         activity-tracker-bot-tracker_activity_bot    Up 10 seconds
def456         activity-tracker-bot-data_postgres_api       Up 11 seconds
ghi789         postgres:15-alpine                           Up (healthy) 12 seconds
jkl012         redis:7-alpine                               Up (healthy) 12 seconds
```

**Check Health**:

```bash
# API health check
curl http://localhost:8080/health/live
# Expected: {"status":"ok"}

# Check logs (should see no errors)
make logs-bot
# Ctrl+C to exit

make logs-api
# Ctrl+C to exit
```

## Step 6: Test Bot in Telegram

1. Open Telegram app
2. Search for your bot username (from @BotFather)
3. Send `/start`

**Expected Response**:
```
Добро пожаловать в Activity Tracker Bot!

Этот бот поможет вам отслеживать вашу активность...

[📝 Записать] [📋 История] [⚙️ Настройки]
```

If you see this - **SUCCESS!** 🎉

## Step 7: Run Tests

Verify everything works:

```bash
# Run all tests in Docker
make test-all-docker
```

**Expected Output**:
```
===== test session starts =====
...
collected 45 items

tests/unit/test_imports.py ✓✓                 [ 4%]
tests/unit/services/test_user_service.py ✓✓✓   [11%]
...
===== 45 passed in 12.34s =====
```

If all tests pass - **PERFECT!** ✅

## Development Workflow

Now you can work on the project:

### View Logs

```bash
# All services
make logs

# Bot only
make logs-bot

# API only
make logs-api
```

### Restart Services

```bash
# Restart all
make restart

# Restart bot only
make restart-bot

# Restart API only
make restart-api
```

### Stop Services

```bash
# Stop (keeps data)
make down

# Stop and remove volumes (clean slate)
make clean
```

### Database Access

```bash
# Open psql shell
make shell-db

# Inside psql:
\dt                           # List tables
SELECT * FROM users;          # Query users
\q                            # Quit
```

### Run Tests

```bash
# Import tests (smoke)
make test-imports

# Unit tests
make test-unit-docker

# Integration tests
make test-integration-docker

# All tests
make test-all-docker

# With coverage
make test-coverage-docker
```

### Code Quality

```bash
# Lint code
make lint

# Format code
make format
```

## Common Issues

### Port Already in Use

**Error**:
```
Error starting userland proxy: listen tcp4 0.0.0.0:8080: bind: address already in use
```

**Fix**:
```bash
# Find what's using port 8080
lsof -i :8080

# Kill the process or change port in docker-compose.yml
```

### Bot Token Invalid

**Error** (in logs):
```
aiogram.exceptions.TelegramUnauthorizedError: Unauthorized
```

**Fix**:
1. Check `TELEGRAM_BOT_TOKEN` in `.env`
2. Verify token with @BotFather: send `/mybots` → select your bot → API Token
3. Restart bot: `make restart-bot`

### Database Connection Failed

**Error**:
```
asyncpg.exceptions.InvalidCatalogNameError: database "tracker_db" does not exist
```

**Fix**:
```bash
# Clean and rebuild
make clean
make build
make up
```

### Container Not Starting

**Error**:
```
Container exited with code 1
```

**Fix**:
```bash
# Check logs for specific error
make logs-bot
make logs-api

# Common causes:
# - Missing .env file
# - Invalid environment variables
# - Port conflicts
```

### Tests Failing

**Error**:
```
E   ModuleNotFoundError: No module named 'src'
```

**Fix**:
```bash
# Rebuild containers
make build
make test-all-docker
```

## Folder Structure Overview

```
activity-tracker-bot/
├── .env                      # Your local config (not in git)
├── .env.example              # Template for .env
├── docker-compose.yml        # Service orchestration
├── Makefile                  # Dev commands
│
├── services/
│   ├── tracker_activity_bot/ # Bot service
│   └── data_postgres_api/    # API service
│
├── tests/                    # Integration tests
│
├── docs/                     # Documentation
│   ├── onboarding/          # This guide!
│   ├── project-context/     # AI documentation
│   └── api/                 # API docs
│
├── .ai-framework/           # Git submodule (read-only)
│
└── README.md                 # Project overview
```

## Next Step

Everything running? → **Continue to `02-architecture-tour.md`**

---

**Last Updated**: 2025-11-08
**Est. Time**: 15 minutes
