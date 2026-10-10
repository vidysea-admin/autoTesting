"""The damage-control report as a page (T-168): the lead's two-step route from the project page.

One job — serve `stages/unified_report.py::unified_html` for the project's newest run (or `?run=`),
the same single document `autotester release-report` writes. A project with nothing run yet gets
an empty state, never a report. Mounted from `routes_report.router` (that module and `ui/app.py`
sit at the 300-line cap, so this is a sub-router rather than a new `include_router` in `app.py`).
"""

from __future__ import annotations

from html import escape

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from autotester.stages.unified_report import ReportUnavailable, ReportUnreadable, unified_html
from autotester.ui import theme
from autotester.ui.helpers import _load_project_or_404, _require_safe_id

router = APIRouter()


@router.get("/projects/{slug}/damage-report", response_class=HTMLResponse)
def damage_report(slug: str, run: str | None = None) -> str:
    store, _project = _load_project_or_404(slug)
    if run is not None:
        _require_safe_id(run, "run id")
    try:
        return unified_html(store, run)
    except ReportUnreadable as exc:  # fixed text: field names only, never stored values (DC4)
        body = "<h1>Damage-control report</h1>" + theme.empty_state("⚠️", escape(str(exc)))
        return HTMLResponse(theme.page("Damage-control report", body, active_slug=slug), 500)
    except ReportUnavailable as exc:
        body = "<h1>Damage-control report</h1>" + theme.empty_state(
            "📋", f"{escape(str(exc))} - run a case or a release first; nothing to report yet.")
        return theme.page("Damage-control report", body, active_slug=slug)
