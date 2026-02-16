import json
from pathlib import Path
from src.utils.logging import logger

CONFIG_PATH = Path("/data/config.json")


class ConfigStore:
    """Persists all settings to /data/config.json. Survives container restarts."""

    def __init__(self):
        self._config = self._defaults()
        self._load()

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
        }

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
