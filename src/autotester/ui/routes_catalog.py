"""The test catalog page: one row per `CaseClass`, a green runnable count, and
every blocked row saying why and the one action that clears it.

Contract: qa/contracts/catalog.md CT8. Read-only — `GET /projects/{slug}/catalog`
renders `stages/catalog.py::catalog()`'s output; it writes nothing (D-039).
"""

from __future__ import annotations

from html import escape

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from autotester.schema.catalog import TIER_ORDER, Catalog, CatalogEntry
from autotester.stages.catalog import catalog as build_catalog
from autotester.ui import theme
from autotester.ui.helpers import _load_project_or_404

router = APIRouter()

_REASON_LABEL = {
    "no_flowspec": "no FlowSpec yet",
    "flowspec_not_approved": "FlowSpec not approved",
    "missing_credential": "missing credential",
    "no_ground_truth": "no ground truth",
    "needs_write_policy": "needs a wider write policy",
    "no_live_endpoint": "no live endpoint",
}
"""A human label distinct from the bare enum literal (CT8) — the row still
also carries `entry.unblock_action`'s full, case-specific action text."""


def _status_cell(entry: CatalogEntry) -> str:
    if entry.runnable:
        return theme.pill("runnable", "positive")
    reason_key = entry.blocked_reason.value if entry.blocked_reason else ""
    reason = _REASON_LABEL.get(reason_key, "blocked")
    action = escape(entry.unblock_action) if entry.unblock_action else ""
    return (
        theme.pill(reason, "warning" if entry.applicable else "neutral")
        + (f"<div class='meta'>{action}</div>" if action else "")
    )


def _row(entry: CatalogEntry) -> str:
    return (
        "<tr>"
        f"<td>{escape(entry.case_class.value)}</td>"
        f"<td>{escape(entry.tier.value)}</td>"
        f"<td>{'yes' if entry.applicable else 'no'}</td>"
        f"<td>{_status_cell(entry)}</td>"
        "</tr>"
    )


def _table(cat: Catalog) -> str:
    ordered = sorted(cat.entries, key=lambda e: (TIER_ORDER.index(e.tier), e.case_class.value))
    rows = "".join(_row(e) for e in ordered)
    return (
        "<div style='overflow:auto'><table><thead><tr>"
        "<th>Case class</th><th>Tier</th><th>Applicable</th><th>Status</th>"
        f"</tr></thead><tbody>{rows}</tbody></table></div>"
    )


@router.get("/projects/{slug}/catalog", response_class=HTMLResponse)
def catalog_page(slug: str) -> str:
    store, project = _load_project_or_404(slug)
    spec = store.load_flowspec()
    cat = build_catalog(project, spec, store)
    name = escape(project.name)
    total = len(cat.entries)
    stats = (
        "<div class='stat-row'>"
        + theme.stat(str(cat.runnable_count), "runnable now")
        + theme.stat(str(total), "case classes")
        + "</div>"
    )
    body = (
        theme.breadcrumb(("Projects", "/"), (name, f"/projects/{slug}"), ("Catalog", None))
        + "<h1>Test catalog</h1>" + stats
        + theme.card(_table(cat), title=f"{name} catalog")
    )
    return theme.page(f"{name} · Catalog", body, active_slug=slug)
