"""Authenticated API; public YouTube publishing remains disabled."""
from datetime import datetime, timezone
import importlib.util
import os
from pathlib import Path
import shutil
import sqlite3
import uuid

from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from app.auth import require_api_token
from app.jobs import enqueue_job, get_job, list_jobs
from app.content import build_short_plan
from app.voice import generate_voiceover

app = FastAPI(title="The Jowi Code Automation API", version="0.6.0", description="Authenticated category-aware Shorts planning and job queue; YouTube uploads remain private-only.")
ALLOWED_CATEGORIES = "^(short_video|breaking_news|ai_technology|comedy|entertainment|money_success|psychology)$"


class ServiceStatus(BaseModel):
    service: str
    state: str
    publishing_enabled: bool
    video_generation_configured: bool
    image_generation_adapter_available: bool
    image_generation_mode: str
    ffmpeg_available: bool
    voiceover_adapter_available: bool
    database_backend: str
    database_connected: bool
    database_durable: bool
    youtube_oauth_configured: bool
    timestamp_utc: str


class JobRequest(BaseModel):
    job_type: str = Field(default="money_success", pattern=ALLOWED_CATEGORIES)
    topic: str = Field(min_length=3, max_length=240)


class PlanRequest(BaseModel):
    category: str = Field(default="money_success", pattern="^(breaking_news|ai_technology|comedy|entertainment|money_success|psychology)$")
    topic: str = Field(min_length=3, max_length=240)


class VoiceoverRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1800)


OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/tmp/jowi-code-output"))


def _database_status() -> tuple[str, bool, bool]:
    """Return backend, connectivity, durability without exposing connection details."""
    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url:
        try:
            import psycopg
            with psycopg.connect(database_url, connect_timeout=3) as connection:
                connection.execute("SELECT 1").fetchone()
            return "postgresql", True, True
        except Exception:
            return "postgresql_unreachable", False, True
    path = Path(os.getenv("JOB_DB_PATH", "./data/jobs.sqlite3"))
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(path, timeout=2) as connection:
            connection.execute("SELECT 1").fetchone()
        return "sqlite_ephemeral", True, False
    except Exception:
        return "sqlite_unavailable", False, False


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "jowi-code-automation-api"}


@app.get("/api/status", response_model=ServiceStatus, dependencies=[Depends(require_api_token)])
def status() -> ServiceStatus:
    image_key = os.getenv("AI_HORDE_API_KEY", "").strip()
    image_adapter_available = (
        importlib.util.find_spec("app.image_provider") is not None
        and importlib.util.find_spec("PIL") is not None
    )
    ffmpeg_available = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None
    voiceover_available = importlib.util.find_spec("edge_tts") is not None
    database_backend, database_connected, database_durable = _database_status()
    oauth_configured = all(os.getenv(name, "").strip() for name in (
        "YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"
    ))
    media_components_available = image_adapter_available and ffmpeg_available and voiceover_available
    service_state = "ready" if (
        database_connected and media_components_available and oauth_configured
    ) else "degraded"
    return ServiceStatus(
        service="jowi-code-automation-api",
        state=service_state,
        publishing_enabled=False,
        video_generation_configured=media_components_available,
        image_generation_adapter_available=image_adapter_available,
        image_generation_mode=(
            "registered_key_with_local_fallback"
            if image_key and image_key != "0000000000"
            else "anonymous_shared_low_priority_with_local_fallback"
        ),
        ffmpeg_available=ffmpeg_available,
        voiceover_adapter_available=voiceover_available,
        database_backend=database_backend,
        database_connected=database_connected,
        database_durable=database_durable,
        youtube_oauth_configured=oauth_configured,
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
    )


@app.post("/api/jobs", status_code=202, dependencies=[Depends(require_api_token)])
def create_job(request: JobRequest) -> dict:
    try:
        job_type = "money_success" if request.job_type == "short_video" else request.job_type
        return enqueue_job(job_type, request.topic)
    except ValueError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc


@app.get("/api/jobs", dependencies=[Depends(require_api_token)])
def get_jobs() -> dict:
    return {"jobs": list_jobs()}


@app.get("/api/jobs/{job_id}", dependencies=[Depends(require_api_token)])
def get_job_detail(job_id: str) -> dict:
    try:
        safe_id = str(uuid.UUID(job_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc
    job = get_job(safe_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.post("/api/scripts/plan", dependencies=[Depends(require_api_token)])
def plan_script(request: PlanRequest) -> dict:
    return build_short_plan(request.topic, category=request.category)


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
