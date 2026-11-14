import importlib.util
from pathlib import Path

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "build_static_site.py"
_spec = importlib.util.spec_from_file_location("eagle_static_build", SCRIPT_PATH)
_build = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_build)


def test_static_build_injects_https_api_origin_only(monkeypatch, tmp_path):
    (tmp_path / "dashboard.html").write_text(
        '<html><head><meta name="eagle-api-origin" content=""></head></html>',
        encoding="utf-8",
    )
    (tmp_path / "index.html").write_text("<html>landing</html>", encoding="utf-8")
    monkeypatch.setattr(_build, "ROOT", tmp_path)
    monkeypatch.setattr(_build, "OUTPUT", tmp_path / "dist")
    monkeypatch.setenv("API_ORIGIN", "https://api.example.com")

    _build.main()

    dashboard = (tmp_path / "dist" / "dashboard.html").read_text(encoding="utf-8")
    assert 'content="https://api.example.com"' in dashboard
    assert "GITHUB_TOKEN" not in dashboard
    assert (tmp_path / "dist" / "index.html").read_text(encoding="utf-8") == "<html>landing</html>"


def test_static_build_rejects_non_https_api_origin(monkeypatch, tmp_path):
    (tmp_path / "dashboard.html").write_text(
        '<meta name="eagle-api-origin" content="">', encoding="utf-8"
    )
    (tmp_path / "index.html").write_text("landing", encoding="utf-8")
    monkeypatch.setattr(_build, "ROOT", tmp_path)
    monkeypatch.setattr(_build, "OUTPUT", tmp_path / "dist")
    monkeypatch.setenv("API_ORIGIN", "http://api.example.com")

    with pytest.raises(SystemExit, match="public HTTPS origin"):
        _build.main()


def test_dashboard_uses_api_origin_and_escapes_external_html():
    dashboard = (SCRIPT_PATH.parents[1] / "dashboard.html").read_text(encoding="utf-8")

    assert "const apiUrl = (path) => `${API_ORIGIN}${path}`" in dashboard
    assert "apiWebSocketUrl('/ws')" in dashboard
    assert "fetch(apiUrl('/api/github/overview')" in dashboard
    assert "escapeHtml(t.type)" in dashboard
    assert "escapeHtml(t.severity || '-')" in dashboard
    assert "${t.type}" not in dashboard
