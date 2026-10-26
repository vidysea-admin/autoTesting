"""Sign in, sign up, sign out and the waiting page (T-204, auth.md AU2-AU7).

Login failures for an unknown email, a wrong password and a disabled account return
one identical 401 page (AU2). The rate limit is checked before the password, so a
locked scope gets 429 even with the right password (AU5).
"""

from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from autotester.auth import audit
from autotester.auth.access import authorize
from autotester.auth.accounts import (
    AccountError,
    authenticate,
    claim_admin,
    normalize_email,
    signup,
)
from autotester.auth.config import cookie_secure
from autotester.auth.context import current_principal
from autotester.auth.db import LastAdmin
from autotester.auth.passwords import WeakPassword
from autotester.auth.ratelimit import login_limiter, signup_limiter
from autotester.auth.sessions import create_session, end_session, session_hours
from autotester.schema.auth import PermissionKey
from autotester.ui import auth_view
from autotester.ui.auth_middleware import SESSION_COOKIES, safe_next, session_token

router = APIRouter()

_LOGIN_FAILED = "That email and password do not match an active account."
_TOO_MANY = "Too many sign-in attempts. Wait a few minutes and try again."
_TOO_MANY_SIGNUPS = "Too many sign-up attempts from this address. Wait a few minutes."


def _signed_in(request: Request, user_id: int, has_access: bool, next_path: str) -> Response:
    secure = cookie_secure(request.url.scheme)
    target = safe_next(next_path) if has_access else "/auth/waiting"
    response = RedirectResponse(target, status_code=303)
    response.set_cookie(SESSION_COOKIES[0] if secure else SESSION_COOKIES[1],
                        create_session(user_id), max_age=session_hours() * 3600, path="/",
                        httponly=True, samesite="lax", secure=secure)
    return response


@router.get("/auth/login", response_class=HTMLResponse)
def auth_login_form(next: str = "/") -> str:
    return auth_view.login_page(safe_next(next))


@router.post("/auth/login")
def auth_login_submit(request: Request, email: str = Form(""), password: str = Form(""),
                      next: str = Form("/")) -> Response:
    try:
        account = normalize_email(email)
    except AccountError:
        account = ""
    address = request.client.host if request.client else "unknown"
    if login_limiter.blocked(account, address):
        return HTMLResponse(auth_view.login_page(safe_next(next), _TOO_MANY), status_code=429)
    user = authenticate(email, password)
    if user is None:
        login_limiter.record_failure(account, address)
        audit.record_action(actor=account, target="", action="login-failed")
        return HTMLResponse(auth_view.login_page(safe_next(next), _LOGIN_FAILED),
                            status_code=401)
    audit.record_action(actor=user.email, target=user.email, action="login")
    return _signed_in(request, user.id, bool(user.groups), next)


@router.get("/auth/signup", response_class=HTMLResponse)
def auth_signup_form() -> str:
    return auth_view.signup_page()


@router.post("/auth/signup")
def auth_signup_submit(request: Request, email: str = Form(""),
                       password: str = Form("")) -> Response:
    address = request.client.host if request.client else "unknown"
    if signup_limiter.blocked(address, address):
        return HTMLResponse(auth_view.signup_page(_TOO_MANY_SIGNUPS), status_code=429)
    signup_limiter.record_failure(address, address)  # every attempt counts: each costs one hash
    try:
        user = signup(email, password, cookie_secure(request.url.scheme))
    except (AccountError, WeakPassword) as exc:
        return HTMLResponse(auth_view.signup_page(str(exc)), status_code=400)
    audit.record_action(actor=user.email, target=user.email, action="signup")
    return _signed_in(request, user.id, bool(user.groups), "/")


@router.post("/auth/logout")
def auth_logout(request: Request) -> Response:
    end_session(session_token(request))
    response = RedirectResponse("/auth/login", status_code=303)
    for name in SESSION_COOKIES:
        response.delete_cookie(name, path="/", secure=name.startswith("__Host-"),
                               httponly=True, samesite="lax")
    return response


@router.get("/auth/waiting", response_class=HTMLResponse)
def auth_waiting() -> Response:
    who = current_principal()
    if who is not None and who.permissions:
        return RedirectResponse("/", status_code=303)
    return HTMLResponse(auth_view.waiting_page(who.email if who else ""))


@router.post("/auth/claim-admin")
def auth_claim_admin() -> Response:
    """D-109: a signed-in account takes the admin group while it has no member. The first claim
    wins; a refused one changes nothing. Both are audited."""
    who = current_principal()
    if who is None or who.user_id is None:   # the gate already refused anonymous requests
        return JSONResponse({"detail": "authentication required"}, status_code=401)
    try:
        claim_admin(who.user_id)
    except (AccountError, LastAdmin) as exc:
        audit.record_action(actor=who.email, target=who.email, action="admin.claim_refused")
        return HTMLResponse(auth_view.waiting_page(who.email, str(exc)), status_code=403)
    audit.record_action(actor=who.email, target=who.email, action="admin.claim")
    return RedirectResponse("/", status_code=303)


@router.get("/auth/check")
def auth_check(need: str = "view") -> Response:
    """HO12: what the reverse proxy asks (`forward_auth`) before `/novnc-view/*` (need=view) or
    `/novnc/*` (need=control), so the
    proxy keeps no list of its own. The login gate has already turned a missing or expired
    session into 401/302 and a signed-in account without `live.view` into 403 (policy row);
    here `need=control` additionally wants `live.control`. 200 carries the identity."""
    who = current_principal()
    if who is None or not who.authenticated:
        return JSONResponse({"detail": "authentication required"}, status_code=401)
    if need not in ("view", "control"):       # fail closed on a mistyped proxy rule
        return JSONResponse({"detail": "unknown need"}, status_code=400)
    if need == "control" and not authorize(who, PermissionKey.LIVE_CONTROL):
        return JSONResponse({"detail": "live.control is required to send input"}, status_code=403)
    return JSONResponse({"email": who.email,
                         "can_control": authorize(who, PermissionKey.LIVE_CONTROL)})
