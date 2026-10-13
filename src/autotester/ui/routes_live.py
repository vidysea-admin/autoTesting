"""Presentation-only noVNC page for watching the container's real browser, plus
a process-freshness probe (`/healthz`, AT-085)."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from html import escape
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

import autotester
from autotester.auth.access import authorize
from autotester.auth.context import current_principal
from autotester.schema.auth import PermissionKey
from autotester.ui import theme

router = APIRouter()

# AT-085: the container's uvicorn runs without `--reload` (docker/entrypoint.sh),
# so a source edit made after this module was imported is silently NOT served --
# a "verified live" claim can describe the previous build with nothing on the
# surface to say so. Frozen once, at import time, which for a real `uv run
# uvicorn` process (no reloader) happens exactly once, before the first request
# -- the same "process start" a checker previously read off `ps -o lstart=`.
_PROCESS_STARTED_AT = datetime.now(UTC)


def package_root() -> Path:
    """The installed `autotester` package. Not `repo_root()`: on a server `AUTOTESTER_ROOT`
    points at the data volume (projects/, profiles/, .env), which holds no source."""
    return Path(autotester.__file__).resolve().parent


_SRC_ROOT = package_root()
NOVNC_ENV = "AUTOTESTER_NOVNC_URL"
_DEFAULT_NOVNC = "http://localhost:6080/vnc.html?autoconnect=true&resize=scale"


def novnc_url() -> str:
    """Where the viewer iframe points. Local docker default is the published port; a server
    sets `AUTOTESTER_NOVNC_URL` to a same-origin path (`/novnc/vnc.html?...`) served by the
    reverse proxy, because an http iframe inside an https page is blocked. Only an absolute
    path or an http(s) URL on localhost is accepted: anything else falls back to the default."""
    raw = os.environ.get(NOVNC_ENV, "").strip()
    same_origin = raw.startswith("/") and not raw.startswith("//")
    local = raw.startswith(("http://localhost:", "http://127.0.0.1:"))
    hostile = {"'", '"', "<", ">", " "} & set(raw)
    return raw if (same_origin or local) and not hostile else _DEFAULT_NOVNC


def viewer_url(can_control: bool) -> str:
    """The iframe target. Without `live.control` the viewer is told to be view-only (noVNC's
    `view_only=1`), so a watcher cannot send keys or clicks from this page (HO12)."""
    url = novnc_url()
    if can_control:
        return url
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


def _newest_source_mtime() -> datetime:
    """The most recent mtime under `src/autotester`, scanned fresh on every
    call -- unlike `_PROCESS_STARTED_AT`, this reflects a source edit made
    AFTER the process started. `_SRC_ROOT` is read from the module global (not
    a bound default) so tests can monkeypatch it onto a throwaway directory."""
    mtimes = [p.stat().st_mtime for p in _SRC_ROOT.rglob("*.py")]
    if not mtimes:
        return _PROCESS_STARTED_AT
    return datetime.fromtimestamp(max(mtimes), tz=UTC)


@router.get("/healthz")
def healthz() -> dict[str, str | bool]:
    """AU16 (T-204): an unsigned-in caller (the container health check) gets only
    `{"ok": true}`; the freshness detail below needs `settings.manage`.

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
    }
