import asyncio
import random
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from src.utils.logging import logger

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
]

# Block resource types that waste bandwidth
BLOCKED_RESOURCE_TYPES = ["font", "media", "texttrack", "eventsource", "websocket", "manifest"]
BLOCKED_URL_PATTERNS = [
    "google-analytics.com", "googletagmanager.com", "facebook.net",
    "doubleclick.net", "amazon-adsystem.com", "adservice.google",
    "analytics.", "tracker.", "pixel.", "beacon.",
]


class BrowserManager:
    """Manages a single Playwright Chromium browser context."""

    def __init__(self):
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self.ready = False

    @classmethod
    async def create(cls) -> "BrowserManager":
        """Factory method — creates and initializes browser."""
        manager = cls()
        await manager._init()
        return manager

    async def _init(self):
        """Initialize Playwright and launch browser."""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-extensions",
                "--disable-background-networking",
                "--disable-default-apps",
                "--no-first-run",
                "--single-process",
            ]
        )
        self._context = await self._browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={"width": 1920, "height": 1080},
            java_script_enabled=True,
            ignore_https_errors=True,
        )

        # Block tracking/ads/fonts
        await self._context.route("**/*", self._route_handler)
        self.ready = True
        logger.info("Browser initialized successfully")

    async def _route_handler(self, route):
        """Block unnecessary resource types and tracking URLs."""
        try:
            request = route.request
            if request.resource_type in BLOCKED_RESOURCE_TYPES:
                await route.abort()
                return
            url = request.url.lower()
            for pattern in BLOCKED_URL_PATTERNS:
                if pattern in url:
                    await route.abort()
                    return
            await route.continue_()
        except Exception:
            try:
                await route.continue_()
            except Exception:
                pass

    async def new_page(self) -> Page:
        """Get a new page with a rotated user agent."""
        if not self._context:
            raise RuntimeError("Browser not initialized")
        page = await self._context.new_page()
        await page.set_extra_http_headers({
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        })
        return page

    async def load_page(self, url: str, timeout: int = 30000) -> Page:
        """Load a URL in a new page, wait for network idle, handle popups."""
        page = await self.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            # Wait for network to settle
            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                pass  # Some pages never go fully idle

            # Dismiss cookie popups
            await self._dismiss_popups(page)

            return page
        except Exception:
            await page.close()
            raise

    async def _dismiss_popups(self, page: Page):
        """Try to dismiss common cookie/consent popups."""
        popup_selectors = [
            'button:has-text("Accept")',
            'button:has-text("Accept All")',
            'button:has-text("Accept Cookies")',
            'button:has-text("I Agree")',
            'button:has-text("OK")',
            'button:has-text("Got it")',
            'button:has-text("Agree")',
            '[id*="cookie"] button',
            '[class*="cookie"] button',
            '[id*="consent"] button',
            '[class*="consent"] button',
            '.gdpr-accept',
            '#onetrust-accept-btn-handler',
        ]

        for selector in popup_selectors:
            try:
                btn = page.locator(selector).first
                if await btn.is_visible(timeout=500):
                    await btn.click(timeout=1000)
                    await asyncio.sleep(0.5)
                    break
            except Exception:
                continue

    async def scroll_page(self, page: Page, scroll_count: int = 5, delay: float = 1.0):
        """Progressive scrolling to trigger lazy loading."""
        for i in range(scroll_count):
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
            await asyncio.sleep(delay + random.uniform(0.2, 0.8))

        # Scroll back to top
        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(0.5)

    async def close(self):
        """Clean up browser resources."""
        try:
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception as e:
            logger.warning(f"Error closing browser: {e}")
        finally:
            self.ready = False
