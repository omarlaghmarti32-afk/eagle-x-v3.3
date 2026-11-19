import os

import pytest

os.environ.setdefault("EAGLE_API_TOKEN", "test-token-for-ci-only-16c")
os.environ.setdefault("EAGLE_REQUIRE_STRONG_TOKEN", "0")
os.environ.setdefault("EAGLE_DATA_DIR", "/tmp/eagle-x-test-data")
os.environ.setdefault("EAGLE_LOG_DIR", "/tmp/eagle-x-test-logs")
os.environ.setdefault("EAGLE_LIVE_MONITOR", "0")
os.environ.setdefault("EAGLE_HEALTH_INTERNAL", "0")

from fastapi.testclient import TestClient

import api_server
from core.threat_db import ThreatDB


TOKEN = "test-token-for-ci-only-16c"
AUTH = {"Authorization": f"Bearer {TOKEN}"}
client = TestClient(api_server.app)


def use_test_db(monkeypatch, tmp_path):
    db = ThreatDB(path=tmp_path / "local-console.db")
    monkeypatch.setattr(api_server, "db", db)
    return db


@pytest.fixture(autouse=True)
def use_test_token(monkeypatch):
    import core.security

    monkeypatch.setattr(api_server, "API_TOKEN", TOKEN)
    monkeypatch.setattr(core.security, "API_TOKEN", TOKEN)


def test_local_inventory_and_incidents_require_auth():
    assert client.get("/api/assets").status_code in (401, 403)
    assert client.get("/api/incidents").status_code in (401, 403)
    assert client.post("/api/assets", json={"name": "host-a"}).status_code in (401, 403)
    assert client.post("/api/incidents", json={"title": "Check alert"}).status_code in (401, 403)


def test_asset_inventory_is_local_validated_and_unique(monkeypatch, tmp_path):
    use_test_db(monkeypatch, tmp_path)
    created = client.post(
        "/api/assets",
        headers=AUTH,
        json={
            "name": "edge-server-01",
            "asset_type": "server",
            "address": "10.0.0.12",
            "criticality": "high",
            "notes": "Primary local test asset",
        },
    )
    assert created.status_code == 201
    asset = created.json()["asset"]
    assert asset["name"] == "edge-server-01"
    assert asset["address"] == "10.0.0.12"
    assert client.get("/api/assets", headers=AUTH).json()["assets"] == [asset]

    duplicate = client.post("/api/assets", headers=AUTH, json={"name": "edge-server-01"})
    assert duplicate.status_code == 409
    assert client.post("/api/assets", headers=AUTH, json={"name": "   "}).status_code == 422
    assert client.post(
        "/api/assets", headers=AUTH, json={"name": "bad-type", "asset_type": "unknown"}
    ).status_code == 422


def test_incident_lifecycle_and_asset_link(monkeypatch, tmp_path):
    use_test_db(monkeypatch, tmp_path)
    asset_response = client.post(
        "/api/assets", headers=AUTH, json={"name": "db-node", "asset_type": "server"}
    )
    asset_id = asset_response.json()["asset"]["id"]

    created = client.post(
        "/api/incidents",
        headers=AUTH,
        json={
            "title": "Unexpected login attempts",
            "description": "Review local authentication logs",
            "severity": "high",
            "asset_id": asset_id,
        },
    )
    assert created.status_code == 201
    incident = created.json()["incident"]
    assert incident["status"] == "open"
    assert incident["asset_name"] == "db-node"

    updated = client.patch(
        f"/api/incidents/{incident['id']}", headers=AUTH, json={"status": "investigating"}
    )
    assert updated.status_code == 200
    assert updated.json()["incident"]["status"] == "investigating"
    assert client.get("/api/incidents", headers=AUTH).json()["incidents"][0]["status"] == "investigating"

    assert client.post(
        "/api/incidents", headers=AUTH, json={"title": "Orphan", "asset_id": 999}
    ).status_code == 404
    assert client.patch(
        f"/api/incidents/{incident['id']}", headers=AUTH, json={"status": "deleted"}
    ).status_code == 422
    assert client.patch(
        "/api/incidents/999", headers=AUTH, json={"status": "resolved"}
    ).status_code == 404


def test_detection_rule_routes_require_auth():
    assert client.get("/api/detection-rules").status_code in (401, 403)
    assert client.post("/api/detection-rules", json={}).status_code in (401, 403)
    assert client.post("/api/detection-rules/evaluate", json={}).status_code in (401, 403)
    assert client.patch("/api/detection-rules/1", json={"enabled": False}).status_code in (401, 403)


def test_local_detection_rules_create_evaluate_and_open_one_incident_per_breach(
    monkeypatch, tmp_path
):
    db = use_test_db(monkeypatch, tmp_path)
    asset = client.post(
        "/api/assets", headers=AUTH, json={"name": "api-edge", "asset_type": "server"}
    )
    asset_id = asset.json()["asset"]["id"]

    created = client.post(
        "/api/detection-rules",
        headers=AUTH,
        json={
            "name": "High CPU",
            "metric": "cpu_percent",
            "operator": "gte",
            "threshold": 80,
            "severity": "high",
            "asset_id": asset_id,
        },
    )
    assert created.status_code == 201
    rule = created.json()["rule"]
    assert rule["asset_name"] == "api-edge"
    assert rule["enabled"] is True
    assert client.get("/api/detection-rules", headers=AUTH).json()["rules"] == [rule]

    assert client.post(
        "/api/detection-rules",
        headers=AUTH,
        json={"name": "Bad metric", "metric": "unknown", "operator": "gt", "threshold": 1},
    ).status_code == 422
    assert client.post(
        "/api/detection-rules",
        headers=AUTH,
        json={"name": "Orphan rule", "metric": "cpu_percent", "operator": "gt", "threshold": 1, "asset_id": 999},
    ).status_code == 404
    assert client.post(
        "/api/detection-rules",
        headers=AUTH,
        json={"name": "High CPU", "metric": "cpu_percent", "operator": "gt", "threshold": 90},
    ).status_code == 409

    current = {"cpu_percent": 91.0}
    monkeypatch.setattr(api_server.monitor, "one_shot", lambda: current.copy())
    first = client.post("/api/detection-rules/evaluate", headers=AUTH, json={})
    assert first.status_code == 200
    assert len(first.json()["new_incidents"]) == 1
    incident_id = first.json()["new_incidents"][0]["incident_id"]
    assert first.json()["matches"][0]["incident_id"] == incident_id

    repeated = client.post("/api/detection-rules/evaluate", headers=AUTH, json={})
    assert repeated.json()["new_incidents"] == []
    assert len(db.list_incidents()) == 1

    current["cpu_percent"] = 55.0
    cleared = client.post("/api/detection-rules/evaluate", headers=AUTH, json={})
    assert cleared.json()["cleared"][0]["reason"] == "condition_cleared"
    current["cpu_percent"] = 88.0
    rebreach = client.post("/api/detection-rules/evaluate", headers=AUTH, json={})
    assert len(rebreach.json()["new_incidents"]) == 1
    incidents = db.list_incidents()
    assert len(incidents) == 2
    assert all(item["asset_name"] == "api-edge" for item in incidents)
    assert all(item["source"] == "detection_rule" for item in incidents)

    disabled = client.patch(
        f"/api/detection-rules/{rule['id']}", headers=AUTH, json={"enabled": False}
    )
    assert disabled.status_code == 200
    assert disabled.json()["rule"]["enabled"] is False
    assert disabled.json()["rule"]["active_match"] is False
    assert client.patch(
        "/api/detection-rules/999", headers=AUTH, json={"enabled": True}
    ).status_code == 404
    reenabled = client.patch(
        f"/api/detection-rules/{rule['id']}", headers=AUTH, json={"enabled": True}
    )
    assert reenabled.json()["rule"]["enabled"] is True
    resumed = client.post("/api/detection-rules/evaluate", headers=AUTH, json={})
    assert len(resumed.json()["new_incidents"]) == 1
    assert len(db.list_incidents()) == 3
