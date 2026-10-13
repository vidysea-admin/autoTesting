"""The login gate (T-204, auth.md AU6/AU13/AU14/AU16/AU22): one ASGI middleware that
resolves the session, applies the central route policy and audits state changes.

Registered after the D-066 Origin guard, so the guard runs first (AU18). Unsigned-in
requests get 302 to the login page (browser) or 401 JSON; a signed-in account with no
permissions gets the "waiting for an admin" 403; a project the user may not view gets
the same 404 as a missing project; a route with no policy row is refused.
"""

from __future__ import annotations

from urllib.parse import quote

from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Match

from autotester.auth import audit, policy
from autotester.auth.access import authorize, resource_for
from autotester.auth.config import auth_disabled, cookie_secure
from autotester.auth.context import CURRENT_PRINCIPAL
from autotester.auth.sessions import resolve_session
from autotester.schema.auth import PermissionKey, Principal, RouteRule, all_permissions
from autotester.stages.video_access import video_resource
from autotester.ui import auth_view, error_pages

SESSION_COOKIES = ("__Host-at_session", "at_session")
_UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}
ANONYMOUS = Principal()


def session_token(request: Request) -> str | None:
    """The session cookie value. Where login sets the Secure `__Host-` cookie (AU3), only
    that name is read: accepting the plain name too would let a sibling subdomain or a
    plain-HTTP response plant a session (cookie tossing), which is what the prefix stops."""
    names = SESSION_COOKIES[:1] if cookie_secure(request.url.scheme) else SESSION_COOKIES
    for name in names:
        if request.cookies.get(name):
            return request.cookies[name]
    return None


MAX_NEXT_LENGTH = 2048


def safe_next(value: str | None) -> str:
    """A same-site relative path of at most MAX_NEXT_LENGTH characters, or "/" (AU16: no
    absolute URL, `//host`, scheme; a 100 KB value must not come back in a header)."""
    if (not value or not value.startswith("/") or value.startswith("//") or "\\" in value
            or len(value) > MAX_NEXT_LENGTH or any(ord(c) < 32 for c in value)):
        return "/"
    return value


def _principal(request: Request) -> Principal | None:
    if auth_disabled():
        return Principal(user_id=0, email="local", permissions=frozenset(all_permissions()))
    return resolve_session(session_token(request))


def _wants_html(request: Request) -> bool:
    return "text/html" in request.headers.get("accept", "")


async def _error(request: Request, status: int, detail: str) -> Response:
    return await error_pages.http_exception_handler(request, HTTPException(status, detail))


def _has_handler(scope) -> bool:
    """Would the app run a handler for this method + path? (Not 404 / 405.)"""
    app = scope.get("app")
    routes = getattr(getattr(app, "router", None), "routes", ())
    return any(route.matches(scope)[0] is Match.FULL for route in routes)


async def _video_refusal(request: Request, key: PermissionKey, params: dict[str, str],
                         who: Principal) -> Response | None:
    """T-198b: a `video` rule. A video that does not exist and one the account may not view
    answer the same 404 (AU13, TP1); viewable but without `key` is 403."""
    resource = video_resource(params.get("slug", ""), params.get("video_id", ""))
    if resource is None or not authorize(who, PermissionKey.VIDEO_VIEW, resource):
        return await _error(request, 404, "no such video")
    if not authorize(who, key, resource):
        return await _error(request, 403, "you do not have permission for this action")
    return None


async def _refusal(request: Request, rule: RouteRule | None, params: dict[str, str],
                   who: Principal | None) -> Response | None:
    """The response that refuses this request, or None when it may proceed."""
    if rule is not None and rule.kind == "public":
        return None
    if who is None:
        if _wants_html(request):
            return RedirectResponse("/auth/login?next=" + quote(safe_next(request.url.path)),
                                    status_code=302)
        return JSONResponse({"detail": "authentication required"}, status_code=401)
    if rule is None:  # AU14 default deny -- but a path with no handler keeps its 404/405
        if not _has_handler(request.scope):
            return None
        return await _error(request, 403, "this page is not available to your account")
    if rule.kind == "session":
        return None
    if not who.permissions:
        if _wants_html(request):
            return HTMLResponse(auth_view.waiting_page(who.email), status_code=403)
        return JSONResponse({"detail": "your account is waiting for an administrator"},
                            status_code=403)
    if rule.kind == "member":
        return None
    assert rule.key is not None
    if rule.kind == "key":
        ok = authorize(who, rule.key)
        return None if ok else await _error(request, 403, "you do not have permission")
    if rule.kind == "video":
        return await _video_refusal(request, rule.key, params, who)
    slug = params.get("slug", "")
    resource = resource_for(slug)
    if not authorize(who, PermissionKey.PROJECT_VIEW, resource):
        return await _error(request, 404, f"no project '{slug}'")  # same as a missing one
    if not authorize(who, rule.key, resource):
        return await _error(request, 403, "you do not have permission for this action "
                                          f"({rule.key.value})")   # names the key (TT1)
    return None


class _AuthGate:
    """ASGI middleware; see the module docstring."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request = Request(scope)
        found = policy.route_for(scope["method"], scope["path"])
        template, rule, params = found if found else (None, None, {})
        who = _principal(request)  # no cookie -> None without opening the store
        token = CURRENT_PRINCIPAL.set(who or ANONYMOUS)
        status: list[int] = []

        async def _send(message) -> None:
            if message["type"] == "http.response.start":
                status.append(message["status"])
                if who is not None:  # P8: a signed-in page is never cached (Back after sign-out)
                    headers = [h for h in message.get("headers", [])
                               if h[0].lower() != b"cache-control"]
                    message = {**message, "headers": [*headers, (b"cache-control", b"no-store")]}
            await send(message)

        try:
            refusal = await _refusal(request, rule, params, who)
            if refusal is not None:
                await refusal(scope, receive, _send)
            else:
                await self.app(scope, receive, _send)
        finally:
            CURRENT_PRINCIPAL.reset(token)
            if who is not None and scope["method"] in _UNSAFE:
                audit.record_request(who.email, scope["method"], template or "<unmatched>",
                                     status[0] if status else 500)


def auth_middleware() -> list[Middleware]:
    """For `FastAPI(middleware=...)`, AFTER `origin_guard_middleware()` (AU18)."""
    return [Middleware(_AuthGate)]
