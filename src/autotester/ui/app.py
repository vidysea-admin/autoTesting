"""Thin FastAPI project-list, onboarding and live-view pages over project files.
Every route uses ProjectStore/SecretStore like the CLI (ui.md U1-U5).
Runs, reports and credentials live in their own route modules; never a second source of truth.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from html import escape
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from autotester.browser.secrets import SecretStore, parse_env
from autotester.core.env import load_repo_env
from autotester.core.paths import ProjectPaths
from autotester.schema.project import Project, Source
from autotester.stages.report_export import valid_runs_newest_first
from autotester.store.project_store import ProjectStore
from autotester.ui import (
    error_pages,
    project_view,
    routes_cases,
    routes_catalog,
    routes_crawl_approval,
    routes_crawl_login,
    routes_crawls,
    routes_credentials,
    routes_flow_diagram,
    routes_issues,
    routes_learn,
    routes_live,
    routes_product_map,
    routes_project_edit,
    routes_report,
    routes_runs,
    routes_settings,
    routes_sources,
    routes_video,
    theme,
)
from autotester.ui.env_editor import InvalidEnvValue, set_env_values, validate_env_values
from autotester.ui.helpers import (
    _load_project_or_404,
    _project_slugs,
    _refuse_unsafe_submission,
    _require_project_name,
    _require_reachable_base_url,
    _require_slug,
    origin_guard_middleware,
)
from autotester.ui.routes_report import _run_counts

__all__ = ["_require_slug", "app"]


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Same convention as every real-run script (e.g.
    scripts/run_pathlynks_first_cases.py) -- a plain `uvicorn`/docker process never
    sources .env on its own, so global provider keys (ANTHROPIC_API_KEY etc.) would
    otherwise be invisible to LangChainFallbackProvider() even though the file is
    present on disk. A startup hook, not a module-level call, so TestClient(app)
    (which never runs lifespan unless used as a context manager) never leaks real
    .env values into the test process."""
    load_repo_env()          # AT-228: the one loader the CLI also uses, so both
    yield                    # entry points agree on which credentials exist


app = FastAPI(title="AutoTester", lifespan=_lifespan, middleware=origin_guard_middleware())
error_pages.register_exception_handler(app)  # AT-596: HTML for a browser, JSON for everyone else
app.include_router(routes_cases.router)
app.include_router(routes_project_edit.router)
app.include_router(routes_runs.router)
app.include_router(routes_report.router)
app.include_router(routes_video.router)
app.include_router(routes_flow_diagram.router)
app.include_router(routes_crawls.router)
app.include_router(routes_crawl_login.router)
app.include_router(routes_credentials.router)
app.include_router(routes_crawl_approval.router)
app.include_router(routes_settings.router)
app.include_router(routes_learn.router)
app.include_router(routes_sources.router)
app.include_router(routes_product_map.router)
app.include_router(routes_issues.router)
app.include_router(routes_live.router)
app.include_router(routes_catalog.router)


@app.get("/favicon.ico", status_code=204)
def favicon() -> Response:
    return Response(status_code=204)


def _latest_run_status(slug: str) -> tuple[str | None, dict[str, int]]:
    """The latest run id (or None if the project has never run) and its verdict
    counts — same lookup `routes_report.py`'s report page already does per
    project, reused here rather than a second way to compute "how did the
    last run go" (ui.md U2/U4: real persisted state, never recomputed)."""
    store = ProjectStore(slug)
    runs = valid_runs_newest_first(store)
    if not runs:
        return None, {}
    return runs[0].id, _run_counts(store, runs[0].id)


def _project_card(slug: str) -> str:
    store = ProjectStore(slug)
    project = store.load_project()
    name = escape(project.name) if project else escape(slug)
    case_count = len(store.list_cases())
    safe_slug = escape(slug)
    run_id, counts = _latest_run_status(slug)
    if run_id is None:
        status = "<span class='meta'>never run</span>"
    else:
        status = "".join(theme.badge(escape(k), count=v) for k, v in counts.items())
    return (
        f"<a class='project-card' href='/projects/{safe_slug}'>"
        f"<span class='name'>{name}</span>"
        f"<span class='meta'>{case_count} case{'s' if case_count != 1 else ''}</span>"
        f"<span class='card-status'>{status}</span></a>"
    )


def _portfolio_stats(slugs: list[str]) -> str:
    """Aggregate health across every onboarded project — the piece a
    non-technical user needs before clicking into any one project (feedback
    2026-09-06: the home page showed names and case counts only, nothing
    saying what's actually passing or failing)."""
    total_cases = 0
    never_run = 0
    failing = 0
    healthy = 0
    for slug in slugs:
        total_cases += len(ProjectStore(slug).list_cases())
        _run_id, counts = _latest_run_status(slug)
        if _run_id is None:
            never_run += 1
        elif counts.get("FAIL", 0) > 0 or counts.get("BLOCKED", 0) > 0:
            failing += 1
        else:
            healthy += 1
    tiles = [
        theme.stat(str(len(slugs)), "projects"),
        theme.stat(str(total_cases), "cases"),
        theme.stat(str(healthy), "latest run clean"),
    ]
    if failing:
        tiles.append(theme.stat(str(failing), "latest run failing"))
    if never_run:
        tiles.append(theme.stat(str(never_run), "never run"))
    return f"<div class='stat-row'>{''.join(tiles)}</div>"


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    slugs = _project_slugs()
    header = (
        "<div class='page-header'><div><h1>Projects</h1>"
        "<p class='subtitle'>Onboard a product once, then let AutoTester keep watching it.</p>"
        "</div><a class='btn btn-primary' href='/onboard'>+ New project</a></div>"
    )
    if not slugs:
        body = header + theme.empty_state(
            "🧪", "No projects yet — onboard your first one to get started.",
            "<a class='btn btn-primary' href='/onboard'>+ New project</a>",
        )
    else:
        cards = "".join(_project_card(s) for s in slugs)
        body = (
            header + _portfolio_stats(slugs)
            + f"<div class='project-grid'>{cards}</div>"
        )
    return theme.page("Projects", body)


@app.get("/onboard", response_class=HTMLResponse)
def onboard_form() -> str:
    body = (
        theme.breadcrumb(("Projects", "/"), ("Onboard", None))
        + "<h1>Onboard a project</h1>"
        "<p class='subtitle'>Give AutoTester a URL and test account. Add whatever you already "
        "know; otherwise it can learn by exploring after approval.</p>"
        f"{theme.card(project_view.intake_form())}"
    )
    return theme.page("Onboard", body)


def _guard_intake(project: Project, sources: list[Source], values: dict[str, str]) -> Path:
    """Apply old and newly submitted secrets before any intake artifact write."""
    env_path = ProjectPaths(project.slug).env_file
    present = parse_env(env_path.read_text(encoding="utf-8")) if env_path.exists() else {}
    submitted = {ref.key for ref in project.secrets}
    owned_elsewhere = {
        ref.key
        for slug in _project_slugs() if slug != project.slug
        for existing in [ProjectStore(slug).load_project()]
        if existing is not None
        for ref in existing.secrets
    }
    if submitted.intersection(present) or submitted.intersection(owned_elsewhere):
        raise HTTPException(
            400, "a credential key is already in use; choose a project-specific key",
        )
    guard = SecretStore(project, values, present)
    # AT-079: `slug` becomes the directory name, every page's URL, and text on
    # the home index -- an ordinary credential shape (lowercase/digits/hyphens)
    # was never checked here, only its regex SHAPE was (_require_slug).
    _refuse_unsafe_submission(
        [("the slug", project.slug),
         ("the name", project.name), ("the base URL", project.base_url),
         ("allowed domains", ", ".join(project.allowed_domains)),
         *[("a credential description", ref.description or "") for ref in project.secrets],
         *[("an intake statement", source.text or source.path or source.url or "")
           for source in sources],
         *[("a source label", source.label or "") for source in sources]],
        project, guard,
    )
    return env_path


@app.post("/onboard")
async def onboard_submit(request: Request) -> RedirectResponse:
    form = await request.form()
    slug, name = str(form.get("slug", "")), str(form.get("name", ""))
    base_url = str(form.get("base_url", ""))
    allowed_domains = str(form.get("allowed_domains", ""))
    _require_slug(slug)
    _require_project_name(name)
    if ProjectStore(slug).load_project() is not None:
        raise HTTPException(400, "a project with this slug already exists")
    domains = [d.strip() for d in allowed_domains.split(",") if d.strip()]
    draft = Project(slug=slug, name=name, base_url=base_url, allowed_domains=domains)
    refs, values = routes_project_edit.parse_secret_rows(
        draft, *(
            [str(v) for v in form.getlist(field)] for field in (
                "credential_key", "credential_value", "credential_domains",
                "credential_description",
            )
        ),
    )
    project = draft.model_copy(update={"secrets": refs})
    sources = routes_sources.parse_intake_sources(
        slug, str(form.get("evals", "")), str(form.get("conditions", "")),
        str(form.get("use_cases", "")),
        *([str(v) for v in form.getlist(field)] for field in (
            "source_kind", "source_value", "source_label",
        )),
    )
    try:
        validate_env_values(values)
    except InvalidEnvValue as exc:
        raise HTTPException(400, str(exc)) from exc
    env_path = _guard_intake(project, sources, values)
    _require_reachable_base_url(base_url, domains)  # guard new secrets before any echo path
    store = ProjectStore(slug)
    store.save_project(project)
    for source in sources:
        store.add_source(source)
    set_env_values(env_path, values)
    return RedirectResponse(f"/projects/{slug}", status_code=303)


@app.get("/projects/{slug}", response_class=HTMLResponse)
def project_detail(slug: str) -> str:
    store, project = _load_project_or_404(slug)
    spec = store.load_flowspec()
    review = spec.review.status.value if spec is not None else "no flowspec yet"
    review_tone = ("positive" if review == "approved"
                   else "warning" if spec is not None else "neutral")
    safe_slug = escape(slug)
    name = escape(project.name)
    case_count = len(store.list_cases())
    stats = (
        "<div class='stat-row'>"
        + theme.stat(str(case_count), "Cases")
        + theme.stat(str(len(project.allowed_domains)), "Allowed domain(s)")
        + "</div>"
    )
    run_button = (
        f"<form method='post' action='/projects/{safe_slug}/run' style='display:inline'>"
        "<button class='btn btn-primary' type='submit'>▶ Run tests</button></form>"
        if case_count else
        "<span class='btn' style='opacity:.5;cursor:default' title='no cases yet'>"
        "▶ Run tests</span>"
    )
    actions = project_view._actions_card(safe_slug, run_button, case_count)
    actions += f"<p><a class='btn' href='/projects/{safe_slug}/catalog'>Test catalog</a></p>"
    body = (
        theme.breadcrumb(("Projects", "/"), (name, None))
        + f"<h1>{name}</h1>"
        f"<p class='subtitle'>{escape(project.base_url)} &middot; review: "
        f"{theme.pill(escape(review), review_tone)}</p>"
        f"{stats}{actions}"
    )
    return theme.page(name, body, active_slug=slug)
