import os

os.environ.setdefault("EAGLE_API_TOKEN", "test-token")
os.environ.setdefault("EAGLE_DATA_DIR", "/tmp/eagle-x-test-data")
os.environ.setdefault("EAGLE_LOG_DIR", "/tmp/eagle-x-test-logs")

from fastapi.testclient import TestClient

# Import after env is set
from api_server import app

client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_status():
    r = client.get("/api/status")
    assert r.status_code == 200
    body = r.json()
    assert body["version"] == "3.3"
    assert "pqc" in body


def test_detect_requires_auth():
    r = client.post("/api/detect", json={"features": [1, 2, 3, 4, 5, 6, 7, 8]})
    assert r.status_code in (401, 403)


def test_detect_with_token():
    r = client.post(
        "/api/detect",
        json={"features": [90, 90, 2e6, 2e6, 400, 300, 80, 0.9], "indicator": "10.0.0.1"},
        headers={"Authorization": "Bearer test-token"},
    )
    assert r.status_code == 200
    assert "analysis" in r.json()


def test_threats_endpoint():
    r = client.get("/api/threats")
    assert r.status_code == 200
    assert "threats" in r.json()
