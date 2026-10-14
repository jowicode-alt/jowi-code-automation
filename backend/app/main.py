"""Development API; publishing remains disabled until readiness checks pass."""
from datetime import datetime, timezone
import os
from pathlib import Path
import uuid

from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from app.auth import require_api_token
from app.jobs import enqueue_job, list_jobs
from app.content import build_short_plan
from app.voice import generate_voiceover

app = FastAPI(title="The Jowi Code Automation API", version="0.4.0", description="Authenticated development queue, Shorts planner, and voiceover; publishing is not enabled.")

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

class PlanRequest(BaseModel):
    topic: str = Field(min_length=3, max_length=240)

class VoiceoverRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1800)

OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/tmp/jowi-code-output"))

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

@app.post("/api/scripts/plan", dependencies=[Depends(require_api_token)])
def plan_script(request: PlanRequest) -> dict:
    return build_short_plan(request.topic)

@app.post("/api/voiceover", dependencies=[Depends(require_api_token)])
async def create_voiceover(request: VoiceoverRequest) -> dict[str, str | int]:
    audio_id = str(uuid.uuid4())
    output_path = OUTPUT_DIR / f"{audio_id}.mp3"
    try:
        await generate_voiceover(request.text, str(output_path))
    except Exception as exc:
        output_path.unlink(missing_ok=True)
        raise HTTPException(status_code=502, detail="Voice provider failed; no audio was created") from exc
    return {"audio_id": audio_id, "status": "ready", "bytes": output_path.stat().st_size, "voice": os.getenv("TTS_VOICE", "en-US-GuyNeural")}

@app.get("/api/voiceover/{audio_id}", dependencies=[Depends(require_api_token)])
def download_voiceover(audio_id: str) -> FileResponse:
    try:
        safe_id = str(uuid.UUID(audio_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Audio file not found") from exc
    path = OUTPUT_DIR / f"{safe_id}.mp3"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(path, media_type="audio/mpeg", filename="jowi-code-voiceover.mp3")
