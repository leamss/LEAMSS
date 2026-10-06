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

# Detect docker-compose CLI
if command -v docker-compose >/dev/null 2>&1; then
    DC="sudo docker-compose"
else
    DC="sudo docker compose"
fi

# Ensure backend/.env exists so docker-compose env_file never fails
touch backend/.env || true

# Build & restart containers cleanly
if [ -f "docker-compose.prod.yml" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Rebuilding Docker production containers..."
    $DC -f docker-compose.prod.yml down || true
    sudo fuser -k 8001/tcp || true
    sudo fuser -k 3000/tcp || true
    $DC -f docker-compose.prod.yml up -d --build --remove-orphans
    # Run complete JSA enrichment + SSG generation inside backend container
    $DC -f docker-compose.prod.yml exec -T backend python scripts/enrich_jsa_and_ssg.py || true
    if command -v node >/dev/null 2>&1; then
        node scripts/sync_start_pages.js || true
        node scripts/patch_all_atlas_ssg.js || true
        node scripts/patch_atlas_footer_flags.js || true
    fi
    # Ensure frontend container serves the freshly generated static Atlas, Start, and Calculator files immediately
    $DC -f docker-compose.prod.yml cp frontend/public/atlas/. frontend:/usr/share/nginx/html/atlas/ || true
    $DC -f docker-compose.prod.yml cp frontend/public/start/. frontend:/usr/share/nginx/html/start/ || true
    $DC -f docker-compose.prod.yml cp frontend/public/calculator/. frontend:/usr/share/nginx/html/calculator/ || true
    $DC -f docker-compose.prod.yml cp frontend/public/start.html frontend:/usr/share/nginx/html/start.html || true
    $DC -f docker-compose.prod.yml cp frontend/public/calculator.html frontend:/usr/share/nginx/html/calculator.html || true
    $DC -f docker-compose.prod.yml cp frontend/public/leamss-logo.png frontend:/usr/share/nginx/html/leamss-logo.png || true
elif [ -f "docker-compose.yml" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Rebuilding Docker containers..."
    $DC down || true
    $DC up -d --build --remove-orphans
    $DC exec -T backend python scripts/enrich_jsa_and_ssg.py || true
    if command -v node >/dev/null 2>&1; then
        node scripts/sync_start_pages.js || true
        node scripts/patch_all_atlas_ssg.js || true
        node scripts/patch_atlas_footer_flags.js || true
    fi
    $DC cp frontend/public/atlas/. frontend:/usr/share/nginx/html/atlas/ || true
    $DC cp frontend/public/start/. frontend:/usr/share/nginx/html/start/ || true
    $DC cp frontend/public/calculator/. frontend:/usr/share/nginx/html/calculator/ || true
    $DC cp frontend/public/start.html frontend:/usr/share/nginx/html/start.html || true
    $DC cp frontend/public/calculator.html frontend:/usr/share/nginx/html/calculator.html || true
    $DC cp frontend/public/leamss-logo.png frontend:/usr/share/nginx/html/leamss-logo.png || true
fi

# Clean up dangling images to keep EC2 disk & RAM clean and fast
sudo docker image prune -f

# Reload host Nginx if present
if systemctl is-active --quiet nginx; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Reloading host Nginx..."
    sudo systemctl reload nginx || true
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Auto-deploy completed successfully! Live at: https://app.leamss.com"
