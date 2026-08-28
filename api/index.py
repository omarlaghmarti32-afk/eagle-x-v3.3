"""Vercel Python entrypoint — exports FastAPI `app`.

Vercel looks for a FastAPI instance named `app` in supported modules.
Background loops are disabled in serverless (no persistent process).
"""

from __future__ import annotations

import os

# Serverless-safe defaults (must be set before importing api_server)
os.environ.setdefault("EAGLE_LIVE_MONITOR", "0")
os.environ.setdefault("EAGLE_HEALTH_INTERNAL", "0")
os.environ.setdefault("EAGLE_DATA_DIR", "/tmp/eagle-x-data")
os.environ.setdefault("EAGLE_LOG_DIR", "/tmp/eagle-x-logs")

from api_server import app  # noqa: E402

__all__ = ["app"]
