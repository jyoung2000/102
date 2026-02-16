#!/bin/bash

# Do NOT use set -e — chown failures must not kill the entrypoint.
# The app must always start, even if permissions can't be fixed.

# Default to Unraid's nobody:users (99:100)
PUID=${PUID:-99}
PGID=${PGID:-100}

echo "========================================="
echo "Wallpaper Scraper — Entrypoint"
echo "Requested PUID=$PUID, PGID=$PGID"
echo "Running as: $(id)"
echo "========================================="

# Verify we are root — if not, skip all permission fixing and just run the app
if [ "$(id -u)" -ne 0 ]; then
    echo "WARNING: Entrypoint is NOT running as root (running as UID=$(id -u))."
    echo "Cannot fix permissions. If you see PermissionError, ensure no 'user:' key"
    echo "is set in docker-compose.yml and no USER directive is in the Dockerfile."
    echo "Starting app directly as current user..."
    mkdir -p /data/logs /data/wallpapers /data/config /tmp/wallpaper-scraper 2>/dev/null || true
    exec "$@"
fi

echo "Running as root — adjusting scraper user to UID=$PUID, GID=$PGID..."

# Adjust the scraper group and user to match requested PUID/PGID
groupmod -o -g "$PGID" scraper 2>/dev/null || true
usermod -o -u "$PUID" -g "$PGID" scraper 2>/dev/null || true

# Create /data subdirectories (volume mount overwrites anything Dockerfile created)
mkdir -p /data/logs /data/wallpapers /data/config /tmp/wallpaper-scraper

# Fix ownership of all app-writable paths
# Each chown is non-fatal — some volume mounts (NFS root_squash, FUSE) reject chown
echo "Fixing /data permissions..."
chown -R scraper:scraper /data 2>&1 || echo "WARNING: chown /data failed (non-fatal)"
echo "Fixing /tmp/wallpaper-scraper permissions..."
chown -R scraper:scraper /tmp/wallpaper-scraper 2>&1 || echo "WARNING: chown /tmp failed (non-fatal)"
echo "Fixing /app permissions..."
chown -R scraper:scraper /app 2>&1 || echo "WARNING: chown /app failed (non-fatal)"
echo "Fixing /opt/playwright-browsers permissions..."
chown -R scraper:scraper /opt/playwright-browsers 2>&1 || echo "WARNING: chown playwright failed (non-fatal)"

# Fix huggingface model cache permissions
if [ -d /root/.cache/huggingface ]; then
    echo "Copying HuggingFace cache to scraper home..."
    mkdir -p /home/scraper/.cache 2>/dev/null || true
    cp -r /root/.cache/huggingface /home/scraper/.cache/huggingface 2>/dev/null || true
    chown -R scraper:scraper /home/scraper/.cache 2>/dev/null || true
fi

# If chown on /data failed, try chmod as a fallback so the scraper user can at least write
if ! su -s /bin/sh scraper -c "test -w /data/logs" 2>/dev/null; then
    echo "WARNING: scraper user cannot write to /data/logs. Trying chmod fallback..."
    chmod -R 777 /data 2>/dev/null || echo "WARNING: chmod /data also failed. Logging will be console-only."
fi

echo "Permissions fixed. Dropping to user scraper (UID=$PUID, GID=$PGID)..."
echo "Verifying scraper user: $(id scraper 2>/dev/null || echo 'user not found')"

# Drop privileges and exec the CMD (uvicorn)
exec gosu scraper "$@"
