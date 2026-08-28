"""Real host metrics collection via psutil."""

from __future__ import annotations

import hashlib
import time
from typing import Dict, List

import psutil

from .config import FEATURE_NAMES


class SystemMonitor:
    def __init__(self):
        self._prev_net = psutil.net_io_counters()
        self._prev_time = time.time()

    def snapshot(self) -> Dict[str, float]:
        now = time.time()
        net = psutil.net_io_counters()
        dt = max(now - self._prev_time, 0.001)

        sent_rate = max(0.0, (net.bytes_sent - self._prev_net.bytes_sent) / dt)
        recv_rate = max(0.0, (net.bytes_recv - self._prev_net.bytes_recv) / dt)

        self._prev_net = net
        self._prev_time = now

        try:
            conns = len(psutil.net_connections(kind="inet"))
        except (psutil.AccessDenied, PermissionError):
            conns = 0

        cpu = float(psutil.cpu_percent(interval=0.1))
        mem = float(psutil.virtual_memory().percent)
        procs = float(len(psutil.pids()))
        disk = float(psutil.disk_usage("/").percent)

        # Lightweight entropy proxy from rate magnitudes
        entropy_proxy = min(1.0, (sent_rate + recv_rate) / 1_000_000.0)

        features = {
            "cpu_percent": cpu,
            "mem_percent": mem,
            "net_bytes_sent_rate": sent_rate,
            "net_bytes_recv_rate": recv_rate,
            "process_count": procs,
            "connection_count": float(conns),
            "disk_usage_percent": disk,
            "entropy_proxy": entropy_proxy,
        }
        return features

    def feature_vector(self) -> List[float]:
        snap = self.snapshot()
        return [snap[name] for name in FEATURE_NAMES]

    def integrity_hash(self, paths: List[str]) -> str:
        h = hashlib.sha3_256()
        for p in paths:
            try:
                with open(p, "rb") as f:
                    while True:
                        chunk = f.read(65536)
                        if not chunk:
                            break
                        h.update(chunk)
            except OSError:
                h.update(p.encode())
        return h.hexdigest()
