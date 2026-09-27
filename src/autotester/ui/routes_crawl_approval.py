"""The crawl-approval card on the credentials page (D-018 consent, gate 2).

Split from `routes_credentials.py` for the 300-line cap - a separate concept
(human consent for one bounded run) from value editing. This form is the
granting surface; `require_consent` in `stages/explore_consent.py` is the
runtime gate that reads what lands here.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from html import escape
from math import isfinite

from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from autotester.browser.secrets import SecretStore
from autotester.core.ids import SigningKeyMissing
from autotester.core.paths import ProjectPaths
from autotester.schema.approval import RunApproval
from autotester.schema.enums import ApprovalKind
from autotester.ui import theme
from autotester.ui.helpers import _load_project_or_404, _refuse_unsafe_submission

router = APIRouter()

def _crawl_approval_form(slug: str, target: str) -> str:
    """Human-readable counterpart to the CLI-only crawl approval command."""
    safe = escape(slug)
    form = (
        f"<p>This approval applies only to <code>{escape(target)}</code>.</p>"
        f"<form method='post' action='/projects/{safe}/crawl-approval'>"
        "<div class='field'><label>Signed by</label>"
        "<input name='granted_by' required placeholder='your name'></div>"
        "<div class='field'><label>Scope</label>"
        "<input name='scope' required placeholder='what this crawl may read and click'></div>"
        "<div class='field'><label>Expires at</label>"
        "<input type='datetime-local' name='expires_at' required></div>"
        "<div class='field'><label>UTC offset in minutes (auto-detected)</label>"
        "<input type='number' id='crawl-timezone-offset' name='timezone_offset_minutes' "
        "min='-840' max='840' value='0' required></div>"
        "<script>const expiry=document.querySelector(\"[name='expires_at']\");"
        "const offset=document.getElementById('crawl-timezone-offset');"
        "const syncOffset=()=>{const selected=new Date(expiry.value);"
        "if(!Number.isNaN(selected.valueOf()))offset.value="
        "String(-selected.getTimezoneOffset());};"
        "expiry.addEventListener('change',syncOffset);"
        "expiry.form.addEventListener('submit',syncOffset);</script>"
        "<div class='field'><label>Maximum actions</label>"
        "<input type='number' name='max_actions' min='1' value='200' required></div>"
        "<div class='field'><label>Wall clock (seconds)</label>"
        "<input type='number' name='wall_clock_s' min='1' step='any' value='600' required></div>"
        "<div class='field'><label>Note (optional)</label>"
        "<input name='note' placeholder='why this crawl is approved'></div>"
        "<button type='submit'>Save crawl approval</button></form>"
    )
    return f"<section id='crawl-approval'>{theme.card(form, title='Approve a crawl')}</section>"


def _in_force(approval: RunApproval, slug: str, target: str) -> bool:
    """What the consent gate would honour for this project's crawl ΓÇö never list
    more. Listing a grant the gate would refuse is a false reassurance, so this
    checks the same signature `core/consent.py` does (AT-110) — a card that
    still showed a forged or legacy-unsigned row as "in force" would be
    exactly that false reassurance in the one place a human actually looks."""
    if not (approval.project == slug and approval.run_kind is ApprovalKind.CRAWL
            and approval.target == target and approval.is_intact
            and not approval.is_expired(datetime.now(UTC))):
        return False
    try:
        return approval.is_signed_and_verified
    except SigningKeyMissing:
        return False  # fail closed: can't verify, don't claim it's in force


def _approvals_card(approvals: list[RunApproval], slug: str, target: str, saved: str,
                    existing: bool) -> str:
    """Confirmation plus the grants in force (AT-435). Saving used to redirect to an
    identical page, so a human clicked again and a duplicate grant was written.
    The banner is looked up ON DISK by id; the query string is never echoed."""
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
        f"<tr><td>{escape(a.granted_by)}</td><td>{escape(a.scope)}</td>"
        f"<td>{a.max_actions}</td><td>{a.wall_clock_s:g}s</td>"
        f"<td>{escape(a.expires_at)}</td><td><code>{escape(a.id)}</code></td></tr>"
        for a in active
    )
    table = (
        "<table><tr><th>Signed by</th><th>Scope</th><th>Max actions</th><th>Wall clock</th>"
        f"<th>Expires (UTC)</th><th>Id</th></tr>{rows}</table>" if active
        else "<p class='meta'>No crawl approval is in force for this target.</p>"
    )
    # Only crawl grants: a READ/ADVERSARIAL grant is none of "expired, edited or
    # for another target", so counting it gave a false reason (AT-452).
    crawl = [a for a in approvals if a.run_kind is ApprovalKind.CRAWL]
    others = len(crawl) - len(active)
    # "or project": `_in_force` also requires this project, so a grant naming
    # another one is counted here and needs a reason that is true of it (AT-455).
    note = (f"<p class='meta'>{others} more on file are expired, edited after granting, or for "
            "another target or project, and are not honoured.</p>" if others else "")
    return theme.card(banner + table + note, title="Approvals in force")


def _matching_grant(approvals: list[RunApproval], candidate: RunApproval) -> RunApproval | None:
    """An in-force grant identical to `candidate` in everything but when it was
    signed ΓÇö a repeated click, not a new decision."""
    def bounds(a: RunApproval) -> dict[str, object]:
        payload = a._bound_payload()
        payload.pop("granted_at")
        return {**payload, "note": a.note}

    return next((a for a in approvals if a.is_intact
                 and not a.is_expired(datetime.now(UTC)) and bounds(a) == bounds(candidate)),
                None)


def _approval_error(slug: str, detail: str) -> HTMLResponse:
    safe = escape(slug)
    body = theme.breadcrumb(
        ("Projects", "/"), (safe, f"/projects/{safe}"), ("Credentials", None),
    ) + "<h1>Crawl approval not saved</h1>" + theme.card(
        f"<p>{escape(detail)}</p><p><a class='btn' href='/projects/{safe}/env#crawl-approval'>"
        "Return to crawl approval</a></p>", title="Check the approval details",
    )
    return HTMLResponse(
        theme.page("Crawl approval not saved", body, active_slug=slug), status_code=400,
    )


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



@router.post("/projects/{slug}/crawl-approval")
def crawl_approval_submit(
    slug: str, granted_by: str = Form(""), scope: str = Form(""),
    expires_at: str = Form(""), max_actions: str = Form(""),
    wall_clock_s: str = Form(""), timezone_offset_minutes: str = Form("0"),
    note: str = Form(""),
) -> Response:
    """Persist one bounded approval; project and target always come from disk."""
    store, project = _load_project_or_404(slug)
    signer, allowed_scope = granted_by.strip(), scope.strip()
    try:
        if not signer or not allowed_scope:
            raise HTTPException(400, "crawl approval requires a signer and scope")
        secrets = SecretStore.load(project, ProjectPaths(slug).env_file, strict=False)
        _refuse_unsafe_submission([
            ("signer", signer), ("scope", allowed_scope), ("expiry", expires_at),
            ("maximum actions", max_actions), ("wall clock", wall_clock_s),
            ("timezone offset", timezone_offset_minutes), ("note", note),
        ], project, secrets)
        actions, seconds = int(max_actions), float(wall_clock_s)
        offset = int(timezone_offset_minutes)
        if actions <= 0 or seconds <= 0 or not isfinite(seconds):
            raise HTTPException(400, "crawl approval bounds must be positive")
        if not -840 <= offset <= 840:
            raise HTTPException(400, "timezone offset must be between -840 and 840 minutes")
        expiry = _future_iso(expires_at, offset)
    except ValueError:
        return _approval_error(slug, "crawl bounds must be numbers")
    except HTTPException as exc:
        return _approval_error(slug, str(exc.detail))
    now = datetime.now(UTC).isoformat()
    candidate = RunApproval(
        project=project.slug, run_kind=ApprovalKind.CRAWL, target=project.base_url,
        scope=allowed_scope, max_actions=actions, wall_clock_s=seconds,
        granted_by=signer, granted_at=now, expires_at=expiry,
        note=note.strip() or None,
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

