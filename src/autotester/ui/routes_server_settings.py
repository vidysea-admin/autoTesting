"""The admin page for server limits (hosting.md HO15): run concurrency and the upload ceiling.

One job: show the values in force, validate a submission through `ServerSettings` (strict, so
nothing is coerced), save it, audit the change and let the queue notice a raised cap at once.
Reachable only with `settings.manage` (central policy row). A refusal says which field and why,
never the text typed; nothing is stored unless every field is valid.
"""

from __future__ import annotations

import re
from html import escape

from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from pydantic import ValidationError

from autotester.auth import audit
from autotester.auth.context import current_principal
from autotester.schema.server_settings import (
    MAX_CONCURRENT_RUNS_CEILING,
    MAX_UPLOAD_BYTES_CEILING,
    MIN_UPLOAD_BYTES,
    ServerSettings,
)
from autotester.store.server_settings import (
    effective_max_concurrent_runs,
    effective_max_upload_bytes,
    load_server_settings,
    save_server_settings,
)
from autotester.ui import theme
from autotester.ui.run_queue import get_queue

router = APIRouter()
_DIGITS = re.compile(r"[0-9]{1,20}")


def _int_or_none(raw: str) -> int | None:
    """Digits only (no sign, decimal point, exponent, space or separator); else None."""
    text = raw.strip()
    return int(text) if _DIGITS.fullmatch(text) else None


def _page(error: str = "", notice: str = "") -> str:
    _saved, unreadable = load_server_settings()
    warn = f"<p class='alert'>{escape(unreadable)}</p>" if unreadable else ""
    msg = (f"<p class='alert'>{escape(error)}</p>" if error else
           f"<p class='meta'>{escape(notice)}</p>" if notice else "")
    form = (
        "<form method='post' action='/settings/server'>"
        f"<p><label>Runs at once, server-wide (1-{MAX_CONCURRENT_RUNS_CEILING})<br>"
        f"<input name='max_concurrent_runs' inputmode='numeric' "
        f"value='{effective_max_concurrent_runs()}'></label></p>"
        f"<p><label>Largest recording upload, in bytes ({MIN_UPLOAD_BYTES} to "
        f"{MAX_UPLOAD_BYTES_CEILING})<br><input name='max_upload_bytes' inputmode='numeric' "
        f"value='{effective_max_upload_bytes()}'></label></p>"
        "<button class='btn btn-primary' type='submit'>Save</button></form>"
    )
    body = (theme.breadcrumb(("Projects", "/"), ("Settings", "/settings/providers"),
                             ("Server limits", None))
            + "<h1>Server limits</h1><p class='subtitle'>Applied to the next run start and the "
              "next upload; no restart needed.</p>" + warn + msg + theme.card(form))
    return theme.page("Server limits", body)


@router.get("/settings/server", response_class=HTMLResponse)
def server_settings_view() -> str:
    return _page()


@router.post("/settings/server")
def server_settings_submit(max_concurrent_runs: str = Form(""),
                           max_upload_bytes: str = Form("")) -> Response:
    runs, upload = _int_or_none(max_concurrent_runs), _int_or_none(max_upload_bytes)
    try:
        if runs is None or upload is None:
            raise ValueError
        settings = ServerSettings(max_concurrent_runs=runs, max_upload_bytes=upload)
    except (ValueError, ValidationError):
        bad = "runs at once" if runs is None or not 1 <= runs <= MAX_CONCURRENT_RUNS_CEILING \
            else "upload size"
        return HTMLResponse(_page(error=f"Not saved: {bad} is not a whole number in its allowed "
                                        "range. Nothing was changed."), status_code=400)
    before = (effective_max_concurrent_runs(), effective_max_upload_bytes())
    save_server_settings(settings)
    who = current_principal()
    audit.record_action(who.email if who else "unknown", "server-settings",
                        f"max_concurrent_runs {before[0]}->{settings.max_concurrent_runs}; "
                        f"max_upload_bytes {before[1]}->{settings.max_upload_bytes}")
    get_queue().nudge()   # a raised cap starts a waiting run now, not at the next press
    return RedirectResponse("/settings/server", status_code=303)
