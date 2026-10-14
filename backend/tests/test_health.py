from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint_is_live():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "jowi-code-automation-api",
    }


def test_status_fails_closed_when_token_is_not_configured(monkeypatch):
    monkeypatch.delenv("API_ACCESS_TOKEN", raising=False)
    response = client.get("/api/status")
    assert response.status_code == 503


def test_status_rejects_missing_or_invalid_token(monkeypatch):
    monkeypatch.setenv("API_ACCESS_TOKEN", "test-token-for-tests-only")
    assert client.get("/api/status").status_code == 401
    assert client.get("/api/status", headers={"Authorization": "Bearer wrong"}).status_code == 401


def test_status_requires_token_and_does_not_enable_publishing(monkeypatch):
    monkeypatch.setenv("API_ACCESS_TOKEN", "test-token-for-tests-only")
    response = client.get("/api/status", headers={"Authorization": "Bearer test-token-for-tests-only"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["state"] == "development"
    assert payload["publishing_enabled"] is False
    assert "timestamp_utc" in payload
