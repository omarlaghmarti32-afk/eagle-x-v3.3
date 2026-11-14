import io
import json
import urllib.error

from core.github_command_center import GitHubCommandCenter, _api_error_code


def _api_result(data, status=200):
    return True, data, status, None


def _api_error(status, reason="github_api_error"):
    return False, None, status, reason


def _service_with_responses(security=True, deployment_status_access=True, workflow_access=True):
    service = GitHubCommandCenter(repository="owner/repo", token="")

    def fake_get(path):
        if path == "/repos/owner/repo":
            return _api_result({
                "full_name": "owner/repo",
                "html_url": "https://github.com/owner/repo",
                "visibility": "public",
                "default_branch": "main",
                "pushed_at": "2026-11-10T12:00:00Z",
                "updated_at": "2026-11-10T12:00:00Z",
                "archived": False,
            })
        if path.endswith("/actions/runs?per_page=20"):
            if not workflow_access:
                return _api_error(403, "permission_required")
            return _api_result({"workflow_runs": [
                {
                    "name": "CI", "display_title": "Run tests", "status": "completed",
                    "conclusion": "failure", "head_branch": "main",
                    "html_url": "https://github.com/owner/repo/actions/runs/1",
                    "updated_at": "2026-11-10T12:00:00Z",
                },
                {
                    "name": "Docker", "display_title": "Build image", "status": "completed",
                    "conclusion": "success", "head_branch": "main",
                    "html_url": "https://github.com/owner/repo/actions/runs/2",
                    "updated_at": "2026-11-10T11:00:00Z",
                },
            ]})
        if path.endswith("/deployments?per_page=5"):
            return _api_result([{
                "id": 22, "environment": "Production",
                "created_at": "2026-11-10T12:05:00Z", "ref": "abc123",
            }])
        if path.endswith("/deployments/22/statuses?per_page=1"):
            if not deployment_status_access:
                return _api_error(403, "permission_required")
            return _api_result([{
                "state": "error", "description": "Deployment failed",
                "created_at": "2026-11-10T12:06:00Z",
                "target_url": "https://vercel.com/deployments/22",
            }])
        if path.endswith("/dependabot/alerts?state=open&per_page=100"):
            if not security:
                return _api_error(401)
            return _api_result([{
                "html_url": "https://github.com/owner/repo/security/dependabot/1",
                "security_vulnerability": {
                    "severity": "critical", "package": {"name": "example-lib"},
                },
                "security_advisory": {"summary": "Critical issue in example-lib"},
            }])
        if path.endswith("/code-scanning/alerts?state=open&per_page=100"):
            return _api_error(401) if not security else _api_result([])
        raise AssertionError(f"Unexpected GitHub API path: {path}")

    service._get = fake_get
    return service


def test_overview_prioritizes_deployment_and_vulnerability_findings():
    overview = _service_with_responses().get_overview()

    assert overview["connected"] is True
    assert overview["summary"]["failed_workflows"] == 1
    assert overview["summary"]["failed_deployments"] == 1
    assert overview["summary"]["open_vulnerabilities"] == 1
    assert overview["sections"]["security"]["status"] == "alerts"
    assert overview["priorities"][0]["priority"] == "critical"
    titles = [item["title"] for item in overview["priorities"]]
    assert any("فشل النشر" in title for title in titles)
    assert any("ثغرة critical" in title for title in titles)
    assert any("فشل سير العمل" in title for title in titles)
    assert all(item["action"] for item in overview["priorities"])


def test_unreadable_security_alerts_are_not_reported_as_zero():
    overview = _service_with_responses(security=False).get_overview()

    assert overview["summary"]["open_vulnerabilities"] is None
    assert overview["sections"]["security"]["status"] == "partial"
    assert overview["sections"]["security"]["dependabot"] == "authentication_required"
    assert any("تغطية الثغرات غير مكتملة" in item["title"] for item in overview["priorities"])
    assert any("لا تضع الرمز في المتصفح" in item["action"] for item in overview["priorities"])


def test_unreadable_deployment_status_is_partial_not_success_or_zero():
    overview = _service_with_responses(deployment_status_access=False).get_overview()

    assert overview["summary"]["failed_deployments"] is None
    assert overview["sections"]["deployments"]["status"] == "partial"
    assert overview["sections"]["deployments"]["items"][0]["state"] == "unavailable"
    assert any("حالة النشر غير مكتملة" in item["title"] for item in overview["priorities"])


def test_unreadable_workflows_are_not_reported_as_zero():
    overview = _service_with_responses(workflow_access=False).get_overview()

    assert overview["summary"]["failed_workflows"] is None
    assert overview["sections"]["workflows"]["status"] == "unavailable"
    assert overview["sections"]["workflows"]["error"] == "permission_required"
    assert any("بيانات Actions غير مكتملة" in item["title"] for item in overview["priorities"])


def test_invalid_repository_setting_is_rejected(monkeypatch):
    monkeypatch.setenv("EAGLE_GITHUB_REPO", "https://evil.example/owner/repo")

    try:
        GitHubCommandCenter(token="")
        assert False, "invalid repository must be rejected"
    except ValueError as exc:
        assert "owner/repository" in str(exc)


def test_github_disabled_security_feature_is_classified_without_exposing_body(monkeypatch):
    def disabled_alerts(*args, **kwargs):
        raise urllib.error.HTTPError(
            "https://api.github.com/repos/owner/repo/dependabot/alerts",
            403,
            "Forbidden",
            {},
            io.BytesIO(json.dumps({"message": "Dependabot alerts are disabled for this repository."}).encode()),
        )

    monkeypatch.setattr("urllib.request.urlopen", disabled_alerts)
    service = GitHubCommandCenter(repository="owner/repo", token="")
    result = service._get("/repos/owner/repo/dependabot/alerts?state=open")

    assert result[0] is False
    assert result[2] == 403
    assert result[3] == "feature_disabled"
    assert "disabled for this repository" not in str(result)


def test_http_error_codes_are_classified_safely():
    assert _api_error_code(_api_error(401)) == "authentication_required"
    assert _api_error_code(_api_error(403, "permission_required")) == "permission_required"
    assert _api_error_code(_api_error(403, "rate_limited")) == "rate_limited"
