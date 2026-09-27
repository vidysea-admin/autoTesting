"""The explorer, on screen: crawl history, one crawl's screen graph, its
Excel export, and the two buttons that start a crawl or fold it into the
FlowSpec (Track B5).

Before this, `autotester explore` wrote a graph to disk that nothing rendered.
Contract: qa/contracts/explore.md (X11 artifacts are human-readable) +
qa/contracts/ui.md.
"""

from __future__ import annotations

import logging
from html import escape
from math import isfinite

from fastapi import APIRouter, Form
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from starlette.background import BackgroundTask

from autotester.browser.secrets import SecretStore
from autotester.core.ids import run_id
from autotester.core.paths import ProjectPaths
from autotester.core.redact import Redactor
from autotester.schema.crawl import Crawl, CrawlBounds
from autotester.schema.enums import IssueKind
from autotester.schema.flowspec import FlowSpec
from autotester.schema.screen_graph import ScreenNode
from autotester.stages.coverage import diff_crawl, queue_requests, unreached_screens
from autotester.stages.crawl_report import export_crawl_excel
from autotester.stages.explore_merge import merge_screens
from autotester.stages.explore_status import displayed_status, is_success
from autotester.stages.merge_flowspec import resolve_requests
from autotester.store.project_store import ProjectStore
from autotester.ui import crawl_view, theme
from autotester.ui.helpers import _load_project_or_404, _require_safe_id, _reserved_temp_path
from autotester.ui.routes_crawl_login import login_card

router = APIRouter()
logger = logging.getLogger(__name__)

_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _crawl_error(slug: str, status: int, title: str, detail: str) -> HTMLResponse:
    safe = escape(slug)
    detail = detail.split("Grant one with:", 1)[0].strip()
    action = (
        f"<p><a class='btn' href='/projects/{safe}/env#crawl-approval'>"
        "Review credentials and approve crawl</a></p>"
    )
    body = _crumbs(slug) + f"<h1>{escape(title)}</h1>" + theme.card(
        f"<p>{escape(detail)}</p>{action}", title="Crawl not started",
    )
    return HTMLResponse(theme.page(escape(title), body, active_slug=slug), status_code=status)


def _parse_bounds(values: tuple[str, str, str, str]) -> CrawlBounds:
    try:
        screens, actions, seconds, depth = (
            int(values[0]), int(values[1]), float(values[2]), int(values[3])
        )
    except ValueError:
        raise ValueError("all crawl bounds must be numbers") from None
    if screens <= 0 or actions <= 0 or seconds <= 0 or depth <= 0 or not isfinite(seconds):
        raise ValueError("all crawl bounds must be positive")
    return CrawlBounds(max_screens=screens, max_actions=actions,
                       wall_clock_s=seconds, max_depth=depth)


def _load_flowspec_safe(store: ProjectStore) -> tuple[FlowSpec | None, str | None]:
    """AT-477: `load_flowspec` raises on a broken flowspec.json. Both crawl
    routes need the spec only to render or compare coverage against, so a
    read failure here is RECORDED, not propagated -- the same trade-off
    AT-472 already made for the crawl record via crawl_coverage.of_run."""
    try:
        return store.load_flowspec(), None
    except ValueError as exc:
        return None, f"the FlowSpec could not be read -- {type(exc).__name__}: {exc}"


def _queue_coverage_gap(store: ProjectStore, crawl: Crawl, redactor: Redactor) -> None:
    """AT-240: fold a finished crawl's screen gap into an open request. AT-477:
    the crawl already ran and saved by the time this runs, so a broken
    flowspec.json must not turn that into a 500 that hides the crawl's result.
    AT-593: log the read failure (scrubbed via redactor) instead of discarding it silently."""
    spec, spec_error = _load_flowspec_safe(store)
    if spec_error is not None:
        logger.warning("coverage gap not queued for %s: %s", crawl.id, redactor.scrub(spec_error))
    if spec is not None:
        queue_requests(store, diff_crawl(spec, store.list_nodes(crawl.id)))


def _coverage_card(
    store: ProjectStore, safe: str, safe_id: str, nodes: list[ScreenNode], redactor: Redactor,
) -> str:
    """AT-477: a broken flowspec.json must render as a stated read failure,
    not a 500 -- same trade-off AT-472 made for the crawl record. AT-608:
    pydantic echoes `input_value=...` in its own error text, so a declared
    secret pasted into flowspec.json reaches this rendered card unless it is
    scrubbed first -- the same `Redactor.scrub` call `_queue_coverage_gap`
    already makes for the log line covering this identical read failure."""
    spec, spec_error = _load_flowspec_safe(store)
    if spec_error is not None:
        return theme.card(
            f"<p class='meta'>{escape(redactor.scrub(spec_error))}</p>",
            title="Against the FlowSpec",
        )
    if spec is not None:
        return theme.card(
            crawl_view.review_line(spec)
            + crawl_view.coverage_card(diff_crawl(spec, nodes), unreached_screens(spec, nodes))
            + f"<form method='post' action='/projects/{safe}/crawls/{safe_id}/merge'>"
            "<button type='submit'>Merge these screens into the FlowSpec</button></form>",
            title="Against the FlowSpec",
        )
    return theme.card(
        "<p class='meta'>This project has no FlowSpec yet.</p>"
        f"<form method='post' action='/projects/{safe}/crawls/{safe_id}/merge'>"
        "<button type='submit'>Create a FlowSpec from these screens</button></form>",
        title="Against the FlowSpec",
    )


def _tone(crawl: Crawl) -> str:
    """X18(c): only a genuinely successful crawl is green; a wall or a legacy no-op is not."""
    return "positive" if is_success(crawl) else "warning"


def _crumbs(slug: str, *tail: tuple[str, str | None]) -> str:
    return theme.breadcrumb(
        ("Projects", "/"), (escape(slug), f"/projects/{escape(slug)}"),
        ("Crawls", f"/projects/{escape(slug)}/crawls" if tail else None), *tail,
    )


@router.get("/projects/{slug}/crawls", response_class=HTMLResponse)
def crawls(slug: str) -> str:
    store, project = _load_project_or_404(slug)
    safe = escape(slug)
    login = login_card(slug, project, store.list_cases())
    crawl_ids = store.list_crawl_ids()
    if not crawl_ids:
        body = _crumbs(slug) + "<h1>Crawls</h1>" + login + theme.empty_state(
            "🕸", "No crawls yet — explore this project to map its screens on its own.",
            crawl_view.bounds_form(slug, "Explore now"),
        )
        return theme.page("Crawls", body, active_slug=slug)
    rows = []
    for crawl_id in crawl_ids:
        crawl = store.load_crawl(crawl_id)
        if crawl is None:
            continue
        rows.append(
            f"<tr><td><a href='/projects/{safe}/crawls/{escape(crawl_id)}'>"
            f"<code>{escape(crawl_id)}</code></a></td>"
            f"<td>{theme.pill(escape(displayed_status(crawl).value), _tone(crawl))}</td>"
            f"<td>{escape(crawl.stop_reason or '—')}</td><td>{crawl.screens}</td>"
            f"<td>{crawl.denied}</td><td>{crawl.issues}</td>"
            f"<td>{crawl.tool_failures}</td>"
            f"<td>{escape(crawl.started_at or '—')}</td></tr>"
        )
    table = (
        "<table class='data-table'><thead><tr><th>Crawl</th><th>Status</th>"
        "<th>Stopped because</th><th>Screens</th><th>Refused</th><th>Issues</th>"
        "<th>Tool failures</th>"
        f"<th>Started</th></tr></thead><tbody>{''.join(rows)}</tbody></table>"
    )
    body = (
        _crumbs(slug) + "<h1>Crawls</h1>" + login
        + theme.card(crawl_view.bounds_form(slug, "Explore again"), title="New bounded crawl")
        + theme.card(table)
    )
    return theme.page("Crawls", body, active_slug=slug)


@router.get("/projects/{slug}/crawls/{crawl_id}", response_class=HTMLResponse)
def crawl_page(slug: str, crawl_id: str) -> str:
    store, project = _load_project_or_404(slug)
    _require_safe_id(crawl_id, "crawl_id")
    crawl = store.load_crawl(crawl_id)
    safe, safe_id = escape(slug), escape(crawl_id)
    if crawl is None:
        body = _crumbs(slug, ("Crawl", None)) + theme.empty_state(
            "❓", f"No crawl '{safe_id}' in this project.")
        return HTMLResponse(theme.page("Crawl not found", body, active_slug=slug), status_code=404)

    nodes = store.list_nodes(crawl_id)
    edges = store.list_edges(crawl_id)
    issues = store.list_crawl_issues(crawl_id)
    names = {n.id: (n.name or n.title or n.url_template) for n in nodes}
    redactor = SecretStore.load(project, store.paths.env_file, strict=False).redactor()
    coverage = _coverage_card(store, safe, safe_id, nodes, redactor)
    body = (
        _crumbs(slug, ("Crawl", None))
        + f"<h1>Crawl <code>{safe_id}</code></h1>"
        + crawl_view.summary_stats(crawl)
        + f"<p><a href='/projects/{safe}/crawls/{safe_id}/report.xlsx'>"
          "Download Excel report</a></p>"
        + theme.card(crawl_view.screen_tree(slug, crawl, nodes, edges), title="Screens found")
        + theme.card(crawl_view.refused_table(edges, names), title="Refused & skipped")
        + theme.card(crawl_view.issues_table(
            [i for i in issues if i.kind is not IssueKind.EVIDENCE], names),
            title="Issues found in the product")
        + theme.card(crawl_view.tool_failures_table(
            [i for i in issues if i.kind is IssueKind.EVIDENCE], names),
            title="What the crawler itself could not do")
        + coverage
        + theme.card(crawl_view.summary_table(crawl), title="Run detail")
    )
    return theme.page(f"Crawl {safe_id}", body, active_slug=slug)


@router.get("/projects/{slug}/crawls/{crawl_id}/report.xlsx")
def download_crawl_excel(slug: str, crawl_id: str) -> FileResponse:
    _load_project_or_404(slug)
    _require_safe_id(crawl_id, "crawl_id")
    out = export_crawl_excel(slug, crawl_id, _reserved_temp_path(".xlsx"))
    return FileResponse(
        out, filename=f"{slug}-{crawl_id}.xlsx", media_type=_XLSX,
        background=BackgroundTask(out.unlink, missing_ok=True),
    )


@router.post("/projects/{slug}/explore")
def start_crawl(
    slug: str, max_screens: str = Form("30"), max_actions: str = Form("200"),
    wall_clock_s: str = Form("600"), max_depth: str = Form("6"),
) -> Response:
    """Synchronous, like the Run button — the same trade-off `routes_runs.py`
    already makes (no background job queue), so the page returns when the crawl
    is genuinely finished rather than promising one that never ran."""
    from autotester.browser.observe import PageObserver
    from autotester.browser.session import BrowserSession
    from autotester.core.consent import ApprovalRequired
    from autotester.schema.crawl import SafetyPolicy
    from autotester.stages import explore as explore_stage
    from autotester.stages import explore_consent

    store, project = _load_project_or_404(slug)
    try:
        bounds = _parse_bounds((max_screens, max_actions, wall_clock_s, max_depth))
    except ValueError as exc:
        return _crawl_error(slug, 400, "Invalid crawl bounds", str(exc))
    case = store.get_case(project.login_case_id) if project.login_case_id else None
    if project.login_case_id and case is None:
        # X17: a declared login that no longer exists must not quietly crawl signed out.
        return _crawl_error(slug, 400, "Login case not found",
                            "the login case declared for this project no longer exists — "
                            "declare another one above the crawl form")
    try:
        explore_consent.require_consent(
            project, store, bounds,
            policy=SafetyPolicy(write_policy=project.write_policy))
    except ApprovalRequired as exc:
        return _crawl_error(slug, 403, "Crawl approval required", str(exc))
    paths = ProjectPaths(slug)
    paths.ensure()
    secrets = SecretStore.load(project, paths.env_file, strict=False)
    observer = PageObserver()
    crawl_id = run_id("crawl")
    try:
        with BrowserSession(project, secrets, paths.crawl_shots_dir(crawl_id),
                            paths, observer=observer) as session:
            crawl = explore_stage.run_crawl(project, session, store, observer=observer,
                                            bounds=bounds, login_case=case, crawl_id=crawl_id)
    except ApprovalRequired as exc:
        return _crawl_error(slug, 403, "Crawl approval required", str(exc))
    _queue_coverage_gap(store, crawl, secrets.redactor())
    return RedirectResponse(f"/projects/{slug}/crawls/{crawl.id}", status_code=303)


@router.post("/projects/{slug}/crawls/{crawl_id}/merge")
def merge_crawl(slug: str, crawl_id: str) -> RedirectResponse:
    """Fold the crawl's screens into the FlowSpec. Sends the spec back to DRAFT
    when anything changed — a crawl may propose screens, never approve them."""
    store, _project = _load_project_or_404(slug)
    _require_safe_id(crawl_id, "crawl_id")
    nodes = store.list_nodes(crawl_id)
    spec = merge_screens(store.load_flowspec(), nodes, slug, crawl_id=crawl_id)
    store.save_flowspec(spec)
    # AT-289: covering a gap and leaving its ask OPEN is the V6 two-seam drift on
    # the CLOSING side — `queue_requests` is called from both entry points, so
    # `resolve_requests` must be too, or the only door an operator has (T-100:
    # no CLI) closes the gap and never closes the request.
    resolve_requests(store, spec, source_id=crawl_id)
    return RedirectResponse(f"/projects/{slug}/crawls/{crawl_id}", status_code=303)
