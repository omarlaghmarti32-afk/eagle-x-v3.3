"""Security unit tests for EAGLE-X v3.3."""

import os

os.environ.setdefault("EAGLE_API_TOKEN", "test-token-for-ci-only-16c")
os.environ.setdefault("EAGLE_REQUIRE_STRONG_TOKEN", "0")
os.environ.setdefault("EAGLE_DATA_DIR", "/tmp/eagle-x-sec-test-data")
os.environ.setdefault("EAGLE_LOG_DIR", "/tmp/eagle-x-sec-test-logs")
os.environ.setdefault("EAGLE_LIVE_MONITOR", "0")
os.environ.setdefault("EAGLE_HEALTH_INTERNAL", "0")

from core.security import is_safe_webhook_url, token_is_weak


def test_token_is_weak_defaults():
    assert token_is_weak("") is True
    assert token_is_weak("change-me") is True
    assert token_is_weak("eagle-x-dev-token-change-me") is True
    assert token_is_weak("short") is True
    assert token_is_weak("a-long-enough-random-secret-32") is False


def test_ssrf_guard_blocks_private():
    assert is_safe_webhook_url("http://127.0.0.1/hook") is False
    assert is_safe_webhook_url("http://localhost/hook") is False
    assert is_safe_webhook_url("http://10.0.0.5/hook") is False
    assert is_safe_webhook_url("http://169.254.169.254/latest/meta-data") is False
    assert is_safe_webhook_url("http://metadata.google.internal/") is False
    assert is_safe_webhook_url("ftp://example.com/x") is False


def test_ssrf_guard_allows_public():
    assert is_safe_webhook_url("https://hooks.slack.com/services/T/B/X") is True
    assert is_safe_webhook_url("https://discord.com/api/webhooks/1/abc") is True


def test_security_headers_present():
    from fastapi.testclient import TestClient
    from api_server import app

    client = TestClient(app)
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert "Content-Security-Policy" in r.headers
