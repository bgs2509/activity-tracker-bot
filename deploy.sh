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
docker-compose down

# Pull latest changes from git
echo ""
echo "📥 Pulling latest changes from git..."
GIT_SSH_COMMAND='ssh -i ~/.ssh/my_VPS_mchost_250927 -o IdentitiesOnly=yes' git pull

# Build and start production containers
echo ""
echo "🔨 Building and starting production containers..."
docker-compose up --build -d

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
