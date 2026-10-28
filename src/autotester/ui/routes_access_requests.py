"""Share-link opening, request-access, and the approvers' list (T-198b / G9, TP3, TP5).

A share link grants nothing: opening it signed in as a non-member shows the same
request-access page as any video the person may not see, and an unknown, revoked or malformed
token shows that page too. Asking is recorded from the session, once per video; approving or
declining belongs to people `authorize()` allows (`stages/video_requests.py`).
"""

from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from autotester.auth import accounts, audit, groups
from autotester.auth.access import authorize
from autotester.auth.db import NotAllowed
from autotester.schema.auth import PermissionKey as K
from autotester.schema.auth import Principal
from autotester.schema.team_enums import AccessRequestStatus
from autotester.stages import video_access as access
from autotester.stages.video_requests import (
    approvers,
    decide,
    latest_request,
    notify_approvers,
    pending_for,
    request_access,
)
from autotester.ui import video_portal_view as view
from autotester.ui.routes_video_portal import who_is

router = APIRouter()
_TOKEN_SHAPE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


def _ask(request: Request, slug: str | None, video_id: str | None) -> Response:
    """Record the signed-in person's request for a video (if it exists and they lack access)
    and answer the same page whatever the outcome, so nothing can be probed."""
    who = who_is()
    res = access.video_resource(slug, video_id) if slug and video_id else None
    if res is not None and authorize(who, K.VIDEO_VIEW, res):
        return RedirectResponse(f"/projects/{slug}/videos/{video_id}", status_code=303)
    if res is not None and slug and video_id:
        req, made = request_access(slug, video_id, who.email)
        if made and req is not None:
            link = str(request.base_url).rstrip("/") + "/access-requests"
            notify_approvers(approvers(res, who.email), link)
    return HTMLResponse(view.request_sent_page())


@router.post("/projects/{slug}/videos/{video_id}/request-access")
def ask_on_page(request: Request, slug: str, video_id: str) -> Response:
    return _ask(request, slug, video_id)


@router.get("/v/{token}")
def open_share_link(token: str) -> Response:
    """A member goes to the video; anyone else gets the request-access page (never the bytes)."""
    who = who_is()
    found = access.resolve_link(token)
    res = access.video_resource(*found) if found else None
    if found is not None and res is not None and authorize(who, K.VIDEO_VIEW, res):
        return RedirectResponse(f"/projects/{found[0]}/videos/{found[1]}", status_code=303)
    shape = token if _TOKEN_SHAPE.fullmatch(token) else "x"
    known = latest_request(*found, who.email) if found and res is not None else None
    return HTMLResponse(view.request_access_page(f"/v/{shape}/request-access", known),
                        status_code=404)


@router.post("/v/{token}/request-access")
def ask_by_link(request: Request, token: str) -> Response:
    found = access.resolve_link(token)
    return _ask(request, found[0] if found else None, found[1] if found else None)


def _labels(requests: list) -> dict[tuple[str, str], str]:
    out: dict[tuple[str, str], str] = {}
    for r in requests:
        source = access.find_video(r.slug, r.video_id)
        out[(r.slug, r.video_id)] = (source.label or source.id) if source else "a video"
    return out


def _requests_page(message: str = "", status: int = 200) -> HTMLResponse:
    """The approvers' page; the New accounts section only for a holder of users.manage."""
    who = who_is()
    pending = pending_for(who)
    manager = authorize(who, K.USERS_MANAGE)
    html = view.approver_requests_page(
        pending, _labels(pending), accounts.list_waiting() if manager else None,
        groups.list_groups(), message)
    return HTMLResponse(html, status_code=status)


@router.get("/access-requests", response_class=HTMLResponse)
def access_requests_page() -> HTMLResponse:
    """Only the requests this account may act on (absence, not 403, for the rest)."""
    return _requests_page()


def _manager() -> Principal:
    who = who_is()
    if not authorize(who, K.USERS_MANAGE):
        raise HTTPException(403, "you do not have permission")
    return who


def _decide_account(user_id: int, approve: bool, form: dict) -> Response:
    """Approve (add to the chosen group) or decline (disable) a waiting account; a refusal
    changes nothing and is audited like any refused admin action."""
    who = _manager()
    target = accounts.get_user(user_id)
    if target is None:
        raise HTTPException(404, "no such account")
    verb = "signup.approve" if approve else "signup.decline"
    try:
        if approve:
            raw = str(form.get("group_id", ""))
            if not raw.isdigit():
                raise accounts.AccountError("choose a group")
            accounts.approve_waiting(user_id, int(raw), who)
        else:
            accounts.decline_waiting(user_id, who)
    except (accounts.AccountError, NotAllowed) as exc:
        audit.record_action(actor=who.email, target=target.email, action=f"{verb}.refused")
        return _requests_page(str(exc), 403 if isinstance(exc, NotAllowed) else 400)
    audit.record_action(actor=who.email, target=target.email, action=verb)
    return RedirectResponse("/access-requests", status_code=303)


@router.post("/access-requests/accounts/{user_id}/approve")
async def approve_account(user_id: int, request: Request) -> Response:
    return _decide_account(user_id, True, dict(await request.form()))


@router.post("/access-requests/accounts/{user_id}/decline")
def decline_account(user_id: int) -> Response:
    return _decide_account(user_id, False, {})


def _decide(request_id: int, approve: bool) -> Response:
    who = who_is()
    done = decide(who, request_id, approve)
    if done is None:
        raise HTTPException(404, "no such request")
    if done.status is not AccessRequestStatus.PENDING and done.decided_by == who.email.lower():
        audit.record_action(actor=who.email, target=f"{done.slug}:{done.video_id}",
                            action=f"access.{done.status.value}")
    return RedirectResponse("/access-requests", status_code=303)


@router.post("/access-requests/{request_id}/approve")
def approve_request(request_id: int) -> Response:
    return _decide(request_id, True)


@router.post("/access-requests/{request_id}/decline")
def decline_request(request_id: int) -> Response:
    return _decide(request_id, False)
