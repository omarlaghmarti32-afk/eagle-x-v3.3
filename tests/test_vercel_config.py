"""Keep Vercel routing delegated to the configured FastAPI entrypoint."""

import json
from pathlib import Path


def test_vercel_config_does_not_rewrite_fastapi_routes():
    config = json.loads((Path(__file__).parents[1] / "vercel.json").read_text())

    # Vercel detects FastAPI and routes requests to main:app automatically.
    # A catch-all rewrite to /api/index can replace the original request path.
    assert "rewrites" not in config
