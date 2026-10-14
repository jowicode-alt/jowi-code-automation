"""Development API; public publishing remains disabled."""
from datetime import datetime, timezone
import os

from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, Field
from app.auth import require_api_token
from app.jobs import enqueue_job, list_jobs

app = FastAPI(title="The Jowi Code Automation API", version="0.2.0", description="Authenticated development queue; publishing is not enabled.")

class ServiceStatus(BaseModel):
    service: str
    state: str
    publishing_enabled: bool
    video_generation_configured: bool
    youtube_oauth_configured: bool
    timestamp_utc: str

class JobRequest(BaseModel):
    job_type: str = Field(default="short_video", pattern="^short_video$")
    topic: str = Field(min_length=3, max_length=240)

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "jowi-code-automation-api"}

@app.get("/api/status", response_model=ServiceStatus, dependencies=[Depends(require_api_token)])
def status() -> ServiceStatus:
    return ServiceStatus(
        service="jowi-code-automation-api", state="development", publishing_enabled=False,
        video_generation_configured=bool(os.getenv("VIDEO_PROVIDER_API_KEY")),
        youtube_oauth_configured=bool(os.getenv("YOUTUBE_CLIENT_ID") and os.getenv("YOUTUBE_CLIENT_SECRET") and os.getenv("YOUTUBE_REFRESH_TOKEN")),
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
    )

@app.post("/api/jobs", status_code=202, dependencies=[Depends(require_api_token)])
def create_job(request: JobRequest) -> dict[str, str]:
    try:
        return enqueue_job(request.job_type, request.topic)
    except ValueError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc

@app.get("/api/jobs", dependencies=[Depends(require_api_token)])
def get_jobs() -> dict[str, list[dict[str, str]]]:
    return {"jobs": list_jobs()}
