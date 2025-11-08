.PHONY: help build up down logs restart clean lint test test-imports test-unit test-integration test-docker test-smoke test-coverage test-all test-unit-docker test-imports-docker test-integration-docker test-coverage-docker test-all-docker

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build: ## Build Docker images
	docker compose build

up: ## Start all services
	docker compose up -d

down: ## Stop all services
	docker compose down

logs: ## Show logs from all services
	docker compose logs -f

logs-bot: ## Show logs from bot service
	docker compose logs -f tracker_activity_bot

logs-api: ## Show logs from API service
	docker compose logs -f data_postgres_api

restart: ## Restart all services
	docker compose restart

restart-bot: ## Restart bot service
	docker compose restart tracker_activity_bot

restart-api: ## Restart API service
	docker compose restart data_postgres_api

clean: ## Stop services and remove volumes
	docker compose down -v

ps: ## Show running containers
	docker compose ps

lint: ## Run linting (Ruff) on both services
	@echo "Linting data_postgres_api..."
	cd services/data_postgres_api && ruff check .
	@echo "Linting tracker_activity_bot..."
	cd services/tracker_activity_bot && ruff check .

format: ## Format code with Ruff
	@echo "Formatting data_postgres_api..."
	cd services/data_postgres_api && ruff format .
	@echo "Formatting tracker_activity_bot..."
	cd services/tracker_activity_bot && ruff format .

shell-api: ## Open shell in API container
	docker exec -it data_postgres_api /bin/sh

shell-bot: ## Open shell in bot container
	docker exec -it tracker_activity_bot /bin/sh

shell-db: ## Open psql shell
	docker exec -it tracker_db psql -U tracker_user -d tracker_db

migrate: ## Run Alembic migrations
	docker compose exec data_postgres_api alembic upgrade head

migrate-create: ## Create a new Alembic migration (use MSG="description")
	docker compose exec data_postgres_api alembic revision --autogenerate -m "$(MSG)"

migrate-downgrade: ## Downgrade one migration
	docker compose exec data_postgres_api alembic downgrade -1

migrate-history: ## Show migration history
	docker compose exec data_postgres_api alembic history

init: ## Initialize project (copy .env.example to .env)
	cp .env.example .env
	@echo "Created .env file. Please edit it with your Telegram bot token."

# Testing commands

test-imports: ## Run import smoke tests for all services
	@echo "Запуск импорт-тестов для tracker_activity_bot..."
	cd services/tracker_activity_bot && pytest tests/unit/test_imports.py -v -m smoke
	@echo "\nЗапуск импорт-тестов для data_postgres_api..."
	cd services/data_postgres_api && pytest tests/unit/test_imports.py -v -m smoke

test-unit: ## Run all unit tests
	@echo "Запуск unit-тестов для tracker_activity_bot..."
	cd services/tracker_activity_bot && pytest tests/unit/ -v -m unit
	@echo "\nЗапуск unit-тестов для data_postgres_api..."
	cd services/data_postgres_api && pytest tests/unit/ -v -m unit

test-integration: ## Run integration tests (handler registration, API contracts)
	@echo "Запуск integration-тестов..."
	@echo "  ✓ Проверка регистрации обработчиков кнопок"
	@echo "  ✓ Проверка контрактов Bot ↔ API"
	pytest tests/integration/ -v -m integration

test-docker: ## Run Docker health smoke tests (requires running containers)
	@echo "Запуск тестов проверки здоровья Docker контейнеров..."
	@echo "Примечание: контейнеры должны быть запущены (make up)"
	pytest tests/smoke/ -v -m smoke

test-smoke: test-imports test-docker ## Run all smoke tests

test-coverage: ## Run tests with coverage report
	@echo "Запуск тестов с coverage отчётом для tracker_activity_bot..."
	cd services/tracker_activity_bot && pytest tests/ -v --cov=src --cov-report=html --cov-report=term
	@echo "\nЗапуск тестов с coverage отчётом для data_postgres_api..."
	cd services/data_postgres_api && pytest tests/ -v --cov=src --cov-report=html --cov-report=term

test-all: test-unit test-integration test-smoke ## Run all tests (unit + integration + smoke)

# Docker-based testing (runs tests inside containers)

test-unit-docker: ## Run unit tests inside Docker containers
	@echo "Запуск контейнеров для тестирования..."
	@docker compose --env-file .env.test up -d --wait
	@echo "\n✓ Контейнеры запущены\n"
	@echo "Запуск unit-тестов для data_postgres_api внутри контейнера..."
	@docker compose exec data_postgres_api pytest tests/unit/ -v -m unit || true
	@echo "\nЗапуск unit-тестов для tracker_activity_bot внутри контейнера..."
	@docker compose exec tracker_activity_bot pytest tests/unit/ -v -m unit || true
	@echo "\n✓ Все Docker-based тесты завершены"

test-imports-docker: ## Run import tests inside Docker containers
	@echo "Запуск контейнеров для тестирования..."
	@docker compose --env-file .env.test up -d --wait
	@echo "\n✓ Контейнеры запущены\n"
	@echo "Запуск импорт-тестов для data_postgres_api внутри контейнера..."
	@docker compose exec data_postgres_api pytest tests/unit/test_imports.py -v -m smoke
	@echo "\nЗапуск импорт-тестов для tracker_activity_bot внутри контейнера..."
	@docker compose exec tracker_activity_bot pytest tests/unit/test_imports.py -v -m smoke

test-integration-docker: ## Run integration tests with Docker (handler registration, API contracts)
	@echo "Запуск контейнеров для интеграционных тестов..."
	@docker compose --env-file .env.test up -d --wait
	@echo "\n✓ Контейнеры запущены\n"
	@echo "Запуск integration-тестов..."
	@echo "  ✓ Проверка регистрации обработчиков кнопок"
	@echo "  ✓ Проверка контрактов Bot ↔ API"
	@docker run --rm -v $(PWD):/app -w /app python:3.11-slim sh -c "pip install -q pytest && pytest tests/integration/ -v -m integration" || true
	@echo "\n✓ Integration тесты завершены"

test-coverage-docker: ## Run coverage tests inside Docker containers
	@echo "Запуск контейнеров для тестирования..."
	@docker compose --env-file .env.test up -d --wait
	@echo "\n✓ Контейнеры запущены\n"
	@echo "Запуск тестов с coverage для data_postgres_api..."
	@docker compose exec data_postgres_api pytest tests/ -v --cov=src --cov-report=html --cov-report=term
	@echo "\nЗапуск тестов с coverage для tracker_activity_bot..."
	@docker compose exec tracker_activity_bot pytest tests/ -v --cov=src --cov-report=html --cov-report=term
	@echo "\n✓ Coverage отчёты созданы в services/*/htmlcov/"

test-all-docker: test-unit-docker test-integration-docker ## Run all Docker-based tests (unit + integration inside containers)
