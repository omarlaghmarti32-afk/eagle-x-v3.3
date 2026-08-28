"""Optional packet-level observation via scapy (requires privileges).

If scapy is missing or capture is denied, returns empty samples safely.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from typing import Deque, Dict, List, Optional

logger = logging.getLogger("EAGLE-X")

try:
    from scapy.all import IP, TCP, UDP, sniff  # type: ignore

    _SCAPY = True
except Exception:
    _SCAPY = False
    logger.info("scapy not available; packet capture disabled")


class PacketCapture:
    def __init__(self, iface: Optional[str] = None, maxlen: int = 500):
        self.iface = iface
        self.samples: Deque[Dict] = deque(maxlen=maxlen)
        self.enabled = _SCAPY
        self.error: Optional[str] = None

    def capture_burst(self, count: int = 20, timeout: int = 2) -> List[Dict]:
        if not self.enabled:
            return []
        try:
            packets = sniff(iface=self.iface, count=count, timeout=timeout, store=True)
            out: List[Dict] = []
            for pkt in packets:
                rec = {
                    "ts": time.time(),
                    "len": len(pkt),
                    "proto": None,
                    "src": None,
                    "dst": None,
                    "sport": None,
                    "dport": None,
                }
                if IP in pkt:
                    rec["src"] = pkt[IP].src
                    rec["dst"] = pkt[IP].dst
                    rec["proto"] = pkt[IP].proto
                if TCP in pkt:
                    rec["sport"] = int(pkt[TCP].sport)
                    rec["dport"] = int(pkt[TCP].dport)
                    rec["proto"] = "TCP"
                elif UDP in pkt:
                    rec["sport"] = int(pkt[UDP].sport)
                    rec["dport"] = int(pkt[UDP].dport)
                    rec["proto"] = "UDP"
                out.append(rec)
                self.samples.append(rec)
            return out
        except Exception as e:
            self.error = str(e)
            logger.warning(f"Packet capture failed: {e}")
            return []

    def summary_features(self) -> Dict[str, float]:
        """Aggregate recent packets into numeric features."""
        if not self.samples:
            return {
                "pkt_rate": 0.0,
                "avg_size": 0.0,
                "tcp_ratio": 0.0,
                "unique_dst": 0.0,
            }
        items = list(self.samples)
        n = len(items)
        avg_size = sum(i["len"] for i in items) / n
        tcp = sum(1 for i in items if i.get("proto") == "TCP") / n
        unique_dst = float(len({i.get("dst") for i in items if i.get("dst")}))
        span = max(items[-1]["ts"] - items[0]["ts"], 0.001)
        return {
            "pkt_rate": n / span,
            "avg_size": avg_size,
            "tcp_ratio": tcp,
            "unique_dst": unique_dst,
        }

    def status(self) -> dict:
        return {
            "scapy": _SCAPY,
            "enabled": self.enabled,
            "iface": self.iface,
            "buffered": len(self.samples),
            "error": self.error,
        }
