"""EAGLE-X v3.3 Core Modules

Lazy exports so importing a single submodule does not force heavy deps
(e.g. sklearn) unless needed.
"""

from __future__ import annotations

__all__ = [
    "PQCManager",
    "AIThreatDetector",
    "NetworkMonitor",
    "SelfHealingEngine",
    "SystemMonitor",
    "ThreatDB",
    "CryptoEngine",
    "RealPQC",
    "PacketCapture",
]


def __getattr__(name: str):
    if name == "PQCManager":
        from .pqc_manager import PQCManager

        return PQCManager
    if name == "AIThreatDetector":
        from .ai_detector import AIThreatDetector

        return AIThreatDetector
    if name == "NetworkMonitor":
        from .network_monitor import NetworkMonitor

        return NetworkMonitor
    if name == "SelfHealingEngine":
        from .self_healing import SelfHealingEngine

        return SelfHealingEngine
    if name == "SystemMonitor":
        from .system_monitor import SystemMonitor

        return SystemMonitor
    if name == "ThreatDB":
        from .threat_db import ThreatDB

        return ThreatDB
    if name == "CryptoEngine":
        from .crypto_engine import CryptoEngine

        return CryptoEngine
    if name == "RealPQC":
        from .pqc_real import RealPQC

        return RealPQC
    if name == "PacketCapture":
        from .packet_capture import PacketCapture

        return PacketCapture
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
