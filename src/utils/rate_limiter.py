import asyncio
import time


class RateLimiter:
    """Simple async rate limiter with configurable delay between requests."""

    def __init__(self, delay_seconds: float = 2.0):
        self.delay = delay_seconds
        self._last_request = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self):
        """Wait until enough time has passed since the last request."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request
            if elapsed < self.delay:
                await asyncio.sleep(self.delay - elapsed)
            self._last_request = time.monotonic()

    def update_delay(self, delay_seconds: float):
        """Update the delay between requests."""
        self.delay = delay_seconds
