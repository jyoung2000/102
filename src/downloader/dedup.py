from pathlib import Path
import imagehash
from PIL import Image
from src.utils.logging import logger


class DedupChecker:
    """Perceptual hash deduplication."""

    def __init__(self, hamming_threshold: int = 8):
        self.threshold = hamming_threshold
        self._session_hashes: set[str] = set()

    def compute_hash(self, image_path: Path) -> str:
        """Compute perceptual hash for an image."""
        with Image.open(image_path) as img:
            phash = imagehash.phash(img)
            return str(phash)

    def is_duplicate_in_session(self, img_hash: str) -> bool:
        """Check if this hash is a duplicate within the current scraping session."""
        for existing_hash in self._session_hashes:
            distance = _hamming_distance(img_hash, existing_hash)
            if distance <= self.threshold:
                logger.info(f"Duplicate in session: hash={img_hash}, distance={distance}")
                return True
        return False

    def add_to_session(self, img_hash: str):
        """Add a hash to the session set."""
        self._session_hashes.add(img_hash)

    def clear_session(self):
        """Clear session hashes."""
        self._session_hashes.clear()


def _hamming_distance(hash1: str, hash2: str) -> int:
    """Calculate Hamming distance between two hex hash strings."""
    try:
        h1 = imagehash.hex_to_hash(hash1)
        h2 = imagehash.hex_to_hash(hash2)
        return h1 - h2
    except Exception:
        # If hashes can't be compared, treat as different
        return 999
