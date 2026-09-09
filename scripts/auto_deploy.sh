#!/bin/bash
# ==============================================================================
# LEAMSS Automated Auto-Deploy & Continuous Delivery Script for EC2
# ==============================================================================

set -e

PROJECT_DIR="/home/ubuntu/LEAMSS"
cd "$PROJECT_DIR" || exit 1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Checking for updates from origin/main..."

# Fetch latest commits without modifying working tree
git fetch origin main

LOCAL_COMMIT=$(git rev-parse HEAD)
REMOTE_COMMIT=$(git rev-parse origin/main)

FORCE_DEPLOY=false
if [ "$1" = "--force" ] || [ "$1" = "-f" ]; then
    FORCE_DEPLOY=true
fi

if [ "$LOCAL_COMMIT" = "$REMOTE_COMMIT" ] && [ "$FORCE_DEPLOY" = false ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Everything up-to-date ($LOCAL_COMMIT). No deploy needed."
    exit 0
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Deploying updates ($LOCAL_COMMIT -> $REMOTE_COMMIT | Force: $FORCE_DEPLOY)..."

# Reset working directory cleanly to match origin/main
git reset --hard origin/main

# Build & restart containers
if [ -f "docker-compose.prod.yml" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Rebuilding Docker production containers..."
    sudo docker-compose -f docker-compose.prod.yml down --remove-orphans
    sudo docker-compose -f docker-compose.prod.yml build --no-cache
    sudo docker-compose -f docker-compose.prod.yml up -d
elif [ -f "docker-compose.yml" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Rebuilding Docker containers..."
    sudo docker-compose down --remove-orphans
    sudo docker-compose build --no-cache
    sudo docker-compose up -d
fi

# Clean up dangling images to keep EC2 disk & RAM clean and fast
sudo docker image prune -f

# Reload host Nginx if present
if systemctl is-active --quiet nginx; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Reloading host Nginx..."
    sudo systemctl reload nginx || true
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Auto-deploy completed successfully! Live at: https://app.leamss.com"
