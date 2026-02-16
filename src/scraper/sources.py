"""
Built-in wallpaper source catalog.

Each source is a known wallpaper site with curated scraping URLs.
The generic adapter handles the actual scraping — these are just
starting points with metadata so the user can toggle them on/off.
"""

# Each source entry:
#   id          - unique slug (used as key in config)
#   name        - display name
#   description - short blurb for the GUI
#   category    - grouping for the GUI (Nature, Abstract, etc.)
#   urls        - list of scraping entry points for this source
#   max_pages   - default max pages to crawl (override per-source)
#   enabled     - default enabled state on first launch

WALLPAPER_SOURCES = [
    # --- Nature & Landscape ---
    {
        "id": "wallhaven_nature",
        "name": "Wallhaven - Nature",
        "description": "Community-curated nature and landscape wallpapers, sorted by favorites",
        "category": "Nature",
        "urls": [
            "https://wallhaven.cc/search?q=nature+landscape&categories=100&purity=100&sorting=favorites&order=desc",
        ],
        "max_pages": 10,
        "enabled": True,
    },
    {
        "id": "wallhaven_mountains",
        "name": "Wallhaven - Mountains",
        "description": "Mountain scenery wallpapers with high resolution",
        "category": "Nature",
        "urls": [
            "https://wallhaven.cc/search?q=mountain+scenery&categories=100&purity=100&sorting=favorites&order=desc",
        ],
        "max_pages": 10,
        "enabled": True,
    },
    {
        "id": "wallhaven_ocean",
        "name": "Wallhaven - Ocean & Beach",
        "description": "Ocean, beach, and coastal wallpapers",
        "category": "Nature",
        "urls": [
            "https://wallhaven.cc/search?q=ocean+beach+sea&categories=100&purity=100&sorting=favorites&order=desc",
        ],
        "max_pages": 10,
        "enabled": False,
    },
    {
        "id": "wallhaven_forest",
        "name": "Wallhaven - Forest",
        "description": "Forests, trees, and woodland landscapes",
        "category": "Nature",
        "urls": [
            "https://wallhaven.cc/search?q=forest+trees+woods&categories=100&purity=100&sorting=favorites&order=desc",
        ],
        "max_pages": 10,
        "enabled": False,
    },
    {
        "id": "wallpaperflare_nature",
        "name": "WallpaperFlare - Nature",
        "description": "Nature and landscape wallpapers from WallpaperFlare",
        "category": "Nature",
        "urls": [
            "https://www.wallpaperflare.com/search?wallpaper=nature+landscape",
        ],
        "max_pages": 10,
        "enabled": False,
    },
    # --- Space & Astronomy ---
    {
        "id": "wallhaven_space",
        "name": "Wallhaven - Space",
        "description": "Space, galaxies, nebulae, and astronomy wallpapers",
        "category": "Space",
        "urls": [
            "https://wallhaven.cc/search?q=space+galaxy+nebula&categories=100&purity=100&sorting=favorites&order=desc",
        ],
        "max_pages": 10,
        "enabled": True,
    },
    {
        "id": "wallpaperflare_space",
        "name": "WallpaperFlare - Space",
        "description": "Astronomy and space imagery from WallpaperFlare",
        "category": "Space",
        "urls": [
            "https://www.wallpaperflare.com/search?wallpaper=space+galaxy+stars",
        ],
        "max_pages": 8,
        "enabled": False,
    },
    # --- City & Architecture ---
    {
        "id": "wallhaven_city",
        "name": "Wallhaven - Cityscape",
        "description": "Urban skylines, cityscapes, and architecture",
        "category": "City",
        "urls": [
            "https://wallhaven.cc/search?q=cityscape+skyline&categories=100&purity=100&sorting=favorites&order=desc",
        ],
        "max_pages": 10,
        "enabled": False,
    },
    {
        "id": "wallhaven_night_city",
        "name": "Wallhaven - Night City",
        "description": "Cities at night with neon lights and reflections",
        "category": "City",
        "urls": [
            "https://wallhaven.cc/search?q=night+city+neon&categories=100&purity=100&sorting=favorites&order=desc",
        ],
        "max_pages": 8,
        "enabled": False,
    },
    # --- Abstract & Art ---
    {
        "id": "wallhaven_abstract",
        "name": "Wallhaven - Abstract",
        "description": "Abstract patterns, gradients, and digital art",
        "category": "Abstract",
        "urls": [
            "https://wallhaven.cc/search?q=abstract+gradient&categories=100&purity=100&sorting=favorites&order=desc",
        ],
        "max_pages": 10,
        "enabled": True,
    },
    {
        "id": "wallhaven_minimalist",
        "name": "Wallhaven - Minimalist",
        "description": "Clean, minimal wallpapers with simple compositions",
        "category": "Abstract",
        "urls": [
            "https://wallhaven.cc/search?q=minimalist+minimal&categories=100&purity=100&sorting=favorites&order=desc",
        ],
        "max_pages": 8,
        "enabled": False,
    },
    {
        "id": "wallpaperflare_abstract",
        "name": "WallpaperFlare - Abstract",
        "description": "Abstract and artistic wallpapers",
        "category": "Abstract",
        "urls": [
            "https://www.wallpaperflare.com/search?wallpaper=abstract+art+colorful",
        ],
        "max_pages": 8,
        "enabled": False,
    },
    # --- Animals ---
    {
        "id": "wallhaven_animals",
        "name": "Wallhaven - Animals",
        "description": "Wildlife and animal photography wallpapers",
        "category": "Animals",
        "urls": [
            "https://wallhaven.cc/search?q=wildlife+animal&categories=100&purity=100&sorting=favorites&order=desc",
        ],
        "max_pages": 8,
        "enabled": False,
    },
    # --- Dark & Moody ---
    {
        "id": "wallhaven_dark",
        "name": "Wallhaven - Dark",
        "description": "Dark themed wallpapers, AMOLED-friendly",
        "category": "Dark",
        "urls": [
            "https://wallhaven.cc/search?q=dark+amoled+black&categories=100&purity=100&sorting=favorites&order=desc",
        ],
        "max_pages": 10,
        "enabled": True,
    },
    {
        "id": "wallpaperflare_dark",
        "name": "WallpaperFlare - Dark",
        "description": "Dark and moody wallpapers from WallpaperFlare",
        "category": "Dark",
        "urls": [
            "https://www.wallpaperflare.com/search?wallpaper=dark+black+amoled",
        ],
        "max_pages": 8,
        "enabled": False,
    },
    # --- Seasonal ---
    {
        "id": "wallhaven_autumn",
        "name": "Wallhaven - Autumn",
        "description": "Autumn foliage, golden leaves, and fall scenery",
        "category": "Seasonal",
        "urls": [
            "https://wallhaven.cc/search?q=autumn+fall+foliage&categories=100&purity=100&sorting=favorites&order=desc",
        ],
        "max_pages": 8,
        "enabled": False,
    },
    {
        "id": "wallhaven_winter",
        "name": "Wallhaven - Winter",
        "description": "Snow, ice, and winter landscapes",
        "category": "Seasonal",
        "urls": [
            "https://wallhaven.cc/search?q=winter+snow+ice&categories=100&purity=100&sorting=favorites&order=desc",
        ],
        "max_pages": 8,
        "enabled": False,
    },
    # --- HDQWalls ---
    {
        "id": "hdqwalls_nature",
        "name": "HDQWalls - Nature",
        "description": "High-quality nature wallpapers from HDQWalls",
        "category": "Nature",
        "urls": [
            "https://hdqwalls.com/category/nature-wallpapers",
        ],
        "max_pages": 8,
        "enabled": False,
    },
    {
        "id": "hdqwalls_space",
        "name": "HDQWalls - Space",
        "description": "Space and astronomy wallpapers from HDQWalls",
        "category": "Space",
        "urls": [
            "https://hdqwalls.com/category/space-wallpapers",
        ],
        "max_pages": 8,
        "enabled": False,
    },
    {
        "id": "hdqwalls_abstract",
        "name": "HDQWalls - Abstract",
        "description": "Abstract and digital art from HDQWalls",
        "category": "Abstract",
        "urls": [
            "https://hdqwalls.com/category/abstract-wallpapers",
        ],
        "max_pages": 8,
        "enabled": False,
    },
    # --- Mobile ---
    {
        "id": "wallhaven_mobile",
        "name": "Wallhaven - Mobile (Portrait)",
        "description": "Portrait-oriented wallpapers for phones",
        "category": "Mobile",
        "urls": [
            "https://wallhaven.cc/search?q=&categories=100&purity=100&sorting=favorites&order=desc&ratios=portrait",
        ],
        "max_pages": 10,
        "enabled": False,
    },
    # --- Photography ---
    {
        "id": "wallhaven_sunset",
        "name": "Wallhaven - Sunset",
        "description": "Sunset and sunrise golden hour photography",
        "category": "Nature",
        "urls": [
            "https://wallhaven.cc/search?q=sunset+sunrise+golden+hour&categories=100&purity=100&sorting=favorites&order=desc",
        ],
        "max_pages": 8,
        "enabled": False,
    },
    {
        "id": "wallhaven_macro",
        "name": "Wallhaven - Macro",
        "description": "Macro photography and close-up shots",
        "category": "Nature",
        "urls": [
            "https://wallhaven.cc/search?q=macro+closeup+detail&categories=100&purity=100&sorting=favorites&order=desc",
        ],
        "max_pages": 6,
        "enabled": False,
    },
    # --- Top rated / Curated ---
    {
        "id": "wallhaven_top_all",
        "name": "Wallhaven - Top Rated (All Time)",
        "description": "The highest-rated wallpapers on Wallhaven across all categories",
        "category": "Curated",
        "urls": [
            "https://wallhaven.cc/search?q=&categories=100&purity=100&sorting=favorites&order=desc&topRange=1y",
        ],
        "max_pages": 15,
        "enabled": True,
    },
    {
        "id": "wallhaven_top_4k",
        "name": "Wallhaven - Top 4K",
        "description": "Top-rated 4K (3840x2160) wallpapers",
        "category": "Curated",
        "urls": [
            "https://wallhaven.cc/search?q=&categories=100&purity=100&sorting=favorites&order=desc&atleast=3840x2160",
        ],
        "max_pages": 10,
        "enabled": False,
    },
    {
        "id": "wallhaven_top_ultrawide",
        "name": "Wallhaven - Top Ultrawide",
        "description": "Top-rated ultrawide (21:9) wallpapers",
        "category": "Curated",
        "urls": [
            "https://wallhaven.cc/search?q=&categories=100&purity=100&sorting=favorites&order=desc&ratios=21x9",
        ],
        "max_pages": 8,
        "enabled": False,
    },
]


def get_source_by_id(source_id: str) -> dict | None:
    """Look up a source by its ID."""
    for source in WALLPAPER_SOURCES:
        if source["id"] == source_id:
            return source.copy()
    return None


def get_all_categories() -> list[str]:
    """Get unique category list in display order."""
    seen = set()
    cats = []
    for source in WALLPAPER_SOURCES:
        cat = source["category"]
        if cat not in seen:
            seen.add(cat)
            cats.append(cat)
    return cats


def get_default_enabled_ids() -> list[str]:
    """Get IDs of sources that are enabled by default."""
    return [s["id"] for s in WALLPAPER_SOURCES if s.get("enabled", False)]
