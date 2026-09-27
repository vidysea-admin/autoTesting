"""Run history, per-case screenshots, and portable downloads. Contract:
qa/contracts/ui-report.md UR1-UR4.
"""

from __future__ import annotations

from html import escape
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, HTMLResponse, Response
from starlette.background import BackgroundTask

from autotester.core.trace import read_spans
from autotester.schema.enums import EvidenceKind, Result
from autotester.schema.trace import LLMSpan, StageSpan
from autotester.stages.report_export import (
    export_excel,
    export_html,
    png_base64,
    valid_runs_newest_first,
)
from autotester.store.project_store import ProjectStore
from autotester.ui import theme
from autotester.ui.helpers import (
    _load_project_or_404,
    _require_safe_id,
    _reserved_temp_path,
)

router = APIRouter()


def _run_counts(store: ProjectStore, run_id: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for verdict in store.load_verdicts(run_id):
        counts[verdict.result.value] = counts.get(verdict.result.value, 0) + 1
    return counts


def _counts_stats(counts: dict[str, int]) -> str:
    return "<div class='stat-row'>" + "".join(
        theme.stat(str(v), theme.badge(escape(k))) for k, v in counts.items()
    ) + "</div>"


def _counts_badges(counts: dict[str, int]) -> str:
    """Compact inline pills (a run-history row) rather than full-size stat
    tiles — a stat tile's ~2rem number is meant for one page-level headline,
    not repeated once per row (that's what made the run-history table read
    as a wall of oversized, meaningless numbers)."""
    if not counts:
        return "<span class='meta'>no verdicts</span>"
    return "<div class='run-results'>" + "".join(
        theme.badge(escape(k), count=v) for k, v in counts.items()
    ) + "</div>"


def _run_date(store: ProjectStore, run_id: str) -> str:
    run = store.load_run(run_id)
    return escape(run.created_at.strftime("%Y-%m-%d %H:%M")) if run else ""


def _step_flow(run_dir: Path, evidence: list, case_index: int, trusted_root: Path) -> str:
    """The DFS-style trace Umesh asked for: the literal ordered sequence of
    screens THIS case actually walked through — never every hypothetical
    branch (that's the deferred, explicitly-descoped BFS/mindmap idea,
    qa/feedback-inbox.md). Each thumbnail links to a same-page CSS-only
    lightbox (`:target`) so the compact flow can still show full detail on
    click, no JS needed."""
    shots = sorted(
        (s for s in evidence if s.kind is EvidenceKind.SCREENSHOT),
        key=lambda s: s.step_order if s.step_order is not None else 10**9,
    )
    steps: list[str] = []
    lightboxes: list[str] = []
    for i, shot in enumerate(shots):
        data = png_base64(run_dir / shot.path, run_dir, trusted_root)
        if data is None:
            continue
        lb_id = f"lb-{case_index}-{i}"
        caption = escape(shot.label or shot.path)
        steps.append(
            f"<a class='flow-step' href='#{lb_id}'>"
            f"<span class='thumb'><img src='data:image/png;base64,{data}' loading='lazy'></span>"
            f"<span class='step-label'>{caption}</span></a>"
        )
        lightboxes.append(
            f"<a href='#' class='lightbox' id='{lb_id}'>"
            f"<img src='data:image/png;base64,{data}'>"
            f"<span class='lightbox-caption'>{caption}</span></a>"
        )
    if not steps:
        return "<p class='meta'>no screenshots captured</p>"
    arrow = "<span class='flow-arrow'>→</span>"
    return f"<div class='flow'>{arrow.join(steps)}</div>{''.join(lightboxes)}"


def _failure_list(failures: list) -> str:
    if not failures:
        return ""
    items = "".join(
        f"<li><code>{escape(f.criterion_id)}</code> — {escape(f.reason)}"
        + (f" <em>{escape(f.fix_hint)}</em>" if f.fix_hint else "") + "</li>"
        for f in failures
    )
    return f"<ul class='failure-list'>{items}</ul>"


def _trace_card(store: ProjectStore, run_id: str) -> str:
    """RT7: a read-only VIEW over `trace.jsonl` — per-stage time, and per-LLM
    -call latency/cost/model — never a second source of truth (core-invariants
    C6). A run with no trace yet (or one from before D-041) renders nothing."""
    spans = read_spans(store.paths.run_trace(run_id))
    stage_rows = "".join(
        f"<tr><td>{escape(s.stage.value)}</td><td>{escape(s.status)}</td>"
        f"<td>{s.duration_s:.2f}s</td></tr>"
        for s in spans if isinstance(s, StageSpan) and s.duration_s is not None
    )
    llm_rows = "".join(
        f"<tr><td>{escape(s.role)}</td><td>{escape(s.provider)}</td>"
        f"<td>{s.latency_s:.2f}s</td><td>${s.cost:.4f}</td></tr>"
        for s in spans if isinstance(s, LLMSpan)
    )
    if not stage_rows and not llm_rows:
        return ""
    body = ""
    if stage_rows:
        body += ("<table><tr><th>Stage</th><th>Status</th><th>Duration</th></tr>"
                  f"{stage_rows}</table>")
    if llm_rows:
        body += ("<table><tr><th>Role</th><th>Model</th><th>Latency</th><th>Cost</th></tr>"
                  f"{llm_rows}</table>")
    return theme.card(body, title="Trace")


def _unknown_run_page(slug: str, run_id: str) -> HTMLResponse:
    safe_slug = escape(slug)
    body = theme.breadcrumb(
        ("Projects", "/"), (safe_slug, f"/projects/{safe_slug}"),
        ("Report", f"/projects/{safe_slug}/report"), ("Run not found", None),
    ) + "<h1>Run not found</h1>" + theme.empty_state(
        "🔎", f"No completed run envelope exists for {escape(run_id)}.",
    )
    return HTMLResponse(theme.page("Run not found", body, active_slug=slug), status_code=404)


@router.get("/projects/{slug}/runs/{run_id}", response_class=HTMLResponse)
def run_view(slug: str, run_id: str) -> Response:
    store, _project = _load_project_or_404(slug)
    _require_safe_id(run_id, "run_id")
    if run_id not in {run.id for run in valid_runs_newest_first(store)}:
        return _unknown_run_page(slug, run_id)
    safe_slug = escape(slug)
    safe_run_id = escape(run_id)
    run_dir = store.paths.run_dir(run_id)
    cases = {c.id: c for c in store.list_cases()}
    verdicts = {v.case_id: v for v in store.load_verdicts(run_id)}
    results = store.load_results(run_id)
    counts = _run_counts(store, run_id)

    def _case_body(r, case_index: int) -> str:
        verdict = verdicts.get(r.case_id)
        meta = [f"<span class='meta'>{escape(r.outcome.value)}</span>"]
        if verdict:
            meta.append(theme.badge(escape(verdict.result.value)))
            if verdict.grader_provider:
                provider = escape(verdict.grader_provider)
                meta.append(f"<span class='meta'>judged by {provider}</span>")
        scoreboard = (
            f"<p class='scoreboard'>{escape(verdict.scoreboard)}</p>"
            if verdict and verdict.scoreboard else ""
        )
        failures = _failure_list(verdict.failures) if verdict else ""
        error = f"<p class='scoreboard'>{escape(r.error)}</p>" if r.error else ""
        return (
            f"<div class='case-meta'>{''.join(meta)}</div>{scoreboard}{failures}{error}"
            f"{_step_flow(run_dir, r.evidence, case_index, store.paths.dir)}"
        )

    sections = "".join(
        theme.card(_case_body(r, i), title=escape(cases[r.case_id].title if r.case_id in cases
                                                  else r.case_id))
        for i, r in enumerate(results)
    )
    body = (
        theme.breadcrumb(
            ("Projects", "/"), (safe_slug, f"/projects/{safe_slug}"),
            ("Report", f"/projects/{safe_slug}/report"), ("Run", None),
        )
        + f"<h1>Run <code>{safe_run_id}</code></h1>"
        + (_counts_stats(counts) if counts else "")
        + _trace_card(store, run_id)
        + (sections or theme.empty_state("📭", "No case results in this run yet."))
    )
    return theme.page(f"Run {safe_run_id}", body, active_slug=slug)


@router.get("/projects/{slug}/report", response_class=HTMLResponse)
def report(slug: str) -> str:
    store, _project = _load_project_or_404(slug)
    safe_slug = escape(slug)
    breadcrumb = theme.breadcrumb(
        ("Projects", "/"), (safe_slug, f"/projects/{safe_slug}"), ("Report", None),
    )
    runs = valid_runs_newest_first(store)
    if not runs:
        body = breadcrumb + "<h1>Report</h1>" + theme.empty_state(
            "📋", "no runs yet — run a case against this project to see a report here.",
        )
        return theme.page("Report", body, active_slug=slug)
    run_ids = [run.id for run in runs]
    latest = runs[0]
    safe_run_id = escape(latest.id)

    case_ids = set(latest.case_ids)
    passed = {v.case_id for v in store.load_verdicts(latest.id)
              if v.result is Result.PASS and v.case_id in case_ids}
    pass_rate = f"{round(100 * len(passed) / len(latest.case_ids))}%" if latest.case_ids else "—"
    cases = {case.id: case for case in store.list_cases()}
    flow_count = len({cases[case_id].flow_id for case_id in latest.case_ids if case_id in cases})
    overview = "<div class='stat-row'>" + "".join((
        theme.stat(str(len(run_ids)), "Total runs"),
        theme.stat(pass_rate, "Latest-run pass rate"),
        theme.stat(str(len(latest.case_ids)), f"cases covering {flow_count} distinct flows"),
    )) + "</div>"

    downloads = (
        f"<a class='btn' href='/projects/{safe_slug}/report.xlsx'>⬇ Download Excel</a> "
        f"<a class='btn' href='/projects/{safe_slug}/report.html'>⬇ Download HTML</a>"
    )
    history_rows = "".join(
        f"<tr><td><a href='/projects/{safe_slug}/runs/{escape(rid)}'><code>{escape(rid)}</code>"
        f"</a><br><span class='run-date'>{_run_date(store, rid)}</span></td>"
        f"<td>{_counts_badges(_run_counts(store, rid))}</td></tr>"
        for rid in run_ids
    )
    history = theme.card(
        f"<table><tr><th>Run</th><th>Results</th></tr>{history_rows}</table>", title="Run history"
    )
    body = (
        breadcrumb + "<h1>Report</h1>"
        f"<p class='subtitle'>Latest run <code>{safe_run_id}</code> · "
        f"<a href='/projects/{safe_slug}/runs/{safe_run_id}'>view case-by-case</a> · "
        f"{downloads}</p>"
        f"{overview}"
        f"{history}"
    )
    return theme.page(f"Report — {safe_slug}", body, active_slug=slug)


def _no_runs_page(slug: str) -> HTMLResponse:
    """A download link reached with nothing to export (AT-431). The report page
    hides the buttons when there are no runs, so this is a bookmarked or shared
    URL — it used to be a bare 500 from the exporter's uncaught ValueError."""
    safe_slug = escape(slug)
    body = theme.breadcrumb(
        ("Projects", "/"), (safe_slug, f"/projects/{safe_slug}"),
        ("Report", f"/projects/{safe_slug}/report"), ("No runs yet", None),
    ) + "<h1>No runs yet</h1>" + theme.empty_state(
        "📋", "There is nothing to download until this project has been run.",
    ) + f"<p><a href='/projects/{safe_slug}/report'>Back to the report</a></p>"
    return HTMLResponse(theme.page("No runs yet", body, active_slug=slug), status_code=404)


@router.get("/projects/{slug}/report.xlsx")
def download_report_excel(slug: str) -> Response:
    store, _project = _load_project_or_404(slug)
    if not valid_runs_newest_first(store):
        return _no_runs_page(slug)
    out = export_excel(slug, None, _reserved_temp_path(".xlsx"))
    return FileResponse(
        out, filename=f"{slug}-report.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        background=BackgroundTask(out.unlink, missing_ok=True),
    )


@router.get("/projects/{slug}/report.html")
def download_report_html(slug: str) -> Response:
    store, _project = _load_project_or_404(slug)
    if not valid_runs_newest_first(store):
        return _no_runs_page(slug)
    out = export_html(slug, None, _reserved_temp_path(".html"))
    return FileResponse(
        out, filename=f"{slug}-report.html", media_type="text/html",
        background=BackgroundTask(out.unlink, missing_ok=True),
    )
