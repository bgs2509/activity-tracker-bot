#!/bin/bash

# One-time migration script for existing databases
# Use this ONCE when transitioning from auto-created tables to Alembic migrations
# After running this, use deploy.sh for all future deployments

set -e

echo "================================================"
echo "🔄 Migrating existing database to Alembic"
echo "================================================"
echo ""
echo "⚠️  WARNING: This script should only be run ONCE"
echo "   for existing databases created before Alembic."
echo ""
read -p "Continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

echo ""
echo "🔍 Checking database state..."

# Check if users table exists
if docker exec tracker_db psql -U tracker_user -d tracker_db -tAc "SELECT to_regclass('public.users');" | grep -q "users"; then
    echo "✅ Database tables exist"

    # Check if last_poll_time column exists
    if docker exec tracker_db psql -U tracker_user -d tracker_db -tAc "SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='last_poll_time';" | grep -q "last_poll_time"; then
        echo "✅ Column last_poll_time exists - stamping at version 002"
        docker exec data_postgres_api alembic stamp 002
    else
        echo "⚠️  Column last_poll_time missing - stamping at version 001"
        docker exec data_postgres_api alembic stamp 001
        echo "🔄 Applying migration 002..."
        docker exec data_postgres_api alembic upgrade head
    fi
else
    echo "❌ Database is empty - use deploy.sh instead"
    exit 1
fi

echo ""
echo "================================================"
echo "✅ Migration complete!"
echo "================================================"
echo ""
echo "From now on, use ./deploy.sh for deployments"
