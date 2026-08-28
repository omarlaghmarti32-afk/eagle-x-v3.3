#!/usr/bin/env python3
"""External health monitor — polls EAGLE-X and logs/alerts on failure.

Usage:
  python scripts/health_monitor.py
  EAGLE_HEALTH_URL=https://localhost/api/health/deep python scripts/health_monitor.py
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

URL = os.environ.get("EAGLE_HEALTH_URL", "http://127.0.0.1:8080/api/health/deep")
INTERVAL = float(os.environ.get("EAGLE_HEALTH_INTERVAL", "30"))
TIMEOUT = float(os.environ.get("EAGLE_HEALTH_TIMEOUT", "8"))
FAIL_THRESHOLD = int(os.environ.get("EAGLE_HEALTH_FAIL_THRESHOLD", "3"))
LOG_PATH = Path(os.environ.get("EAGLE_HEALTH_LOG", "/tmp/eagle-health-monitor.log"))
INSECURE = os.environ.get("EAGLE_HEALTH_INSECURE", "0") in ("1", "true", "True")


def log(msg: str) -> None:
    line = f"{datetime.now(timezone.utc).isoformat()} | {msg}"
    print(line, flush=True)
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def fetch() -> tuple[int, dict]:
    ctx = None
    if INSECURE and URL.startswith("https://"):
        import ssl

        ctx = ssl._create_unverified_context()
    req = urllib.request.Request(URL, method="GET")
    with urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx) as resp:
        body = json.loads(resp.read().decode("utf-8"))
        return resp.status, body


def main() -> int:
    log(f"Health monitor started url={URL} interval={INTERVAL}s")
    consecutive_fails = 0
    while True:
        try:
            status_code, body = fetch()
            st = body.get("status", "unknown")
            failed = body.get("failed", [])
            if status_code == 200 and st in ("ok", "degraded"):
                if st == "degraded":
                    log(f"WARN degraded failed={failed} uptime={body.get('uptime_seconds')}")
                    consecutive_fails += 1
                else:
                    log(
                        f"OK status={st} uptime={body.get('uptime_seconds')} "
                        f"packets={body.get('packets_scanned')}"
                    )
                    consecutive_fails = 0
            else:
                consecutive_fails += 1
                log(f"FAIL http={status_code} body={body} streak={consecutive_fails}")
        except Exception as e:
            consecutive_fails += 1
            log(f"FAIL error={e} streak={consecutive_fails}")

        if consecutive_fails >= FAIL_THRESHOLD:
            log(f"ALERT service unhealthy for {consecutive_fails} consecutive checks")
            # Optional webhook
            webhook = os.environ.get("EAGLE_HEALTH_WEBHOOK")
            if webhook:
                try:
                    data = json.dumps(
                        {
                            "text": f"EAGLE-X unhealthy: {consecutive_fails} fails",
                            "url": URL,
                        }
                    ).encode()
                    req = urllib.request.Request(
                        webhook,
                        data=data,
                        headers={"Content-Type": "application/json"},
                        method="POST",
                    )
                    urllib.request.urlopen(req, timeout=5)
                except Exception as we:
                    log(f"webhook error: {we}")

        time.sleep(INTERVAL)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        log("Health monitor stopped")
        sys.exit(0)
