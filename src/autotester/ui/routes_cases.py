"""Create, list, rename and delete a project's test cases from the UI.
Contract: qa/contracts/ui.md (U1-U6).

AT-057: onboarding used to dead-end — a new project had zero cases, its Run
button was permanently disabled, and cases were creatable only from Python
(`ProjectStore.add_case`) or from `stages/expand.py` off a reviewed FlowSpec
that itself needs an ingested video. Neither is reachable by a non-technical
user, which made "onboard a product and test it without touching the CLI"
(T-100's own goal-task note) false in practice.

Plain server-rendered HTML with a fixed number of step rows — no JS framework
and no HTMX, per ui.md's no-fire list. Blank rows are ignored, so a one-step
smoke test costs one field.
"""

from __future__ import annotations

from html import escape
from typing import Any

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from autotester.browser.secrets import SecretStore
from autotester.core.paths import ProjectPaths
from autotester.schema.case import Case
from autotester.schema.enums import KIND_BY_CLASS, Action, CaseClass
from autotester.schema.flowspec import ExpectedState, Step
from autotester.schema.project import Project
from autotester.store.project_store import PinnedCaseError, ProjectStore
from autotester.ui import theme
from autotester.ui.case_form import (
    STEP_ROWS,
    _credential_datalist,
    _options,
    _step_row,
)
from autotester.ui.helpers import (
    _load_project_or_404,
    _refuse_unsafe_submission,
    _require_reachable_navigate_steps,
    _require_safe_id,
)

router = APIRouter()









@router.get("/projects/{slug}/cases/new", response_class=HTMLResponse)
def new_case_form(slug: str) -> str:
    _store, project = _load_project_or_404(slug)
    safe_slug = escape(slug)
    name = escape(project.name)

    rows = "".join(
        _step_row(i, Action.NAVIGATE.value if i == 0 else Action.CLICK.value,
                  project.base_url if i == 0 else "", bool(project.secrets))
        for i in range(STEP_ROWS)
    )
    table = (
        "<table class='step-table'><tr><th>#</th><th>Action</th><th>Target</th>"
        "<th>Value</th><th>Expect to see</th></tr>"
        f"{rows}</table>"
        f"{_credential_datalist(project)}"
        "<p class='hint'>Leave a row blank to skip it. A row counts if it has a target "
        "or a value.</p>"
        + ("<p class='hint'>For a password or any other credential, pick the saved "
           "<code>{{SECRET:KEY}}</code> from the value box rather than typing the real "
           "value — the real value is never stored in a test case.</p>"
           if project.secrets else "")
    )
    fields = (
        "<div class='field'><label for='title'>What are you checking?</label>"
        "<input id='title' name='title' required "
        "placeholder='Sign-in page loads and shows the login form'></div>"
        "<div class='field'><label for='case_class'>Kind of check</label>"
        f"<select id='case_class' name='case_class'>"
        f"{_options([c.value for c in CaseClass], CaseClass.HAPPY.value)}</select>"
        "<span class='hint'>happy = the normal path; the others are the worst/edge "
        "cases AutoTester grades against.</span></div>"
        f"{table}"
        "<button class='btn btn-primary' type='submit'>Add case</button>"
    )
    form = (
        f"<form method='post' action='/projects/{safe_slug}/cases'>{fields}</form>"
    )
    body = (
        theme.breadcrumb(("Projects", "/"), (name, f"/projects/{safe_slug}"),
                          ("New case", None))
        + "<h1>Add a case</h1>"
        "<p class='subtitle'>One falsifiable claim about the product — AutoTester runs "
        "these steps in a real browser and grades what it sees.</p>"
        f"{theme.card(form)}"
    )
    return theme.page("New case", body, active_slug=slug)


def _build_steps(
    actions: list[str], targets: list[str], values: list[str], expects: list[str]
) -> list[Step]:
    """Keep only rows a human actually filled in, renumbering from 1 so a skipped
    middle row never leaves a hole in `Step.order`."""
    steps: list[Step] = []
    for action, target, value, expect in zip(actions, targets, values, expects, strict=False):
        if not target.strip() and not value.strip():
            continue
        try:
            parsed = Action(action)
        except ValueError as exc:
            raise HTTPException(400, "that is not one of the offered step actions") from exc
        expected = (
            ExpectedState(visible_text=[expect.strip()]) if expect.strip()
            else ExpectedState()
        )
        steps.append(Step(
            order=len(steps) + 1, action=parsed, target=target.strip(),
            value=value.strip() or None, expected=expected,
        ))
    return steps



def _refuse_duplicate(store: ProjectStore, case: Case) -> None:
    """AT-060: `add_case` is idempotent on the content id, so a second case with
    identical steps was silently swallowed and the user redirected as if it had
    worked. Because `title` sits outside `compute_id`'s payload, that also made
    re-submitting the form the natural — and silently failing — way to fix a
    typo'd title. Say so, and point at the rename that does work."""
    if not store.has_case(case.id):
        return
    existing = store.get_case(case.id)
    existing_title = existing.title if existing else "an existing case"
    raise HTTPException(400, (
        f"this project already has a case with exactly these steps: "
        f"'{existing_title}'. Change a step to make it a different case, or rename "
        f"the existing one from the cases list."
    ))


def _guard_submitted_case(form: Any, project: Project, secrets: SecretStore) -> None:
    """Every user-supplied text of a case submission, labelled so a refusal can
    name the box it came from (AT-070/AT-071/AT-077)."""
    _refuse_unsafe_submission(
        [("the title", str(form.get("title", ""))),
         *[("a Target box", str(v)) for v in form.getlist("step_target")],
         *[("a Value box", str(v)) for v in form.getlist("step_value")],
         *[("an Expect box", str(v)) for v in form.getlist("step_expected")]],
        project, secrets,
    )


@router.post("/projects/{slug}/cases")
async def create_case(slug: str, request: Request) -> RedirectResponse:
    """Reads the raw form rather than declaring `list[str] = Form(...)` params:
    the step inputs are repeated fields, and `getlist` is the direct way to read
    them without a mutable default in the signature (ruff B008)."""
    store, project = _load_project_or_404(slug)
    secrets = SecretStore.load(project, ProjectPaths(slug).env_file, strict=False)
    form = await request.form()
    title = str(form.get("title", ""))
    case_class = str(form.get("case_class", ""))
    if not title.strip():
        raise HTTPException(400, "a case needs a title")
    try:
        parsed_class = CaseClass(case_class)
    except ValueError as exc:
        # AT-075: never echo raw form input -- a pasted credential would land
        # in the response body and the access log.
        raise HTTPException(400, "that is not one of the offered kinds of check") from exc

    _guard_submitted_case(form, project, secrets)
    steps = _build_steps(
        [str(v) for v in form.getlist("step_action")],
        [str(v) for v in form.getlist("step_target")],
        [str(v) for v in form.getlist("step_value")],
        [str(v) for v in form.getlist("step_expected")],
    )
    if not steps:
        raise HTTPException(400, "a case needs at least one step")
    _require_reachable_navigate_steps(steps, project)

    case = Case(
        project=slug,
        flow_id="manual",
        kind=KIND_BY_CLASS[parsed_class],
        case_class=parsed_class,
        title=title.strip(),
        # rationale is NOT provenance: `stages/run_case_pipeline.default_rubric`
        # feeds it to the grader verbatim as the claim to judge the evidence
        # against. An earlier version set "added by hand from the UI" here, and
        # the grader duly went looking for a UI-addition step and FAILed a case
        # whose screenshot plainly showed the very thing it asked for. Left
        # None so the rubric falls back to the user's own title; provenance
        # lives in flow_id="manual".
        rationale=None,
        steps=steps,
    )
    _refuse_duplicate(store, case)
    store.add_case(case)
    return RedirectResponse(f"/projects/{slug}/cases", status_code=303)


def _case_row(slug: str, case: Case) -> str:
    """One case: what it claims, how it is classified, and the two things a
    human needs to be able to do about it — rename and delete."""
    safe_id = escape(case.id)
    steps = len(case.steps)
    return (
        "<tr>"
        f"<td><form method='post' action='/projects/{slug}/cases/{safe_id}/rename' "
        "class='row-form'>"
        f"<input name='title' value='{escape(case.title)}' aria-label='Case title'>"
        "<button class='btn' type='submit'>Rename</button></form></td>"
        f"<td>{theme.pill(escape(case.case_class.value))}</td>"
        f"<td class='meta'>{steps} step{'s' if steps != 1 else ''}</td>"
        f"<td><form method='post' action='/projects/{slug}/cases/{safe_id}/delete'>"
        "<button class='btn btn-danger' type='submit'>Delete</button></form></td>"
        "</tr>"
    )


@router.get("/projects/{slug}/cases", response_class=HTMLResponse)
def cases_list(slug: str) -> str:
    """AT-060: cases existed only as a number on the project page — there was no
    way to see what a project actually checks, let alone fix a title or remove a
    case added by mistake."""
    store, project = _load_project_or_404(slug)
    safe_slug = escape(slug)
    name = escape(project.name)
    cases = store.list_cases()
    if cases:
        rows = "".join(_case_row(safe_slug, c) for c in cases)
        body_inner = (
            "<table><tr><th>Case</th><th>Class</th><th>Steps</th><th></th></tr>"
            f"{rows}</table>"
        )
    else:
        body_inner = theme.empty_state(
            "🧪", "No cases yet — this project cannot run until it has one.",
            f"<a class='btn btn-primary' href='/projects/{safe_slug}/cases/new'>"
            "+ Add the first case</a>",
        )
    body = (
        theme.breadcrumb(("Projects", "/"), (name, f"/projects/{safe_slug}"),
                          ("Cases", None))
        + "<h1>Cases</h1>"
        "<p class='subtitle'>Each one is a claim AutoTester checks in a real browser. "
        "Steps are what identify a case, so changing them means a new case.</p>"
        f"<div class='card-actions' style='margin-bottom:1.2rem'>"
        f"<a class='btn btn-primary' href='/projects/{safe_slug}/cases/new'>+ Add case</a>"
        "</div>"
        f"{theme.card(body_inner)}"
    )
    return theme.page("Cases", body, active_slug=slug)


@router.post("/projects/{slug}/cases/{case_id}/rename")
def rename_case(slug: str, case_id: str, title: str = Form(...)) -> RedirectResponse:
    """Title is deliberately outside `Case.compute_id()`, so renaming keeps the
    id — and with it every past run, verdict and rubric already attached."""
    store, project = _load_project_or_404(slug)
    _require_safe_id(case_id, "case id")
    if not title.strip():
        raise HTTPException(400, "a case needs a title")
    case = store.get_case(case_id)
    if case is None:
        raise HTTPException(404, f"no case '{case_id}'")
    secrets = SecretStore.load(project, ProjectPaths(slug).env_file, strict=False)
    _refuse_unsafe_submission([("the title", title)], project, secrets,
                               exempt={"the title": case.title})
    store.update_case(case.model_copy(update={"title": title.strip()}))
    return RedirectResponse(f"/projects/{slug}/cases", status_code=303)


@router.post("/projects/{slug}/cases/{case_id}/delete")
def delete_case(slug: str, case_id: str) -> RedirectResponse:
    """Past runs and verdicts are history and stay on disk — only the case
    itself stops being scheduled.

    AT-585: a pinned case refuses here with a 409, not a 404 — the case
    exists and was found, it is specifically protected from pruning."""
    store, _project = _load_project_or_404(slug)
    _require_safe_id(case_id, "case id")
    try:
        deleted = store.delete_case(case_id)
    except PinnedCaseError as exc:
        raise HTTPException(409, str(exc)) from exc
    if not deleted:
        raise HTTPException(404, f"no case '{case_id}'")
    return RedirectResponse(f"/projects/{slug}/cases", status_code=303)
