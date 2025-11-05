#!/bin/bash
# Script to run Alembic migration inside the container

set -e

echo "Running Alembic migration to add last_poll_time column..."

# Check if we're inside a container or need to exec into one
if [ -f /.dockerenv ]; then
    # We're inside the container
    cd /app
    alembic upgrade head
else
    # We're outside, need to exec into container
    docker compose exec -T data_postgres_api alembic upgrade head
fi

echo "Migration completed successfully!"
