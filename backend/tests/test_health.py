from fastapi.testclient import TestClient
import asyncio
import pytest
from pathlib import Path

from app.main import app
from app.render import render_short
from app.youtube import upload_video_private
from app.pipeline import build_private_draft

client = TestClient(app)
TEST_TOKEN = "test-token-for-tests-only"
HEADERS = {"Authorization": f"Bearer {TEST_TOKEN}"}


def test_health_endpoint_is_live():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "jowi-code-automation-api"}


def test_status_fails_closed_when_token_is_not_configured(monkeypatch):
    monkeypatch.delenv("API_ACCESS_TOKEN", raising=False)
    assert client.get("/api/status").status_code == 503


def test_status_rejects_missing_or_invalid_token(monkeypatch):
    monkeypatch.setenv("API_ACCESS_TOKEN", TEST_TOKEN)
    assert client.get("/api/status").status_code == 401
    assert client.get("/api/status", headers={"Authorization": "Bearer wrong"}).status_code == 401


def test_status_requires_token_and_does_not_enable_publishing(monkeypatch):
    monkeypatch.setenv("API_ACCESS_TOKEN", TEST_TOKEN)
    response = client.get("/api/status", headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["state"] == "development"
    assert response.json()["publishing_enabled"] is False
    assert "timestamp_utc" in response.json()


def test_job_queue_requires_authentication(monkeypatch, tmp_path):
    monkeypatch.setenv("JOB_DB_PATH", str(tmp_path / "jobs.sqlite3"))
    monkeypatch.setenv("API_ACCESS_TOKEN", TEST_TOKEN)
    assert client.post("/api/jobs", json={"topic": "Build your future"}).status_code == 401
    assert client.get("/api/jobs").status_code == 401


def test_job_queue_creates_and_lists_jobs(monkeypatch, tmp_path):
    monkeypatch.setenv("JOB_DB_PATH", str(tmp_path / "jobs.sqlite3"))
    monkeypatch.setenv("API_ACCESS_TOKEN", TEST_TOKEN)
    created = client.post("/api/jobs", json={"topic": "Build your future"}, headers=HEADERS)
    assert created.status_code == 202
    assert created.json()["status"] == "queued"
    assert created.json()["topic"] == "Build your future"
    listed = client.get("/api/jobs", headers=HEADERS)
    assert listed.status_code == 200
    assert len(listed.json()["jobs"]) == 1


def test_job_queue_limits_new_jobs_to_three_per_utc_day(monkeypatch, tmp_path):
    monkeypatch.setenv("JOB_DB_PATH", str(tmp_path / "jobs.sqlite3"))
    monkeypatch.setenv("API_ACCESS_TOKEN", TEST_TOKEN)
    for number in range(3):
        response = client.post("/api/jobs", json={"topic": f"Topic number {number}"}, headers=HEADERS)
        assert response.status_code == 202
    limited = client.post("/api/jobs", json={"topic": "One more topic"}, headers=HEADERS)
    assert limited.status_code == 429


def test_script_planner_returns_brand_consistent_vertical_scenes(monkeypatch):
    monkeypatch.setenv("API_ACCESS_TOKEN", TEST_TOKEN)
    response = client.post("/api/scripts/plan", json={"topic": "Discipline"}, headers=HEADERS)
    assert response.status_code == 200
    plan = response.json()
    assert plan["format"] == "YouTube Short, vertical 9:16"
    assert plan["tagline"] == "Master Your Mind. Build Your Future."
    assert len(plan["scenes"]) == 4
    assert "black male lion" in plan["scenes"][0]["visual_prompt"]
    assert "no on-screen captions" in plan["voice"]
    assert plan["publishing_enabled"] is False


def test_script_planner_requires_authentication(monkeypatch):
    monkeypatch.setenv("API_ACCESS_TOKEN", TEST_TOKEN)
    assert client.post("/api/scripts/plan", json={"topic": "Discipline"}).status_code == 401


def test_voiceover_requires_authentication(monkeypatch):
    monkeypatch.setenv("API_ACCESS_TOKEN", TEST_TOKEN)
    assert client.post("/api/voiceover", json={"text": "Stay focused."}).status_code == 401
    assert client.get("/api/voiceover/not-a-uuid", headers=HEADERS).status_code == 404


def test_voiceover_generation_and_download(monkeypatch, tmp_path):
    import app.main as main_module
    monkeypatch.setenv("API_ACCESS_TOKEN", TEST_TOKEN)
    monkeypatch.setattr(main_module, "OUTPUT_DIR", tmp_path)

    async def fake_voiceover(text, output_path):
        Path(output_path).write_bytes(b"test-audio")
        return output_path

    monkeypatch.setattr(main_module, "generate_voiceover", fake_voiceover)
    created = client.post("/api/voiceover", json={"text": "Stay focused."}, headers=HEADERS)
    assert created.status_code == 200
    audio_id = created.json()["audio_id"]
    downloaded = client.get(f"/api/voiceover/{audio_id}", headers=HEADERS)
    assert downloaded.status_code == 200
    assert downloaded.content == b"test-audio"


def test_youtube_upload_fails_closed_without_oauth(monkeypatch, tmp_path):
    monkeypatch.delenv("YOUTUBE_CLIENT_ID", raising=False)
    monkeypatch.delenv("YOUTUBE_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("YOUTUBE_REFRESH_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="not configured"):
        upload_video_private(str(tmp_path / "missing.mp4"), "Title", "Description")


def test_renderer_requires_four_scene_images():
    with pytest.raises(ValueError, match="exactly four"):
        render_short([], "voice.mp3", "out.mp4")


def test_pipeline_requires_four_existing_scene_images(tmp_path):
    with pytest.raises(ValueError, match="Four existing scene images"):
        asyncio.run(build_private_draft("Discipline", [], str(tmp_path)))


def test_pipeline_creates_private_draft_and_cleans_temporary_media(monkeypatch, tmp_path):
    import app.pipeline as pipeline
    images = []
    for index in range(4):
        path = tmp_path / f"scene-{index}.png"
        path.write_bytes(b"fake-image")
        images.append(str(path))

    async def fake_voice(text, output_path):
        Path(output_path).write_bytes(b"fake-audio")

    def fake_render(scene_images, audio_path, output_path):
        Path(output_path).write_bytes(b"fake-video")
        return output_path

    def fake_upload(file_path, title, description, tags):
        assert Path(file_path).is_file()
        assert "Master Your Mind. Build Your Future." in description
        return {"video_id": "private-test-id", "privacy_status": "private"}

    monkeypatch.setattr(pipeline, "generate_voiceover", fake_voice)
    monkeypatch.setattr(pipeline, "render_short", fake_render)
    monkeypatch.setattr(pipeline, "upload_video_private", fake_upload)
    output_dir = tmp_path / "output"
    result = asyncio.run(build_private_draft("Discipline", images, str(output_dir)))
    assert result["video_id"] == "private-test-id"
    assert result["privacy_status"] == "private"
    assert list(output_dir.iterdir()) == []


def test_job_detail_requires_auth_and_returns_only_requested_job(monkeypatch, tmp_path):
    monkeypatch.setenv("JOB_DB_PATH", str(tmp_path / "jobs.sqlite3"))
    monkeypatch.setenv("API_ACCESS_TOKEN", TEST_TOKEN)
    created = client.post("/api/jobs", json={"topic": "Discipline"}, headers=HEADERS).json()
    job_id = created["id"]
    assert client.get(f"/api/jobs/{job_id}").status_code == 401
    response = client.get(f"/api/jobs/{job_id}", headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["id"] == job_id
    assert response.json()["status"] == "queued"
    assert client.get("/api/jobs/not-a-uuid", headers=HEADERS).status_code == 404
    assert client.get("/api/jobs/00000000-0000-0000-0000-000000000000", headers=HEADERS).status_code == 404



def test_job_lifecycle_tracks_updated_time_and_rejects_invalid_transitions(monkeypatch, tmp_path):
    from app.jobs import get_job, update_job_status

    monkeypatch.setenv("JOB_DB_PATH", str(tmp_path / "jobs.sqlite3"))
    created = client.post(
        "/api/jobs", json={"topic": "Build discipline"}, headers=HEADERS
    ).json()
    job_id = created["id"]
    initial = get_job(job_id)
    assert initial["updated_at_utc"]
    assert initial["error"] is None
    assert initial["result"] is None

    blocked = update_job_status(
        job_id, "blocked", error="Image generation provider is not configured"
    )
    assert blocked["status"] == "blocked"
    assert blocked["error"] == "Image generation provider is not configured"
    assert blocked["updated_at_utc"]
    assert blocked["result"] is None

    with pytest.raises(ValueError, match="Invalid job status transition"):
        update_job_status(job_id, "completed", result={"video_id": "fake"})
    retried = update_job_status(job_id, "queued")
    assert retried["status"] == "queued"
    assert retried["error"] is None


def test_existing_sqlite_queue_schema_is_migrated(monkeypatch, tmp_path):
    import sqlite3
    from app.jobs import get_job

    db_path = tmp_path / "legacy.sqlite3"
    connection = sqlite3.connect(db_path)
    connection.execute(
        "CREATE TABLE jobs (id TEXT PRIMARY KEY, job_type TEXT NOT NULL, "
        "topic TEXT NOT NULL, status TEXT NOT NULL, created_at_utc TEXT NOT NULL)"
    )
    connection.execute(
        "INSERT INTO jobs VALUES (?, ?, ?, ?, ?)",
        ("00000000-0000-0000-0000-000000000001", "short_video", "Legacy job",
         "queued", "2026-10-14T00:00:00+00:00"),
    )
    connection.commit()
    connection.close()
    monkeypatch.setenv("JOB_DB_PATH", str(db_path))
    job = get_job("00000000-0000-0000-0000-000000000001")
    assert job["status"] == "queued"
    assert job["updated_at_utc"] is None
    assert job["error"] is None
    assert job["result"] is None


def test_worker_claims_job_and_blocks_honestly_without_image_provider(monkeypatch, tmp_path):
    from app.jobs import get_job
    from app.worker import run_once, BLOCKED_REASON

    monkeypatch.setenv("JOB_DB_PATH", str(tmp_path / "worker.sqlite3"))
    monkeypatch.setenv("API_ACCESS_TOKEN", TEST_TOKEN)
    created = client.post(
        "/api/jobs", json={"topic": "Build discipline"}, headers=HEADERS
    ).json()

    result = run_once()
    assert result["state"] == "blocked"
    assert result["job_id"] == created["id"]
    job = get_job(created["id"])
    assert job["status"] == "blocked"
    assert BLOCKED_REASON in job["error"]
    assert job["result"]["media_created"] is False
    assert job["result"]["youtube_upload"] is None
    assert len(job["result"]["plan"]["scenes"]) == 4


def test_worker_returns_idle_when_queue_is_empty(monkeypatch, tmp_path):
    from app.worker import run_once

    monkeypatch.setenv("JOB_DB_PATH", str(tmp_path / "empty-worker.sqlite3"))
    assert run_once() == {"state": "idle", "message": "No queued jobs."}


def test_worker_processes_only_one_job_per_invocation(monkeypatch, tmp_path):
    from app.jobs import get_job
    from app.worker import run_once

    monkeypatch.setenv("JOB_DB_PATH", str(tmp_path / "one-at-a-time.sqlite3"))
    monkeypatch.setenv("API_ACCESS_TOKEN", TEST_TOKEN)
    first = client.post("/api/jobs", json={"topic": "First topic"}, headers=HEADERS).json()
    second = client.post("/api/jobs", json={"topic": "Second topic"}, headers=HEADERS).json()

    assert run_once()["job_id"] == first["id"]
    assert get_job(first["id"])["status"] == "blocked"
    assert get_job(second["id"])["status"] == "queued"


def test_worker_completes_only_after_pipeline_confirms_private_upload(monkeypatch, tmp_path):
    from app.jobs import get_job
    import app.pipeline as pipeline
    from app.worker import run_once

    monkeypatch.setenv("JOB_DB_PATH", str(tmp_path / "worker-complete.sqlite3"))
    monkeypatch.setenv("API_ACCESS_TOKEN", TEST_TOKEN)
    monkeypatch.setenv("SCENE_ASSETS_DIR", str(tmp_path / "scenes"))
    scene_dir = tmp_path / "scenes"
    scene_dir.mkdir()
    for index in range(1, 5):
        (scene_dir / f"scene-{index}.png").write_bytes(b"test-image")
    created = client.post(
        "/api/jobs", json={"topic": "Build discipline"}, headers=HEADERS
    ).json()

    async def fake_pipeline(topic, scene_images):
        assert len(scene_images) == 4
        return {
            "video_id": "confirmed-private-id",
            "privacy_status": "private",
            "title": topic,
            "status": "uploaded_private",
        }

    monkeypatch.setattr(pipeline, "build_private_draft", fake_pipeline)
    result = run_once()
    job = get_job(created["id"])
    assert result["state"] == "completed"
    assert job["status"] == "completed"
    assert job["result"]["youtube_upload"]["video_id"] == "confirmed-private-id"
    assert job["result"]["youtube_upload"]["privacy_status"] == "private"


def test_worker_does_not_complete_if_pipeline_does_not_confirm_private_upload(monkeypatch, tmp_path):
    from app.jobs import get_job
    import app.pipeline as pipeline
    from app.worker import run_once

    monkeypatch.setenv("JOB_DB_PATH", str(tmp_path / "worker-unverified.sqlite3"))
    monkeypatch.setenv("API_ACCESS_TOKEN", TEST_TOKEN)
    monkeypatch.setenv("SCENE_ASSETS_DIR", str(tmp_path / "scenes"))
    scene_dir = tmp_path / "scenes"
    scene_dir.mkdir()
    for index in range(1, 5):
        (scene_dir / f"scene-{index}.png").write_bytes(b"test-image")
    created = client.post(
        "/api/jobs", json={"topic": "Build discipline"}, headers=HEADERS
    ).json()

    async def fake_pipeline(topic, scene_images):
        return {"status": "uploaded_private", "privacy_status": "public", "video_id": "wrong"}

    monkeypatch.setattr(pipeline, "build_private_draft", fake_pipeline)
    result = run_once()
    job = get_job(created["id"])
    assert result["state"] == "failed"
    assert job["status"] == "failed"
    assert "did not confirm a private YouTube upload" in job["error"]
