"""Read-only GitHub health aggregation for the EAGLE-X command center.

The GitHub credential is read only from the server environment and is never
returned to API consumers. Public repository and workflow data still works
without a token; security alert APIs require an appropriately scoped token.
"""

from __future__ import annotations

import json
import copy
import hashlib
import os
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_REPOSITORY = "omarlaghmarti32-afk/eagle-x-v3.3"
API_ROOT = "https://api.github.com"
GITHUB_ROOT = "https://github.com"
_REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_FAILURE_CONCLUSIONS = {"failure", "timed_out", "action_required"}
_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
_CACHE_LOCK = threading.Lock()
_OVERVIEW_CACHE: Dict[Tuple[str, str], Tuple[float, Dict[str, Any]]] = {}


def _api_error_code(result: Tuple[bool, Any, Optional[int], Optional[str]]) -> Optional[str]:
    """Map provider responses to safe, stable codes; never expose raw bodies."""
    if result[0]:
        return None
    if result[3] == "rate_limited":
        return "rate_limited"
    if result[3] == "feature_disabled":
        return "feature_disabled"
    if result[2] == 401:
        return "authentication_required"
    if result[2] == 403 or result[3] == "permission_required":
        return "permission_required"
    if result[2] == 404:
        return "not_found_or_permission_required"
    if result[3] == "github_unreachable":
        return "github_unreachable"
    return "github_api_error"


def _api_error_ar(code: Optional[str]) -> str:
    return {
        "authentication_required": "رمز GitHub غير صالح أو منتهي الصلاحية.",
        "permission_required": "رمز GitHub لا يملك صلاحية القراءة المطلوبة.",
        "feature_disabled": "الميزة الأمنية غير مفعّلة في إعدادات المستودع.",
        "rate_limited": "تجاوزت الطلبات حد GitHub المؤقت؛ أعد المحاولة لاحقاً.",
        "not_found_or_permission_required": "المورد غير موجود أو لا تسمح صلاحيات GitHub بعرضه.",
        "github_unreachable": "تعذر الاتصال بـ GitHub قبل انتهاء المهلة.",
        "github_api_error": "تعذر قراءة البيانات من GitHub.",
    }.get(code or "", "تعذر قراءة البيانات من GitHub.")


class GitHubCommandCenter:
    """Fetch a bounded, read-only snapshot from the GitHub REST API."""

    def __init__(self, repository: Optional[str] = None, token: Optional[str] = None):
        self.repository = (repository or os.environ.get("EAGLE_GITHUB_REPO") or DEFAULT_REPOSITORY).strip()
        self.token = token if token is not None else os.environ.get("EAGLE_GITHUB_TOKEN", "").strip()
        if not _REPOSITORY_RE.fullmatch(self.repository):
            raise ValueError("EAGLE_GITHUB_REPO must be in owner/repository format")
        self.owner, self.name = self.repository.split("/", 1)
        try:
            timeout = float(os.environ.get("EAGLE_GITHUB_TIMEOUT", "6"))
        except ValueError:
            timeout = 6.0
        self.timeout = max(2.0, min(timeout, 15.0))

    @property
    def repository_url(self) -> str:
        return f"{GITHUB_ROOT}/{self.owner}/{self.name}"

    def _get(self, path: str) -> Tuple[bool, Any, Optional[int], Optional[str]]:
        request = urllib.request.Request(
            f"{API_ROOT}{path}",
            headers={
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "EAGLE-X-Security-Command-Center",
                **({"Authorization": f"Bearer {self.token}"} if self.token else {}),
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return True, json.loads(response.read().decode("utf-8")), response.status, None
        except urllib.error.HTTPError as exc:
            # Classify provider errors without returning their bodies or headers.
            try:
                message = json.loads(exc.read().decode("utf-8")).get("message", "").lower()
            except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
                message = ""
            if "disabled" in message:
                reason = "feature_disabled"
            elif "rate limit" in message or "secondary rate" in message:
                reason = "rate_limited"
            elif "resource not accessible" in message:
                reason = "permission_required"
            else:
                reason = "github_api_error"
            return False, None, exc.code, reason
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            return False, None, None, "github_unreachable"

    def _repo_path(self, suffix: str = "") -> str:
        quoted = urllib.parse.quote(self.repository, safe="/")
        return f"/repos/{quoted}{suffix}"

    @staticmethod
    def _rows(result: Tuple[bool, Any, Optional[int], Optional[str]], key: Optional[str] = None) -> List[Dict[str, Any]]:
        if not result[0]:
            return []
        data = result[1]
        if key:
            data = data.get(key, []) if isinstance(data, dict) else []
        return data if isinstance(data, list) else []

    def _security_availability(self, result: Tuple[bool, Any, Optional[int], Optional[str]]) -> str:
        if result[0]:
            return "available"
        if result[3] == "feature_disabled":
            return "feature_disabled"
        if result[3] == "rate_limited":
            return "rate_limited"
        if result[2] == 401 and not self.token:
            return "authentication_required"
        if result[2] in (401, 403):
            return "permission_required"
        if result[2] == 404:
            return "not_enabled_or_permission_required"
        return "unavailable"

    def _deployment_statuses(self, deployment_id: int) -> Tuple[bool, Any, Optional[int], Optional[str]]:
        return self._get(self._repo_path(f"/deployments/{deployment_id}/statuses?per_page=1"))

    def get_overview(self) -> Dict[str, Any]:
        """Return a compact snapshot and actionable Arabic priority list."""
        endpoints = {
            "repository": self._repo_path(),
            "workflows": self._repo_path("/actions/runs?per_page=20"),
            "deployments": self._repo_path("/deployments?per_page=5"),
            "dependabot": self._repo_path("/dependabot/alerts?state=open&per_page=100"),
            "code_scanning": self._repo_path("/code-scanning/alerts?state=open&per_page=100"),
        }
        with ThreadPoolExecutor(max_workers=len(endpoints)) as pool:
            futures = {name: pool.submit(self._get, path) for name, path in endpoints.items()}
            results = {name: future.result() for name, future in futures.items()}

        repo_result = results["repository"]
        checked_at = datetime.now(timezone.utc).isoformat()
        if not repo_result[0] or not isinstance(repo_result[1], dict):
            error_code = _api_error_code(repo_result)
            error_title = {
                "authentication_required": "رمز GitHub غير صالح",
                "permission_required": "صلاحية قراءة GitHub ناقصة",
                "not_found_or_permission_required": "المستودع غير موجود أو غير متاح",
                "rate_limited": "تم تجاوز حد GitHub المؤقت",
            }.get(error_code, "تعذّر الوصول إلى المستودع")
            error_action = {
                "authentication_required": "حدّث EAGLE_GITHUB_TOKEN على الخادم، ولا تضعه في المتصفح.",
                "permission_required": "امنح الرمز صلاحية قراءة بيانات المستودع ثم أعد المحاولة.",
                "not_found_or_permission_required": "تحقق من EAGLE_GITHUB_REPO ومن وصول الرمز إلى المستودع.",
                "rate_limited": "انتظر حتى يتجدد حد الطلبات ثم أعد المحاولة.",
            }.get(error_code, "تحقق من EAGLE_GITHUB_REPO واتصال الخادم بـ GitHub، ثم أعد المحاولة.")
            priorities = [{
                "priority": "high",
                "title": error_title,
                "reason": _api_error_ar(error_code),
                "action": error_action,
                "url": self.repository_url,
            }]
            return {
                "connected": False,
                "repository": {"full_name": self.repository, "url": self.repository_url},
                "checked_at": checked_at,
                "error": error_code,
                "summary": {"failed_workflows": None, "failed_deployments": None, "open_vulnerabilities": None},
                "sections": {
                    "workflows": {"status": "unknown", "runs": []},
                    "deployments": {"status": "unknown", "items": []},
                    "security": {"status": "unknown", "dependabot": "unavailable", "code_scanning": "unavailable", "alerts": []},
                },
                "priorities": priorities,
            }

        repo = repo_result[1]
        repo_link = repo.get("html_url") or self.repository_url
        workflow_error = _api_error_code(results["workflows"])
        deployment_list_error = _api_error_code(results["deployments"])
        runs = self._rows(results["workflows"], "workflow_runs")
        normalized_runs = []
        for run in runs:
            normalized_runs.append({
                "name": str(run.get("name") or "Workflow"),
                "title": str(run.get("display_title") or run.get("name") or "Workflow run"),
                "status": str(run.get("status") or "unknown"),
                "conclusion": run.get("conclusion"),
                "branch": str(run.get("head_branch") or ""),
                "event": str(run.get("event") or ""),
                "updated_at": run.get("updated_at") or run.get("created_at"),
                "url": run.get("html_url") or repo_link,
            })
        failed_runs = [r for r in normalized_runs if (r.get("conclusion") or "") in _FAILURE_CONCLUSIONS]
        active_runs = [r for r in normalized_runs if r.get("status") in ("queued", "in_progress", "waiting", "requested")]
        workflows_state = "unavailable" if workflow_error else ("failed" if failed_runs else ("running" if active_runs else ("healthy" if normalized_runs else "unknown")))

        deployment_rows = self._rows(results["deployments"])
        deployments: List[Dict[str, Any]] = []
        status_ids = []
        for item in deployment_rows[:5]:
            deployment_id = item.get("id")
            if isinstance(deployment_id, int):
                status_ids.append((deployment_id, item))
            else:
                deployments.append({
                    "environment": str(item.get("environment") or "—"),
                    "state": "unknown",
                    "created_at": item.get("created_at"),
                    "url": repo_link,
                    "ref": str(item.get("ref") or ""),
                })
        if status_ids:
            with ThreadPoolExecutor(max_workers=min(5, len(status_ids))) as pool:
                status_futures = [(item, pool.submit(self._deployment_statuses, deployment_id)) for deployment_id, item in status_ids]
                for item, future in status_futures:
                    status_result = future.result()
                    statuses = self._rows(status_result)
                    latest = statuses[0] if statuses else {}
                    status_error = _api_error_code(status_result)
                    deployments.append({
                        "environment": str(item.get("environment") or "—"),
                        "state": "unavailable" if status_error else str(latest.get("state") or "unknown"),
                        "description": _api_error_ar(status_error) if status_error else str(latest.get("description") or ""),
                        "created_at": latest.get("created_at") or item.get("created_at"),
                        "url": latest.get("target_url") or latest.get("log_url") or f"{repo_link}/deployments",
                        "ref": str(item.get("ref") or ""),
                        "error": status_error,
                    })
        deployments.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
        failed_deployments = [d for d in deployments if d.get("state") in ("failure", "error")]
        active_deployments = [d for d in deployments if d.get("state") in ("queued", "in_progress", "pending")]
        deployment_status_errors = any(d.get("error") for d in deployments)
        if deployment_list_error:
            deployments_state = "unavailable"
        elif failed_deployments:
            deployments_state = "failed"
        elif deployment_status_errors:
            deployments_state = "partial"
        elif active_deployments:
            deployments_state = "in_progress"
        elif deployments and any(d.get("state") == "success" for d in deployments):
            deployments_state = "healthy"
        else:
            deployments_state = "unknown"

        dependabot_result = results["dependabot"]
        code_result = results["code_scanning"]
        dep_availability = self._security_availability(dependabot_result)
        code_availability = self._security_availability(code_result)
        security_alerts: List[Dict[str, Any]] = []
        for alert in self._rows(dependabot_result):
            vulnerability = alert.get("security_vulnerability") or {}
            advisory = alert.get("security_advisory") or {}
            package = vulnerability.get("package") or {}
            severity = str(vulnerability.get("severity") or advisory.get("severity") or "medium").lower()
            security_alerts.append({
                "source": "Dependabot",
                "severity": severity,
                "title": str(advisory.get("summary") or f"تحديث أمني مطلوب للحزمة {package.get('name') or 'غير معروفة'}"),
                "package": str(package.get("name") or ""),
                "url": alert.get("html_url") or f"{repo_link}/security/dependabot",
            })
        for alert in self._rows(code_result):
            rule = alert.get("rule") or {}
            instance = alert.get("most_recent_instance") or {}
            location = instance.get("location") or {}
            severity = str(rule.get("security_severity_level") or rule.get("severity") or "medium").lower()
            security_alerts.append({
                "source": "Code scanning",
                "severity": severity,
                "title": str(rule.get("description") or rule.get("name") or "نتيجة فحص أمني"),
                "package": str(location.get("path") or ""),
                "url": alert.get("html_url") or f"{repo_link}/security/code-scanning",
            })
        accessible_security = dep_availability == "available" and code_availability == "available"
        security_state = "alerts" if security_alerts else ("clear" if accessible_security else "partial")

        priorities: List[Dict[str, Any]] = []
        for deployment in failed_deployments[:3]:
            priorities.append({
                "priority": "critical",
                "title": f"فشل النشر في {deployment.get('environment') or 'البيئة'}",
                "reason": deployment.get("description") or "آخر حالة نشر مسجلة هي failure/error.",
                "action": "افتح سجل النشر، أصلح الخطأ في البناء أو الإعدادات، ثم أعد النشر بعد نجاح CI.",
                "url": deployment.get("url") or repo_link,
            })
        for run in failed_runs[:3]:
            priorities.append({
                "priority": "high",
                "title": f"فشل سير العمل: {run['name']}",
                "reason": f"انتهى التشغيل على الفرع {run.get('branch') or 'غير محدد'} بنتيجة {run.get('conclusion')}.",
                "action": "افتح سجل التشغيل، ابدأ من أول خطوة فاشلة، ثم أعد تشغيل الاختبارات قبل الدمج أو النشر.",
                "url": run["url"],
            })
        if workflow_error:
            priorities.append({
                "priority": "medium",
                "title": "بيانات Actions غير مكتملة",
                "reason": _api_error_ar(workflow_error),
                "action": "تحقق من صلاحية Actions: read في EAGLE_GITHUB_TOKEN ومن وصوله إلى المستودع.",
                "url": f"{repo_link}/actions",
            })
        if deployment_list_error or deployment_status_errors:
            deployment_error = deployment_list_error or next(
                (item.get("error") for item in deployments if item.get("error")),
                "github_api_error",
            )
            priorities.append({
                "priority": "medium",
                "title": "حالة النشر غير مكتملة",
                "reason": _api_error_ar(deployment_error),
                "action": "تحقق من صلاحية Deployments: read في EAGLE_GITHUB_TOKEN ثم حدّث بيانات المركز.",
                "url": f"{repo_link}/deployments",
            })
        for alert in security_alerts:
            priorities.append({
                "priority": alert["severity"] if alert["severity"] in _SEVERITY_ORDER else "medium",
                "title": f"ثغرة {alert['severity']}: {alert['title']}",
                "reason": f"مصدر التنبيه: {alert['source']}" + (f" • {alert['package']}" if alert.get("package") else ""),
                "action": "حدّث الحزمة أو أصلح موضع الكود، ثم أعد الفحص وأغلق التنبيه بعد التحقق.",
                "url": alert["url"],
            })
        if not accessible_security:
            missing = []
            if dep_availability != "available":
                missing.append("Dependabot")
            if code_availability != "available":
                missing.append("Code scanning")
            reason = "تعذرت قراءة " + " و".join(missing) + "؛ لذلك لا يمكن تأكيد خلو المستودع من الثغرات."
            if not self.token:
                action = "أضف EAGLE_GITHUB_TOKEN على الخادم بصلاحية قراءة تنبيهات Dependabot وCode scanning، ثم أعد التحميل. لا تضع الرمز في المتصفح."
            else:
                action = "تحقق من صلاحية الرمز لقراءة تنبيهات Dependabot وCode scanning، ومن تفعيل الميزات الأمنية في إعدادات المستودع."
            priorities.append({
                "priority": "medium",
                "title": "تغطية الثغرات غير مكتملة",
                "reason": reason,
                "action": action,
                "url": f"{repo_link}/security",
            })
        if not priorities:
            priorities.append({
                "priority": "low",
                "title": "لا توجد مشكلة عاجلة ظاهرة",
                "reason": "آخر بيانات GitHub المقروءة لا تعرض تشغيلًا فاشلًا أو نشرًا فاشلًا أو تنبيهات أمنية مفتوحة.",
                "action": "استمر في مراجعة التشغيلات والتنبيهات بعد كل تغيير مهم.",
                "url": repo_link,
            })
        priorities.sort(key=lambda item: _SEVERITY_ORDER.get(item["priority"], 4))

        return {
            "connected": True,
            "repository": {
                "full_name": str(repo.get("full_name") or self.repository),
                "url": repo_link,
                "visibility": str(repo.get("visibility") or "unknown"),
                "default_branch": str(repo.get("default_branch") or "main"),
                "pushed_at": repo.get("pushed_at"),
                "updated_at": repo.get("updated_at"),
                "archived": bool(repo.get("archived")),
            },
            "checked_at": checked_at,
            "summary": {
                "failed_workflows": None if workflow_error else len(failed_runs),
                "active_workflows": len(active_runs),
                "failed_deployments": None if deployment_list_error or deployment_status_errors else len(failed_deployments),
                "open_vulnerabilities": len(security_alerts) if accessible_security else None,
            },
            "sections": {
                "workflows": {
                    "status": workflows_state,
                    "runs": normalized_runs[:8],
                    "error": workflow_error,
                },
                "deployments": {
                    "status": deployments_state,
                    "items": deployments[:5],
                    "error": deployment_list_error,
                },
                "security": {
                    "status": security_state,
                    "dependabot": dep_availability,
                    "code_scanning": code_availability,
                    "alerts": sorted(security_alerts, key=lambda item: _SEVERITY_ORDER.get(item["severity"], 4))[:20],
                },
            },
            "priorities": priorities[:12],
        }


def github_integration_enabled() -> bool:
    """GitHub is opt-in; local EAGLE-X features work without this integration."""
    return os.environ.get("EAGLE_GITHUB_ENABLED", "0").strip().lower() in {
        "1", "true", "yes", "on"
    }


def get_github_overview() -> Dict[str, Any]:
    """Convenience entry point; never contacts GitHub unless explicitly enabled."""
    if not github_integration_enabled():
        return {
            "enabled": False,
            "connected": False,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "error": "integration_disabled",
            "summary": {
                "failed_workflows": None,
                "failed_deployments": None,
                "open_vulnerabilities": None,
            },
            "sections": {
                "workflows": {"status": "unknown", "runs": []},
                "deployments": {"status": "unknown", "items": []},
                "security": {
                    "status": "unknown",
                    "dependabot": "unavailable",
                    "code_scanning": "unavailable",
                    "alerts": [],
                },
            },
            "priorities": [{
                "priority": "info",
                "title": "تكامل GitHub اختياري وغير مفعّل",
                "reason": "تعمل وظائف EAGLE-X المحلية دون إرسال طلبات إلى GitHub.",
                "action": "لتفعيل هذا التكامل اختياريًا، اضبط EAGLE_GITHUB_ENABLED=1 على الخادم.",
            }],
        }
    try:
        service = GitHubCommandCenter()
        token_fingerprint = hashlib.sha256(service.token.encode("utf-8")).hexdigest()
        cache_key = (service.repository, token_fingerprint)
        try:
            cache_ttl = max(0.0, min(float(os.environ.get("EAGLE_GITHUB_CACHE_SECONDS", "60")), 600.0))
        except ValueError:
            cache_ttl = 60.0
        if cache_ttl:
            with _CACHE_LOCK:
                cached = _OVERVIEW_CACHE.get(cache_key)
                if cached and time.monotonic() - cached[0] < cache_ttl:
                    return copy.deepcopy(cached[1])
        overview = service.get_overview()
        if cache_ttl:
            with _CACHE_LOCK:
                _OVERVIEW_CACHE[cache_key] = (time.monotonic(), overview)
        return overview
    except ValueError as exc:
        return {
            "connected": False,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "error": str(exc),
            "summary": {"failed_workflows": None, "failed_deployments": None, "open_vulnerabilities": None},
            "sections": {
                "workflows": {"status": "unknown", "runs": []},
                "deployments": {"status": "unknown", "items": []},
                "security": {"status": "unknown", "dependabot": "unavailable", "code_scanning": "unavailable", "alerts": []},
            },
            "priorities": [{
                "priority": "high",
                "title": "إعداد المستودع غير صالح",
                "reason": "يجب تحديد EAGLE_GITHUB_REPO بصيغة owner/repository.",
                "action": "صحح متغير EAGLE_GITHUB_REPO على الخادم ثم أعد المحاولة.",
                "url": f"{GITHUB_ROOT}",
            }],
        }
