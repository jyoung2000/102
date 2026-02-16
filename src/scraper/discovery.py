import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from src.utils.logging import logger

# Minimum dimensions to consider an image a wallpaper candidate
MIN_CANDIDATE_WIDTH = 400
MIN_CANDIDATE_HEIGHT = 300

# Patterns that indicate high-resolution images in URLs
HIGHRES_URL_PATTERNS = [
    r'\d{3,4}x\d{3,4}',  # 1920x1080, 3840x2160
    r'[-_](4k|8k|uhd|hd|fhd|qhd|2k)',
    r'[-_](original|full|large|big|high|max|raw)',
    r'/original/',
    r'/full/',
    r'/download/',
    r'/large/',
    r'/w_\d{4}/',
    r'[-_](3840|2560|1920|1440)',
]

# URL patterns that indicate non-wallpaper images (icons, avatars, etc)
REJECT_PATTERNS = [
    r'(favicon|icon|logo|avatar|badge|sprite|emoji|thumb(nail)?[-_]?(s|small|tiny|xs))',
    r'(pixel|spacer|blank|transparent|placeholder|loading|spinner)',
    r'(banner|ad[-_]|advert|promo|popup|overlay)',
    r'\.(gif|svg|ico)(\?|$)',
    r'(1x1|2x2|10x10)',
    r'/avatars?/',
    r'/icons?/',
    r'/logos?/',
    r'(gravatar|googleusercontent.*=s\d{2})',
    r'data:image',
]

# File extensions we care about
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.tif'}


def is_image_url(url: str) -> bool:
    """Check if URL looks like an image."""
    parsed = urlparse(url.lower().split('?')[0])
    path = parsed.path
    return any(path.endswith(ext) for ext in IMAGE_EXTENSIONS)


def should_reject(url: str) -> bool:
    """Check if URL matches rejection patterns (icons, logos, etc)."""
    url_lower = url.lower()
    for pattern in REJECT_PATTERNS:
        if re.search(pattern, url_lower):
            return True
    return False


def score_image_url(url: str, attrs: dict = None, link_text: str = "") -> float:
    """Score an image URL based on how likely it is to be a wallpaper."""
    score = 0.0
    url_lower = url.lower()

    if should_reject(url_lower):
        return -1.0

    if not is_image_url(url_lower) and 'image' not in url_lower:
        return -1.0

    # URL pattern scores
    for pattern in HIGHRES_URL_PATTERNS:
        if re.search(pattern, url_lower):
            score += 3.0
            break

    # Dimension extraction from URL
    dim_match = re.search(r'(\d{3,5})x(\d{3,5})', url_lower)
    if dim_match:
        w, h = int(dim_match.group(1)), int(dim_match.group(2))
        if w >= 1920 or h >= 1920:
            score += 5.0
        elif w >= 1280 or h >= 1280:
            score += 3.0

    # File extension
    if any(url_lower.endswith(ext) for ext in ['.jpg', '.jpeg', '.png']):
        score += 1.0
    if url_lower.endswith('.webp'):
        score += 0.5

    # Attribute-based scoring
    if attrs:
        # Width/height attributes
        width = _parse_dim(attrs.get('width', ''))
        height = _parse_dim(attrs.get('height', ''))
        if width and height:
            if width >= 1920 or height >= 1920:
                score += 4.0
            elif width >= 800 or height >= 800:
                score += 2.0
            elif width < MIN_CANDIDATE_WIDTH or height < MIN_CANDIDATE_HEIGHT:
                score -= 3.0

        # Alt text suggesting wallpaper
        alt = (attrs.get('alt', '') or '').lower()
        if any(kw in alt for kw in ['wallpaper', 'desktop', 'background', 'landscape', 'nature']):
            score += 2.0

    # Link text scoring
    if link_text:
        link_lower = link_text.lower()
        if any(kw in link_lower for kw in ['download', 'full size', 'original', 'hd', '4k']):
            score += 4.0

    return score


def _parse_dim(val: str) -> int | None:
    """Parse a dimension value (might be '1920', '1920px', etc)."""
    if not val:
        return None
    match = re.search(r'(\d+)', str(val))
    if match:
        return int(match.group(1))
    return None


def discover_images(html: str, page_url: str) -> list[dict]:
    """
    Discover wallpaper candidate images from HTML.
    Returns list of {url, score, width, height, alt} sorted by score desc.
    """
    soup = BeautifulSoup(html, "lxml")
    candidates = {}
    base_url = page_url

    # 1. Direct <img> tags
    for img in soup.find_all("img"):
        urls = _get_image_urls_from_tag(img, base_url)
        for url in urls:
            if url not in candidates:
                score = score_image_url(url, dict(img.attrs))
                if score >= 0:
                    candidates[url] = {
                        "url": url,
                        "score": score,
                        "width": _parse_dim(img.get("width", "")),
                        "height": _parse_dim(img.get("height", "")),
                        "alt": img.get("alt", ""),
                    }

    # 2. <a> tags linking to images
    for a_tag in soup.find_all("a", href=True):
        href = urljoin(base_url, a_tag["href"])
        if is_image_url(href) and not should_reject(href):
            link_text = a_tag.get_text(strip=True)
            score = score_image_url(href, link_text=link_text)
            if score >= 0:
                if href not in candidates or candidates[href]["score"] < score:
                    candidates[href] = {
                        "url": href,
                        "score": score,
                        "width": None,
                        "height": None,
                        "alt": link_text or "",
                    }

    # 3. <picture> and <source> tags
    for picture in soup.find_all("picture"):
        for source in picture.find_all("source"):
            srcset = source.get("srcset", "")
            urls = _parse_srcset(srcset, base_url)
            for url in urls:
                if not should_reject(url):
                    score = score_image_url(url) + 2.0  # Bonus for <picture>
                    if url not in candidates or candidates[url]["score"] < score:
                        candidates[url] = {
                            "url": url,
                            "score": score,
                            "width": None,
                            "height": None,
                            "alt": "",
                        }

    # 4. og:image and twitter:image meta tags
    for meta in soup.find_all("meta"):
        prop = meta.get("property", "") or meta.get("name", "")
        if prop in ("og:image", "twitter:image", "twitter:image:src"):
            content = meta.get("content", "")
            if content:
                url = urljoin(base_url, content)
                if not should_reject(url):
                    score = score_image_url(url) + 1.0
                    if url not in candidates or candidates[url]["score"] < score:
                        candidates[url] = {
                            "url": url,
                            "score": score,
                            "width": None,
                            "height": None,
                            "alt": "",
                        }

    # Sort by score descending
    results = sorted(candidates.values(), key=lambda x: x["score"], reverse=True)
    return results


def _get_image_urls_from_tag(img, base_url: str) -> list[str]:
    """Extract all possible image URLs from an img tag."""
    urls = []

    # Standard src
    src = img.get("src", "")
    if src and not src.startswith("data:"):
        urls.append(urljoin(base_url, src))

    # data-src (lazy loading)
    for attr in ["data-src", "data-original", "data-lazy-src", "data-full",
                 "data-large", "data-hi-res", "data-zoom"]:
        val = img.get(attr, "")
        if val and not val.startswith("data:"):
            urls.append(urljoin(base_url, val))

    # srcset — pick highest resolution
    srcset = img.get("srcset", "")
    if srcset:
        urls.extend(_parse_srcset(srcset, base_url))

    return urls


def _parse_srcset(srcset: str, base_url: str) -> list[str]:
    """Parse srcset attribute, return URLs sorted by resolution (highest first)."""
    if not srcset:
        return []

    entries = []
    for part in srcset.split(","):
        part = part.strip()
        if not part:
            continue
        pieces = part.split()
        if pieces:
            url = urljoin(base_url, pieces[0])
            # Parse width descriptor (e.g., "800w")
            width = 0
            if len(pieces) > 1:
                desc = pieces[-1]
                w_match = re.match(r'(\d+)w', desc)
                x_match = re.match(r'(\d+(?:\.\d+)?)x', desc)
                if w_match:
                    width = int(w_match.group(1))
                elif x_match:
                    width = int(float(x_match.group(1)) * 1000)
            entries.append((url, width))

    # Sort by width descending, return URLs
    entries.sort(key=lambda x: x[1], reverse=True)
    return [e[0] for e in entries]


def find_pagination(html: str, page_url: str) -> list[str]:
    """Find pagination links (next page, load more)."""
    soup = BeautifulSoup(html, "lxml")
    next_urls = []

    # "Next" links
    next_selectors = [
        'a[rel="next"]',
        'a.next',
        '.next a',
        '.pagination .next a',
        'a:has-text("Next")',
        'a:has-text("next")',
        'a:has-text("→")',
        'a:has-text("»")',
        '.pager-next a',
        'li.next a',
    ]

    for selector in next_selectors:
        try:
            link = soup.select_one(selector)
            if link and link.get("href"):
                url = urljoin(page_url, link["href"])
                if url not in next_urls:
                    next_urls.append(url)
        except Exception:
            continue

    # Page number links
    try:
        current_page = _detect_current_page(page_url)
        if current_page is not None:
            next_page_url = _increment_page_url(page_url, current_page)
            if next_page_url and next_page_url not in next_urls:
                next_urls.append(next_page_url)
    except Exception:
        pass

    return next_urls


def _detect_current_page(url: str) -> int | None:
    """Try to detect the current page number from URL."""
    patterns = [
        r'[?&]page=(\d+)',
        r'[?&]p=(\d+)',
        r'/page/(\d+)',
        r'/p/(\d+)',
        r'[?&]offset=(\d+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return int(match.group(1))
    return None


def _increment_page_url(url: str, current_page: int) -> str | None:
    """Generate URL for the next page."""
    replacements = [
        (r'([?&]page=)\d+', rf'\g<1>{current_page + 1}'),
        (r'([?&]p=)\d+', rf'\g<1>{current_page + 1}'),
        (r'(/page/)\d+', rf'\g<1>{current_page + 1}'),
        (r'(/p/)\d+', rf'\g<1>{current_page + 1}'),
    ]
    for pattern, replacement in replacements:
        new_url = re.sub(pattern, replacement, url)
        if new_url != url:
            return new_url
    return None
