import logging
import sys
from pathlib import Path


def setup_logging() -> logging.Logger:
    """Set up logging. NEVER raises an exception — falls back to console."""
    logger = logging.getLogger("wallpaper_scraper")
    logger.setLevel(logging.INFO)

    # Prevent duplicate handlers on repeated calls
    if logger.handlers:
        return logger

    # Console handler (always works)
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))
    logger.addHandler(console)

    # File handler (best-effort, never crash)
    try:
        log_dir = Path("/data/logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_dir / "scraper.log")
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        ))
        logger.addHandler(file_handler)
    except Exception:
        logger.warning("Could not create log file at /data/logs/scraper.log — using console only")

    return logger


# Module-level logger — safe to import anywhere, will NEVER crash
logger = setup_logging()
