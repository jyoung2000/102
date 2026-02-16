import time
from fastapi import APIRouter, Request, HTTPException
from src.api.models import (
    ScrapeRequest, ScrapeResponse, JobStatus,
    SettingsUpdate, BaserowConfig, HealthResponse, StatsResponse
)
from src.storage.baserow import BaserowClient
from src.utils.logging import logger

router = APIRouter(prefix="/api")


@router.get("/health")
async def health(request: Request) -> dict:
    """Health check endpoint."""
    return {
        "status": "ok",
        "browser_ready": bool(request.app.state.browser and request.app.state.browser.ready),
        "ai_model_loaded": request.app.state.captioner is not None,
        "baserow_configured": request.app.state.config_store.is_baserow_configured(),
        "uptime_seconds": round(time.time() - request.app.state.start_time, 1),
    }


@router.post("/scrape")
async def start_scrape(request: Request, body: ScrapeRequest) -> ScrapeResponse:
    """Submit a new scraping job."""
    if not request.app.state.browser or not request.app.state.browser.ready:
        raise HTTPException(status_code=503, detail="Browser not ready")

    if not request.app.state.config_store.is_baserow_configured():
        raise HTTPException(status_code=400, detail="Baserow not configured. Go to the Baserow tab first.")

    overrides = {}
    if body.max_pages is not None:
        overrides["max_pages"] = body.max_pages
    if body.aspect_ratios is not None:
        overrides["aspect_ratios"] = body.aspect_ratios
    if body.min_width is not None:
        overrides["min_width"] = body.min_width
    if body.min_height is not None:
        overrides["min_height"] = body.min_height

    job = await request.app.state.job_queue.submit(body.urls, overrides)
    return ScrapeResponse(
        job_id=job.job_id,
        status=job.status,
        message=f"Job queued with {len(body.urls)} URL(s)"
    )


@router.get("/jobs")
async def list_jobs(request: Request) -> list[dict]:
    """List all jobs."""
    return request.app.state.job_queue.list_jobs()


@router.get("/jobs/{job_id}")
async def get_job(request: Request, job_id: str) -> dict:
    """Get job details."""
    job = request.app.state.job_queue.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.to_dict()


@router.delete("/jobs/{job_id}")
async def cancel_job(request: Request, job_id: str) -> dict:
    """Cancel a job."""
    success = request.app.state.job_queue.cancel_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found or not cancellable")
    return {"message": "Job cancelled"}


@router.get("/settings")
async def get_settings(request: Request) -> dict:
    """Get current settings (token masked)."""
    return request.app.state.config_store.get_masked()


@router.put("/settings")
async def update_settings(request: Request, body: SettingsUpdate) -> dict:
    """Update settings."""
    updates = body.model_dump(exclude_none=True)
    if updates:
        request.app.state.config_store.update_all(updates)
    return {"message": "Settings saved", "settings": request.app.state.config_store.get_masked()}


@router.get("/baserow/status")
async def baserow_status(request: Request) -> dict:
    """Get Baserow connection status."""
    config = request.app.state.config_store.get("baserow")
    if not config.get("api_url") or not config.get("api_token"):
        return {"configured": False, "message": "Baserow not configured"}

    client = BaserowClient(
        api_url=config["api_url"],
        api_token=config["api_token"],
        table_id=config.get("table_id", 810),
    )
    try:
        result = await client.test_connection()
        return {"configured": True, **result}
    finally:
        await client.close()


@router.put("/baserow/config")
async def update_baserow_config(request: Request, body: BaserowConfig) -> dict:
    """Update Baserow configuration."""
    request.app.state.config_store.update("baserow", {
        "api_url": body.api_url.rstrip("/"),
        "api_token": body.api_token,
        "table_id": body.table_id,
    })
    request.app.state.baserow_configured = bool(body.api_url and body.api_token)
    return {"message": "Baserow config saved"}


@router.post("/baserow/test")
async def test_baserow(request: Request) -> dict:
    """Test Baserow connection with current config."""
    config = request.app.state.config_store.get("baserow")
    if not config.get("api_url") or not config.get("api_token"):
        return {"success": False, "error": "Baserow URL and token are required"}

    client = BaserowClient(
        api_url=config["api_url"],
        api_token=config["api_token"],
        table_id=config.get("table_id", 810),
    )
    try:
        return await client.test_connection()
    finally:
        await client.close()


@router.get("/stats")
async def get_stats(request: Request) -> dict:
    """Get scraping statistics."""
    stats = request.app.state.job_queue.get_stats()
    stats["ai_model"] = "BLIP-base (Salesforce/blip-image-captioning-base)"
    stats["uptime_seconds"] = round(time.time() - request.app.state.start_time, 1)
    stats["browser_status"] = (
        "ready" if request.app.state.browser and request.app.state.browser.ready
        else "not available"
    )
    return stats
