"""The central route policy (AU14, AU16, TF4): the rule table, its matcher, the unit merge.

`ROUTE_POLICY` is the table T-204's login gate walks: a request is matched against its
templates by method and path, and a route not in it matches nothing and is refused (default
deny), so a route added later without a row is unreachable until someone declares what it
needs. `merge_route_policies` (T-205/TF4) folds units' own `"<METHOD> <path>"` dicts into one
table and fails loudly on a duplicate route, an invented permission key (R63) or a `public`
outside AU16's closed set; it is not yet wired to the table above, which T-204 owns.
"""

from __future__ import annotations

import re
from collections.abc import Collection, Mapping

from autotester.schema.auth import PermissionKey as K
from autotester.schema.auth import RouteRule

PUBLIC_RULE = RouteRule(kind="public")
SESSION = RouteRule(kind="session")
MEMBER = RouteRule(kind="member")


def _key(key: K) -> RouteRule:
    return RouteRule(kind="key", key=key)


def _project(key: K) -> RouteRule:
    return RouteRule(kind="project", key=key)


def _video(key: K) -> RouteRule:
    return RouteRule(kind="video", key=key)


_P = "/projects/{slug}"
_VIEW, _EDIT, _RUN = _project(K.PROJECT_VIEW), _project(K.PROJECT_EDIT), _project(K.PROJECT_RUN)
_REPORT, _VIDEO = _project(K.REPORT_VIEW), _project(K.VIDEO_VIEW)
_CRED = _project(K.CREDENTIALS_EDIT)
_SETTINGS, _USERS, _GROUPS = (_key(K.SETTINGS_MANAGE), _key(K.USERS_MANAGE),
                              _key(K.GROUPS_MANAGE))

_V = _P + "/videos/{video_id}"
PORTAL_POLICY: dict[tuple[str, str], RouteRule] = {
    # T-198b (team-intake.md TP1-TP6). The page and the request-access POST answer a person with
    # no access with the request-access page (handler); every byte/data route is a `video` rule.
    ("GET", "/shared"): _key(K.VIDEO_VIEW),
    ("GET", _V): _key(K.VIDEO_VIEW), ("POST", _V + "/request-access"): _key(K.VIDEO_VIEW),
    ("GET", "/v/{token}"): _key(K.VIDEO_VIEW),
    ("POST", "/v/{token}/request-access"): _key(K.VIDEO_VIEW),
    ("GET", _V + "/media"): _video(K.VIDEO_VIEW), ("GET", _V + "/comments"): _video(K.VIDEO_VIEW),
    **{("POST", _V + tail): _video(K.VIDEO_SHARE) for tail in (
        "/share-link", "/share-link/revoke", "/shares")},
    **{("POST", _V + tail): _video(K.COMMENT_CREATE) for tail in (
        "/comments", "/comments/{comment_id}/edit", "/comments/{comment_id}/delete")},
    ("POST", _V + "/comments/{comment_id}/promote"): _project(K.PROJECT_EDIT),
    ("GET", "/access-requests"): _key(K.ACCESS_APPROVE),
    **{("POST", "/access-requests/{request_id}/" + tail): _key(K.ACCESS_APPROVE)
       for tail in ("approve", "decline")},
}

ROUTE_POLICY: dict[tuple[str, str], RouteRule] = {
    # AU16: the closed public set
    ("GET", "/auth/login"): PUBLIC_RULE, ("POST", "/auth/login"): PUBLIC_RULE,
    ("GET", "/auth/signup"): PUBLIC_RULE, ("POST", "/auth/signup"): PUBLIC_RULE,
    ("GET", "/healthz"): PUBLIC_RULE,
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
        "/issues/{issue_id}/pin", "/env", "/access", "/catalog", "/sources/drive/{job_id}")},
    **{("GET", _P + tail): _REPORT for tail in (
        "/runs/{run_id}", "/report", "/report.xlsx", "/report.html", "/damage-report",
        "/test/{run_id}")},
    ("GET", _P + "/runs/{run_id}/videos/{video_path:path}"): _VIDEO,
    ("GET", _P + "/frames/{source_id}/{name:path}"): _VIDEO,
    **{("POST", _P + tail): _EDIT for tail in (
        "/cases", "/cases/{case_id}/rename", "/cases/{case_id}/delete", "/edit",
        "/login-case", "/flowspec/approve", "/flowspec/request-edit", "/cases/generate",
        "/crawls/{crawl_id}/merge", "/issues/{issue_id}/pin", "/sources",
        "/sources/{source_id}/analyze", "/env/url")},
    **{("POST", _P + tail): _project(K.VIDEO_UPLOAD) for tail in (
        "/sources/upload", "/sources/drive")},   # T-198: file and Drive-link intake
    **{("POST", _P + tail): _RUN for tail in ("/run", "/explore", "/crawl-approval", "/test")},
    **{("POST", _P + tail): _CRED for tail in (
        "/secrets", "/secrets/{key}/delete", "/env", "/env/add")},
    # the handler checks project.assign or video.share for the relation asked (AU12)
    ("POST", _P + "/access"): _VIEW,
    **PORTAL_POLICY,
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


def route_for(method: str, path: str) -> tuple[str, RouteRule, dict[str, str]] | None:
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


# --- TF4: merge each unit's own policy dict (T-205) ---

PUBLIC = "public"  # a unit-policy grant (T-205); `ROUTE_POLICY` above uses `PUBLIC_RULE`
RoutePolicy = Mapping[str, "str | tuple[str, str]"]


class PolicyError(ValueError):
    """The unit policies cannot be merged; the message names the unit and the route."""


def _check_entry(unit: str, route: str, grant: str | tuple[str, str], *,
                 catalogue: Collection[str], public_routes: Collection[str],
                 routes: Collection[str] | None) -> None:
    if routes is not None and route not in routes:
        raise PolicyError(f"{unit}: policy names a route that does not exist: {route!r}")
    if grant == PUBLIC:
        if route not in public_routes:
            raise PolicyError(f"{unit}: {route!r} is marked public but is not in the closed "
                              "public set (auth.md AU16)")
        return
    if not isinstance(grant, tuple) or len(grant) != 2:
        raise PolicyError(f"{unit}: {route!r} must be 'public' or (permission key, resolver)")
    if grant[0] not in catalogue:
        raise PolicyError(f"{unit}: {route!r} uses permission key {grant[0]!r}, which is not "
                          "in the closed catalogue (R63: a unit cannot invent a key)")


def merge_route_policies(
    units: Mapping[str, RoutePolicy], *, catalogue: Collection[str],
    public_routes: Collection[str], routes: Collection[str] | None = None,
) -> dict[str, str | tuple[str, str]]:
    """The central table: every unit's routes, deterministically (units in name order).

    `routes` is the set of `"<METHOD> <path>"` the app really serves; when given, a policy
    row for a route outside it is an error. Raises `PolicyError`; never last-wins."""
    table: dict[str, str | tuple[str, str]] = {}
    owner: dict[str, str] = {}
    for unit in sorted(units):
        for route, grant in units[unit].items():
            if route in table:
                raise PolicyError(f"duplicate route {route!r}: claimed by {owner[route]} "
                                  f"and {unit}")
            _check_entry(unit, route, grant, catalogue=catalogue, public_routes=public_routes,
                         routes=routes)
            table[route], owner[route] = grant, unit
    return table
