from core.ai_detector import AIThreatDetector


def test_train_and_analyze_normal():
    det = AIThreatDetector(sensitivity=0.9)
    det.train_mock()
    # low resource vector should often be benign
    result = det.analyze([10, 40, 1000, 2000, 150, 20, 50, 0.05])
    assert "threat_detected" in result
    assert "confidence" in result
    assert "timestamp" in result


def test_analyze_high_anomaly():
    det = AIThreatDetector(sensitivity=0.5)
    det.train_mock()
    result = det.analyze([95, 95, 5_000_000, 5_000_000, 500, 400, 90, 0.95])
    assert result["threat_detected"] is True
    assert result["confidence"] > 0.5


def test_feature_padding():
    det = AIThreatDetector()
    det.train_mock()
    result = det.analyze([1.0, 2.0])  # short vector
    assert "error" not in result or result.get("threat_detected") is not None
