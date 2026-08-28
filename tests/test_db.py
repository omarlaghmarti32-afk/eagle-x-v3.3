from core.threat_db import ThreatDB


def test_threat_and_blocklist(tmp_path):
    db = ThreatDB(path=tmp_path / "t.db")
    tid = db.add_threat("TEST", 0.9, severity="high", source="unit")
    assert tid >= 1
    assert db.count_threats() == 1
    threats = db.list_threats()
    assert threats[0]["threat_type"] == "TEST"

    db.add_block("1.2.3.4", "ip", reason="unit")
    assert db.is_blocked("1.2.3.4") is True
    assert db.is_blocked("9.9.9.9") is False


def test_audit(tmp_path):
    db = ThreatDB(path=tmp_path / "t.db")
    db.add_audit("unit_event", {"ok": True}, signature="abc")
