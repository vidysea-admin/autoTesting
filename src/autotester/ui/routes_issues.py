"""Operator-facing video issue ledger and its human-compatible workbook.

AT-597: `stages/issues.py::pin_issue_as_case` (T-184/AT-585) had no human-
reachable caller. The pin form below is that caller for the UI — reusing the
existing case-steps editor (`ui/case_form.py`) and the same guards a hand-added
case gets (`ui/routes_cases.py::_build_steps`/`_refuse_duplicate`/
`_guard_submitted_case`, `ui/helpers.py::_require_reachable_navigate_steps`) —
so a pinned case can never carry a guessed or unreachable step. `cli_issues.py`
adds a second, scriptable entry point to the same constructor.
"""

from __future__ import annotations

from html import escape

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from starlette.background import BackgroundTask

from autotester.browser.secrets import SecretStore
from autotester.core.paths import ProjectPaths
from autotester.schema.enums import Action
from autotester.schema.issue import Issue
from autotester.stages.issues import (
    ISSUE_COLUMNS,
    export_issues_excel,
    issue_row,
    pin_issue_as_case,
    refuse_if_issue_already_pinned,
)
from autotester.store.project_store import PinnedCaseError, ProjectStore
from autotester.ui import theme
from autotester.ui.case_form import STEP_ROWS, _credential_datalist, _step_row
from autotester.ui.helpers import (
    _load_project_or_404,
    _require_reachable_navigate_steps,
    _require_safe_id,
    _reserved_temp_path,
)
from autotester.ui.routes_cases import _build_steps, _guard_submitted_case, _refuse_duplicate

router = APIRouter()


def _find_issue_or_404(store: ProjectStore, issue_id: str) -> Issue:
    issue = next((i for i in store.list_issues() if i.id == issue_id), None)
    if issue is None:
        raise HTTPException(404, f"no issue '{issue_id}'")
    return issue


def _issue_action_cell(slug: str, issue: Issue, pinned_issue_ids: set[str]) -> str:
    """The one thing a human can do about a finding beyond reading it: turn a
    confirmed bug into a case that runs every regression and cannot be pruned."""
    if issue.id in pinned_issue_ids:
        return f"<td>{theme.pill('pinned', tone='positive')}</td>"
    href = f"/projects/{escape(slug)}/issues/{escape(issue.id)}/pin"
    return f"<td><a class='btn' href='{href}'>Pin as regression case</a></td>"


@router.get("/projects/{slug}/issues", response_class=HTMLResponse)
def issues_page(slug: str) -> str:
    store, project = _load_project_or_404(slug)
    issues = store.list_issues()
    pinned_issue_ids = {c.pinned_issue_id for c in store.list_cases() if c.pinned_issue_id}
    name = escape(project.name)
    header = (
        "".join(f"<th>{escape(column)}</th>" for column in ISSUE_COLUMNS)
        + "<th>Regression</th>"
    )
    rows = "".join(
        "<tr>" + "".join(f"<td>{escape(str(cell))}</td>" for cell in issue_row(issue))
        + _issue_action_cell(slug, issue, pinned_issue_ids) + "</tr>"
        for issue in sorted(issues, key=lambda item: (item.recording_label, item.at_s))
    ) or f"<tr><td colspan='{len(ISSUE_COLUMNS) + 1}'>No video issues derived yet.</td></tr>"
    body = (
        theme.breadcrumb(("Projects", "/"), (name, f"/projects/{slug}"), ("Issues", None))
        + "<h1>Video issues</h1>"
        + f"<p class='subtitle'>{len(issues)} finding(s) · "
          f"<a class='btn' href='/projects/{escape(slug)}/issues.xlsx'>⬇ Download Excel</a></p>"
        + theme.card(
            f"<div style='overflow:auto'><table><thead><tr>{header}</tr></thead>"
            f"<tbody>{rows}</tbody></table></div>", title=f"{name} issues")
    )
    return theme.page(f"{name} · Issues", body, active_slug=slug)


@router.get("/projects/{slug}/issues.xlsx")
def download_issues(slug: str) -> FileResponse:
    store, _project = _load_project_or_404(slug)
    out = export_issues_excel(store.list_issues(), _reserved_temp_path(".xlsx"))
    return FileResponse(
        out, filename=f"{slug}-issues.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        background=BackgroundTask(out.unlink, missing_ok=True),
    )


@router.get("/projects/{slug}/issues/{issue_id}/pin", response_class=HTMLResponse)
def pin_issue_form(slug: str, issue_id: str) -> str:
    store, project = _load_project_or_404(slug)
    _require_safe_id(issue_id, "issue id")
    issue = _find_issue_or_404(store, issue_id)
    safe_slug = escape(slug)
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
        "<p class='hint'>These are the confirmed reproduction steps — AutoTester never "
        "guesses them from the finding's narrative. Leave a row blank to skip it; a row "
        "counts if it has a target or a value.</p>"
    )
    fields = (
        f"<p><strong>{escape(issue.title)}</strong></p>"
        f"<p class='subtitle'>{escape(issue.what_is_wrong)}</p>"
        f"{table}"
        "<button class='btn btn-primary' type='submit'>Pin as regression case</button>"
    )
    form = (
        f"<form method='post' action='/projects/{safe_slug}/issues/{escape(issue_id)}/pin'>"
        f"{fields}</form>"
    )
    body = (
        theme.breadcrumb(
            ("Projects", "/"), (escape(project.name), f"/projects/{safe_slug}"),
            ("Issues", f"/projects/{safe_slug}/issues"), ("Pin as regression case", None),
        )
        + "<h1>Pin as regression case</h1>"
        "<p class='subtitle'>Once pinned, this case runs in every future regression run and "
        "cannot be deleted — only use confirmed steps that actually reproduce the bug.</p>"
        + theme.card(form)
    )
    return theme.page("Pin as regression case", body, active_slug=slug)


@router.post("/projects/{slug}/issues/{issue_id}/pin")
async def pin_issue(slug: str, issue_id: str, request: Request) -> RedirectResponse:
    store, project = _load_project_or_404(slug)
    _require_safe_id(issue_id, "issue id")
    issue = _find_issue_or_404(store, issue_id)
    secrets = SecretStore.load(project, ProjectPaths(slug).env_file, strict=False)
    form = await request.form()
    _guard_submitted_case(form, project, secrets)
    steps = _build_steps(
        [str(v) for v in form.getlist("step_action")],
        [str(v) for v in form.getlist("step_target")],
        [str(v) for v in form.getlist("step_value")],
        [str(v) for v in form.getlist("step_expected")],
    )
    if not steps:
        raise HTTPException(400, "confirm at least one reproduction step before pinning")
    _require_reachable_navigate_steps(steps, project)
    case = pin_issue_as_case(issue, flow_id="manual", steps=steps, project=slug)
    try:
        refuse_if_issue_already_pinned(store, issue_id, case.id)
    except PinnedCaseError as exc:
        raise HTTPException(409, str(exc)) from exc
    _refuse_duplicate(store, case)
    store.add_case(case)
    return RedirectResponse(f"/projects/{slug}/cases", status_code=303)
