#!/bin/bash
set -e

# Default to Unraid's nobody:users (99:100)
PUID=${PUID:-99}
PGID=${PGID:-100}

echo "Starting with UID=$PUID, GID=$PGID"

# Adjust the scraper group and user to match requested PUID/PGID
groupmod -o -g "$PGID" scraper 2>/dev/null || true
usermod -o -u "$PUID" -g "$PGID" scraper 2>/dev/null || true

# Create /data subdirectories (volume mount overwrites anything Dockerfile created)
mkdir -p /data/logs /data/wallpapers /data/config /tmp/wallpaper-scraper

# Fix ownership of all app-writable paths
chown -R scraper:scraper /data
chown -R scraper:scraper /tmp/wallpaper-scraper
chown -R scraper:scraper /app
chown -R scraper:scraper /opt/playwright-browsers

# Fix huggingface model cache permissions
if [ -d /root/.cache/huggingface ]; then
    cp -r /root/.cache/huggingface /home/scraper/.cache/huggingface 2>/dev/null || true
    chown -R scraper:scraper /home/scraper/.cache 2>/dev/null || true
fi

echo "Permissions fixed. Dropping to user scraper (UID=$PUID, GID=$PGID)..."

# Drop privileges and exec the CMD (uvicorn)
exec gosu scraper "$@"
