"""Global AI/API provider keys. Contract: qa/contracts/ui-settings.md US1-US4.
A different concept from a project's own `SecretRef`s (routes_credentials.py):
these are read straight from `os.environ` by `providers/langchain_fallback.py`
and `providers/gemini.py`, not scoped to any one project.
"""

from __future__ import annotations

import os
from html import escape

from fastapi import APIRouter, Form, HTTPException, Response
from fastapi.responses import HTMLResponse, RedirectResponse

from autotester.browser.secrets import parse_env
from autotester.core.env import HARNESS_KEYS
from autotester.core.paths import repo_root
from autotester.ui import theme
from autotester.ui.credential_guard import PROVIDER_KEYS
from autotester.ui.env_editor import InvalidEnvValue, set_env_value
from autotester.ui.routes_credentials import can_view_credentials

router = APIRouter()

# The complete, closed set this page manages (US1) -- a new provider key is a
# code change in ui/credential_guard.py, not a dynamic field.
# T-169 adds the acceptance-script login (email + write-only password) to the same closed set.
_PROVIDER_KEYS = (*PROVIDER_KEYS, *HARNESS_KEYS)
_WRITE_ONLY = frozenset({"AUTOTESTER_HARNESS_PASSWORD"})  # never prefilled, not even for viewers


def _present_keys() -> dict[str, str]:
    env_path = repo_root() / ".env"
    return parse_env(env_path.read_text(encoding="utf-8")) if env_path.exists() else {}


@router.get("/settings/providers", response_class=HTMLResponse)
def provider_settings_view() -> str:
    present = _present_keys()
    show = can_view_credentials()  # T-204 AU21: values only for credentials.view
    in_env = {k for k in _PROVIDER_KEYS if os.environ.get(k)}  # server env keys count as set

    def _status_cell(key: str) -> str:
        return (theme.pill("● Set", "positive") if present.get(key) or key in in_env
                else theme.pill("○ Not set", "neutral"))

    # 2026-09-21 UX amendment (Umesh, Approver): same as the credentials
    # editor — the stored value is shown IN the field (prefilled, editable);
    # *_KEY rows stay masked with a show/hide toggle. Owner-only display.
    _EYE = ("<button type='button' class='btn btn-sm' tabindex='-1' "
            "onclick=\"var i=this.parentNode.querySelector('input');"
            "i.type=i.type==='password'?'text':'password';"
            "this.textContent=i.type==='password'?'show':'hide';\">show</button>")

    def _row(key: str) -> str:
        write_only = key in _WRITE_ONLY
        is_secret = key.endswith("_KEY") or not show or write_only
        shown = present.get(key, "") if show and not write_only else ""
        eye = _EYE if show and is_secret and not write_only else ""
        input_type = "password" if is_secret else "text"
        return (
            f"<tr><td><code>{escape(key)}</code></td>"
            f"<td>{_status_cell(key)}</td>"
            f"<form method='post' action='/settings/providers'>"
            f"<input type='hidden' name='key' value='{escape(key)}'>"
            f"<td style='display:flex;gap:6px'>"
            f"<input type='{input_type}' name='value' "
            f"value='{escape(shown)}' aria-label='Value for {escape(key)}' "
            f"placeholder='new value' style='flex:1'>{eye}"
            f"</td>"
            f"<td><button class='btn btn-sm' type='submit'>Save</button></td></form></tr>"
        )

    rows = "".join(_row(key) for key in _PROVIDER_KEYS)
    table = (f"<table><tr><th>Key</th><th>Status</th>"
             f"<th>Value (edit and Save)</th><th></th></tr>{rows}</table>")
    body = (
        theme.breadcrumb(("Projects", "/"), ("Settings", None))
        + "<h1>Provider settings</h1>"
        "<p class='subtitle'>Global AI/API keys every project's grading and agent steps fall "
        "back through. Saved values are shown (masked with show/hide) so you can verify and "
        "edit them; they never leave this page.</p>"
        f"{theme.card(table)}"
    )
    return theme.page("Settings", body)


@router.post("/settings/providers")
def provider_settings_submit(key: str = Form(...), value: str = Form("")) -> Response:
    if key not in _PROVIDER_KEYS:
        raise HTTPException(400, f"'{key}' is not a known provider setting")
    if not value.strip():
        # Same wipe-guard as the per-project credentials editor: an empty
        # masked field means "nothing typed", never "erase" the stored key.
        body = (theme.breadcrumb(("Projects", "/"), ("Settings", None))
                + "<h1>Provider key not saved</h1>" + theme.card(
                    f"<p>No new value was typed for <code>{escape(key)}</code>, so nothing "
                    f"was changed — the stored key (if any) is untouched.</p>"
                    f"<p><a class='btn' href='/settings/providers'>Return to settings</a></p>",
                    title="Empty fields are ignored"))
        return HTMLResponse(theme.page("Provider key not saved", body), status_code=400)
    try:
        set_env_value(repo_root() / ".env", key, value)
    except InvalidEnvValue as exc:
        raise HTTPException(400, str(exc)) from exc
    return RedirectResponse("/settings/providers", status_code=303)
