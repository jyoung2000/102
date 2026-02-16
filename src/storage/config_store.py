import json
from pathlib import Path
from src.utils.logging import logger

CONFIG_PATH = Path("/data/config.json")
SOURCE_STATS_PATH = Path("/data/source_stats.json")


class ConfigStore:
    """Persists all settings to /data/config.json. Survives container restarts."""

    def __init__(self):
        self._config = self._defaults()
        self._source_stats = self._load_source_stats()
        self._load()
        self._init_source_overrides()

    def _defaults(self) -> dict:
        return {
            "baserow": {
                "api_url": "",
                "api_token": "",
                "table_id": 810,
            },
            "scraper": {
                "request_delay_seconds": 2,
                "max_concurrent_downloads": 3,
                "max_pages_per_site": 50,
                "page_load_timeout_seconds": 30,
            },
            "resolution": {
                "min_width": 1920,
                "min_height": 1080,
                "target_aspect_ratios": ["16:9", "9:16", "21:9", "4:3", "3:2", "1:1"],
            },
            "compression": {
                "quality": 85,
            },
            "deduplication": {
                "enabled": True,
                "hamming_distance_threshold": 8,
                "check_baserow": True,
            },
            "sources": {},  # {source_id: {"enabled": bool}} — overrides per source
        }

    def _init_source_overrides(self):
        """Ensure the sources section exists."""
        if "sources" not in self._config:
            self._config["sources"] = {}

    # --- Source stats persistence ---

    def _load_source_stats(self) -> dict:
        """Load per-source scraping stats from disk."""
        try:
            if SOURCE_STATS_PATH.exists():
                with open(SOURCE_STATS_PATH) as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load source stats: {e}")
        return {}

    def _save_source_stats(self):
        """Persist per-source stats to disk."""
        try:
            SOURCE_STATS_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(SOURCE_STATS_PATH, "w") as f:
                json.dump(self._source_stats, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save source stats: {e}")

    def get_source_stats(self, source_id: str = None) -> dict:
        """Get per-source stats. None returns all."""
        if source_id:
            return self._source_stats.get(source_id, {
                "total_uploaded": 0, "total_discovered": 0,
                "total_errors": 0, "total_duplicates": 0,
                "last_scraped": None,
            })
        return self._source_stats.copy()

    def update_source_stats(self, source_id: str, uploaded: int, discovered: int,
                            errors: int, duplicates: int):
        """Update stats for a specific source after a scrape job completes."""
        if source_id not in self._source_stats:
            self._source_stats[source_id] = {
                "total_uploaded": 0, "total_discovered": 0,
                "total_errors": 0, "total_duplicates": 0,
                "last_scraped": None,
            }
        s = self._source_stats[source_id]
        s["total_uploaded"] += uploaded
        s["total_discovered"] += discovered
        s["total_errors"] += errors
        s["total_duplicates"] += duplicates
        from datetime import datetime
        s["last_scraped"] = datetime.now().isoformat()
        self._save_source_stats()

    # --- Source enabled/disabled ---

    def is_source_enabled(self, source_id: str, default: bool = False) -> bool:
        """Check if a source is enabled (user override or catalog default)."""
        overrides = self._config.get("sources", {})
        if source_id in overrides:
            return overrides[source_id].get("enabled", default)
        return default

    def set_source_enabled(self, source_id: str, enabled: bool):
        """Toggle a source on or off."""
        if "sources" not in self._config:
            self._config["sources"] = {}
        if source_id not in self._config["sources"]:
            self._config["sources"][source_id] = {}
        self._config["sources"][source_id]["enabled"] = enabled
        self._save()

    def get_source_overrides(self) -> dict:
        """Get all user overrides for sources."""
        return self._config.get("sources", {}).copy()

    def _load(self):
        """Load config from disk, merging with defaults."""
        try:
            if CONFIG_PATH.exists():
                with open(CONFIG_PATH, "r") as f:
                    saved = json.load(f)
                self._deep_merge(self._config, saved)
                logger.info("Loaded config from /data/config.json")
        except Exception as e:
            logger.warning(f"Could not load config: {e}, using defaults")

    def _save(self):
        """Save config to disk."""
        try:
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_PATH, "w") as f:
                json.dump(self._config, f, indent=2)
            logger.info("Config saved to /data/config.json")
        except Exception as e:
            logger.error(f"Could not save config: {e}")

    def _deep_merge(self, base: dict, override: dict):
        """Merge override into base, preserving nested structure."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def get(self, section: str = None, key: str = None):
        """Get a config value. section=None returns entire config."""
        if section is None:
            return self._config.copy()
        section_data = self._config.get(section, {})
        if key is None:
            return section_data.copy() if isinstance(section_data, dict) else section_data
        return section_data.get(key)

    def update(self, section: str, data: dict):
        """Update a config section and save."""
        if section not in self._config:
            self._config[section] = {}
        if isinstance(self._config[section], dict):
            self._config[section].update(data)
        else:
            self._config[section] = data
        self._save()

    def update_all(self, data: dict):
        """Update entire config and save."""
        self._deep_merge(self._config, data)
        self._save()

    def get_masked(self) -> dict:
        """Get config with sensitive fields masked (for API responses)."""
        config = self.get()
        if config.get("baserow", {}).get("api_token"):
            token = config["baserow"]["api_token"]
            config["baserow"]["api_token"] = f"***{token[-3:]}" if len(token) > 3 else "***"
        return config

    def is_baserow_configured(self) -> bool:
        """Check if Baserow connection is configured."""
        br = self._config.get("baserow", {})
        return bool(br.get("api_url") and br.get("api_token"))
