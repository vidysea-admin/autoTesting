"""AU14 (T-204, extended by T-198b): a table pinning every route policy row.

Split out of test_ui_auth_escalation.py to stay under the 300-line cap.
"""

from __future__ import annotations

from autotester.auth import policy

# -- B P3: every route policy row is pinned -----------------------------------------------

_P = "/projects/{slug}"
EXPECTED: dict[tuple[str, str], tuple[str, str | None]] = {
    **{("GET", p): ("public", None) for p in ("/auth/login", "/auth/signup", "/healthz")},
    **{("POST", p): ("public", None) for p in ("/auth/login", "/auth/signup")},
    ("POST", "/auth/logout"): ("session", None), ("GET", "/auth/waiting"): ("session", None),
    ("GET", "/favicon.ico"): ("member", None), ("GET", "/"): ("member", None),
    ("GET", "/onboard"): ("key", "project.create"), ("POST", "/onboard"): ("key", "project.create"),
    ("GET", "/inbox"): ("key", "report.view"),
    ("GET", "/live"): ("key", "live.view"), ("GET", "/auth/check"): ("key", "live.view"),
    ("GET", "/settings/server"): ("key", "settings.manage"),
    ("POST", "/settings/server"): ("key", "settings.manage"),
    **{("GET", p): ("key", "settings.manage") for p in (
        "/settings/providers", "/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc")},
    ("POST", "/settings/providers"): ("key", "settings.manage"),
    ("GET", "/admin/users"): ("key", "users.manage"),
    ("POST", "/admin/users/{user_id}/{action}"): ("key", "users.manage"),
    **{(m, p): ("key", "groups.manage") for m, p in (
        ("GET", "/admin/groups"), ("POST", "/admin/groups"), ("GET", "/admin/groups/{group_id}"),
        ("POST", "/admin/groups/{group_id}"), ("POST", "/admin/groups/{group_id}/delete"))},
    **{("GET", _P + t): ("project", "project.view") for t in (
        "", "/cases/new", "/cases", "/edit", "/flowspec", "/requests", "/sources",
        "/product-map", "/flow-diagram", "/schedule", "/crawls", "/crawls/{crawl_id}",
        "/crawls/{crawl_id}/report.xlsx", "/issues", "/issues.xlsx",
        "/issues/{issue_id}/pin", "/env", "/access", "/catalog", "/sources/drive/{job_id}",
        "/proposals")},
    **{("GET", _P + t): ("project", "report.view") for t in (
        "/runs/{run_id}", "/tracker", "/tracker/export.csv", "/tracker/export.xlsx",
        "/tracker/{bug_key}", "/test/{run_id}", "/report", "/report.xlsx", "/report.html",
        "/damage-report")},
    ("GET", _P + "/runs/{run_id}/videos/{video_path:path}"): ("project", "video.view"),
    ("GET", _P + "/frames/{source_id}/{name:path}"): ("project", "video.view"),
    **{("POST", _P + t): ("project", "project.edit") for t in (
        "/cases", "/cases/{case_id}/rename", "/cases/{case_id}/delete", "/edit", "/login-case",
        "/flowspec/approve", "/flowspec/request-edit", "/cases/generate",
        "/crawls/{crawl_id}/merge", "/issues/{issue_id}/pin", "/sources",
        "/sources/{source_id}/analyze", "/env/url", "/tracker/{bug_key}/assignee",
        "/proposals/stage", "/proposals/review")},
    **{("POST", _P + t): ("project", "video.upload") for t in ("/sources/upload","/sources/drive")},
    **{("POST", _P + t): ("project", "project.run") for t in ("/run", "/test", "/explore",
                                                                "/crawl-approval")},
    **{("POST", _P + t): ("project", "credentials.edit") for t in (
        "/secrets", "/secrets/{key}/delete", "/env", "/env/add")},
    **{("POST", _P + t): ("project", "schedule.manage") for t in (
        "/schedule", "/schedule/pause", "/schedule/resume", "/schedule/delete")},
    ("POST", _P + "/access"): ("project", "project.view"),
    # T-198b developer portal (G9): pinned independently of policy.PORTAL_POLICY.
    ("GET", "/shared"): ("key", "video.view"), ("GET", "/v/{token}"): ("key", "video.view"),
    ("POST", "/v/{token}/request-access"): ("key", "video.view"),
    ("GET", _P + "/videos/{video_id}"): ("key", "video.view"),
    ("POST", _P + "/videos/{video_id}/request-access"): ("key", "video.view"),
    ("GET", _P + "/videos/{video_id}/media"): ("video", "video.view"),
    ("GET", _P + "/videos/{video_id}/comments"): ("video", "video.view"),
    **{("POST", _P + "/videos/{video_id}" + t): ("video", "video.share") for t in (
        "/share-link", "/share-link/revoke", "/shares")},
    **{("POST", _P + "/videos/{video_id}/comments" + t): ("video", "comment.create")
       for t in ("", "/{comment_id}/edit", "/{comment_id}/delete")},
    ("POST", _P + "/videos/{video_id}/comments/{comment_id}/promote"): ("project", "project.edit"),
    ("POST", _P + "/videos/{video_id}/review"): ("video", "video.upload"),
    ("GET", "/access-requests"): ("key", "access.approve"),
    **{("POST", "/access-requests/{request_id}" + t): ("key", "access.approve")
       for t in ("/approve", "/decline")},
}


def test_au14_every_policy_row_requires_exactly_its_pinned_key() -> None:
    """A row quietly downgraded (/onboard to member, /openapi.json to member, the credentials
    group to project.view) must turn this red: the policy table is the whole defence on
    routes whose handler does not re-check."""
    actual = {row: (rule.kind, rule.key.value if rule.key else None)
              for row, rule in policy.ROUTE_POLICY.items()}
    assert actual == EXPECTED


def test_au14_a_key_route_403_names_the_missing_key_and_nothing_else(
        tmp_path, monkeypatch) -> None:
    """The shared gate names the permission key from the policy row (TS1), for key routes too."""
    from auth_harness import ADMIN, account, gate_on, login

    from autotester.auth import accounts, groups

    gate_on(tmp_path, monkeypatch)
    account(ADMIN)
    ops = groups.create_group("Viewers", ["project.view@all"])
    uid = account("viewer@team.test")
    accounts.set_user_groups(uid, [ops.id])
    resp = login("viewer@team.test").get("/live", headers={"accept": "application/json"})
    assert resp.status_code == 403
    assert "live.view" in resp.text and "viewer@team.test" not in resp.text
