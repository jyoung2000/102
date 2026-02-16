import asyncio
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.scraper.engine import ScraperEngine, ScrapeProgress
from src.utils.logging import logger

JOBS_PATH = Path("/data/jobs.json")
STATS_PATH = Path("/data/stats.json")


class Job:
    """Represents a scraping job."""
    def __init__(self, urls: list[str], config_overrides: dict = None):
        self.job_id = uuid.uuid4().hex[:12]
        self.urls = urls
        self.config_overrides = config_overrides or {}
        self.status = "queued"
        self.created_at = datetime.now().isoformat()
        self.started_at: Optional[str] = None
        self.completed_at: Optional[str] = None
        self.progress = ScrapeProgress()
        self._cancel_event = asyncio.Event()
        self._task: Optional[asyncio.Task] = None

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "urls": self.urls,
            "status": self.status,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "progress": self.progress.to_dict(),
        }

    def cancel(self):
        self._cancel_event.set()
        self.status = "cancelled"


class JobQueue:
    """In-memory async job queue. Max 1 concurrent job."""

    def __init__(self):
        self._jobs: dict[str, Job] = {}
        self._queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None
        self._stats = self._load_stats()
        self._load_history()

    def _load_stats(self) -> dict:
        """Load persistent stats."""
        try:
            if STATS_PATH.exists():
                with open(STATS_PATH) as f:
                    return json.load(f)
        except Exception:
            pass
        return {
            "total_scraped": 0,
            "total_uploaded": 0,
            "total_duplicates": 0,
            "total_errors": 0,
            "aspect_ratio_breakdown": {},
            "site_breakdown": {},
        }

    def _save_stats(self):
        """Persist stats to disk."""
        try:
            STATS_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(STATS_PATH, "w") as f:
                json.dump(self._stats, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save stats: {e}")

    def _load_history(self):
        """Load job history from disk."""
        try:
            if JOBS_PATH.exists():
                with open(JOBS_PATH) as f:
                    history = json.load(f)
                # We only keep history for display, don't re-queue
                for jdata in history[-50:]:  # Keep last 50 jobs
                    job = Job(jdata.get("urls", []))
                    job.job_id = jdata["job_id"]
                    job.status = jdata.get("status", "unknown")
                    job.created_at = jdata.get("created_at", "")
                    job.started_at = jdata.get("started_at")
                    job.completed_at = jdata.get("completed_at")
                    # Restore progress
                    prog = jdata.get("progress", {})
                    job.progress.total_discovered = prog.get("total_discovered", 0)
                    job.progress.total_downloaded = prog.get("total_downloaded", 0)
                    job.progress.total_uploaded = prog.get("total_uploaded", 0)
                    job.progress.total_skipped = prog.get("total_skipped", 0)
                    job.progress.total_errors = prog.get("total_errors", 0)
                    job.progress.total_duplicates = prog.get("total_duplicates", 0)
                    job.progress.status = jdata.get("status", "unknown")
                    self._jobs[job.job_id] = job
        except Exception as e:
            logger.warning(f"Could not load job history: {e}")

    def _save_history(self):
        """Persist job history to disk."""
        try:
            JOBS_PATH.parent.mkdir(parents=True, exist_ok=True)
            history = [j.to_dict() for j in list(self._jobs.values())[-50:]]
            with open(JOBS_PATH, "w") as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save job history: {e}")

    async def submit(self, urls: list[str], config_overrides: dict = None) -> Job:
        """Submit a new scraping job."""
        job = Job(urls, config_overrides)
        self._jobs[job.job_id] = job
        await self._queue.put(job)
        self._save_history()
        logger.info(f"Job {job.job_id} queued with {len(urls)} URLs")

        # Start worker if not running
        if not self._running:
            self._start_worker()

        return job

    def _start_worker(self):
        """Start the background job worker."""
        if self._worker_task and not self._worker_task.done():
            return
        self._worker_task = asyncio.create_task(self._worker())

    async def _worker(self):
        """Process jobs from the queue one at a time."""
        self._running = True
        try:
            while True:
                try:
                    job = await asyncio.wait_for(self._queue.get(), timeout=5.0)
                except asyncio.TimeoutError:
                    if self._queue.empty():
                        break
                    continue

                await self._run_job(job)
                self._queue.task_done()
        finally:
            self._running = False

    async def _run_job(self, job: Job):
        """Execute a single job."""
        from src.scraper.engine import ScraperEngine

        job.status = "running"
        job.started_at = datetime.now().isoformat()
        self._save_history()

        # Get app state for engine creation
        app = self._app
        if not app:
            job.status = "failed"
            job.progress.errors.append("App not available")
            return

        # Create engine with current config
        config = app.state.config_store.get()
        # Apply overrides
        if job.config_overrides:
            if "max_pages" in job.config_overrides:
                config.setdefault("scraper", {})["max_pages_per_site"] = job.config_overrides["max_pages"]
            if "aspect_ratios" in job.config_overrides:
                config.setdefault("resolution", {})["target_aspect_ratios"] = job.config_overrides["aspect_ratios"]
            if "min_width" in job.config_overrides:
                config.setdefault("resolution", {})["min_width"] = job.config_overrides["min_width"]
            if "min_height" in job.config_overrides:
                config.setdefault("resolution", {})["min_height"] = job.config_overrides["min_height"]

        # Create Baserow client if configured
        baserow = None
        br_config = app.state.config_store.get("baserow")
        if br_config.get("api_url") and br_config.get("api_token"):
            from src.storage.baserow import BaserowClient
            baserow = BaserowClient(
                api_url=br_config["api_url"],
                api_token=br_config["api_token"],
                table_id=br_config.get("table_id", 810),
            )

        engine = ScraperEngine(
            browser=app.state.browser,
            captioner=app.state.captioner,
            baserow=baserow,
            config=config,
        )

        try:
            for url in job.urls:
                if job._cancel_event.is_set():
                    break
                await engine.scrape_url(url, job.progress, job._cancel_event)

            if not job._cancel_event.is_set():
                job.status = job.progress.status
            else:
                job.status = "cancelled"
        except Exception as e:
            logger.error(f"Job {job.job_id} failed: {e}")
            job.status = "failed"
            job.progress.errors.append(str(e))
        finally:
            job.completed_at = datetime.now().isoformat()
            if baserow:
                await baserow.close()

            # Update global stats
            self._update_stats(job)
            self._save_history()

    def _update_stats(self, job: Job):
        """Update persistent stats from a completed job."""
        p = job.progress
        self._stats["total_scraped"] += p.total_discovered
        self._stats["total_uploaded"] += p.total_uploaded
        self._stats["total_duplicates"] += p.total_duplicates
        self._stats["total_errors"] += p.total_errors

        # Merge aspect ratio counts
        for ratio, count in p.aspect_ratios.items():
            self._stats["aspect_ratio_breakdown"][ratio] = (
                self._stats["aspect_ratio_breakdown"].get(ratio, 0) + count
            )

        # Track by site
        from urllib.parse import urlparse
        for url in job.urls:
            site = urlparse(url).netloc
            self._stats["site_breakdown"][site] = (
                self._stats["site_breakdown"].get(site, 0) + p.total_uploaded
            )

        self._save_stats()

    def get_job(self, job_id: str) -> Optional[Job]:
        return self._jobs.get(job_id)

    def list_jobs(self) -> list[dict]:
        jobs = sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)
        return [j.to_dict() for j in jobs[:50]]

    def cancel_job(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if job and job.status in ("queued", "running"):
            job.cancel()
            self._save_history()
            return True
        return False

    def get_stats(self) -> dict:
        return self._stats.copy()

    def set_app(self, app):
        """Set reference to FastAPI app for accessing state."""
        self._app = app

    _app = None
