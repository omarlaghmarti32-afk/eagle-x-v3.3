"""Continuous host monitoring stream."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import AsyncGenerator, Dict, List

from .config import MONITOR_INTERVAL
from .system_monitor import SystemMonitor

logger = logging.getLogger("EAGLE-X")


class NetworkMonitor:
    def __init__(self):
        self.system = SystemMonitor()
        self.packets_scanned = 0
        logger.info("Network/System monitor initialized (psutil-backed)")

    async def start_monitoring(
        self, duration: int = 0, interval: float = MONITOR_INTERVAL
    ) -> AsyncGenerator[List[float], None]:
        """Yield feature vectors. duration=0 means run forever."""
        logger.info(
            f"Starting continuous monitoring (duration={duration or 'infinite'}s, interval={interval}s)"
        )
        start = time.time()
        while True:
            if duration and (time.time() - start) >= duration:
                break
            features = self.system.feature_vector()
            self.packets_scanned += 1
            yield features
            await asyncio.sleep(interval)

    def one_shot(self) -> Dict[str, float]:
        return self.system.snapshot()
