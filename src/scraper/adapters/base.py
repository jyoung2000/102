from abc import ABC, abstractmethod
from src.metadata.schemas import ScrapedImageInfo


class BaseAdapter(ABC):
    """Abstract base class for site adapters."""

    @abstractmethod
    async def discover(self, page_html: str, page_url: str) -> list[ScrapedImageInfo]:
        """Discover wallpaper images from page content."""
        ...

    @abstractmethod
    async def get_full_resolution_url(self, image_info: ScrapedImageInfo, page_html: str) -> str:
        """Resolve the full-resolution download URL for an image."""
        ...

    @abstractmethod
    async def get_next_page(self, page_html: str, page_url: str) -> str | None:
        """Get the URL of the next page, or None if no more pages."""
        ...
