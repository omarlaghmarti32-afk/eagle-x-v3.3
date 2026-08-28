from core.pqc_manager import PQCManager
from core.pqc_real import RealPQC


def test_pqc_manager_always_works():
    m = PQCManager()
    status = m.get_status()
    assert status["status"] == "Active"
    assert "mode" in status
    token = m.encrypt("hello")
    assert m.decrypt(token) == "hello"


def test_real_pqc_status():
    p = RealPQC()
    s = p.status()
    assert "available" in s
    # If available, kem demo should work
    if p.available:
        r = p.encapsulate()
        assert r is not None
        assert len(r.shared_secret) > 0
