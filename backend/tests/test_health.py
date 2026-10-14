from fastapi.testclient import TestClient

from app.main import app

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
