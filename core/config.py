"""Central configuration for EAGLE-X v3.3"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("EAGLE_DATA_DIR", BASE_DIR / "data"))
LOG_DIR = Path(os.environ.get("EAGLE_LOG_DIR", "/tmp"))

DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

VERSION = "3.3"
SEAL = "310-70-94"

# Security
API_TOKEN = os.environ.get("EAGLE_API_TOKEN", "eagle-x-dev-token-change-me")
SENSITIVITY = float(os.environ.get("EAGLE_AI_SENSITIVITY", "0.75"))
MONITOR_INTERVAL = float(os.environ.get("EAGLE_MONITOR_INTERVAL", "2.0"))

# Paths
DB_PATH = DATA_DIR / "eagle_x.db"
KEY_PATH = DATA_DIR / "master.key"
AUDIT_PATH = DATA_DIR / "audit.jsonl"

# Feature names used by detector
FEATURE_NAMES = [
    "cpu_percent",
    "mem_percent",
    "net_bytes_sent_rate",
    "net_bytes_recv_rate",
    "process_count",
    "connection_count",
    "disk_usage_percent",
    "entropy_proxy",
]
