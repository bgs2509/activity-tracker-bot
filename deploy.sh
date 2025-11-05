#!/bin/bash

# Deployment script for VPS
# This script stops containers, pulls latest changes, and rebuilds production containers

set -e  # Exit on any error

echo "================================================"
echo "🚀 Starting deployment process..."
echo "================================================"

# Stop and remove existing containers
echo ""
echo "🛑 Stopping existing containers..."
docker compose down

# Pull latest changes from git
echo ""
echo "📥 Pulling latest changes from git..."
sudo GIT_SSH_COMMAND='ssh -i /home/bgs/.ssh/HenryBud_Ubuntu_Lenovo73 -o IdentitiesOnly=yes' git pull

# Build and start production containers
echo ""
echo "🔨 Building and starting production containers..."
docker compose up --build -d

# Wait for database to be ready
echo ""
echo "⏳ Waiting for database to be ready..."
sleep 5

# Run database migrations
echo ""
echo "🗄️  Running database migrations..."
docker exec data_postgres_api alembic upgrade head

# Verify migration was applied
echo ""
echo "✅ Verifying database schema..."
docker exec tracker_db psql -U tracker_user -d tracker_db -c "\d users" | grep last_poll_time || echo "⚠️  Warning: last_poll_time column may not exist"

echo ""
echo "================================================"
echo "✅ DOCKER SYSTEM PRUNE -FORCE!"
echo "================================================"
docker system prune --force


echo ""
echo "================================================"
echo "✅ Deployment completed successfully!"
echo "================================================"
echo ""
echo "📊 ALL Container status:"
docker ps
