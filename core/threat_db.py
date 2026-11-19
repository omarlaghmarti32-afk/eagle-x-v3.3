"""SQLite-backed threat log and audit trail."""

from __future__ import annotations

import json
import math
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
        conn.execute("PRAGMA foreign_keys = ON")
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

                CREATE TABLE IF NOT EXISTS assets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    asset_type TEXT NOT NULL,
                    address TEXT,
                    criticality TEXT NOT NULL DEFAULT 'medium',
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS detection_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    metric TEXT NOT NULL,
                    operator TEXT NOT NULL CHECK(operator IN ('gt', 'gte', 'lt', 'lte', 'eq')),
                    threshold REAL NOT NULL,
                    severity TEXT NOT NULL CHECK(severity IN ('low', 'medium', 'high', 'critical')),
                    enabled INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0, 1)),
                    asset_id INTEGER REFERENCES assets(id) ON DELETE SET NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_detection_rules_enabled ON detection_rules(enabled);

                CREATE TABLE IF NOT EXISTS detection_rule_state (
                    rule_id INTEGER PRIMARY KEY REFERENCES detection_rules(id) ON DELETE CASCADE,
                    active_match INTEGER NOT NULL DEFAULT 0 CHECK(active_match IN (0, 1)),
                    active_incident_id INTEGER REFERENCES incidents(id) ON DELETE SET NULL,
                    last_value REAL,
                    last_evaluated_at TEXT
                );

                CREATE TABLE IF NOT EXISTS incidents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    severity TEXT NOT NULL DEFAULT 'medium',
                    status TEXT NOT NULL DEFAULT 'open',
                    source TEXT NOT NULL DEFAULT 'manual',
                    asset_id INTEGER REFERENCES assets(id) ON DELETE SET NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status);
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

    def add_asset(
        self,
        name: str,
        asset_type: str,
        address: Optional[str] = None,
        criticality: str = "medium",
        notes: str = "",
    ) -> int:
        ts = datetime.now(timezone.utc).isoformat()
        with self._lock, self._conn() as conn:
            cur = conn.execute(
                """INSERT INTO assets
                   (name, asset_type, address, criticality, notes, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (name, asset_type, address, criticality, notes, ts, ts),
            )
            return int(cur.lastrowid)

    def list_assets(self, limit: int = 200) -> List[Dict[str, Any]]:
        with self._lock, self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM assets ORDER BY name COLLATE NOCASE LIMIT ?", (limit,)
            ).fetchall()
            return [dict(row) for row in rows]

    def get_asset(self, asset_id: int) -> Optional[Dict[str, Any]]:
        with self._lock, self._conn() as conn:
            row = conn.execute("SELECT * FROM assets WHERE id = ?", (asset_id,)).fetchone()
            return dict(row) if row else None

    def add_incident(
        self,
        title: str,
        description: str = "",
        severity: str = "medium",
        source: str = "manual",
        asset_id: Optional[int] = None,
    ) -> int:
        ts = datetime.now(timezone.utc).isoformat()
        with self._lock, self._conn() as conn:
            cur = conn.execute(
                """INSERT INTO incidents
                   (title, description, severity, status, source, asset_id, created_at, updated_at)
                   VALUES (?, ?, ?, 'open', ?, ?, ?, ?)""",
                (title, description, severity, source, asset_id, ts, ts),
            )
            return int(cur.lastrowid)

    def list_incidents(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock, self._conn() as conn:
            rows = conn.execute(
                """SELECT i.*, a.name AS asset_name
                   FROM incidents AS i LEFT JOIN assets AS a ON a.id = i.asset_id
                   ORDER BY i.id DESC LIMIT ?""",
                (limit,),
            ).fetchall()
            return [dict(row) for row in rows]

    def update_incident_status(self, incident_id: int, status: str) -> bool:
        ts = datetime.now(timezone.utc).isoformat()
        with self._lock, self._conn() as conn:
            cur = conn.execute(
                "UPDATE incidents SET status = ?, updated_at = ? WHERE id = ?",
                (status, ts, incident_id),
            )
            return cur.rowcount > 0

    def add_detection_rule(
        self,
        name: str,
        metric: str,
        operator: str,
        threshold: float,
        severity: str = "medium",
        enabled: bool = True,
        asset_id: Optional[int] = None,
    ) -> int:
        ts = datetime.now(timezone.utc).isoformat()
        with self._lock, self._conn() as conn:
            cur = conn.execute(
                """INSERT INTO detection_rules
                   (name, metric, operator, threshold, severity, enabled, asset_id, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (name, metric, operator, threshold, severity, int(enabled), asset_id, ts, ts),
            )
            return int(cur.lastrowid)

    def list_detection_rules(self) -> List[Dict[str, Any]]:
        with self._lock, self._conn() as conn:
            rows = conn.execute(
                """SELECT r.*, a.name AS asset_name,
                          COALESCE(s.active_match, 0) AS active_match,
                          s.active_incident_id, s.last_value, s.last_evaluated_at
                   FROM detection_rules AS r
                   LEFT JOIN assets AS a ON a.id = r.asset_id
                   LEFT JOIN detection_rule_state AS s ON s.rule_id = r.id
                   ORDER BY r.id DESC"""
            ).fetchall()
            rules = [dict(row) for row in rows]
            for rule in rules:
                rule["enabled"] = bool(rule["enabled"])
                rule["active_match"] = bool(rule["active_match"])
            return rules

    def get_detection_rule(self, rule_id: int) -> Optional[Dict[str, Any]]:
        with self._lock, self._conn() as conn:
            row = conn.execute(
                """SELECT r.*, a.name AS asset_name,
                          COALESCE(s.active_match, 0) AS active_match,
                          s.active_incident_id, s.last_value, s.last_evaluated_at
                   FROM detection_rules AS r
                   LEFT JOIN assets AS a ON a.id = r.asset_id
                   LEFT JOIN detection_rule_state AS s ON s.rule_id = r.id
                   WHERE r.id = ?""",
                (rule_id,),
            ).fetchone()
            if row is None:
                return None
            rule = dict(row)
            rule["enabled"] = bool(rule["enabled"])
            rule["active_match"] = bool(rule["active_match"])
            return rule

    def set_detection_rule_enabled(self, rule_id: int, enabled: bool) -> bool:
        ts = datetime.now(timezone.utc).isoformat()
        with self._lock, self._conn() as conn:
            rule = conn.execute("SELECT name FROM detection_rules WHERE id = ?", (rule_id,)).fetchone()
            if rule is None:
                return False
            cur = conn.execute(
                "UPDATE detection_rules SET enabled = ?, updated_at = ? WHERE id = ?",
                (int(enabled), ts, rule_id),
            )
            state = conn.execute(
                "SELECT active_match FROM detection_rule_state WHERE rule_id = ?", (rule_id,)
            ).fetchone()
            if not enabled and state and state["active_match"]:
                conn.execute(
                    """UPDATE detection_rule_state
                       SET active_match = 0, active_incident_id = NULL, last_evaluated_at = ?
                       WHERE rule_id = ?""",
                    (ts, rule_id),
                )
                details = {"rule_id": rule_id, "name": rule["name"], "reason": "disabled"}
                conn.execute(
                    "INSERT INTO audit (timestamp, event, details, signature) VALUES (?, ?, ?, '')",
                    (ts, "detection_rule_cleared", json.dumps(details)),
                )
            return cur.rowcount > 0

    def evaluate_detection_rules(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate local telemetry; create one incident per breach episode."""
        compare = {
            "gt": lambda value, threshold: value > threshold,
            "gte": lambda value, threshold: value >= threshold,
            "lt": lambda value, threshold: value < threshold,
            "lte": lambda value, threshold: value <= threshold,
            "eq": lambda value, threshold: value == threshold,
        }
        evaluated = 0
        matches: List[Dict[str, Any]] = []
        new_incidents: List[Dict[str, Any]] = []
        cleared: List[Dict[str, Any]] = []
        ts = datetime.now(timezone.utc).isoformat()

        with self._lock, self._conn() as conn:
            rules = conn.execute("SELECT * FROM detection_rules ORDER BY id").fetchall()
            for rule in rules:
                state = conn.execute(
                    "SELECT * FROM detection_rule_state WHERE rule_id = ?", (rule["id"],)
                ).fetchone()
                was_active = bool(state and state["active_match"])

                if not rule["enabled"]:
                    if was_active:
                        conn.execute(
                            """UPDATE detection_rule_state
                               SET active_match = 0, active_incident_id = NULL, last_evaluated_at = ?
                               WHERE rule_id = ?""",
                            (ts, rule["id"]),
                        )
                        details = {"rule_id": rule["id"], "name": rule["name"], "reason": "disabled"}
                        conn.execute(
                            "INSERT INTO audit (timestamp, event, details, signature) VALUES (?, ?, ?, '')",
                            (ts, "detection_rule_cleared", json.dumps(details)),
                        )
                        cleared.append(details)
                    continue

                raw_value = metrics.get(rule["metric"])
                if raw_value is None:
                    continue
                try:
                    value = float(raw_value)
                    threshold = float(rule["threshold"])
                except (TypeError, ValueError, OverflowError):
                    continue
                if not math.isfinite(value) or not math.isfinite(threshold):
                    continue

                evaluated += 1
                matched = compare[rule["operator"]](value, threshold)
                if matched:
                    incident_id = state["active_incident_id"] if was_active else None
                    created = not was_active
                    if created:
                        description = (
                            f"Detection rule #{rule['id']} matched: {rule['metric']} "
                            f"{rule['operator']} {threshold:g}; observed {value:g}."
                        )
                        incident_cur = conn.execute(
                            """INSERT INTO incidents
                               (title, description, severity, status, source, asset_id, created_at, updated_at)
                               VALUES (?, ?, ?, 'open', 'detection_rule', ?, ?, ?)""",
                            (rule["name"], description, rule["severity"], rule["asset_id"], ts, ts),
                        )
                        incident_id = int(incident_cur.lastrowid)
                        conn.execute(
                            """INSERT INTO audit (timestamp, event, details, signature)
                               VALUES (?, ?, ?, '')""",
                            (
                                ts,
                                "detection_rule_triggered",
                                json.dumps(
                                    {
                                        "rule_id": rule["id"],
                                        "incident_id": incident_id,
                                        "metric": rule["metric"],
                                        "value": value,
                                        "threshold": threshold,
                                        "asset_id": rule["asset_id"],
                                    }
                                ),
                            ),
                        )
                        conn.execute(
                            """INSERT INTO detection_rule_state
                               (rule_id, active_match, active_incident_id, last_value, last_evaluated_at)
                               VALUES (?, 1, ?, ?, ?)
                               ON CONFLICT(rule_id) DO UPDATE SET
                                 active_match = 1,
                                 active_incident_id = excluded.active_incident_id,
                                 last_value = excluded.last_value,
                                 last_evaluated_at = excluded.last_evaluated_at""",
                            (rule["id"], incident_id, value, ts),
                        )
                    match = {
                        "rule_id": rule["id"],
                        "name": rule["name"],
                        "metric": rule["metric"],
                        "operator": rule["operator"],
                        "threshold": threshold,
                        "value": value,
                        "severity": rule["severity"],
                        "asset_id": rule["asset_id"],
                        "incident_id": incident_id,
                        "new_incident": created,
                    }
                    matches.append(match)
                    if created:
                        new_incidents.append(match)
                elif was_active:
                    conn.execute(
                        """UPDATE detection_rule_state
                           SET active_match = 0, active_incident_id = NULL,
                               last_value = ?, last_evaluated_at = ?
                           WHERE rule_id = ?""",
                        (value, ts, rule["id"]),
                    )
                    details = {
                        "rule_id": rule["id"],
                        "name": rule["name"],
                        "value": value,
                        "reason": "condition_cleared",
                    }
                    conn.execute(
                        "INSERT INTO audit (timestamp, event, details, signature) VALUES (?, ?, ?, '')",
                        (ts, "detection_rule_cleared", json.dumps(details)),
                    )
                    cleared.append(details)

        return {
            "evaluated": evaluated,
            "matches": matches,
            "new_incidents": new_incidents,
            "cleared": cleared,
        }
