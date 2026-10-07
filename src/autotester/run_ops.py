"""The three operations both machine surfaces expose -- run tests, get a report, get the catalog.

One job: be the single function the CLI (`cli_run.py`) and the MCP server (`mcp_server.py`)
both call, so neither re-implements a stage (C3). A run goes through `ui.routes_runs.run_project`,
the same function the Run button calls, and therefore through the same `RunApproval` gate (CN1).
Every string that leaves here has passed the project's `Redactor` (C5). Contract:
qa/contracts/cli-mcp.md CM1-CM5.
"""

from __future__ import annotations

from collections import Counter

from fastapi import HTTPException
from playwright.sync_api import Error as PlaywrightError

from autotester.browser.secrets import SecretStore
from autotester.core.consent import ApprovalRequired
from autotester.core.ids import SigningKeyMissing
from autotester.core.redact import Redactor
from autotester.providers.base import ProviderError
from autotester.schema.catalog import Catalog
from autotester.schema.cli_output import CaseOutcome, ExitCode, ReportStatus, RunReport
from autotester.schema.enums import EvidenceKind, Result
from autotester.stages.catalog import catalog
from autotester.stages.report_export import valid_runs_newest_first
from autotester.store.project_store import ProjectStore
from autotester.ui.helpers import _load_project_or_404
from autotester.ui.routes_runs import RunNotStarted, plan_project_run, run_project

_STATUS: dict[ExitCode, ReportStatus] = {
    ExitCode.OK: "passed", ExitCode.TEST_FAILED: "failed", ExitCode.USAGE: "usage_error",
    ExitCode.RUN_REFUSED: "refused", ExitCode.INFRASTRUCTURE: "infrastructure_error",
    ExitCode.INTERNAL: "internal_error",
}
# URL and DOM evidence carry the observed value itself, not a file path.
_VALUE_KINDS = frozenset({EvidenceKind.URL, EvidenceKind.DOM})


def exit_code_for(exc: BaseException) -> ExitCode:
    """The one place an exception becomes an exit code (CM1)."""
    if isinstance(exc, RunNotStarted):
        return exc.code
    if isinstance(exc, HTTPException):
        return ExitCode.USAGE
    if isinstance(exc, ApprovalRequired | SigningKeyMissing):
        return ExitCode.RUN_REFUSED
    if isinstance(exc, ProviderError | TimeoutError | OSError | PlaywrightError):
        return ExitCode.INFRASTRUCTURE
    return ExitCode.INTERNAL


def _redactor(project: str) -> Redactor:
    store = ProjectStore(project)
    try:
        loaded = store.load_project()
    except (ValueError, OSError):
        loaded = None
    if loaded is None:
        return Redactor({})
    return SecretStore.load(loaded, store.paths.env_file, strict=False).redactor()


def _scrubbed(report: RunReport) -> RunReport:
    """The last stop before stdout: re-validate the report with every string scrubbed (C5)."""
    clean = _redactor(report.project).scrub_obj(report.model_dump(mode="json"))
    return RunReport.model_validate(clean)


def error_report(project: str, exc: BaseException, *, dry_run: bool = False) -> RunReport:
    code = exit_code_for(exc)
    detail = exc.detail if isinstance(exc, HTTPException) else f"{type(exc).__name__}: {exc}"
    return _scrubbed(RunReport(project=project, status=_STATUS[code], exit_code=int(code),
                               dry_run=dry_run, message=str(detail)))


def _case_outcomes(store: ProjectStore, run_id: str, case_ids: list[str]) -> list[CaseOutcome]:
    titles = {c.id: c.title for c in store.list_cases()}
    results = {r.case_id: r for r in store.load_results(run_id)}
    verdicts = {v.case_id: v for v in store.load_verdicts(run_id)}
    rows = []
    for case_id in dict.fromkeys([*case_ids, *results]):
        result, verdict = results.get(case_id), verdicts.get(case_id)
        rows.append(CaseOutcome(
            case_id=case_id, title=titles.get(case_id, ""),
            outcome=result.outcome if result else None,
            result=verdict.result if verdict else None,
            failures=[f"{f.criterion_id}: {f.reason}" for f in verdict.failures] if verdict else [],
            evidence_paths=[e.path for e in result.evidence if e.kind not in _VALUE_KINDS]
            if result else []))
    return rows


def build_report(store: ProjectStore, run_id: str) -> RunReport:
    """A stored run as the CM2 document. A case no grader judged is NOT_GRADED, never PASS."""
    run = store.load_run(run_id)
    if run is None:
        raise RunNotStarted(404, f"no run '{run_id}' for '{store.paths.slug}'", ExitCode.USAGE)
    cases = _case_outcomes(store, run_id, run.case_ids)
    counts = Counter(c.result.value if c.result else "NOT_GRADED" for c in cases)
    passed = bool(cases) and set(counts) == {Result.PASS.value}
    code = ExitCode.OK if passed else ExitCode.TEST_FAILED
    return _scrubbed(RunReport(
        project=store.paths.slug, status=_STATUS[code], exit_code=int(code), run_id=run_id,
        cases=cases, counts=dict(counts)))


def perform_run(project: str, dry_run: bool = False) -> RunReport:
    """Run (or only plan, with `dry_run`) a project's cases. Never raises: a failure is a report."""
    try:
        if dry_run:
            ids = plan_project_run(project)
            return _scrubbed(RunReport(
                project=project, status="dry_run", exit_code=int(ExitCode.OK), dry_run=True,
                planned_case_ids=ids, message=f"{len(ids)} case(s) would run"))
        run = run_project(project)
        return build_report(ProjectStore(project), run.id)
    except Exception as exc:
        return error_report(project, exc, dry_run=dry_run)


def get_report(project: str, run_id: str | None = None) -> RunReport:
    """The stored report for `run_id`, or the project's latest run. Never raises."""
    try:
        _load_project_or_404(project)
        store = ProjectStore(project)
        if run_id is None:
            runs = valid_runs_newest_first(store)
            if not runs:
                raise RunNotStarted(404, f"no runs exist yet for '{project}'", ExitCode.USAGE)
            run_id = runs[0].id
        return build_report(store, run_id)
    except Exception as exc:
        return error_report(project, exc)


def get_catalog(project: str) -> Catalog:
    """The project's catalog (pure; CT1). Raises `HTTPException` 404 for an unknown project."""
    store, loaded = _load_project_or_404(project)
    return catalog(loaded, store.load_flowspec(), store)
