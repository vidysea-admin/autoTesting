"""The three operations both machine surfaces expose -- run tests, get a report, get the catalog.

One job: be the single function set the CLI (`cli_run.py`) and the MCP server (`mcp_server.py`)
both call, so neither re-implements a stage (C3). A run is `stages.run_launcher.launch_run`, the
same launcher the Run button, the queue worker and the scheduler reach, and therefore the same
`RunApproval` gate (CN1/CN9): there is no parameter here that can grant or skip it. A dry run
only reads. Every string that leaves here has passed the project's `Redactor` (C5). Contract:
qa/contracts/cli-mcp.md CM1-CM5.
"""

from __future__ import annotations

import re
from collections import Counter

from playwright.sync_api import Error as PlaywrightError

from autotester.browser.secrets import parse_env
from autotester.core.consent import ApprovalRequired
from autotester.core.ids import SigningKeyMissing
from autotester.core.paths import SLUG_PATTERN, ProjectPaths
from autotester.core.redact import Redactor
from autotester.providers.base import ProviderError
from autotester.schema.catalog import TIER_BY_CLASS, Catalog
from autotester.schema.cli_output import CaseOutcome, ExitCode, ReportStatus, RunReport
from autotester.schema.enums import EvidenceKind, Result, Trigger
from autotester.schema.project import Project
from autotester.stages.catalog import catalog, tiers_to_run
from autotester.stages.report_export import valid_runs_newest_first
from autotester.stages.run_launcher import DEFAULT_SEAMS, LaunchRefused, RunSeams, launch_run
from autotester.store.project_store import ProjectStore

RUN_SEAMS: RunSeams = DEFAULT_SEAMS
"""The launcher's collaborators for a machine-surface run; looked up at call time."""

_STATUS: dict[ExitCode, ReportStatus] = {
    ExitCode.OK: "passed", ExitCode.TEST_FAILED: "failed", ExitCode.USAGE: "usage_error",
    ExitCode.RUN_REFUSED: "refused", ExitCode.INFRASTRUCTURE: "infrastructure_error",
    ExitCode.INTERNAL: "internal_error",
}
# URL and DOM evidence carry the observed value itself, not a file path.
_VALUE_KINDS = frozenset({EvidenceKind.URL, EvidenceKind.DOM})
_REFUSED_BY_GATE = 403


def exit_code_for(exc: BaseException) -> ExitCode:
    """The one place an exception becomes an exit code (CM1)."""
    if isinstance(exc, LaunchRefused):
        return ExitCode.RUN_REFUSED if exc.status == _REFUSED_BY_GATE else ExitCode.USAGE
    if isinstance(exc, ApprovalRequired | SigningKeyMissing):
        return ExitCode.RUN_REFUSED
    if isinstance(exc, ValueError):
        return ExitCode.USAGE
    if isinstance(exc, ProviderError | TimeoutError | OSError | PlaywrightError):
        return ExitCode.INFRASTRUCTURE
    return ExitCode.INTERNAL


def _redactor(project: str) -> Redactor:
    """Mask root credentials even when the project cannot be deserialized."""
    path = ProjectPaths(project).env_file
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    return Redactor(parse_env(text))


def _scrubbed(report: RunReport) -> RunReport:
    """The last stop before stdout: re-validate the report with every string scrubbed (C5)."""
    try:
        clean = _redactor(report.project).scrub_obj(report.model_dump(mode="json"))
        # This Literal is controlled public vocabulary, not input-derived free text.
        clean["status"] = report.status
        return RunReport.model_validate(clean)
    except (OSError, UnicodeError, ValueError):
        # No masking source means no attacker-controlled string may leave.
        code = report.exit_code or int(ExitCode.INFRASTRUCTURE)
        status = report.status if report.exit_code else _STATUS[ExitCode.INFRASTRUCTURE]
        return RunReport(project="[unavailable]", status=status,
                         exit_code=code, dry_run=report.dry_run,
                         message="Output withheld: credential masking unavailable.")


def error_report(project: str, exc: BaseException, *, dry_run: bool = False) -> RunReport:
    code = exit_code_for(exc)
    detail = exc.reason if isinstance(exc, LaunchRefused) else f"{type(exc).__name__}: {exc}"
    return _scrubbed(RunReport(project=project, status=_STATUS[code], exit_code=int(code),
                               dry_run=dry_run, message=str(detail)))


def _open(project: str) -> tuple[ProjectStore, Project]:
    """A valid slug's store and project, else the launcher's own refusal (400 / 404)."""
    if not re.fullmatch(SLUG_PATTERN, project):
        raise LaunchRefused(400, "invalid project slug")
    store = ProjectStore(project)
    loaded = store.load_project()
    if loaded is None:
        raise LaunchRefused(404, f"no project '{project}'")
    return store, loaded


def plan_run(project: str) -> list[str]:
    """T-174 CM3: the case ids a run WOULD execute, tier by tier. Reads only -- no approval
    is checked or minted, no provider is built, no browser opens, nothing is written."""
    store, loaded = _open(project)
    cases = store.list_cases()
    if not cases:
        raise LaunchRefused(400, f"project '{project}' has no cases to run")
    cat = catalog(loaded, store.load_flowspec(), store)
    return [c.id for tier in tiers_to_run(cat) for c in cases
            if TIER_BY_CLASS[c.case_class] == tier]


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


def stored_run_report(store: ProjectStore, run_id: str) -> RunReport:
    """A stored run as the CM2 document. A case no grader judged is NOT_GRADED, never PASS."""
    run = store.load_run(run_id)
    if run is None:
        raise LaunchRefused(404, f"no run '{run_id}' for '{store.paths.slug}'")
    cases = _case_outcomes(store, run_id, run.case_ids)
    counts = Counter(c.result.value if c.result else "NOT_GRADED" for c in cases)
    passed = bool(cases) and set(counts) == {Result.PASS.value}
    code = ExitCode.OK if passed else ExitCode.TEST_FAILED
    return _scrubbed(RunReport(
        project=store.paths.slug, status=_STATUS[code], exit_code=int(code), run_id=run_id,
        cases=cases, counts=dict(counts)))


def perform_run(project: str, dry_run: bool = False, *, requested_by: str = "cli") -> RunReport:
    """Run (or only plan, with `dry_run`) a project's cases. Never raises: a failure is a report."""
    try:
        if dry_run:
            ids = plan_run(project)
            return _scrubbed(RunReport(
                project=project, status="dry_run", exit_code=int(ExitCode.OK), dry_run=True,
                planned_case_ids=ids, message=f"{len(ids)} case(s) would run"))
        run = launch_run(project, trigger=Trigger.CI, requested_by=requested_by, seams=RUN_SEAMS)
        return stored_run_report(ProjectStore(project), run.id)
    except Exception as exc:
        return error_report(project, exc, dry_run=dry_run)


def get_report(project: str, run_id: str | None = None) -> RunReport:
    """The stored report for `run_id`, or the project's latest run. Never raises."""
    try:
        store, _ = _open(project)
        if run_id is None:
            runs = valid_runs_newest_first(store)
            if not runs:
                raise LaunchRefused(404, f"no runs exist yet for '{project}'")
            run_id = runs[0].id
        return stored_run_report(store, run_id)
    except Exception as exc:
        return error_report(project, exc)


def get_catalog(project: str) -> Catalog | RunReport:
    """Read a catalog or return the same typed, scrubbed error as the other tools."""
    try:
        store, loaded = _open(project)
        result = catalog(loaded, store.load_flowspec(), store)
        clean = _redactor(project).scrub_obj(result.model_dump(mode="json"))
        return Catalog.model_validate(clean)
    except Exception as exc:
        return error_report(project, exc)
