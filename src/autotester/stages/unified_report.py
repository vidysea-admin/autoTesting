"""The damage-control report's loaders and assembly (T-168, `damage-control-report.md` DC1-DC4).

One job — READ the five existing evidence owners and hand their output, unchanged, to one typed
`UnifiedReport`: the release record and its regression diff (`ProjectStore.load_release_record`,
T-167), first-party network evidence (T-170: run `RawResult.evidence`, crawl `list_crawl_network`),
the run's verdicts and cases (`report_export`'s own RE1/RE6 helpers), the persona's revisions
(`PortalPersona.history`, CR4) and the crawl's coverage rows (`crawl_report.crawl_summary`, DC1).
It computes no figure of its own (DC2): a missing input becomes `unavailable: <reason>`, never an
empty list that reads as clean (C12). The HTML is scrubbed with the project's `Redactor` last (DC4).
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from autotester.schema.crawl import Crawl
from autotester.schema.enums import CrawlStatus, EvidenceKind, Outcome
from autotester.schema.run import Evidence, RawResult
from autotester.schema.unified_report import (
    ApiFailure,
    ApiSection,
    CaseLine,
    CoverageSection,
    FailureLine,
    HistorySection,
    RegressionSection,
    RevisionLine,
    UnifiedReport,
    WorkflowSection,
)
from autotester.schema.verdict import Verdict
from autotester.stages.crawl_report import crawl_summary
from autotester.stages.explore_status import displayed_status
from autotester.stages.report_export import (
    _failure_rows,
    _load_redactor,
    _needs_developer_detail,
    _repro_steps,
    _run_sort_key,
    valid_runs_newest_first,
)
from autotester.stages.unified_report_render import render_html
from autotester.store.project_store import ProjectStore

_ROW = re.compile(r"^(?P<method>[A-Z]+) (?P<url>.+) -> (?P<status>-?\d+)$")


def _aware(moment: datetime) -> datetime:
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


def _pick_run(store: ProjectStore, run_id: str | None) -> str:
    """An explicit id, else the newest of the latest release record and the latest run."""
    slug = store.paths.slug
    if run_id:
        known = (store.load_release_record(run_id) or store.load_results(run_id)
                 or store.load_run(run_id))
        if not known:
            raise ValueError(f"no run '{run_id}' recorded for '{slug}'")
        return run_id
    found = [(_aware(r.scope.created_at), r.run_id) for r in store.list_release_records()]
    found += [(_run_sort_key(r)[0], r.id) for r in valid_runs_newest_first(store)]
    if not found:
        raise ValueError(f"no runs exist yet for '{slug}'")
    return max(found)[1]


def load_regression(store: ProjectStore, run_id: str) -> RegressionSection:
    """RR3/RR6: the stored release record's diff, flows and single issues log, as written."""
    record = store.load_release_record(run_id)
    if record is None:
        return RegressionSection(unavailable=(
            f"no release record for run {run_id} (a release is started with `autotester release`)"))
    return RegressionSection(
        release_run_id=record.run_id, git_sha=record.git_sha, finished=record.finished,
        flagged_bad=record.flagged_bad, flagged_reason=record.flagged_reason, diff=record.diff,
        flows=record.flows, issues=record.issues)


def _api_rows(source: str, evidence: Iterable[Evidence]) -> list[ApiFailure]:
    """NA1: each stored first-party NETWORK row that is not a success; an unreadable row is kept
    (status None), never dropped."""
    rows: list[ApiFailure] = []
    for item in evidence:
        if item.kind is not EvidenceKind.NETWORK:
            continue
        parsed = _ROW.match(item.path)
        status = int(parsed["status"]) if parsed else None
        if status is not None and 100 <= status < 400:
            continue
        rows.append(ApiFailure(
            source=source, method=parsed["method"] if parsed else None,
            url=parsed["url"] if parsed else None, status=status, raw=item.path))
    return rows


def load_api(store: ProjectStore, run_id: str, crawl_id: str | None) -> ApiSection:
    failures: list[ApiFailure] = []
    read: list[str] = []
    results = store.load_results(run_id)
    for result in results:
        failures += _api_rows(f"run:{result.case_id}", result.evidence)
    if results:
        read.append(f"run {run_id}")
    if crawl_id and store.paths.crawl_network(crawl_id).exists():
        failures += _api_rows(f"crawl:{crawl_id}", store.list_crawl_network(crawl_id))
        read.append(f"crawl {crawl_id}")
    if not read:
        return ApiSection(unavailable="no run results and no crawl network evidence are stored")
    return ApiSection(failures=failures, sources_read=read)


def _case_ids(store: ProjectStore, run_id: str) -> list[str]:
    record = store.load_release_record(run_id)
    run = store.load_run(run_id)
    ids = record.scope.case_ids if record else (run.case_ids if run else [])
    ids += [r.case_id for r in store.load_results(run_id)]
    ids += [v.case_id for v in store.load_verdicts(run_id)]
    return list(dict.fromkeys(ids))


def load_workflows(store: ProjectStore, run_id: str) -> WorkflowSection:
    """RE1/RE6: every case of the run, the grader's word on it, or honestly `not run`."""
    ids = _case_ids(store, run_id)
    if not ids:
        return WorkflowSection(run_id=run_id, unavailable=f"run {run_id} recorded no cases")
    cases = {c.id: c for c in store.list_cases()}
    raw = {r.case_id: r for r in store.load_results(run_id)}
    verdicts = {v.case_id: v for v in store.load_verdicts(run_id)}
    redactor = _load_redactor(store)
    lines = []
    for case_id in ids:
        case, result, verdict = cases.get(case_id), raw.get(case_id), verdicts.get(case_id)
        detail = _needs_developer_detail(verdict)
        lines.append(CaseLine(
            case_id=case_id, title=case.title if case else case_id,
            flow_id=case.flow_id if case else None, **_status(result, verdict),
            failures=[FailureLine(criterion_id=c, reason=r, fix_hint=h)
                      for c, r, h in _failure_rows(verdict)] if detail else [],
            repro_steps=_repro_steps(case, redactor) if detail else []))
    return WorkflowSection(run_id=run_id, cases=lines)


def _status(result: RawResult | None, verdict: Verdict | None) -> dict[str, str | None]:
    """The grader's result, else `not run` / `no verdict`; never a default PASS (C12)."""
    if verdict is not None:
        return {"result": verdict.result.value, "scoreboard": verdict.scoreboard,
                "outcome": result.outcome.value if result else None}
    if result is None or result.outcome is Outcome.NOT_RUN:
        return {"result": "not run", "outcome": result.outcome.value if result else None,
                "reason": (result.not_run_reason if result else None) or "no result recorded"}
    return {"result": "no verdict", "outcome": result.outcome.value,
            "reason": "executed but never graded"}


def load_history(store: ProjectStore) -> HistorySection:
    """CR4: the persona's own dated revisions with their counts, newest first."""
    persona = store.load_portal_persona()
    if persona is None:
        return HistorySection(unavailable="no portal persona is recorded (no crawl updated one)")
    if not persona.history:
        return HistorySection(unavailable="the portal persona has no recorded revisions yet")
    return HistorySection(revisions=[RevisionLine(revision=r, counts=r.counts())
                                     for r in reversed(persona.history)])


def _unreached(crawl: Crawl) -> list[tuple[str, str]]:
    cov = crawl.coverage
    if cov is None:
        return []
    rows = [(h.reason, f"{h.name or h.selector} @ {h.url_template}") for h in cov.holes]
    rows += [(h.reason, f"screen {h.url_template}") for h in cov.screens_not_entered]
    rows += [(f"permitted: {h.reason}", f"{h.name or h.selector} @ {h.url_template}")
             for h in cov.permitted_holes]
    return rows


def load_coverage(store: ProjectStore, crawl_id: str | None) -> CoverageSection:
    """DC1: the crawl page's own rows, verbatim, plus every control/screen it did not exercise."""
    crawl = store.load_crawl(crawl_id) if crawl_id else None
    if crawl is None:
        return CoverageSection(unavailable="no crawl is recorded for this project")
    cov = crawl.coverage
    complete = (displayed_status(crawl) is CrawlStatus.COMPLETED and cov is not None
                and not cov.error and not cov.holes and not cov.screens_not_entered
                and not crawl.skipped_unchanged)
    return CoverageSection(crawl_id=crawl.id, rows=crawl_summary(crawl),
                           unreached=_unreached(crawl), incomplete=not complete)


def build_report(store: ProjectStore, run_id: str | None = None) -> UnifiedReport:
    """One report for one run: raises `ValueError` when the project has no run at all."""
    rid = _pick_run(store, run_id)
    crawls = store.list_crawl_ids()
    crawl_id = crawls[0] if crawls else None
    return UnifiedReport(
        project=store.paths.slug, run_id=rid, regression=load_regression(store, rid),
        api=load_api(store, rid, crawl_id), workflows=load_workflows(store, rid),
        history=load_history(store), coverage=load_coverage(store, crawl_id))


def unified_html(store: ProjectStore, run_id: str | None = None) -> str:
    """The one artifact's text: rendered, then scrubbed of any declared secret value (DC4)."""
    return _load_redactor(store).scrub(render_html(build_report(store, run_id)))


def export_unified_html(project_slug: str, run_id: str | None, out_path: Path,
                        root: Path | None = None) -> Path:
    store = ProjectStore(project_slug, root)
    if store.load_project() is None:
        raise ValueError(f"no project '{project_slug}' yet")
    html = unified_html(store, run_id)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    return out_path
