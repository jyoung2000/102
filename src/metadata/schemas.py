from pydantic import BaseModel, Field
from typing import Optional


class WallpaperRow(BaseModel):
    """Pydantic model mapping to Baserow table fields."""
    wallpaperTitle: str
    Width: int
    Height: int
    imgUrl: str
    Alt_Text: str = ""
    Artist_text: str = ""
    Artist_link: str = ""
    IsMobile: bool = False
    IsReported: bool = False
    IsVip: bool = False
    OrgUploadDate: str = ""
    CategoryTags: str = ""
    imageFile: list = Field(default_factory=list)
    imgHash: str = ""

    def to_baserow_dict(self) -> dict:
        """Convert to Baserow API format with exact field names (including spaces)."""
        return {
            "wallpaperTitle": self.wallpaperTitle,
            "Width": self.Width,
            "Height": self.Height,
            "imgUrl": self.imgUrl,
            "Alt Text": self.Alt_Text,
            "Artist text": self.Artist_text,
            "Artist link": self.Artist_link,
            "IsMobile": self.IsMobile,
            "IsReported": self.IsReported,
            "IsVip": self.IsVip,
            "OrgUploadDate": self.OrgUploadDate,
            "CategoryTags": self.CategoryTags,
            "imageFile": self.imageFile,
            "imgHash": self.imgHash,
        }


class ScrapedImageInfo(BaseModel):
    """Information about a discovered image before processing."""
    url: str
    page_url: str
    score: float = 0.0
    width: Optional[int] = None
    height: Optional[int] = None
    artist_name: str = ""
    artist_link: str = ""
    upload_date: str = ""
    existing_tags: list[str] = Field(default_factory=list)
    alt_text: str = ""
    title: str = ""
