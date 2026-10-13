"""The one ordered list of routers the UI app serves (T-204/T-205, TF3).

Every feature registers its router by adding it to `ROUTERS`; `ui/app.py` calls
`include_all(app)` once and holds no per-unit `include_router` line. Order is route order, so
the 17 routers that existed before this file keep the order `app.py` had. The Group 10 units
(`STUBS`) are empty `APIRouter()`s registered now and filled by their own unit: such a unit
replaces its stub in `ROUTERS` with its real router, without editing `app.py`.
A route registered here still needs a row in the central route policy table
(`auth/policy.py`), or the login gate refuses it (auth.md AU14, T-204).
"""

from __future__ import annotations

from fastapi import APIRouter, FastAPI

from autotester.ui import (
    routes_admin,
    routes_auth,
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
    routes_project_access,
    routes_project_edit,
    routes_report,
    routes_runs,
    routes_settings,
    routes_sources,
    routes_team_run,
    routes_video,
)

STUBS: dict[str, APIRouter] = {
    name: APIRouter() for name in (
        "schedule", "team_run", "inbox", "profile", "tracker", "video_review", "video_portal",
        "access_requests",
    )
}
"""Group 10 routers, empty until their unit fills them (zero routes: nothing is exposed)."""

ROUTERS: tuple[APIRouter, ...] = (
    routes_auth.router,
    routes_admin.router,
    routes_cases.router,
    routes_project_edit.router,
    routes_runs.router,
    routes_report.router,
    routes_video.router,
    routes_flow_diagram.router,
    routes_crawls.router,
    routes_crawl_login.router,
    routes_credentials.router,
    routes_crawl_approval.router,
    routes_settings.router,
    routes_learn.router,
    routes_sources.router,
    routes_product_map.router,
    routes_issues.router,
    routes_live.router,
    routes_catalog.router,
    routes_project_access.router,
    routes_team_run.router,   # T-201b; its `STUBS['team_run']` stays registered, empty
    *STUBS.values(),
)


def include_all(app: FastAPI) -> None:
    """Register every router in `ROUTERS`, in order."""
    for router in ROUTERS:
        app.include_router(router)
