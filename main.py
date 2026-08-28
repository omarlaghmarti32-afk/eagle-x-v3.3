"""Root-level FastAPI entry for Vercel / generic ASGI hosts."""

from __future__ import annotations

import os

os.environ.setdefault("EAGLE_LIVE_MONITOR", "0")
os.environ.setdefault("EAGLE_HEALTH_INTERNAL", "0")
os.environ.setdefault("EAGLE_DATA_DIR", os.environ.get("EAGLE_DATA_DIR", "/tmp/eagle-x-data"))
os.environ.setdefault("EAGLE_LOG_DIR", os.environ.get("EAGLE_LOG_DIR", "/tmp/eagle-x-logs"))

from api_server import app  # noqa: E402

__all__ = ["app"]
