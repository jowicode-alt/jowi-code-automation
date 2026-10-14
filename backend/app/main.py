"""Development API scaffold; publishing is disabled."""
from datetime import datetime, timezone
import os

from fastapi import FastAPI, Depends
from pydantic import BaseModel
from app.auth import require_api_token

app = FastAPI(title="The Jowi Code Automation API", version="0.1.1", description="Development scaffold; publishing is not enabled.")

class ServiceStatus(BaseModel):
    service: str
    state: str
    publishing_enabled: bool
    video_generation_configured: bool
    youtube_oauth_configured: bool
    timestamp_utc: str

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "jowi-code-automation-api"}

@app.get("/api/status", response_model=ServiceStatus, dependencies=[Depends(require_api_token)])
def status() -> ServiceStatus:
    return ServiceStatus(
        service="jowi-code-automation-api",
        state="development",
        publishing_enabled=False,
        video_generation_configured=bool(os.getenv("VIDEO_PROVIDER_API_KEY")),
        youtube_oauth_configured=bool(os.getenv("YOUTUBE_CLIENT_ID") and os.getenv("YOUTUBE_CLIENT_SECRET") and os.getenv("YOUTUBE_REFRESH_TOKEN")),
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
    )
