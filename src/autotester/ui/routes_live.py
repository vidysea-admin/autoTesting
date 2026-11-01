"""Presentation-only noVNC page for watching the container's real browser, the auth-gated
same-origin relay to the container's websockify (`/novnc/*`, `/novnc-view/*`; AT-1419), plus
a process-freshness probe (`/healthz`, AT-085)."""

from __future__ import annotations

import asyncio
import contextlib
import os
import re
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from urllib.parse import quote, urlparse

import httpx
from fastapi import APIRouter, Request, WebSocket
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
from starlette.requests import HTTPConnection
from websockets.asyncio.client import connect as ws_connect

import autotester
from autotester.auth.access import authorize
from autotester.auth.context import current_principal
from autotester.core.env import on_cloud_run
from autotester.schema.auth import PermissionKey
from autotester.store.filestore import validate_store_env
from autotester.store.mongo_routes import store_selection
from autotester.ui import theme
from autotester.ui.auth_middleware import _principal
from autotester.ui.helpers import _host_allowed
from autotester.ui.routes_auth import live_access_refusal

router = APIRouter()

# AT-085: uvicorn runs without `--reload` (docker/entrypoint.sh), so an edit made after import
# is silently NOT served. Frozen once at import: the same "process start" a checker read off
# `ps -o lstart=`.
_PROCESS_STARTED_AT = datetime.now(UTC)


def package_root() -> Path:
    """The installed `autotester` package. Not `repo_root()`: on a server `AUTOTESTER_ROOT`
    points at the data volume (projects/, profiles/, .env), which holds no source."""
    return Path(autotester.__file__).resolve().parent


_SRC_ROOT = package_root()
NOVNC_ENV = "AUTOTESTER_NOVNC_URL"
_DEFAULT_NOVNC = "http://localhost:6080/vnc.html?autoconnect=true&resize=scale"
_CLOUD_RUN_NOVNC = "/novnc/vnc.html?autoconnect=true&resize=scale&path=novnc/websockify"


def novnc_url() -> str:
    """Where the viewer iframe points: the local published port, or `AUTOTESTER_NOVNC_URL` (a
    same-origin path, since an http iframe in an https page is blocked); on Cloud Run
    (`K_SERVICE`, no Caddy) the app's own relay path (E6.6). Only an absolute path or an
    http(s) localhost URL is accepted: anything else falls back to the default."""
    raw = os.environ.get(NOVNC_ENV, "").strip()
    same_origin = raw.startswith("/") and not raw.startswith("//")
    local = raw.startswith(("http://localhost:", "http://127.0.0.1:"))
    hostile = {"'", '"', "<", ">", " "} & set(raw)
    default = _CLOUD_RUN_NOVNC if on_cloud_run() else _DEFAULT_NOVNC
    return raw if (same_origin or local) and not hostile else default


def view_only_url(url: str) -> str:
    """The viewer pointed at the VIEW-ONLY endpoint (`/novnc/` -> `/novnc-view/`, incl. the
    websocket `path=`; `:6080` -> `:6081`): a `-viewonly` VNC server drops input (HO12)."""
    for host in ("localhost", "127.0.0.1"):
        url = url.replace(f"{host}:6080", f"{host}:6081")
    if url.startswith("/novnc/"):
        url = "/novnc-view/" + url[len("/novnc/"):]
    return url.replace("path=novnc/", "path=novnc-view/")


def viewer_url(can_control: bool) -> str:
    """The iframe target; without `live.control` the view-only endpoint (HO12) plus a UI hint."""
    url = novnc_url()
    if can_control:
        return url
    url = view_only_url(url)
    return url + ("&" if "?" in url else "?") + "view_only=1"


@router.get("/live", response_class=HTMLResponse)
def live_view() -> str:
    who = current_principal()
    can_control = who is not None and authorize(who, PermissionKey.LIVE_CONTROL)
    body = (
        theme.breadcrumb(("Projects", "/"), ("Live view", None))
        + "<h1>Live view</h1>"
        "<p class='subtitle'>Watch the real browser as a run happens.</p>"
        "<div class='live-tip'><strong>A black screen below is normal.</strong> It is the "
        "container's real display, empty whenever no run is in progress. Open a project and "
        "press <em>▶ Run tests</em> with this page open in a second tab.</div>"
        + ("" if can_control else
           "<div class='live-tip live-tip-muted'>View only: sending input needs the "
           "<code>live.control</code> permission.</div>")
        + "<div class='live-tip live-tip-muted'>To slow a run down, set "
        "<code>AUTOTESTER_SLOW_MO_MS=1500</code> before "
        "<code>docker compose up -d</code>.</div>"
        f"<div class='live-shell'><iframe src='{escape(viewer_url(can_control))}'></iframe></div>"
    )
    return theme.page("Live view", body)


# AT-1419 / E6: the in-app noVNC relay (Cloud Run has no Caddy; docker/Caddyfile is the model).
# VNC_UPSTREAMS is the ONLY place an upstream is named: no request value or env var (E6.8).
VNC_UPSTREAMS: dict[str, tuple[str, int]] = {"/novnc": ("127.0.0.1", 6080),
                                             "/novnc-view": ("127.0.0.1", 6081)}
_NEED = {"/novnc": "control", "/novnc-view": "view"}   # the Caddyfile's forward_auth `need=`
_CONNECT_TIMEOUT_S = 3.0
_READ_TIMEOUT_S = 15.0
_MAX_FRAME = 32 * 1024 * 1024   # a raw 4K noVNC framebuffer update is ~33 MB; larger -> close 1009
_FORWARD_HEADERS = ("accept", "range", "if-none-match", "if-modified-since", "user-agent")
_BACK_HEADERS = ("content-type", "last-modified", "etag")   # never Cookie / Authorization
_BAD_PATH = re.compile(r"[\x00-\x1f\\]|\.\.|^/|^[A-Za-z][A-Za-z0-9+.-]*:")   # NUL \ .. // scheme


async def _relay_http(prefix: str, path: str, request: Request) -> Response:
    """E6.1: GET `<prefix>/<path>` -> `http://<loopback>/<path>`, prefix stripped."""
    refusal = live_access_refusal(current_principal(), _NEED[prefix])
    if refusal is not None:
        return PlainTextResponse(refusal[1], refusal[0])
    if not path or _BAD_PATH.search(path):   # an empty path is the bare `/novnc/`: never the app
        return PlainTextResponse("That path is not allowed.", 403 if not path else 400)
    host, port = VNC_UPSTREAMS[prefix]
    url = f"http://{host}:{port}/{quote(path, safe='/')}"
    if request.url.query:
        url += "?" + request.url.query
    headers = {k: v for k, v in request.headers.items() if k in _FORWARD_HEADERS}
    timeout = httpx.Timeout(_READ_TIMEOUT_S, connect=_CONNECT_TIMEOUT_S)
    try:
        async with httpx.AsyncClient(trust_env=False, timeout=timeout) as upstream:
            got = await upstream.get(url, headers=headers)
    except (httpx.HTTPError, httpx.InvalidURL):   # never name the upstream address (E6.7)
        return PlainTextResponse("The live browser view is not running right now.", 502)
    return Response(got.content, status_code=got.status_code,
                    headers={k: got.headers[k] for k in _BACK_HEADERS if k in got.headers})


def _own_origin(headers: dict[str, str], secure: bool) -> bool:
    """E6.4: an `Origin`, when sent, is this app's own (the browser sent it for the host it
    reached). A missing one is a non-browser client: cookie and permission decide."""
    origin = headers.get("origin")
    if origin is None:
        return True
    try:
        parts = urlparse(origin)
    except ValueError:
        return False
    same_host = parts.netloc.lower() == headers.get("host", "").lower()
    return (parts.scheme in ("http", "https") and same_host
            and (parts.scheme == "https" or not secure))


def _ws_refusal(ws: WebSocket, prefix: str) -> str | None:
    """Why this handshake is refused, or None. The login gate and the Origin/Host guard are HTTP
    middleware and never see a websocket scope, so the same checks run here, BEFORE accept."""
    secure, headers = ws.url.scheme == "wss", dict(ws.headers.items())
    if not _host_allowed(headers.get("host", "")) or not _own_origin(headers, secure):
        return "host or origin not allowed"
    conn = HTTPConnection({**ws.scope, "scheme": "https" if secure else "http"})
    refusal = live_access_refusal(_principal(conn), _NEED[prefix])   # type: ignore[arg-type]
    return None if refusal is None else refusal[1]


async def _client_to_upstream(ws: WebSocket, up) -> None:
    while (message := await ws.receive())["type"] != "websocket.disconnect":
        payload = message.get("bytes") or message.get("text") or b""
        if len(payload) > _MAX_FRAME:
            await ws.close(code=1009)
            return
        if payload:
            await up.send(payload)


async def _upstream_to_client(ws: WebSocket, up) -> None:
    async for frame in up:
        await (ws.send_bytes(frame) if isinstance(frame, bytes) else ws.send_text(frame))


async def _pump(ws: WebSocket, up) -> None:
    """Frames both ways until either side ends; then both are closed (nothing left open)."""
    tasks = [asyncio.ensure_future(_client_to_upstream(ws, up)),
             asyncio.ensure_future(_upstream_to_client(ws, up))]

    async def cleanup() -> None:
        await asyncio.gather(*tasks, return_exceptions=True)
        with contextlib.suppress(Exception):
            await up.close()
        ended = up.close_code   # 1000/1001 normal, 1009 too big, anything else is an error
        with contextlib.suppress(Exception):   # the client may be gone already
            await ws.close(code=1000 if ended in (1000, 1001) else 1009 if ended == 1009 else 1011)

    try:
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    finally:
        for task in tasks:
            task.cancel()
        try:   # a cancelled handler (client vanished, server stopping) still closes the upstream
            await asyncio.shield(asyncio.ensure_future(cleanup()))
        except asyncio.CancelledError:
            with contextlib.suppress(Exception):
                up.transport.abort()
            raise


async def _relay_ws(ws: WebSocket, prefix: str) -> None:
    """E6.2: `WebSocket <prefix>/websockify` <-> the loopback websockify, frames unchanged."""
    if _ws_refusal(ws, prefix) is not None:
        await ws.close(code=1008)         # before accept: the upgrade is answered 403, no dial
        return
    chosen = "binary" if "binary" in (ws.scope.get("subprotocols") or []) else None
    await ws.accept(subprotocol=chosen)
    host, port = VNC_UPSTREAMS[prefix]
    try:
        up = await ws_connect(f"ws://{host}:{port}/websockify", subprotocols=[chosen]
                              if chosen else None, max_size=_MAX_FRAME, compression=None,
                              open_timeout=_CONNECT_TIMEOUT_S, close_timeout=2,
                              ping_interval=None, proxy=None)
    except Exception:
        await ws.close(code=1011)
        return
    await _pump(ws, up)


def _register(prefix: str) -> None:
    async def http_relay(request: Request, path: str = "") -> Response:
        return await _relay_http(prefix, path, request)

    async def ws_relay(ws: WebSocket) -> None:
        await _relay_ws(ws, prefix)

    router.add_api_route(f"{prefix}/{{path:path}}", http_relay, methods=["GET"],
                         include_in_schema=False)
    router.add_api_websocket_route(f"{prefix}/websockify", ws_relay)


async def _forbidden() -> Response:
    return PlainTextResponse("Forbidden", 403)


for _prefix in VNC_UPSTREAMS:
    _register(_prefix)
# E6.5: bare and look-alike VNC names are never the app and never the viewer (Caddy @vnc_other)
for _lookalike in ("/novnc", "/novnc-view", "/websockify", "/websockify/{rest:path}",
                   "/vnc.html", "/vnc_lite.html"):
    router.add_api_route(_lookalike, _forbidden, methods=["GET"], include_in_schema=False)


def _newest_source_mtime() -> datetime:
    """The most recent mtime under `src/autotester`, scanned fresh on every
    call -- unlike `_PROCESS_STARTED_AT`, this reflects a source edit made
    AFTER the process started. `_SRC_ROOT` is read from the module global (not
    a bound default) so tests can monkeypatch it onto a throwaway directory."""
    mtimes = [p.stat().st_mtime for p in _SRC_ROOT.rglob("*.py")]
    if not mtimes:
        return _PROCESS_STARTED_AT
    return datetime.fromtimestamp(max(mtimes), tz=UTC)


def store_readiness() -> dict[str, object]:
    """Which backend holds each area, and whether the chosen backends answer a ping (M26).

    Never raises and never carries an exception text, URI or database name: any failure (an
    outage, an unset URI, a bad selection) is `reachable: false`, the same as startup's refusal."""
    try:
        areas = store_selection()
    except ValueError:
        return {"areas": {}, "reachable": False}
    try:
        validate_store_env()
    except Exception:  # readiness is a boolean; the reason stays server-side
        return {"areas": areas, "reachable": False}
    return {"areas": areas, "reachable": True}


@router.get("/healthz")
def healthz() -> dict[str, object]:
    """AU16 (T-204): an unsigned-in caller (the container health check) gets only
    `{"ok": true}`; the freshness detail below, and `store` (mongo-store M26: the backend per
    area and whether it answers), need `settings.manage`. It stays 200 while the store is down.

    One HTTP call standing in for the `ps` + `find -newermt` archaeology
    AT-085's checker had to do by hand: when this process started, and
    whether any `.py` file under `src/autotester` is newer than that. Reads no
    project state and loads no store -- same presentation-only invariant
    `/live` (D4) holds."""
    who = current_principal()
    if who is None or not authorize(who, PermissionKey.SETTINGS_MANAGE):
        return {"ok": True}
    newest = _newest_source_mtime()
    return {
        "started_at": _PROCESS_STARTED_AT.isoformat(),
        "newest_source_mtime": newest.isoformat(),
        "serving_stale_code": newest > _PROCESS_STARTED_AT,
        "store": store_readiness(),
    }
