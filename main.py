"""Root-level FastAPI entry for Vercel / generic ASGI hosts."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

os.environ.setdefault("EAGLE_LIVE_MONITOR", "0")
os.environ.setdefault("EAGLE_HEALTH_INTERNAL", "0")
os.environ.setdefault(
    "EAGLE_DATA_DIR", os.environ.get("EAGLE_DATA_DIR", "/tmp/eagle-x-data")
)
os.environ.setdefault(
    "EAGLE_LOG_DIR", os.environ.get("EAGLE_LOG_DIR", "/tmp/eagle-x-logs")
)

from api_server import app  # noqa: E402

__all__ = ["app"]
