from core.health import run_health_checks
from core.pqc_manager import PQCManager
from core.ai_detector import AIThreatDetector
from core.threat_db import ThreatDB


def test_run_health_checks(tmp_path, monkeypatch):
    monkeypatch.setenv("EAGLE_DATA_DIR", str(tmp_path))
    # Re-import paths would need reload; pass components directly
    db = ThreatDB(path=tmp_path / "h.db")
    pqc = PQCManager()
    det = AIThreatDetector()
    det.train_mock()
    report = run_health_checks(
        db=db, pqc=pqc, detector=det, uptime_seconds=1, packets_scanned=0, live_monitor=False
    )
    assert report["status"] in ("ok", "degraded")
    assert "checks" in report
    assert "host" in report["checks"]
