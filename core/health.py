"""Deep health checks for EAGLE-X components."""

from __future__ import annotations

import os
import shutil
import time
from pathlib import Path
from typing import Any, Dict, Optional

import psutil

from .config import DATA_DIR, DB_PATH, KEY_PATH, SEAL, VERSION


def _check_disk(path: Path, min_free_mb: int = 100) -> Dict[str, Any]:
    try:
        usage = shutil.disk_usage(path)
        free_mb = usage.free // (1024 * 1024)
        ok = free_mb >= min_free_mb
        return {
            "ok": ok,
            "free_mb": free_mb,
            "total_mb": usage.total // (1024 * 1024),
            "used_percent": round(usage.used / usage.total * 100, 1),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _check_db(db) -> Dict[str, Any]:
    try:
        count = db.count_threats()
        exists = Path(DB_PATH).exists()
        return {"ok": True, "path": str(DB_PATH), "exists": exists, "threats": count}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _check_crypto(pqc) -> Dict[str, Any]:
    try:
        token = pqc.encrypt("health-check")
        plain = pqc.decrypt(token)
        sig = pqc.sign("health-check")
        verified = pqc.verify_signature("health-check", sig)
        ok = plain == "health-check" and verified
        return {
            "ok": ok,
            "mode": getattr(pqc, "mode", "unknown"),
            "key_exists": Path(KEY_PATH).exists(),
            "pqc": pqc.get_status().get("pqc", {}),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _check_ai(detector) -> Dict[str, Any]:
    try:
        result = detector.analyze([10, 40, 1000, 2000, 150, 20, 50, 0.05])
        ok = "threat_detected" in result and "confidence" in result
        return {"ok": ok, "trained": getattr(detector, "_is_trained", False)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _check_host() -> Dict[str, Any]:
    try:
        cpu = psutil.cpu_percent(interval=0.05)
        mem = psutil.virtual_memory()
        return {
            "ok": True,
            "cpu_percent": cpu,
            "mem_percent": mem.percent,
            "mem_available_mb": mem.available // (1024 * 1024),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def run_health_checks(
    *,
    db=None,
    pqc=None,
    detector=None,
    uptime_seconds: int = 0,
    packets_scanned: int = 0,
    live_monitor: bool = False,
) -> Dict[str, Any]:
    checks: Dict[str, Any] = {
        "disk": _check_disk(DATA_DIR),
        "host": _check_host(),
    }
    if db is not None:
        checks["database"] = _check_db(db)
    if pqc is not None:
        checks["crypto"] = _check_crypto(pqc)
    if detector is not None:
        checks["ai"] = _check_ai(detector)

    failed = [name for name, c in checks.items() if not c.get("ok")]
    status = "ok" if not failed else "degraded" if len(failed) < len(checks) else "down"

    return {
        "status": status,
        "version": VERSION,
        "seal": SEAL,
        "uptime_seconds": uptime_seconds,
        "packets_scanned": packets_scanned,
        "live_monitor": live_monitor,
        "checks": checks,
        "failed": failed,
        "timestamp": time.time(),
    }
