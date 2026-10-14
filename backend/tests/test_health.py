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


def test_status_endpoint_does_not_enable_publishing():
    response = client.get("/api/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["state"] == "development"
    assert payload["publishing_enabled"] is False
    assert "timestamp_utc" in payload
