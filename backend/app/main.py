"""Initial API scaffold for The Jowi Code Automation.

This service intentionally exposes no publishing or render controls yet.
Those endpoints must be authenticated and tested before deployment.
"""
from datetime import datetime, timezone
import os

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(
    title="The Jowi Code Automation API",
    version="0.1.0",
    description="Development scaffold; publishing is not enabled.",
)


class ServiceStatus(BaseModel):
    service: str
    state: str
    publishing_enabled: bool
    video_generation_configured: bool
    youtube_oauth_configured: bool
    timestamp_utc: str


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness check. Does not reveal secrets or environment values."""
    return {"status": "ok", "service": "jowi-code-automation-api"}


@app.get("/api/status", response_model=ServiceStatus)
def status() -> ServiceStatus:
    """Report configuration presence only, never secret contents."""
    return ServiceStatus(
        service="jowi-code-automation-api",
        state="development",
        publishing_enabled=False,
        video_generation_configured=bool(os.getenv("VIDEO_PROVIDER_API_KEY")),
        youtube_oauth_configured=bool(
            os.getenv("YOUTUBE_CLIENT_ID")
            and os.getenv("YOUTUBE_CLIENT_SECRET")
            and os.getenv("YOUTUBE_REFRESH_TOKEN")
        ),
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
    )
