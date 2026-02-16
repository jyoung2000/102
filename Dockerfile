FROM python:3.12-slim AS builder
WORKDIR /app

# Install CPU-only PyTorch FIRST (saves ~2 GB vs CUDA build)
RUN pip install --no-cache-dir --prefix=/install \
    torch --index-url https://download.pytorch.org/whl/cpu

# Then install everything else
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# --- Runtime stage ---
FROM python:3.12-slim
WORKDIR /app

# System deps for Playwright Chromium + Pillow image codecs + gosu for privilege dropping
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libatk-bridge2.0-0 libdrm2 libxkbcommon0 \
    libgbm1 libasound2 libxshmfence1 libx11-xcb1 \
    libjpeg62-turbo libwebp7 libpng16-16 \
    fonts-liberation \
    gosu \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY . .

# Set Playwright browsers to a fixed path (not user-dependent ~/.cache)
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright-browsers

# CRITICAL: Install Playwright Chromium browser binary
# Previous build OMITTED this and crash-looped with "Executable doesn't exist"
RUN mkdir -p /opt/playwright-browsers && \
    playwright install --with-deps chromium

# Pre-download BLIP-base model during build (no network fetch at runtime)
RUN python scripts/download_model.py

# Create the app user (UID/GID will be adjusted at runtime by entrypoint.sh)
RUN groupadd -g 1000 scraper && \
    useradd -u 1000 -g scraper -m -s /bin/bash scraper

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

EXPOSE 1629
VOLUME ["/data"]

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:1629/api/health')" || exit 1

# Entrypoint handles PUID/PGID, creates /data dirs, then drops to app user
ENTRYPOINT ["/app/entrypoint.sh"]

# Single worker — multiple workers duplicate BLIP model in RAM
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "1629", "--workers", "1"]
