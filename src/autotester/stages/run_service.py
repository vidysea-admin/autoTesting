"""Run / report / catalog as plain functions for the CLI and the MCP server (T-174, CM1-CM4).

One job: turn the existing `launch_run`, the stored run artifacts and `catalog()` into the typed
`RegressionReport` / `Catalog` a machine reads, mapping every outcome onto one `ExitCode`. The CLI
(`cli_run.py`) and the MCP adapter (`mcp_server.py`) both call these and nothing else, so neither
holds a second implementation of a stage (C3). Nothing here raises: a failure is a report.

A dry run lists what would run and touches nothing: no approval row is minted, no run directory
made, no provider or browser built. It is not a route around the consent gate -- a real run still
goes through `launch_run`, which re-checks the `RunApproval` itself.
"""

from __future__ import annotations

import re
from collections import Counter
from urllib.parse import urlsplit

from autotester.core.exit_codes import ExitCode
from autotester.core.safe_names import SLUG_PATTERN
from autotester.providers.base import ProviderError
from autotester.schema.case import Case
from autotester.schema.catalog import Catalog
from autotester.schema.cli_output import CaseReport, RegressionReport
from autotester.schema.enums import CaseStatus, EvidenceKind, Outcome, Result
from autotester.schema.run import RawResult
from autotester.schema.verdict import Verdict
from autotester.stages.catalog import catalog
from autotester.stages.report_export import _latest_run_id, _load_redactor
from autotester.stages.run_launcher import DEFAULT_SEAMS, LaunchRefused, launch_run
from autotester.store.project_store import ProjectStore

_STATUS = {ExitCode.OK: "passed", ExitCode.TEST_FAILED: "failed", ExitCode.USAGE: "usage",
           ExitCode.REFUSED: "refused", ExitCode.INFRA: "infra", ExitCode.INTERNAL: "internal",
           ExitCode.INCONCLUSIVE: "inconclusive"}
_INLINE_KINDS = {EvidenceKind.URL, EvidenceKind.DOM}   # `path` holds the value, not a file


_PLAIN_HOST = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?(?::\d{1,5})?")
_PLAIN_SEGMENT = re.compile(r"[a-z-]{1,32}")


def _pasteable(url: str) -> frozenset[str]:
    """The base_url stays readable in the hint only when ALL hold (a positive allowlist, C5):
    `urlsplit` succeeds; scheme is http or https; the URL is pure ASCII with no whitespace or
    control character and no `;`, `?` or `#`; the netloc is a plain host[:port] (no userinfo, no
    `%`, no brackets); and the path is empty, `/`, or segments that each match `[a-z-]{1,32}`
    (lowercase letters and hyphens: no digits, `%`, dots or colons). Anything else, or a
    ValueError from the parser, exempts nothing, so the `.env` match masks it as before."""
    if not url.isascii() or not all("!" <= c <= "~" for c in url) or set(url) & set(";?#"):
        return frozenset()
    try:
        parts = urlsplit(url)
    except ValueError:
        return frozenset()
    if parts.scheme not in ("http", "https") or not _PLAIN_HOST.fullmatch(parts.netloc):
        return frozenset()
    path = parts.path.removesuffix("/")
    if path and not all(_PLAIN_SEGMENT.fullmatch(seg) for seg in path.removeprefix("/").split("/")):
        return frozenset()
    return frozenset({url})


def _report(store: ProjectStore | None, project: str, code: ExitCode, **fields) -> RegressionReport:
    """Build and scrub: every string passes the project's `Redactor` before it leaves (C5)."""
    report = RegressionReport(project=project, exit_code=int(code),
                       **{"status": _STATUS[code], **fields})
    if store is None or (proj := store.load_project()) is None:
        return report
    scrubbed = _load_redactor(store).scrub_obj(report.model_dump(mode="json"))
    if report.message:  # the grant hint's --target is the project's own stored base_url (already
        # plain in project.json): keep it pasteable even when it equals a .env login URL, but
        # only if that URL carries no credential (userinfo/query/fragment): checker B B1
        scrubbed["message"] = _load_redactor(store, _pasteable(proj.base_url)).scrub(
            report.message)
    return RegressionReport.model_validate(scrubbed)


def _open(slug: str) -> tuple[ProjectStore | None, str | None]:
    if not re.fullmatch(SLUG_PATTERN, slug):
        return None, "invalid project slug"
    store = ProjectStore(slug)
    return (store, None) if store.load_project() is not None else (None, f"no project '{slug}'")


def _runnable(store: ProjectStore) -> list[Case]:
    return [c for c in store.list_cases() if c.status is not CaseStatus.RETIRED]


def plan_dry_run(slug: str) -> RegressionReport:
    """What `run` would execute, with nothing started and nothing written."""
    store, why = _open(slug)
    if store is None:
        return _report(None, slug, ExitCode.USAGE, message=why, dry_run=True)
    cases = _runnable(store)
    if not cases:
        return _report(store, slug, ExitCode.USAGE, dry_run=True,
                       message=f"project '{slug}' has no cases to run")
    return _report(store, slug, ExitCode.OK, dry_run=True, status="dry_run",
                   message=f"would run {len(cases)} case(s); no approval checked, nothing started",
                   case_ids=[c.id for c in cases])


def _case_report(result: RawResult, verdict: Verdict | None) -> CaseReport:
    return CaseReport(
        case_id=result.case_id, outcome=result.outcome, error=result.error,
        result=verdict.result if verdict else None,
        scoreboard=verdict.scoreboard if verdict else "",
        evidence_paths=[e.path for e in result.evidence if e.kind not in _INLINE_KINDS])


def report_for(slug: str, run_id: str | None = None) -> RegressionReport:
    """The stored, redacted report of one run (the latest when `run_id` is None)."""
    store, why = _open(slug)
    if store is None:
        return _report(None, slug, ExitCode.USAGE, message=why)
    try:
        run_id = run_id or _latest_run_id(store)
    except ValueError as exc:
        return _report(store, slug, ExitCode.USAGE, message=str(exc))
    if store.load_run(run_id) is None:
        return _report(store, slug, ExitCode.USAGE, message=f"no run '{run_id}' for '{slug}'")
    verdicts = {v.case_id: v for v in store.load_verdicts(run_id)}
    cases = [_case_report(r, verdicts.get(r.case_id)) for r in store.load_results(run_id)]
    counts = dict(Counter(v.result.value for v in verdicts.values()))
    code, message = _headline(cases, counts)
    return _report(store, slug, code, run_id=run_id, message=message,
                   case_ids=[c.case_id for c in cases], verdict_counts=counts, cases=cases)


_UNRUN = (Outcome.ERRORED, Outcome.NOT_RUN)


def _headline(cases: list[CaseReport], counts: dict[str, int]) -> tuple[ExitCode, str | None]:
    """The ONE rule for a run's headline and exit code. `passed` needs at least one case and
    every case judged PASS: a FAIL is `failed`; anything else short of PASS (INCONCLUSIVE,
    BLOCKED, errored or not-run executor outcome, no verdict) is `inconclusive`, never green."""
    if counts.get(Result.FAIL.value, 0) > 0:
        return ExitCode.TEST_FAILED, None
    unjudged = [c for c in cases if c.result is not Result.PASS or c.outcome in _UNRUN]
    if cases and not unjudged:
        return ExitCode.OK, None
    if not cases:
        return ExitCode.INCONCLUSIVE, "no case was judged: the run produced no results"
    parts = [f"{n} {label}" for n, label in (
        (sum(c.outcome in _UNRUN for c in cases), "errored or not run"),
        (sum(c.result is Result.INCONCLUSIVE for c in cases), "inconclusive"),
        (sum(c.result is Result.BLOCKED for c in cases), "blocked"),
        (sum(c.result is None for c in cases), "without a verdict")) if n]
    return ExitCode.INCONCLUSIVE, (f"{len(unjudged)} of {len(cases)} case(s) not judged PASS ("
                                   + ", ".join(parts) + "): not a pass")


def run_regression(slug: str) -> RegressionReport:
    """Run the project through the one launcher (every gate inside it) and report the run."""
    if (probe := _open(slug))[0] is None:
        return _report(None, slug, ExitCode.USAGE, message=probe[1])
    try:
        launched = launch_run(slug, seams=DEFAULT_SEAMS)
    except LaunchRefused as exc:
        code = ExitCode.REFUSED if exc.status == 403 else ExitCode.USAGE
        return _report(probe[0], slug, code, message=exc.reason)
    except (ProviderError, TimeoutError, OSError) as exc:
        return _report(probe[0], slug, ExitCode.INFRA, message=f"{type(exc).__name__}: {exc}")
    except Exception as exc:    # an AutoTester bug is still a report with its own code
        return _report(probe[0], slug, ExitCode.INTERNAL, message=f"{type(exc).__name__}: {exc}")
    return report_for(slug, launched.id)


def catalog_for(slug: str) -> Catalog | RegressionReport:
    """The project's test catalog, or the usage report saying why there is none."""
    store, why = _open(slug)
    if store is None:
        return _report(None, slug, ExitCode.USAGE, message=why)
    project = store.load_project()
    assert project is not None
    return catalog(project, store.load_flowspec(), store)
