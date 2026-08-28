"""SQLite-backed threat log and audit trail."""

from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import DB_PATH


class ThreatDB:
    def __init__(self, path: Path = DB_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_schema()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._lock, self._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS threats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    threat_type TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    severity TEXT NOT NULL,
                    source TEXT,
                    features TEXT,
                    action_taken TEXT,
                    status TEXT NOT NULL,
                    sealed TEXT
                );

                CREATE TABLE IF NOT EXISTS audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event TEXT NOT NULL,
                    details TEXT,
                    signature TEXT
                );

                CREATE TABLE IF NOT EXISTS blocklist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    indicator TEXT NOT NULL UNIQUE,
                    indicator_type TEXT NOT NULL,
                    reason TEXT,
                    created_at TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1
                );

                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    packets_scanned INTEGER,
                    threats_detected INTEGER,
                    cpu REAL,
                    mem REAL
                );
                """
            )

    def add_threat(
        self,
        threat_type: str,
        confidence: float,
        severity: str = "medium",
        source: str = "detector",
        features: Optional[Dict[str, Any]] = None,
        action_taken: str = "logged",
        status: str = "detected",
        sealed: Optional[str] = None,
    ) -> int:
        ts = datetime.now(timezone.utc).isoformat()
        with self._lock, self._conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO threats
                (timestamp, threat_type, confidence, severity, source, features, action_taken, status, sealed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ts,
                    threat_type,
                    confidence,
                    severity,
                    source,
                    json.dumps(features or {}),
                    action_taken,
                    status,
                    sealed,
                ),
            )
            return int(cur.lastrowid)

    def list_threats(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock, self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM threats ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    def count_threats(self) -> int:
        with self._lock, self._conn() as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM threats").fetchone()
            return int(row["c"])

    def add_audit(self, event: str, details: Optional[Dict] = None, signature: str = "") -> None:
        ts = datetime.now(timezone.utc).isoformat()
        with self._lock, self._conn() as conn:
            conn.execute(
                "INSERT INTO audit (timestamp, event, details, signature) VALUES (?, ?, ?, ?)",
                (ts, event, json.dumps(details or {}), signature),
            )

    def add_block(self, indicator: str, indicator_type: str = "ip", reason: str = "") -> None:
        ts = datetime.now(timezone.utc).isoformat()
        with self._lock, self._conn() as conn:
            conn.execute(
                """
                INSERT INTO blocklist (indicator, indicator_type, reason, created_at, active)
                VALUES (?, ?, ?, ?, 1)
                ON CONFLICT(indicator) DO UPDATE SET active=1, reason=excluded.reason
                """,
                (indicator, indicator_type, reason, ts),
            )

    def is_blocked(self, indicator: str) -> bool:
        with self._lock, self._conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM blocklist WHERE indicator=? AND active=1", (indicator,)
            ).fetchone()
            return row is not None

    def list_blocks(self) -> List[Dict[str, Any]]:
        with self._lock, self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM blocklist WHERE active=1 ORDER BY id DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    def record_metrics(self, packets: int, threats: int, cpu: float, mem: float) -> None:
        ts = datetime.now(timezone.utc).isoformat()
        with self._lock, self._conn() as conn:
            conn.execute(
                "INSERT INTO metrics (timestamp, packets_scanned, threats_detected, cpu, mem) VALUES (?, ?, ?, ?, ?)",
                (ts, packets, threats, cpu, mem),
            )
