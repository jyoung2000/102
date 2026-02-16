import asyncio
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from src.scraper.browser import BrowserManager
from src.scraper.adapters.generic import GenericAdapter
from src.downloader.manager import DownloadManager
from src.downloader.compressor import compress_to_jpeg, generate_filename
from src.downloader.validator import validate_image
from src.downloader.dedup import DedupChecker
from src.ai.captioner import WallpaperCaptioner
from src.storage.baserow import BaserowClient
from src.metadata.schemas import WallpaperRow, ScrapedImageInfo
from src.utils.logging import logger
from src.utils.rate_limiter import RateLimiter


class ScrapeProgress:
    """Tracks progress of a scraping job."""
    def __init__(self):
        self.total_discovered = 0
        self.total_downloaded = 0
        self.total_uploaded = 0
        self.total_skipped = 0
        self.total_errors = 0
        self.total_duplicates = 0
        self.current_url = ""
        self.current_page = 0
        self.status = "running"
        self.errors: list[str] = []
        self.aspect_ratios: dict[str, int] = {}

    def to_dict(self) -> dict:
        return {
            "total_discovered": self.total_discovered,
            "total_downloaded": self.total_downloaded,
            "total_uploaded": self.total_uploaded,
            "total_skipped": self.total_skipped,
            "total_errors": self.total_errors,
            "total_duplicates": self.total_duplicates,
            "current_url": self.current_url,
            "current_page": self.current_page,
            "status": self.status,
            "errors": self.errors[-10:],  # Last 10 errors
            "aspect_ratios": self.aspect_ratios,
        }


class ScraperEngine:
    """Orchestrates the full scraping pipeline."""

    def __init__(
        self,
        browser: BrowserManager | None,
        captioner: WallpaperCaptioner | None,
        baserow: BaserowClient | None,
        config: dict,
    ):
        self.browser = browser
        self.captioner = captioner
        self.baserow = baserow
        self.adapter = GenericAdapter()
        self.config = config

        scraper_conf = config.get("scraper", {})
        self.downloader = DownloadManager(
            max_concurrent=scraper_conf.get("max_concurrent_downloads", 3),
            timeout=scraper_conf.get("page_load_timeout_seconds", 30) * 1.0,
        )
        self.dedup = DedupChecker(
            hamming_threshold=config.get("deduplication", {}).get("hamming_distance_threshold", 8)
        )
        self.rate_limiter = RateLimiter(
            delay_seconds=scraper_conf.get("request_delay_seconds", 2)
        )
        self.max_pages = scraper_conf.get("max_pages_per_site", 50)

    async def scrape_url(
        self,
        url: str,
        progress: ScrapeProgress,
        cancel_event: asyncio.Event | None = None,
    ):
        """Scrape wallpapers from a URL (may follow pagination)."""
        current_url = url
        pages_scraped = 0

        try:
            while current_url and pages_scraped < self.max_pages:
                if cancel_event and cancel_event.is_set():
                    progress.status = "cancelled"
                    return

                progress.current_url = current_url
                progress.current_page = pages_scraped + 1

                logger.info(f"Scraping page {pages_scraped + 1}: {current_url}")

                # Load page with browser
                page_html = await self._load_page(current_url)
                if not page_html:
                    progress.errors.append(f"Failed to load: {current_url}")
                    progress.total_errors += 1
                    break

                # Discover images
                candidates = await self.adapter.discover(page_html, current_url)
                progress.total_discovered += len(candidates)

                # Process each candidate
                for candidate in candidates:
                    if cancel_event and cancel_event.is_set():
                        progress.status = "cancelled"
                        return

                    await self._process_candidate(candidate, progress)
                    await self.rate_limiter.acquire()

                # Find next page
                next_url = await self.adapter.get_next_page(page_html, current_url)
                if next_url and next_url != current_url:
                    current_url = next_url
                    pages_scraped += 1
                    await self.rate_limiter.acquire()
                else:
                    break

            if progress.status == "running":
                progress.status = "completed"

        except Exception as e:
            logger.error(f"Scrape error: {e}")
            progress.errors.append(str(e))
            progress.total_errors += 1
            progress.status = "failed"
        finally:
            await self.downloader.close()

    async def _load_page(self, url: str) -> str | None:
        """Load a page and return its HTML."""
        if not self.browser or not self.browser.ready:
            logger.error("Browser not available")
            return None

        page = None
        try:
            timeout = self.config.get("scraper", {}).get("page_load_timeout_seconds", 30) * 1000
            page = await self.browser.load_page(url, timeout=timeout)

            # Scroll to trigger lazy loading
            await self.browser.scroll_page(page, scroll_count=3, delay=0.8)

            html = await page.content()
            return html
        except Exception as e:
            logger.error(f"Failed to load page {url}: {e}")
            return None
        finally:
            if page:
                try:
                    await page.close()
                except Exception:
                    pass

    async def _process_candidate(self, candidate: ScrapedImageInfo, progress: ScrapeProgress):
        """Process a single image candidate through the full pipeline."""
        filepath = None
        try:
            # Download
            filepath = await self.downloader.download(candidate.url, referer=candidate.page_url)
            progress.total_downloaded += 1

            # Validate
            res_config = self.config.get("resolution", {})
            validation = validate_image(
                filepath,
                min_width=res_config.get("min_width", 1920),
                min_height=res_config.get("min_height", 1080),
                allowed_ratios=res_config.get("target_aspect_ratios"),
            )

            if not validation.valid:
                logger.info(f"Skipped: {validation.rejection_reason}")
                progress.total_skipped += 1
                return

            # Track aspect ratio
            ratio = validation.aspect_ratio
            progress.aspect_ratios[ratio] = progress.aspect_ratios.get(ratio, 0) + 1

            # Dedup
            img_hash = self.dedup.compute_hash(filepath)

            if self.dedup.is_duplicate_in_session(img_hash):
                logger.info(f"Duplicate in session, skipping")
                progress.total_duplicates += 1
                return

            dedup_config = self.config.get("deduplication", {})
            if dedup_config.get("enabled", True) and dedup_config.get("check_baserow", True):
                if self.baserow:
                    try:
                        if await self.baserow.check_hash_exists(img_hash):
                            logger.info(f"Duplicate in Baserow, skipping")
                            progress.total_duplicates += 1
                            self.dedup.add_to_session(img_hash)
                            return
                    except Exception as e:
                        logger.warning(f"Baserow dedup check failed: {e}")

            # Compress to JPEG
            quality = self.config.get("compression", {}).get("quality", 85)
            jpeg_bytes, orig_width, orig_height = compress_to_jpeg(filepath, quality=quality)

            # AI Caption
            ai_result = {"title": "Beautiful Wallpaper", "alt_text": "A wallpaper image.", "tags": "wallpaper"}
            if self.captioner:
                try:
                    ai_result = await asyncio.wait_for(
                        self.captioner.process_image(filepath, candidate.existing_tags),
                        timeout=30.0,
                    )
                except asyncio.TimeoutError:
                    logger.warning("AI caption timed out, using defaults")
                except Exception as e:
                    logger.warning(f"AI caption failed: {e}")

            # Upload to Baserow
            if self.baserow:
                source_site = urlparse(candidate.page_url).netloc
                filename = generate_filename(source_site, img_hash, orig_width, orig_height)

                # Step 1: Upload file
                file_result = await self.baserow.upload_file(jpeg_bytes, filename)
                baserow_filename = file_result["name"]

                # Step 2: Create row
                row = WallpaperRow(
                    wallpaperTitle=ai_result["title"],
                    Width=orig_width,
                    Height=orig_height,
                    imgUrl=candidate.url,
                    Alt_Text=ai_result["alt_text"],
                    Artist_text=candidate.artist_name,
                    Artist_link=candidate.artist_link,
                    IsMobile=validation.is_portrait,
                    IsReported=False,
                    IsVip=False,
                    OrgUploadDate=candidate.upload_date or datetime.now().strftime("%Y-%m-%d"),
                    CategoryTags=ai_result["tags"],
                    imageFile=[{"name": baserow_filename}],
                    imgHash=img_hash,
                )

                await self.baserow.create_row(row.to_baserow_dict())
                progress.total_uploaded += 1
                self.dedup.add_to_session(img_hash)

                logger.info(f"Uploaded: {ai_result['title']} ({orig_width}x{orig_height})")
            else:
                logger.warning("Baserow not configured, skipping upload")
                progress.total_skipped += 1

        except Exception as e:
            logger.error(f"Error processing {candidate.url[:80]}: {e}")
            progress.errors.append(f"{candidate.url[:60]}: {str(e)[:100]}")
            progress.total_errors += 1
        finally:
            # Clean up temp file
            if filepath:
                self.downloader.cleanup_file(filepath)
