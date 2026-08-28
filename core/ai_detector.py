"""Hybrid anomaly + supervised threat detector."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

import numpy as np
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.preprocessing import StandardScaler

from .config import FEATURE_NAMES, SENSITIVITY

logger = logging.getLogger("EAGLE-X")


class AIThreatDetector:
    def __init__(self, sensitivity: float = SENSITIVITY):
        self.sensitivity = sensitivity
        self.feature_count = len(FEATURE_NAMES)
        self.scaler = StandardScaler()
        self.anomaly = IsolationForest(
            n_estimators=200, contamination=0.05, random_state=42
        )
        self.clf = RandomForestClassifier(n_estimators=150, random_state=42)
        self._is_trained = False
        logger.info("AI Threat Detector ready (IsolationForest + RandomForest)")

    def train_mock(self) -> None:
        """Train on synthetic host-metric distributions (bootstrap)."""
        rng = np.random.default_rng(42)
        n = 2000
        # Normal baseline
        normal = np.column_stack(
            [
                rng.normal(15, 8, n),   # cpu
                rng.normal(45, 10, n),  # mem
                rng.exponential(50_000, n),  # sent
                rng.exponential(80_000, n),  # recv
                rng.normal(180, 30, n),  # processes
                rng.normal(40, 15, n),   # connections
                rng.normal(55, 10, n),   # disk
                rng.uniform(0.01, 0.2, n),  # entropy
            ]
        )
        # Attack-like spikes
        attack = np.column_stack(
            [
                rng.normal(85, 10, n // 4),
                rng.normal(90, 5, n // 4),
                rng.exponential(2_000_000, n // 4),
                rng.exponential(2_500_000, n // 4),
                rng.normal(400, 50, n // 4),
                rng.normal(300, 80, n // 4),
                rng.normal(70, 10, n // 4),
                rng.uniform(0.6, 1.0, n // 4),
            ]
        )
        X = np.vstack([normal, attack])
        y = np.array([0] * len(normal) + [1] * len(attack))

        self.scaler.fit(X)
        Xs = self.scaler.transform(X)
        self.anomaly.fit(Xs[y == 0])  # train anomaly on normal only
        self.clf.fit(Xs, y)
        self._is_trained = True
        logger.info("Models trained on synthetic host baselines")

    def _prepare(self, network_data: Union[List[float], np.ndarray]) -> np.ndarray:
        data = np.asarray(network_data, dtype=float).flatten()
        if data.size != self.feature_count:
            if data.size < self.feature_count:
                data = np.pad(data, (0, self.feature_count - data.size))
            else:
                data = data[: self.feature_count]
        return data

    def analyze(self, network_data: Union[List[float], np.ndarray]) -> Dict[str, Any]:
        if not self._is_trained:
            self.train_mock()

        try:
            data = self._prepare(network_data)
            scaled = self.scaler.transform(data.reshape(1, -1))

            anomaly_score = float(-self.anomaly.score_samples(scaled)[0])  # higher = more anomalous
            pred = int(self.clf.predict(scaled)[0])
            proba = float(self.clf.predict_proba(scaled)[0][1])

            # Hybrid decision
            threat = bool(pred == 1 or anomaly_score > (1.5 - self.sensitivity))
            confidence = max(proba, min(0.99, anomaly_score / 3.0))

            severity = "low"
            if confidence >= 0.85:
                severity = "critical"
            elif confidence >= 0.7:
                severity = "high"
            elif confidence >= 0.55:
                severity = "medium"

            threat_type = "BENIGN"
            if threat:
                # Heuristic classification from dominant features
                cpu, mem, sent, recv, procs, conns, disk, ent = data
                if sent > 1_000_000 or recv > 1_000_000:
                    threat_type = "TRAFFIC_ANOMALY"
                elif cpu > 80 and conns > 150:
                    threat_type = "RESOURCE_ABUSE"
                elif procs > 350:
                    threat_type = "PROCESS_SPIKE"
                else:
                    threat_type = "BEHAVIORAL_ANOMALY"

            return {
                "threat_detected": threat,
                "threat_type": threat_type,
                "confidence": float(confidence),
                "severity": severity,
                "anomaly_score": anomaly_score,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "features": {name: float(v) for name, v in zip(FEATURE_NAMES, data)},
            }
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            return {
                "threat_detected": False,
                "threat_type": "ERROR",
                "confidence": 0.0,
                "severity": "low",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
            }
