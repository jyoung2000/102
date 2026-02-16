import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from src.utils.logging import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Non-fatal startup: every component init is wrapped in try/except.
    The GUI must ALWAYS load even if browser, AI, or Baserow fails.
    """
    app.state.start_time = time.time()

    # 1. Config store (reads /data/config.json)
    try:
        from src.storage.config_store import ConfigStore
        app.state.config_store = ConfigStore()
        logger.info("Config loaded")
    except Exception as e:
        logger.error(f"Config store failed: {e}")
        from src.storage.config_store import ConfigStore
        app.state.config_store = ConfigStore()

    # 2. AI model (BLIP-base) — should work since model is baked into image
    try:
        from src.ai.captioner import WallpaperCaptioner
        app.state.captioner = WallpaperCaptioner()
        logger.info("AI model loaded")
    except Exception as e:
        logger.error(f"AI model failed to load: {e}")
        app.state.captioner = None

    # 3. Browser (Playwright Chromium) — may fail, non-fatal
    try:
        from src.scraper.browser import BrowserManager
        app.state.browser = await BrowserManager.create()
        logger.info("Browser ready")
    except Exception as e:
        logger.warning(f"Browser failed to start: {e}")
        app.state.browser = None

    # 4. Check Baserow config (don't connect yet)
    app.state.baserow_configured = app.state.config_store.is_baserow_configured()

    # 5. Job queue
    try:
        from src.api.jobs import JobQueue
        app.state.job_queue = JobQueue()
        app.state.job_queue.set_app(app)
        logger.info("Job queue initialized")
    except Exception as e:
        logger.error(f"Job queue failed: {e}")
        from src.api.jobs import JobQueue
        app.state.job_queue = JobQueue()
        app.state.job_queue.set_app(app)

    logger.info("Wallpaper Scraper started on port 1629")

    yield

    # Cleanup
    logger.info("Shutting down...")
    if hasattr(app.state, 'browser') and app.state.browser:
        try:
            await app.state.browser.close()
        except Exception:
            pass


# Create FastAPI app
app = FastAPI(
    title="Wallpaper Scraper",
    version="1.0.0",
    lifespan=lifespan,
)

# Mount static files
app.mount("/static", StaticFiles(directory="src/web/static"), name="static")

# Register API routes
from src.api.routes import router as api_router
app.include_router(api_router)


@app.get("/")
async def serve_gui():
    """Serve the SPA index.html."""
    return FileResponse("src/web/static/index.html")
