import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

from src.scraper.adapters.base import BaseAdapter
from src.scraper.discovery import (
    discover_images, find_pagination, is_image_url,
    score_image_url, should_reject, _parse_srcset
)
from src.metadata.schemas import ScrapedImageInfo
from src.metadata.extractor import extract_artist_info, extract_upload_date, extract_existing_tags
from src.utils.logging import logger


class GenericAdapter(BaseAdapter):
    """
    Universal wallpaper adapter — works on ANY wallpaper site with zero site-specific code.

    Discovery strategy:
    1. Scan page for all <img>, <a href=*.jpg>, <picture>, <source>, og:image, etc.
    2. Score each candidate by dimensions, URL patterns, link text, position
    3. Filter by minimum score threshold
    4. For each candidate, try to find higher-resolution version (download links, srcset)
    5. Extract metadata (artist, date, tags) from page
    """

    def __init__(self, min_score: float = 1.0):
        self.min_score = min_score

    async def discover(self, page_html: str, page_url: str) -> list[ScrapedImageInfo]:
        """Discover wallpaper candidate images from any page."""
        soup = BeautifulSoup(page_html, "lxml")

        # Get base image candidates
        raw_candidates = discover_images(page_html, page_url)

        # Extract page-level metadata
        artist_name, artist_link = extract_artist_info(soup, page_url)
        upload_date = extract_upload_date(soup)
        existing_tags = extract_existing_tags(soup)

        results = []
        seen_urls = set()

        for candidate in raw_candidates:
            if candidate["score"] < self.min_score:
                continue

            url = candidate["url"]
            if url in seen_urls:
                continue
            seen_urls.add(url)

            # Try to find a higher-resolution version
            full_url = self._find_higher_res(url, soup, page_url)
            if full_url != url:
                logger.info(f"Upgraded URL: {url[:80]}... -> {full_url[:80]}...")

            info = ScrapedImageInfo(
                url=full_url,
                page_url=page_url,
                score=candidate["score"],
                width=candidate.get("width"),
                height=candidate.get("height"),
                artist_name=artist_name,
                artist_link=artist_link,
                upload_date=upload_date,
                existing_tags=existing_tags,
                alt_text=candidate.get("alt", ""),
                title=candidate.get("alt", ""),
            )
            results.append(info)

        logger.info(f"Discovered {len(results)} candidates from {page_url}")
        return results

    async def get_full_resolution_url(self, image_info: ScrapedImageInfo, page_html: str) -> str:
        """Try to resolve the highest resolution URL available."""
        soup = BeautifulSoup(page_html, "lxml")
        return self._find_higher_res(image_info.url, soup, image_info.page_url)

    async def get_next_page(self, page_html: str, page_url: str) -> str | None:
        """Find the next page URL."""
        next_urls = find_pagination(page_html, page_url)
        return next_urls[0] if next_urls else None

    def _find_higher_res(self, url: str, soup: BeautifulSoup, page_url: str) -> str:
        """Try to find a higher-resolution version of the image."""
        best_url = url
        best_score = score_image_url(url)

        # Strategy 1: Check if the image is wrapped in a link to a larger version
        for a_tag in soup.find_all("a", href=True):
            # Find <a> tags that contain an <img> with our URL
            img_children = a_tag.find_all("img")
            for img in img_children:
                img_src = img.get("src", "")
                img_data_src = img.get("data-src", "")
                if url.endswith(img_src.split("/")[-1]) or url.endswith(img_data_src.split("/")[-1]):
                    href = urljoin(page_url, a_tag["href"])
                    if is_image_url(href) and not should_reject(href):
                        new_score = score_image_url(href)
                        if new_score > best_score:
                            best_url = href
                            best_score = new_score

        # Strategy 2: Look for download links near the image
        download_patterns = [
            r'download',
            r'full[_-]?size',
            r'original',
            r'high[_-]?res',
            r'full[_-]?resolution',
        ]

        for a_tag in soup.find_all("a", href=True):
            text = (a_tag.get_text(strip=True) or "").lower()
            href_str = a_tag["href"].lower()
            classes = " ".join(a_tag.get("class", []))

            for pattern in download_patterns:
                if re.search(pattern, text) or re.search(pattern, href_str) or re.search(pattern, classes):
                    href = urljoin(page_url, a_tag["href"])
                    if is_image_url(href) and not should_reject(href):
                        new_score = score_image_url(href) + 5.0
                        if new_score > best_score:
                            best_url = href
                            best_score = new_score
                    break

        # Strategy 3: URL manipulation — try common high-res URL patterns
        url_upgrades = self._generate_url_upgrades(url)
        for upgraded_url in url_upgrades:
            new_score = score_image_url(upgraded_url)
            if new_score > best_score:
                best_url = upgraded_url
                best_score = new_score

        return best_url

    def _generate_url_upgrades(self, url: str) -> list[str]:
        """Generate potential high-resolution URL variants."""
        upgrades = []

        # Replace thumbnail indicators with full-size
        replacements = [
            (r'/thumb(nail)?s?/', '/'),
            (r'/small/', '/large/'),
            (r'/medium/', '/large/'),
            (r'/preview/', '/original/'),
            (r'/thumb/', '/original/'),
            (r'[-_](small|thumb|preview|medium|s|m)\.(jpg|jpeg|png|webp)',
             r'.\2'),
            (r'[-_](150|200|300|400|500|600|800)\.(jpg|jpeg|png|webp)',
             r'.\2'),
            (r'\?w=\d+&?', '?'),
            (r'\?width=\d+&?', '?'),
            (r'\?h=\d+&?', '?'),
            (r'\?height=\d+&?', '?'),
            (r'\?resize=\d+[x,]\d+&?', '?'),
            (r'\?fit=\d+[x,]\d+&?', '?'),
        ]

        for pattern, replacement in replacements:
            new_url = re.sub(pattern, replacement, url, flags=re.IGNORECASE)
            # Clean up trailing ? or &
            new_url = re.sub(r'[?&]$', '', new_url)
            if new_url != url:
                upgrades.append(new_url)

        return upgrades
