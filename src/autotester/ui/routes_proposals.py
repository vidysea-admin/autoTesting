"""Review a project's proposed test cases from the UI: list, approve, prune, single or bulk.
Contract: qa/contracts/failure-bundle.md (FB5, human pruning before provider spend).

The page is a thin face over the same functions `autotester expand --proposals/--approve/
--prune` calls (`stages.expand.stage_and_review`, `ProjectStore.list_case_proposals`); it
decides nothing itself. Proposals are content-addressed, so there is no title/step edit here
for the same reason the CLI has none: changed content is a fresh proposal needing fresh review.
Authorization is the central policy rows (`auth/policy.py`), `project.edit` like the FlowSpec gate.
"""

from __future__ import annotations

from html import escape

from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from autotester.browser.secrets import SecretStore
from autotester.core.paths import ProjectPaths
from autotester.schema.case import CaseProposal
from autotester.schema.enums import ReviewStatus
from autotester.stages import expand as expand_stage
from autotester.stages import review as review_stage
from autotester.ui import theme
from autotester.ui.helpers import _load_project_or_404, _refuse_unsafe_submission

router = APIRouter()


def _refusal(slug: str, title: str, message: str, status: int = 400) -> HTMLResponse:
    back = f"<a class='btn' href='/projects/{escape(slug)}/proposals'>Back to proposals</a>"
    body = theme.card(f"<p>{escape(message)}</p><p style='margin-top:14px'>{back}</p>",
                      title=title)
    return HTMLResponse(theme.page(title, body, active_slug=slug), status_code=status)


def _row(p: CaseProposal, flows: dict[str, tuple[str, str]]) -> str:
    name, screen = flows.get(p.flow_id, (p.flow_id, ""))
    tone = {"approved": "good", "pruned": "bad"}.get(p.status, "neutral")
    t, pid = escape(p.title), escape(p.id)
    buttons = (
        f"<button class='btn' type='submit' name='single' value='approve:{pid}' "
        f"aria-label='Approve {t}'>Approve</button> "
        f"<button class='btn' type='submit' name='single' value='prune:{pid}' "
        f"aria-label='Prune {t}'>Prune</button>")
    by = f" by {escape(p.reviewed_by)}" if p.reviewed_by else ""
    return (
        f"<tr><td><input type='checkbox' name='proposal_id' value='{pid}' "
        f"id='pick-{pid}' aria-label='Select {t}'></td>"
        f"<td>{escape(p.case_class.value)}</td>"
        f"<td><label for='pick-{pid}'>{t}</label></td>"
        f"<td>{escape(name)}<br><span class='hint'>{escape(screen)}</span></td>"
        f"<td>{escape(p.rationale)}</td>"
        f"<td>{theme.pill(p.status, tone)}{by}</td>"
        f"<td>{buttons}</td></tr>")


def _list_html(slug: str, rows: list[CaseProposal], flows: dict[str, tuple[str, str]]) -> str:
    table = (
        "<table class='step-table'><caption class='hint'>Proposed test cases</caption>"
        "<thead><tr><th scope='col'>Pick</th><th scope='col'>Kind</th>"
        "<th scope='col'>Title</th><th scope='col'>Flow / screen</th>"
        "<th scope='col'>Why proposed</th><th scope='col'>Status</th>"
        "<th scope='col'>Decide</th></tr></thead><tbody>"
        + "".join(_row(p, flows) for p in rows) + "</tbody></table>")
    controls = (
        "<div class='field'><label for='by'>Your name (signs the decision)</label>"
        "<input id='by' name='by' required></div>"
        "<button class='btn btn-primary' type='submit' name='decision' value='approve'>"
        "Approve selected</button> "
        "<button class='btn' type='submit' name='decision' value='prune'>Prune selected</button>"
        "<p class='hint'>The normal path (happy) cannot be pruned: it stays pending until "
        "approved. Only approved proposals ever reach a model call.</p>")
    return (f"<form method='post' action='/projects/{escape(slug)}/proposals/review'>"
            f"{table}{controls}</form>")


@router.get("/projects/{slug}/proposals", response_class=HTMLResponse)
def proposals_page(slug: str) -> str:
    store, project = _load_project_or_404(slug)
    crumbs = theme.breadcrumb(("Projects", "/"),
                              (escape(project.name), f"/projects/{escape(slug)}"),
                              ("Proposals", None))
    spec = store.load_flowspec()
    if spec is None or spec.review.status is not ReviewStatus.APPROVED:
        msg = ("<p>Proposed cases appear once the FlowSpec is approved.</p>"
               f"<a class='btn' href='/projects/{escape(slug)}/flowspec'>Review the FlowSpec</a>")
        return theme.page("Proposals", crumbs + "<h1>Proposed cases</h1>" + theme.card(msg),
                          active_slug=slug)
    fp = CaseProposal.fingerprint_for(spec)
    rows = [p for p in store.list_case_proposals() if p.spec_fingerprint == fp]
    flows = {f.id: (f.name, f.entry_screen) for f in spec.flows}
    stage = (f"<form method='post' action='/projects/{escape(slug)}/proposals/stage'>"
             "<button class='btn' type='submit'>Propose cases for review</button></form>")
    body = _list_html(slug, rows, flows) if rows else theme.empty_state(
        "?", "No proposals staged for this FlowSpec yet.", stage)
    return theme.page("Proposals", crumbs + "<h1>Proposed cases</h1>"
                      + theme.card(body, title="Review before any model call"), active_slug=slug)


@router.post("/projects/{slug}/proposals/stage")
def stage_proposals(slug: str) -> Response:
    store, _project = _load_project_or_404(slug)
    spec = store.load_flowspec()
    if spec is None:
        return _refusal(slug, "Nothing to propose", "There is no FlowSpec yet.")
    try:
        expand_stage.stage_and_review(store, spec, [], [], "")
    except (ValueError, review_stage.FlowSpecNotReviewed) as exc:
        return _refusal(slug, "Cannot propose cases", str(exc))
    return RedirectResponse(f"/projects/{slug}/proposals", status_code=303)


@router.post("/projects/{slug}/proposals/review")
def review_proposals(slug: str, by: str = Form(""), decision: str = Form(""),
                     single: str = Form(""),
                     proposal_id: list[str] = Form(default=[])) -> Response:  # noqa: B008
    """One decision for the ticked rows (bulk) or for one row's own button (single)."""
    store, project = _load_project_or_404(slug)
    if single:
        decision, _, only = single.partition(":")
        proposal_id = [only]
    if decision not in ("approve", "prune") or not proposal_id:
        return _refusal(slug, "Nothing to decide", "Pick at least one proposal and a decision.")
    if not by.strip():
        return _refusal(slug, "This review is not signed",
                        "A decision needs a name so the audit trail says who reviewed it.")
    secrets = SecretStore.load(project, ProjectPaths(slug).env_file, strict=False)
    try:
        _refuse_unsafe_submission([("name", by)], project, secrets)
    except HTTPException as exc:
        return _refusal(slug, "This review cannot be saved", str(exc.detail))
    spec = store.load_flowspec()
    if spec is None:
        return _refusal(slug, "Nothing to review", "There is no FlowSpec yet.")
    fp = CaseProposal.fingerprint_for(spec)
    known = {p.id for p in store.list_case_proposals() if p.spec_fingerprint == fp}
    if not set(proposal_id) <= known:   # check all first: a bulk request is all-or-nothing
        return _refusal(slug, "Proposal not found",
                        "A selected proposal is absent or belongs to an older FlowSpec.", 404)
    ids = list(dict.fromkeys(proposal_id))
    try:
        expand_stage.stage_and_review(
            store, spec, ids if decision == "approve" else [],
            ids if decision == "prune" else [], by.strip())
    except (ValueError, review_stage.FlowSpecNotReviewed) as exc:
        return _refusal(slug, "Cannot record the decision", str(exc))
    return RedirectResponse(f"/projects/{slug}/proposals", status_code=303)
