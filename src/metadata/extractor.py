import re
from datetime import datetime
from bs4 import BeautifulSoup
from src.utils.logging import logger


def extract_artist_info(soup: BeautifulSoup, page_url: str) -> tuple[str, str]:
    """Extract artist name and link from page markup."""
    artist_name = ""
    artist_link = ""

    # Common patterns for artist attribution
    selectors = [
        # Direct artist/author links
        'a[rel="author"]',
        'a.author',
        'a.artist',
        '.author a',
        '.artist a',
        '.photographer a',
        '.creator a',
        '[itemprop="author"] a',
        '[itemprop="creator"] a',
        # User profile links
        '.user-info a',
        '.uploader a',
        '.submitted-by a',
        '.posted-by a',
    ]

    for selector in selectors:
        try:
            elem = soup.select_one(selector)
            if elem:
                name = elem.get_text(strip=True)
                if name and len(name) < 100:
                    artist_name = name
                    href = elem.get("href", "")
                    if href:
                        if href.startswith("/"):
                            from urllib.parse import urljoin
                            artist_link = urljoin(page_url, href)
                        elif href.startswith("http"):
                            artist_link = href
                    break
        except Exception:
            continue

    return artist_name, artist_link


def extract_upload_date(soup: BeautifulSoup) -> str:
    """Extract upload/publish date from page markup. Returns YYYY-MM-DD or today."""
    # Try structured data first
    date_selectors = [
        'time[datetime]',
        '[itemprop="datePublished"]',
        '[itemprop="uploadDate"]',
        'meta[property="article:published_time"]',
        '.date',
        '.upload-date',
        '.published',
    ]

    for selector in date_selectors:
        try:
            elem = soup.select_one(selector)
            if elem:
                date_str = elem.get("datetime") or elem.get("content") or elem.get_text(strip=True)
                if date_str:
                    parsed = _parse_date(date_str)
                    if parsed:
                        return parsed
        except Exception:
            continue

    return datetime.now().strftime("%Y-%m-%d")


def _parse_date(date_str: str) -> str | None:
    """Try to parse various date formats into YYYY-MM-DD."""
    formats = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d",
        "%B %d, %Y",
        "%b %d, %Y",
        "%d %B %Y",
        "%d %b %Y",
        "%m/%d/%Y",
        "%d/%m/%Y",
    ]

    # Strip timezone offset like +00:00 for simpler parsing
    clean = re.sub(r'\+\d{2}:\d{2}$', '', date_str.strip())

    for fmt in formats:
        try:
            dt = datetime.strptime(clean, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    # Try regex extraction
    match = re.search(r'(\d{4})-(\d{2})-(\d{2})', date_str)
    if match:
        return match.group(0)

    return None


def extract_existing_tags(soup: BeautifulSoup) -> list[str]:
    """Extract any existing tags/categories from the page."""
    tags = []

    tag_selectors = [
        '.tag',
        '.tags a',
        '[rel="tag"]',
        '.category a',
        '.categories a',
        '.keyword',
        '.keywords a',
        'meta[name="keywords"]',
    ]

    for selector in tag_selectors:
        try:
            if selector.startswith('meta'):
                elem = soup.select_one(selector)
                if elem:
                    content = elem.get("content", "")
                    tags.extend([t.strip() for t in content.split(",") if t.strip()])
            else:
                elems = soup.select(selector)
                for elem in elems[:30]:
                    text = elem.get_text(strip=True)
                    if text and len(text) < 50:
                        tags.append(text)
        except Exception:
            continue

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for tag in tags:
        lower = tag.lower()
        if lower not in seen:
            seen.add(lower)
            unique.append(tag)

    return unique[:30]
