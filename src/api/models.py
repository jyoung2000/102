from pydantic import BaseModel, Field
from typing import Optional


class ScrapeRequest(BaseModel):
    urls: list[str] = Field(..., min_length=1, description="URLs to scrape")
    max_pages: Optional[int] = Field(None, description="Override max pages per site")
    aspect_ratios: Optional[list[str]] = Field(None, description="Filter aspect ratios")
    min_width: Optional[int] = Field(None, description="Override min width")
    min_height: Optional[int] = Field(None, description="Override min height")


class ScrapeResponse(BaseModel):
    job_id: str
    status: str
    message: str


class JobStatus(BaseModel):
    job_id: str
    status: str
    urls: list[str]
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    progress: dict = {}


class SettingsUpdate(BaseModel):
    scraper: Optional[dict] = None
    resolution: Optional[dict] = None
    compression: Optional[dict] = None
    deduplication: Optional[dict] = None


class BaserowConfig(BaseModel):
    api_url: str = ""
    api_token: str = ""
    table_id: int = 810


class HealthResponse(BaseModel):
    status: str
    browser_ready: bool
    ai_model_loaded: bool
    baserow_configured: bool
    uptime_seconds: float


class StatsResponse(BaseModel):
    total_scraped: int = 0
    total_uploaded: int = 0
    total_duplicates: int = 0
    total_errors: int = 0
    aspect_ratio_breakdown: dict = {}
    site_breakdown: dict = {}
    ai_model: str = "BLIP-base"
    avg_inference_time: float = 0.0
    uptime_seconds: float = 0.0
    browser_status: str = "unknown"


class SourceToggle(BaseModel):
    enabled: bool


class ScrapeSourcesRequest(BaseModel):
    source_ids: Optional[list[str]] = Field(None, description="Specific source IDs to scrape. None = all enabled.")
