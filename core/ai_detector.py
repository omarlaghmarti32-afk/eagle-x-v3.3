import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from datetime import datetime
from typing import Dict, List, Union
import logging

logger = logging.getLogger("EAGLE-X")

class AIThreatDetector:
    """AI-powered Threat Detection System (RandomForest baseline)"""
    def __init__(self):
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        self._is_trained = False
        self.feature_count = 4
        logger.info("AI Threat Detector initialized (RandomForest + StandardScaler)")

    def train_mock(self):
        # Generate synthetic data for "Normal" vs "Threat"
        # Features: [packet_size, frequency, protocol_id, entropy]
        X = np.random.rand(1000, self.feature_count)
        y = (X[:, 0] + X[:, 3] > 1.2).astype(int)  # Simple threshold for "threat"
        self.scaler.fit(X)
        self.model.fit(self.scaler.transform(X), y)
        self._is_trained = True
        logger.info("AI Model trained on synthetic security datasets")

    def analyze(self, network_data: Union[List[float], np.ndarray]) -> Dict:
        if not self._is_trained:
            self.train_mock()

        try:
            data = np.asarray(network_data, dtype=float).flatten()
            if data.size != self.feature_count:
                logger.warning(
                    f"Invalid feature count: expected {self.feature_count}, got {data.size}. Using fallback."
                )
                # Pad or truncate safely
                if data.size < self.feature_count:
                    data = np.pad(data, (0, self.feature_count - data.size))
                else:
                    data = data[: self.feature_count]

            scaled_data = self.scaler.transform(data.reshape(1, -1))
            prediction = int(self.model.predict(scaled_data)[0])
            proba = self.model.predict_proba(scaled_data)[0]
            confidence = float(proba[prediction])

            return {
                "threat_detected": bool(prediction == 1),
                "confidence": confidence,
                "timestamp": datetime.now().isoformat(),
                "features_used": data.tolist(),
            }
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            return {
                "threat_detected": False,
                "confidence": 0.0,
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
            }
