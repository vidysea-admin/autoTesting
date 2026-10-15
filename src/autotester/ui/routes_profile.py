"""The signed-in user's own report-email checkbox; this page never sends mail."""

from __future__ import annotations

import os

from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from autotester.auth.context import current_principal
from autotester.delivery.email import is_configured
from autotester.store.notification_prefs import load_notification_pref, save_notification_pref
from autotester.ui import theme

router = APIRouter()


def _profile_user_id() -> int:
    who = current_principal()
    if who is None or not who.authenticated:
        raise HTTPException(401, "sign in to manage your profile")
    assert who.user_id is not None
    return who.user_id


@router.get("/profile", response_class=HTMLResponse)
def notification_profile() -> str:
    pref = load_notification_pref(_profile_user_id())
    checked = " checked" if pref.email_run_reports else ""
    status = ("Email is configured on this server." if is_configured(os.environ)
              else "Email is not configured on this server.")
    form = (
        "<form method='post' action='/profile'>"
        "<label><input type='checkbox' name='email_run_reports' value='on'"
        f"{checked}> Email me run reports</label>"
        f"<p class='meta'>{status}</p>"
        "<p>Reports are sent only while you can view the project.</p>"
        "<button class='btn btn-primary' type='submit'>Save</button></form>"
    )
    return theme.page("My profile", "<h1>My profile</h1>" + theme.card(form))


@router.post("/profile")
def update_notification_profile(email_run_reports: str = Form("")) -> Response:
    user_id = _profile_user_id()
    if email_run_reports not in ("", "on"):
        raise HTTPException(400, "invalid notification preference")
    save_notification_pref(user_id, email_run_reports == "on")
    return RedirectResponse("/profile", status_code=303)
