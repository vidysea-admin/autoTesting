"""The central route policy table (AU14, AU16): every route's required permission.

A request is matched against these templates by method and path. A route that is not
in the table matches nothing and is refused (default deny), so a route added later
without a row here is unreachable until someone declares what it needs.
"""

from __future__ import annotations

import re

from autotester.schema.auth import PermissionKey as K
from autotester.schema.auth import RouteRule

PUBLIC = RouteRule(kind="public")
SESSION = RouteRule(kind="session")
MEMBER = RouteRule(kind="member")


def _key(key: K) -> RouteRule:
    return RouteRule(kind="key", key=key)


def _project(key: K) -> RouteRule:
    return RouteRule(kind="project", key=key)


_P = "/projects/{slug}"
_VIEW, _EDIT, _RUN = _project(K.PROJECT_VIEW), _project(K.PROJECT_EDIT), _project(K.PROJECT_RUN)
_REPORT, _VIDEO = _project(K.REPORT_VIEW), _project(K.VIDEO_VIEW)
_CRED = _project(K.CREDENTIALS_EDIT)
_SETTINGS, _USERS, _GROUPS = (_key(K.SETTINGS_MANAGE), _key(K.USERS_MANAGE),
                              _key(K.GROUPS_MANAGE))

ROUTE_POLICY: dict[tuple[str, str], RouteRule] = {
    # AU16: the closed public set
    ("GET", "/auth/login"): PUBLIC, ("POST", "/auth/login"): PUBLIC,
    ("GET", "/auth/signup"): PUBLIC, ("POST", "/auth/signup"): PUBLIC,
    ("GET", "/healthz"): PUBLIC,
    # signed in, even with zero permissions (AU6)
    ("POST", "/auth/logout"): SESSION, ("GET", "/auth/waiting"): SESSION,
    ("GET", "/favicon.ico"): MEMBER,
    ("GET", "/"): MEMBER,
    ("GET", "/onboard"): _key(K.PROJECT_CREATE), ("POST", "/onboard"): _key(K.PROJECT_CREATE),
    ("GET", "/live"): _key(K.LIVE_VIEW),
    ("GET", "/settings/providers"): _SETTINGS, ("POST", "/settings/providers"): _SETTINGS,
    ("GET", "/openapi.json"): _SETTINGS, ("GET", "/docs"): _SETTINGS,
    ("GET", "/docs/oauth2-redirect"): _SETTINGS, ("GET", "/redoc"): _SETTINGS,
    ("GET", "/admin/users"): _USERS,
    ("POST", "/admin/users/{user_id}/{action}"): _USERS,
    ("GET", "/admin/groups"): _GROUPS, ("POST", "/admin/groups"): _GROUPS,
    ("GET", "/admin/groups/{group_id}"): _GROUPS, ("POST", "/admin/groups/{group_id}"): _GROUPS,
    ("POST", "/admin/groups/{group_id}/delete"): _GROUPS,
    # one project: unviewable -> 404, viewable without the key -> 403 (AU13)
    **{("GET", _P + tail): _VIEW for tail in (
        "", "/cases/new", "/cases", "/edit", "/flowspec", "/requests", "/sources",
        "/product-map", "/flow-diagram", "/crawls", "/crawls/{crawl_id}",
        "/crawls/{crawl_id}/report.xlsx", "/issues", "/issues.xlsx",
        "/issues/{issue_id}/pin", "/env", "/access", "/catalog")},
    **{("GET", _P + tail): _REPORT for tail in (
        "/runs/{run_id}", "/report", "/report.xlsx", "/report.html")},
    ("GET", _P + "/runs/{run_id}/videos/{video_path:path}"): _VIDEO,
    ("GET", _P + "/frames/{source_id}/{name:path}"): _VIDEO,
    **{("POST", _P + tail): _EDIT for tail in (
        "/cases", "/cases/{case_id}/rename", "/cases/{case_id}/delete", "/edit",
        "/login-case", "/flowspec/approve", "/flowspec/request-edit", "/cases/generate",
        "/crawls/{crawl_id}/merge", "/issues/{issue_id}/pin", "/sources",
        "/sources/{source_id}/analyze", "/env/url")},
    ("POST", _P + "/sources/upload"): _project(K.VIDEO_UPLOAD),
    **{("POST", _P + tail): _RUN for tail in ("/run", "/explore", "/crawl-approval")},
    **{("POST", _P + tail): _CRED for tail in (
        "/secrets", "/secrets/{key}/delete", "/env", "/env/add")},
    # the handler checks project.assign or video.share for the relation asked (AU12)
    ("POST", _P + "/access"): _VIEW,
}


def _compile(template: str) -> re.Pattern[str]:
    parts = re.split(r"(\{[^}]+\})", template)
    out = []
    for part in parts:
        if part.startswith("{"):
            name, _, conv = part[1:-1].partition(":")
            out.append(f"(?P<{name}>.+)" if conv == "path" else f"(?P<{name}>[^/]+)")
        else:
            out.append(re.escape(part))
    return re.compile("^" + "".join(out) + "$")


_COMPILED = [(method, template, _compile(template), rule)
             for (method, template), rule in ROUTE_POLICY.items()]


def match(method: str, path: str) -> tuple[str, RouteRule, dict[str, str]] | None:
    """(template, rule, path params) for a request, or None (default deny). HEAD is a
    GET; when several templates match, the one with the most literal text wins."""
    verb = "GET" if method == "HEAD" else method
    best: tuple[int, str, RouteRule, dict[str, str]] | None = None
    for m, template, pattern, rule in _COMPILED:
        if m != verb:
            continue
        found = pattern.match(path)
        if found:
            weight = len(re.sub(r"\{[^}]+\}", "", template))
            if best is None or weight > best[0]:
                best = (weight, template, rule, found.groupdict())
    return None if best is None else (best[1], best[2], best[3])
