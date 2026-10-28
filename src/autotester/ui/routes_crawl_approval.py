"""The crawl-approval card on the credentials page (D-018 consent, gate 2).

Split from `routes_credentials.py` for the 300-line cap: human consent for one bounded run,
not value editing. The grant form, the list and Revoke (D-111) live here;
`stages/explore_consent.py::require_consent` is the runtime gate that reads what lands.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from html import escape
from math import isfinite

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from autotester.auth.context import current_principal
from autotester.browser.secrets import SecretStore
from autotester.core.consent import MAX_GRANT_PROBES, validate_grant_bounds
from autotester.core.ids import SigningKeyMissing
from autotester.core.paths import ProjectPaths
from autotester.schema.approval import RunApproval
from autotester.schema.approval_revocation import ApprovalRevocation
from autotester.schema.enums import ApprovalKind
from autotester.store.approval_revocations import add_revocation
from autotester.ui import theme
from autotester.ui.helpers import _load_project_or_404, _refuse_unsafe_submission

router = APIRouter()

_KINDS = (ApprovalKind.CRAWL, ApprovalKind.LIVE_CASE)   # what the UI may grant, as the CLI can


def _signer() -> str:
    """The signed-in human's email, or '' when there is no real session behind the request."""
    who = current_principal()
    return who.email if who is not None and who.user_id else ""


def _kind_and_production(project_production: bool) -> str:
    """Kind selector and production checkbox, forced on for a production project (D-088)."""
    options = "".join(f"<option value='{k.value}'>{k.value}</option>" for k in _KINDS)
    box = ("<input id='ca-production' type='checkbox' checked disabled> "
           "<input type='hidden' name='production' "
           "value='1'> required: this project is declared production (D-088)"
           if project_production else
           "<input id='ca-production' type='checkbox' name='production' value='1'>")
    return (f"<div class='field'><label for='ca-kind'>Kind</label>"
            f"<select id='ca-kind' name='kind'>{options}</select></div>"
            f"<div class='field'><label for='ca-production'>Production</label>{box}</div>")


def _crawl_approval_form(slug: str, target: str, production: bool = False) -> str:
    """The CLI `approve` counterpart; the signer is the signed-in account, never a field."""
    safe = escape(slug)
    form = (
        f"<p>This approval applies only to <code>{escape(target)}</code>.</p>"
        f"<form method='post' action='/projects/{safe}/crawl-approval'>"
        f"<p>Signed by <code>{escape(_signer() or 'nobody - sign in first')}</code></p>"
        f"{_kind_and_production(production)}"
        "<div class='field'><label for='ca-scope'>Scope</label>"
        "<input id='ca-scope' name='scope' required "
        "placeholder='what this crawl may read and click'></div>"
        "<div class='field'><label for='ca-expires'>Expires at (blank if standing)</label>"
        "<input id='ca-expires' type='datetime-local' name='expires_at'></div>"
        "<div class='field'><label for='ca-standing'>Standing</label>"
        "<input id='ca-standing' type='checkbox' name='standing' value='1'> "
        "Standing, until revoked (crawl only; every run is still capped by the limits below)"
        "</div>"
        "<div class='field'><label for='crawl-timezone-offset'>"
        "UTC offset in minutes (auto-detected)</label>"
        "<input type='number' id='crawl-timezone-offset' name='timezone_offset_minutes' "
        "min='-840' max='840' value='0' required></div>"
        "<script>const expiry=document.querySelector(\"[name='expires_at']\");"
        "const offset=document.getElementById('crawl-timezone-offset');"
        "const syncOffset=()=>{const selected=new Date(expiry.value);"
        "if(!Number.isNaN(selected.valueOf()))offset.value="
        "String(-selected.getTimezoneOffset());};"
        "const st=document.getElementById('ca-standing');"
        "st.addEventListener('change',()=>{expiry.disabled=st.checked;});"
        "expiry.addEventListener('change',syncOffset);"
        "expiry.form.addEventListener('submit',syncOffset);</script>"
        "<div class='field'><label for='ca-actions'>Maximum actions</label>"
        "<input id='ca-actions' type='number' name='max_actions' min='1' value='200' "
        "required></div>"
        "<div class='field'><label for='ca-probes'>Maximum probes (0 grants none)</label>"
        "<input id='ca-probes' type='number' name='max_probes' min='0' max='40000' "
        "value='4000' required></div>"
        "<div class='field'><label for='ca-wall'>Wall clock (seconds)</label>"
        "<input id='ca-wall' type='number' name='wall_clock_s' min='1' step='any' "
        "value='600' required></div>"
        "<div class='field'><label for='ca-note'>Note (optional)</label>"
        "<input id='ca-note' name='note' placeholder='why this crawl is approved'></div>"
        "<button type='submit'>Save crawl approval</button></form>"
    )
    return f"<section id='crawl-approval'>{theme.card(form, title='Approve a run')}</section>"


def _in_force(approval: RunApproval, slug: str, target: str) -> bool:
    """What the consent gate would honour for this project's crawl, never more: a forged or
    unsigned row shown as "in force" is false reassurance, so check the signature too (AT-110)."""
    if not (approval.project == slug and approval.run_kind is ApprovalKind.CRAWL
            and approval.target == target and approval.is_intact
            and not approval.is_expired(datetime.now(UTC))):
        return False
    try:
        return approval.is_signed_and_verified
    except SigningKeyMissing:
        return False  # fail closed: can't verify, don't claim it's in force


def _revoke_form(slug: str, approval_id: str) -> str:
    return (f"<form method='post' action='/projects/{escape(slug)}/crawl-approval/"
            f"{escape(approval_id)}/revoke'><input name='reason' placeholder='why' size='14'>"
            "<button type='submit'>Revoke</button></form>")


def _approvals_card(approvals: list[RunApproval], slug: str, target: str, saved: str,
                    existing: bool) -> str:
    """Confirmation plus the grants in force (AT-435), looked up ON DISK by id; the query
    string is never echoed."""
    active = [a for a in approvals if _in_force(a, slug, target)]
    banner = ""
    just_saved = next((a for a in active if a.id == saved), None)
    if just_saved is not None:
        what = ("This approval was already on file ΓÇö nothing new was saved." if existing
                else "It is in force and listed below.")
        heading = "Crawl approval already on file" if existing else "Crawl approval saved"
        banner = (f"<p>{theme.pill('Γ£ô ' + heading, 'positive')} {what} "
                  f"<code>{escape(just_saved.id)}</code></p>")
    rows = "".join(
        f"<tr><td>{escape(a.granted_by)}</td><td>{a.run_kind.value}"
        f"{' (production)' if a.production else ''}</td><td>{escape(a.scope)}</td>"
        f"<td>{a.max_actions}</td><td>{a.wall_clock_s:g}s</td>"
        f"<td>{'<b>Standing, until revoked</b>' if a.is_standing else escape(a.expires_at or '')}"
        f"</td><td><code>{escape(a.id)}</code></td><td>{_revoke_form(slug, a.id)}</td></tr>"
        for a in active
    )
    table = (
        "<table><tr><th>Signed by</th><th>Kind</th><th>Scope</th><th>Max actions</th>"
        "<th>Wall clock</th>"
        f"<th>Expires (UTC)</th><th>Id</th><th></th></tr>{rows}</table>" if active
        else "<p class='meta'>No crawl approval is in force for this target.</p>"
    )
    # Only crawl grants (AT-452); "or project": `_in_force` also requires it (AT-455).
    crawl = [a for a in approvals if a.run_kind is ApprovalKind.CRAWL]
    others = len(crawl) - len(active)
    note = (f"<p class='meta'>{others} more on file are expired, edited after granting, or for "
            "another target or project, and are not honoured.</p>" if others else "")
    return theme.card(banner + table + note, title="Approvals in force")


def _matching_grant(approvals: list[RunApproval], candidate: RunApproval) -> RunApproval | None:
    """An in-force grant identical to `candidate` but for when it was signed: a repeat click."""
    def bounds(a: RunApproval) -> dict[str, object]:
        payload = a._bound_payload()
        payload.pop("granted_at")
        return {**payload, "note": a.note}

    return next((a for a in approvals if a.is_intact
                 and not a.is_expired(datetime.now(UTC)) and bounds(a) == bounds(candidate)),
                None)


def _approval_error(slug: str, detail: str, status: int = 400) -> HTMLResponse:
    safe = escape(slug)
    body = theme.breadcrumb(
        ("Projects", "/"), (safe, f"/projects/{safe}"), ("Credentials", None),
    ) + "<h1>Crawl approval not saved</h1>" + theme.card(
        f"<p>{escape(detail)}</p><p><a class='btn' href='/projects/{safe}/env#crawl-approval'>"
        "Return to crawl approval</a></p>", title="Check the approval details",
    )
    return HTMLResponse(theme.page("Crawl approval not saved", body, active_slug=slug),
                        status_code=status)


def _future_iso(value: str, offset_minutes: int) -> str:
    text = value.strip()
    try:
        expiry = datetime.fromisoformat(text)
    except ValueError:
        raise HTTPException(400, "expiry must be an ISO date and time") from None
    if "T" not in text:
        raise HTTPException(400, "expiry must include an ISO date and time")
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone(timedelta(minutes=offset_minutes)))
    expiry = expiry.astimezone(UTC)
    if expiry <= datetime.now(UTC):
        raise HTTPException(400, "expiry must be in the future")
    return expiry.isoformat()


def _grant_expiry(standing: bool, expires_at: str, offset: int) -> str | None:
    """None for a standing grant (D-111, no date); else the future ISO expiry."""
    if standing and expires_at.strip():
        raise HTTPException(400, "a standing approval has no expiry: clear it or untick standing")
    return None if standing else _future_iso(expires_at, offset)


def _capped(actions: int, seconds: float, expiry: str | None, probes: int,
            kind: ApprovalKind) -> None:
    if not 0 <= probes <= MAX_GRANT_PROBES:
        raise HTTPException(400, f"max probes must be between 0 and {MAX_GRANT_PROBES}")
    try:
        validate_grant_bounds(actions, seconds, None if expiry is None
                              else datetime.fromisoformat(expiry), kind=kind)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None


def _bounds(actions: str, seconds: str, probes: str, offset: str) -> tuple[int, float, int, int]:
    a, w, p, o = int(actions), float(seconds), int(probes), int(offset)
    if a <= 0 or w <= 0 or not isfinite(w):
        raise HTTPException(400, "crawl approval bounds must be positive")
    if not -840 <= o <= 840:
        raise HTTPException(400, "timezone offset must be between -840 and 840 minutes")
    return a, w, o, p


def _checked_kind(kind: str, scope: str) -> ApprovalKind:
    run_kind = ApprovalKind(kind)
    if run_kind not in _KINDS:
        raise HTTPException(400, "kind must be crawl or live_case")
    if not scope:
        raise HTTPException(400, "an approval requires a scope")
    return run_kind


@router.post("/projects/{slug}/crawl-approval")
def crawl_approval_submit(
    request: Request, slug: str, kind: str = Form("crawl"), production: str = Form(""),
    scope: str = Form(""), expires_at: str = Form(""), max_actions: str = Form(""),
    wall_clock_s: str = Form(""), max_probes: str = Form("0"),
    timezone_offset_minutes: str = Form("0"), note: str = Form(""), standing: str = Form(""),
) -> Response:
    """Persist one bounded approval; project and target always come from disk."""
    store, project = _load_project_or_404(slug)
    signer, allowed_scope, on = _signer(), scope.strip(), standing.strip().lower() in ("1", "on")
    if not signer or "authorization" in request.headers:   # human session only, no API token
        return _approval_error(slug, "a grant must come from a signed-in person", 403)
    try:
        run_kind = _checked_kind(kind, allowed_scope)
        secrets = SecretStore.load(project, ProjectPaths(slug).env_file, strict=False)
        _refuse_unsafe_submission([
            ("scope", allowed_scope), ("expiry", expires_at),
            ("maximum actions", max_actions), ("wall clock", wall_clock_s),
            ("maximum probes", max_probes), ("timezone offset", timezone_offset_minutes),
            ("note", note),
        ], project, secrets)
        actions, seconds, offset, probes = _bounds(
            max_actions, wall_clock_s, max_probes, timezone_offset_minutes)
        expiry = _grant_expiry(on, expires_at, offset)
        _capped(actions, seconds, expiry, probes, run_kind)
    except ValueError:
        return _approval_error(slug, "kind and bounds must be valid, numbers for bounds")
    except HTTPException as exc:
        return _approval_error(slug, str(exc.detail))
    candidate = RunApproval(
        project=project.slug, run_kind=run_kind, target=project.base_url,
        production=project.production or production.strip().lower() in ("1", "on"),
        scope=allowed_scope, max_actions=actions, max_probes=probes, wall_clock_s=seconds,
        granted_by=signer, granted_at=datetime.now(UTC).isoformat(), expires_at=expiry,
        standing=on, note=note.strip() or None,
    )
    try:
        candidate.sign()
    except SigningKeyMissing as exc:
        return _approval_error(slug, str(exc))
    already = _matching_grant(store.list_approvals(), candidate)
    if already is None:
        store.add_approval(candidate)
    grant = already or candidate
    flag = "&existing=1" if already else ""
    return RedirectResponse(
        f"/projects/{slug}/env?saved={grant.id}{flag}#crawl-approval", status_code=303,
    )


@router.post("/projects/{slug}/crawl-approval/{approval_id}/revoke")
def crawl_approval_revoke(
    request: Request, slug: str, approval_id: str, reason: str = Form(""),
) -> Response:
    """D-111: withdraw one grant with a signed revocation (what ends a standing approval).
    A signed-in person only, like granting; the grant file is never edited."""
    store, project = _load_project_or_404(slug)
    signer = _signer()
    if not signer or "authorization" in request.headers:
        return _approval_error(slug, "a revocation must come from a signed-in person", 403)
    if all(a.id != approval_id for a in store.list_approvals()):
        return _approval_error(slug, f"no approval in force with id {approval_id}", 404)
    why = reason.strip()[:500] or "revoked from the credentials page"
    try:
        secrets = SecretStore.load(project, ProjectPaths(slug).env_file, strict=False)
        _refuse_unsafe_submission([("reason", why)], project, secrets)
        row = ApprovalRevocation(approval_id=approval_id, revoked_by=signer, reason=why,
                                 revoked_at=datetime.now(UTC).isoformat()).sign()
    except (HTTPException, SigningKeyMissing) as exc:
        return _approval_error(slug, str(getattr(exc, "detail", exc)))
    add_revocation(store.paths.approval_revocations, row)
    return RedirectResponse(f"/projects/{slug}/env#crawl-approval", status_code=303)
