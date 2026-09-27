"""App-wide `HTTPException` -> HTML page, split out of `ui/app.py` to keep that
module under the 300-line design cap. Contract: qa/contracts/ui.md U5.

AT-596: `app.py` registered no exception handler, so every `HTTPException`
raised anywhere under it (400s, 404s, T-184's pinned-case 409) fell through
FastAPI's default handler as a raw `{"detail": ...}` JSON body -- Chrome
renders that as its own built-in JSON viewer: no styling, no nav, no link
back. A browser-driving request (`Accept: text/html`, what every real browser
sends) now gets a page in this app's own visual language instead; a
JSON/API caller -- every existing test that never sets `Accept` gets `*/*`
from httpx, and every fetch that asks for `application/json` -- keeps the
exact JSON body FastAPI already produced, via FastAPI's own default handler,
so no status code, header or JSON shape changes for that caller.

Registered on `starlette.exceptions.HTTPException` (FastAPI's own base class),
not `fastapi.HTTPException` -- Starlette's exception middleware looks a
handler up by walking `type(exc).__mro__`, so registering on the base class
still matches every route's `fastapi.HTTPException` (a subclass) AND
Starlette's own unmatched-route 404 (which is a bare
`starlette.exceptions.HTTPException`, never a `fastapi.HTTPException`, so the
narrower registration this unit shipped at first never saw it) -- a checker
pre-check caught this before Fix cycle 1 closed.
"""

from __future__ import annotations

from collections.abc import Mapping
from html import escape
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler as _default_json_handler
from fastapi.responses import HTMLResponse, Response
from fastapi.utils import is_body_allowed_for_status_code
from starlette.exceptions import HTTPException

from autotester.browser.secrets import SecretStore
from autotester.core.paths import ProjectPaths
from autotester.core.redact import Redactor
from autotester.schema.project import Project
from autotester.ui import theme

_NO_PROJECT_SCOPE = Project(slug="error-pages", name="error-pages", base_url="")
"""Not a real onboarded product -- a pure data carrier so `SecretStore.load`
(browser/secrets.py:117) has SOMETHING to construct with. `load` reads only
`project.secrets` off it (empty here, so every `.env` value lands in the
undeclared "shadow" bucket rather than "declared") and `.redactor()`
(browser/secrets.py:223) remerges declared and undeclared values into one
mask list regardless (AT-004) -- so the `Redactor` this produces is byte-for-
byte identical to any real project's. An app-wide error page has no single
project in scope, and building one is cheaper and more honest than a second,
divergent .env-reading code path (a checker pre-check caught the first
version of this file doing exactly that, via a hand-rolled `parse_env` call)."""


def _repo_redactor() -> Redactor:
    """THE loader every route already calls -- `SecretStore.load`
    (browser/secrets.py:117), against the same repo-root `.env`
    `ProjectPaths(<any slug>).env_file` always resolves to ("one credential
    file for the whole repo," core/paths.py:45) -- then `.redactor()`
    (browser/secrets.py:223), the same method every consumer in this codebase
    calls (`ui/credential_guard.py`, `browser/evidence.py`,
    `stages/orchestrate.py`) to get a `Redactor` out of a `SecretStore`.
    `strict=False` matches every one of those call sites: none of them raises
    `MissingSecret` just because a declared key has no value, and this app
    declares none at all."""
    env_path = ProjectPaths(_NO_PROJECT_SCOPE.slug).env_file
    return SecretStore.load(_NO_PROJECT_SCOPE, env_path, strict=False).redactor()


def _wants_html(request: Request) -> bool:
    """Every real browser sends `Accept: text/html,...`; a JSON/API client
    that asks for `application/json`, or sends no `Accept` at all (httpx's
    `*/*` default -- every pre-existing test), does not."""
    return "text/html" in request.headers.get("accept", "")


def _status_title(status_code: int) -> str:
    try:
        return f"{status_code} {HTTPStatus(status_code).phrase}"
    except ValueError:
        return str(status_code)


def _error_page(
    status_code: int, detail: str, headers: Mapping[str, str] | None = None
) -> HTMLResponse:
    """The themed page. `detail` is redacted before it is escaped -- redact
    first, since scrubbing an already-escaped string would need to match
    against escaped secret values instead of the real ones.

    AT-605: `headers` carries whatever the raised `HTTPException` set --
    a 405's `Allow` (RFC 9110 SS15.5.6 says a 405 response MUST generate one),
    a 401's `WWW-Authenticate`, or nothing (`None`, the common case) -- and is
    passed straight to `HTMLResponse` the same way FastAPI's own default JSON
    handler already forwards it, so the HTML branch drops nothing a JSON
    caller still gets."""
    title = _status_title(status_code)
    safe_detail = escape(_repo_redactor().scrub(detail))
    body = theme.card(
        f"<p>{safe_detail}</p>"
        "<p style='margin-top:14px'><a class='btn' href='/'>&larr; Back to projects</a></p>",
        title=title,
    )
    return HTMLResponse(theme.page(title, body), status_code=status_code, headers=headers)


async def http_exception_handler(request: Request, exc: HTTPException) -> Response:
    """Registered for every route in `app.py`'s routers (`FastAPI.
    add_exception_handler` applies globally, not per-router) AND for a URL
    matching no route at all -- Starlette raises its own bare `HTTPException`
    for that case, which this signature's `starlette.exceptions.HTTPException`
    type also covers."""
    if not _wants_html(request):
        return await _default_json_handler(request, exc)
    if not is_body_allowed_for_status_code(exc.status_code):
        return Response(status_code=exc.status_code, headers=exc.headers)
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return _error_page(exc.status_code, detail, exc.headers)


def register_exception_handler(app: FastAPI) -> None:
    app.add_exception_handler(HTTPException, http_exception_handler)
