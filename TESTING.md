# Testing Guide

This document describes how to run tests for the activity-tracker-bot project.

## Overview

The project includes three types of tests:

1. **Import Tests (Smoke Tests)** - Verify all modules can be imported without errors
2. **Unit Tests** - Test individual components in isolation
3. **Docker Health Tests** - Verify Docker containers are running and healthy

## Test Structure

```
activity-tracker-bot/
├── services/
│   ├── tracker_activity_bot/
│   │   ├── tests/
│   │   │   ├── unit/
│   │   │   │   └── test_imports.py     # Import smoke tests
│   │   ├── pytest.ini                  # Pytest configuration
│   │   └── .coveragerc                 # Coverage configuration
│   │
│   └── data_postgres_api/
│       ├── tests/
│       │   ├── unit/
│       │   │   ├── test_imports.py     # Import smoke tests
│       │   │   └── test_health.py      # Health endpoint tests
│       ├── pytest.ini
│       └── .coveragerc
│
└── tests/
    └── smoke/
        └── test_docker_health.py       # Docker health tests
```

## Environment Variables for Testing

### Overview

The project uses **two separate environment configurations**:

1. **`.env`** (NOT in git) - Real secrets for production/development
2. **`.env.test`** (IN git) - Safe dummy values for testing

This separation ensures that:
- ✅ Tests can run without exposing real secrets
- ✅ New developers can run tests immediately after cloning
- ✅ CI/CD pipelines work without secret management complexity
- ✅ No risk of accidentally committing sensitive tokens

### Why Environment Variables Are Needed

Both services use `pydantic-settings` to validate configuration at startup. Some fields are **required** (no defaults):

**data_postgres_api requires:**
- `DATABASE_URL` - PostgreSQL connection string
- Other fields have defaults (LOG_LEVEL, etc.)

**tracker_activity_bot requires:**
- `TELEGRAM_BOT_TOKEN` - Telegram bot API token
- `DATA_API_URL` - URL to data_postgres_api service
- `REDIS_URL` - Redis connection for FSM storage

Without these variables, even unit tests will fail with `pydantic_core.ValidationError` when importing Settings classes.

### Using .env.test for Testing

The `.env.test` file contains **safe dummy values** that pass pydantic validation:

```bash
# .env.test (safe to commit to git)
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz-DUMMY-TEST-TOKEN
DATABASE_URL=postgresql+asyncpg://test_user:test_password@localhost:5432/test_db
DATA_API_URL=http://localhost:8000
REDIS_URL=redis://localhost:6379/0
LOG_LEVEL=DEBUG
```

**Important:** These values are **NEVER used for actual connections** in unit tests! All external dependencies (database, Redis, Telegram API, HTTP client) are mocked. The values only need to satisfy format validation.

### How Tests Load Environment Variables

Test configuration files (`services/*/tests/conftest.py`) automatically load `.env.test` using `python-dotenv`:

```python
# conftest.py loads .env.test BEFORE importing any application code
from dotenv import load_dotenv

project_root = Path(__file__).parent.parent.parent.parent
test_env_path = project_root / ".env.test"

if test_env_path.exists():
    load_dotenv(test_env_path, override=False)
else:
    # Fallback values if .env.test is missing
    os.environ.setdefault("TELEGRAM_BOT_TOKEN", "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz-TEST")
    # ... other fallbacks
```

### Setting Up Your Real Environment

For running the actual services (not tests), create a `.env` file with real credentials:

```bash
# Copy template
cp .env.example .env

# Edit .env and add your real Telegram bot token from @BotFather
nano .env
```

**IMPORTANT:** Never commit `.env` to git! It's already in `.gitignore`.

### Docker-Based Testing

When running tests inside Docker containers, you have two options:

**Option 1: Use .env.test (automatic)**
```bash
# .env.test is automatically loaded by conftest.py
make test-unit-docker
```

**Option 2: Pass environment variables via docker compose**
```bash
# Override variables for specific test runs
docker compose exec -e TELEGRAM_BOT_TOKEN=test tracker_activity_bot pytest tests/unit/ -v
```

### Local Testing Without Docker

If you want to run tests locally (not in Docker):

1. Install test dependencies in a virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies for the service you want to test
pip install -r services/data_postgres_api/requirements.txt
# or
pip install -r services/tracker_activity_bot/requirements.txt
```

2. Run tests (`.env.test` will be loaded automatically):
```bash
cd services/data_postgres_api && pytest tests/unit/ -v
cd services/tracker_activity_bot && pytest tests/unit/ -v
```

### Security Best Practices

✅ **DO:**
- Commit `.env.test` to git (contains safe dummy values)
- Use `.env` for real secrets (never commit)
- Keep dummy tokens clearly marked as FAKE/DUMMY/TEST
- Use valid format for dummy values (e.g., Telegram token: `10digits:43chars`)

❌ **DON'T:**
- Never commit `.env` file to git
- Never use real secrets in test files
- Never use real secrets in `.env.test`
- Never hardcode secrets in application code

### Verifying Environment Setup

To verify your environment is configured correctly:

```bash
# Check that .env.test exists
ls -la .env.test

# Check that .env is in .gitignore
git check-ignore .env  # Should output: .env

# Run import tests (will fail if env vars are missing)
make test-imports-docker
```

## Running Tests

### Method 1: Using Makefile Commands (Recommended)

The easiest way to run tests is using the provided Makefile commands.

#### Local Testing (requires local pytest installation)

```bash
# Run import smoke tests (fast, no Docker required)
make test-imports

# Run all unit tests
make test-unit

# Run Docker health tests (requires running containers)
make test-docker

# Run all smoke tests (imports + Docker health)
make test-smoke

# Run tests with coverage report
make test-coverage

# Run all tests
make test-all
```

#### Docker-Based Testing (recommended, no local setup needed)

These commands run tests **inside Docker containers**, eliminating the need for local Python environment setup:

```bash
# Run unit tests inside containers (auto-starts containers)
make test-unit-docker

# Run import tests inside containers
make test-imports-docker

# Run tests with coverage inside containers
make test-coverage-docker

# Run all Docker-based tests
make test-all-docker
```

**Benefits of Docker-based testing:**
- ✅ No local Python environment needed
- ✅ Matches production environment exactly
- ✅ All dependencies automatically installed
- ✅ Automatic container startup with `--wait` flag

### Method 2: Running Tests Manually

#### Import Tests (Inside Docker Containers)

Import tests run inside Docker containers where all dependencies are installed:

```bash
# For tracker_activity_bot
docker exec -it tracker_activity_bot pytest tests/unit/test_imports.py -v -m smoke

# For data_postgres_api
docker exec -it data_postgres_api pytest tests/unit/test_imports.py -v -m smoke
```

#### Unit Tests (Inside Docker Containers)

```bash
# For tracker_activity_bot
docker exec -it tracker_activity_bot pytest tests/unit/ -v -m unit

# For data_postgres_api
docker exec -it data_postgres_api pytest tests/unit/ -v -m unit
```

#### Docker Health Tests (On Host Machine)

Docker health tests run on the host machine and verify containers are running:

**Prerequisites:**
- Docker and docker-compose must be installed
- Containers must be running (`make up` or `docker compose up -d`)
- Install test dependencies in a virtual environment:

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Linux/Mac
# or
.venv\Scripts\activate  # On Windows

# Install test dependencies
pip install pytest requests

# Run Docker health tests
pytest tests/smoke/ -v -m smoke
```

## Test Coverage

### Coverage Requirements by Maturity Level

- **Level 1 (PoC)**: ≥ 60% coverage
- **Level 2 (Development)**: ≥ 75% coverage
- **Level 3 (Pre-Production)**: ≥ 80% coverage
- **Level 4 (Production)**: ≥ 85% coverage

### Generating Coverage Reports

```bash
# Generate HTML coverage report
make test-coverage

# View coverage reports
# For tracker_activity_bot:
open services/tracker_activity_bot/htmlcov/index.html

# For data_postgres_api:
open services/data_postgres_api/htmlcov/index.html
```

## What Each Test Type Verifies

### 1. Import Tests

Import tests verify that all Python modules can be imported without errors. They catch:

- Missing dependencies
- Circular import issues
- Syntax errors
- Module structure problems

**Example:**
```python
@pytest.mark.unit
@pytest.mark.smoke
def test_import_main():
    """Verify main module can be imported."""
    from src import main
    assert main is not None
```

### 2. Unit Tests

Unit tests verify individual components work correctly in isolation:

- **test_health.py** - Tests the `/health` endpoint returns correct responses
- More unit tests can be added in `tests/unit/` directory

### 3. Docker Health Tests

Docker health tests verify the infrastructure is working:

- **test_data_api_health_endpoint** - Verifies API service responds to health checks
- **test_postgres_container_running** - Verifies PostgreSQL container is running
- **test_redis_container_running** - Verifies Redis container is running
- **test_bot_container_running** - Verifies bot container is running
- **test_all_containers_healthy** - Verifies no containers are unhealthy

## Continuous Integration

For CI/CD pipelines, tests can be run in this order:

```yaml
# Example CI workflow
steps:
  - name: Build Docker images
    run: make build

  - name: Start services
    run: make up

  - name: Wait for services to be ready
    run: sleep 30

  - name: Run import tests
    run: |
      docker exec tracker_activity_bot pytest tests/unit/test_imports.py -v
      docker exec data_postgres_api pytest tests/unit/test_imports.py -v

  - name: Run unit tests with coverage
    run: |
      docker exec tracker_activity_bot pytest tests/unit/ -v --cov=src --cov-fail-under=60
      docker exec data_postgres_api pytest tests/unit/ -v --cov=src --cov-fail-under=60

  - name: Run Docker health tests
    run: pytest tests/smoke/ -v
```

## Troubleshooting

### Import Tests Fail

If import tests fail, it usually means:
- Missing dependencies in `requirements.txt`
- Circular imports in the code
- Syntax errors in Python files

Check the error message to identify which module failed to import.

### Docker Health Tests Fail

If Docker health tests fail:
1. Ensure containers are running: `docker compose ps`
2. Check container logs: `make logs`
3. Verify health endpoint manually: `curl http://localhost:8000/health`
4. Wait longer for services to start (some services take 30-60 seconds)

### Coverage Too Low

If coverage is below the threshold:
1. Add more unit tests for uncovered code
2. Review coverage report: `open services/*/htmlcov/index.html`
3. Focus on testing business logic and critical paths

## Adding New Tests

### Adding Unit Tests

1. Create a new test file in `services/{service_name}/tests/unit/`
2. Follow the naming convention: `test_*.py`
3. Mark tests with appropriate markers:
   ```python
   @pytest.mark.unit
   def test_my_feature():
       # Test code here
   ```

### Adding Integration Tests (Level 2+)

For Level 2 maturity, integration tests can be added:

```
services/{service_name}/tests/
├── unit/          # Existing unit tests
└── integration/   # NEW: Integration tests
    ├── conftest.py
    └── test_postgres_integration.py
```

## References

- [Pytest Documentation](https://docs.pytest.org/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [Framework Testing Guidelines](.framework/docs/atomic/testing/)
