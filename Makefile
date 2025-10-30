.PHONY: help build up down logs restart clean lint test

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

init: ## Initialize project (copy .env.example to .env)
	cp .env.example .env
	@echo "Created .env file. Please edit it with your Telegram bot token."
