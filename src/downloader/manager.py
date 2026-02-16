import asyncio
import os
import uuid
from pathlib import Path
from urllib.parse import urlparse

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.utils.logging import logger

TEMP_DIR = Path("/tmp/wallpaper-scraper")


class DownloadManager:
    """Async download manager with concurrency control."""

    def __init__(self, max_concurrent: int = 3, timeout: float = 60.0):
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._client: httpx.AsyncClient | None = None
        self._timeout = timeout

    async def _ensure_client(self):
        """Lazily create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                http2=True,
                timeout=httpx.Timeout(self._timeout, connect=15.0),
                follow_redirects=True,
                limits=httpx.Limits(
                    max_keepalive_connections=5,
                    max_connections=10,
                ),
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                }
            )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True,
    )
    async def download(self, url: str, referer: str = "") -> Path:
        """Download an image to temp directory. Returns path to downloaded file."""
        await self._ensure_client()

        async with self._semaphore:
            # Generate a temp filename
            ext = _get_extension(url)
            filename = f"{uuid.uuid4().hex}{ext}"
            filepath = TEMP_DIR / filename

            TEMP_DIR.mkdir(parents=True, exist_ok=True)

            headers = {}
            if referer:
                headers["Referer"] = referer

            # Stream to disk to avoid holding large images in memory
            async with self._client.stream("GET", url, headers=headers) as response:
                response.raise_for_status()

                # Validate content type
                content_type = response.headers.get("content-type", "")
                if not _is_image_content_type(content_type):
                    # Some servers don't send correct content-type, still try
                    logger.warning(f"Unexpected content-type '{content_type}' for {url[:80]}")

                total_size = 0
                max_size = 100 * 1024 * 1024  # 100 MB limit

                with open(filepath, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=65536):
                        total_size += len(chunk)
                        if total_size > max_size:
                            filepath.unlink(missing_ok=True)
                            raise ValueError(f"File exceeds {max_size // 1024 // 1024}MB limit")
                        f.write(chunk)

            logger.info(f"Downloaded {total_size / 1024:.0f}KB: {url[:80]}")
            return filepath

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def cleanup_file(self, filepath: Path):
        """Delete a temp file."""
        try:
            filepath.unlink(missing_ok=True)
        except Exception as e:
            logger.warning(f"Could not delete temp file {filepath}: {e}")


def _get_extension(url: str) -> str:
    """Extract file extension from URL."""
    parsed = urlparse(url)
    path = parsed.path.lower().split("?")[0]
    for ext in ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.tif']:
        if path.endswith(ext):
            return ext
    return '.jpg'  # Default


def _is_image_content_type(content_type: str) -> bool:
    """Check if content-type indicates an image."""
    ct = content_type.lower()
    return ct.startswith("image/") or "octet-stream" in ct
