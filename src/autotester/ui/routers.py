"""The one list of routers the UI app serves (moved out of `ui/app.py` by T-204).

Every feature registers its router by adding it to `ROUTERS`; `app.py` calls
`include_all(app)` once. A route registered here still needs a row in the central
route policy table (`auth/policy.py`), or the login gate refuses it (auth.md AU14).
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
    routes_video,
)

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
)


def include_all(app: FastAPI) -> None:
    for router in ROUTERS:
        app.include_router(router)
