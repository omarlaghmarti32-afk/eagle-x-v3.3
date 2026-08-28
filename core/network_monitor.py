import asyncio
import time
import random
import socket
import logging
from typing import AsyncGenerator, List

logger = logging.getLogger("EAGLE-X")

class NetworkMonitor:
    """Real-time Network Monitoring System (simulated packet stream)"""
    def __init__(self, port: int = 8080):
        self.port = port
        try:
            self.hostname = socket.gethostname()
        except Exception:
            self.hostname = "localhost"
        logger.info(f"Network Monitor listening on {self.hostname}:{self.port}")

    async def start_monitoring(self, duration: int = 60) -> AsyncGenerator[List[float], None]:
        logger.info(f"Starting network scan for {duration} seconds...")
        start_time = time.time()
        while time.time() - start_time < duration:
            # Simulate network packet features:
            # [packet_size, frequency, protocol_id, entropy]
            packet_data = [random.random() for _ in range(4)]
            yield packet_data
            await asyncio.sleep(2)
