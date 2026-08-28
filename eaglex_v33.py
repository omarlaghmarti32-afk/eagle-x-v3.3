#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════════════════════
# EAGLE-X v3.3 – Operational Cybersecurity Engine
# Seal: 310-70-94 | Noran Ultimate Systems
# ═══════════════════════════════════════════════════════════════════════════════

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
import time
from typing import Dict

from core.ai_detector import AIThreatDetector
from core.config import LOG_DIR, SEAL, VERSION
from core.network_monitor import NetworkMonitor
from core.pqc_manager import PQCManager
from core.self_healing import SelfHealingEngine
from core.threat_db import ThreatDB

LOG_FILE = os.path.join(str(LOG_DIR), "eagle-x.log")
os.makedirs(str(LOG_DIR), exist_ok=True)

logging.basicConfig(
    level=getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | EAGLE-X | %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("EAGLE-X")


class EAGLEX:
    def __init__(self):
        self.version = VERSION
        self.seal = SEAL
        self.pqc = PQCManager()
        self.ai = AIThreatDetector()
        self.monitor = NetworkMonitor()
        self.db = ThreatDB()
        self.healer = SelfHealingEngine(crypto=self.pqc.crypto, db=self.db)
        self.threat_history = []
        self.system_metrics = {
            "uptime_seconds": 0,
            "packets_scanned": 0,
            "threats_neutralized": 0,
            "system_integrity": 100.0,
            "pqc_status": self.pqc.algorithm,
        }

    async def run(self, duration: int = 60):
        logger.info(f"EAGLE-X v{self.version} starting... Seal: {self.seal}")
        print(
            r"""
    _______  _______  _______  _______        __   __ 
   |       ||   _   ||       ||       |      |  |_|  |
   |    ___||  |_|  ||    ___||    ___| ____ |       |
   |   |___ |       ||   | __ ||   |___ |____||       |
   |    ___||       ||   ||  ||    ___|      |       |
   |   |___ |   _   ||   |_| ||   |___        |     | 
   |_______||__| |__||_______||_______|        |___|  
        """
        )

        self.ai.train_mock()
        self.db.add_audit("cli_start", {"duration": duration})
        start_time = time.time()

        async for packet in self.monitor.start_monitoring(duration):
            self.system_metrics["packets_scanned"] += 1
            self.system_metrics["uptime_seconds"] = int(time.time() - start_time)

            analysis = self.ai.analyze(packet)
            if analysis.get("threat_detected"):
                self.system_metrics["threats_neutralized"] += 1
                sealed = self.pqc.seal(analysis)
                tid = self.db.add_threat(
                    threat_type=analysis.get("threat_type", "UNKNOWN"),
                    confidence=float(analysis.get("confidence", 0)),
                    severity=analysis.get("severity", "medium"),
                    source="cli",
                    features=analysis.get("features"),
                    action_taken="heal",
                    status="neutralized",
                    sealed=sealed.get("ciphertext"),
                )
                self.threat_history.append(analysis)
                logger.warning(
                    f"THREAT #{tid} {analysis.get('threat_type')} conf={analysis['confidence']:.2%}"
                )
                result = await self.healer.heal(
                    analysis.get("threat_type", "UNKNOWN"),
                    context={"features": analysis.get("features")},
                )
                if result.get("success"):
                    logger.info("Threat neutralized successfully.")
            else:
                logger.info(
                    f"Scan normal | cpu={analysis.get('features', {}).get('cpu_percent', 0):.1f}% "
                    f"mem={analysis.get('features', {}).get('mem_percent', 0):.1f}%"
                )

        self.db.add_audit("cli_stop", self.system_metrics)

    def get_status(self) -> Dict:
        return {
            "version": self.version,
            "seal": self.seal,
            "status": "Operational",
            "metrics": self.system_metrics,
            "recent_threats": self.threat_history[-10:],
            "pqc": self.pqc.get_status(),
            "db_threats": self.db.count_threats(),
        }


def main():
    parser = argparse.ArgumentParser(description="EAGLE-X v3.3 Operational Engine")
    parser.add_argument("--mode", choices=["production", "staging"], default="production")
    parser.add_argument("--duration", type=int, default=60, help="0 = run forever")
    args = parser.parse_args()

    eagle = EAGLEX()
    try:
        asyncio.run(eagle.run(args.duration))
    except KeyboardInterrupt:
        logger.info("EAGLE-X shutting down gracefully...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
