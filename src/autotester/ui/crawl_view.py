"""HTML fragments for the crawl pages — split from `routes_crawls.py` to keep
both under the 300-line cap (C2), same as `case_form.py` for the case form.

Every value that reaches these functions is escaped here; the routes module
assembles fragments and never interpolates raw model text itself.
"""

from __future__ import annotations

from html import escape
from pathlib import Path

from autotester.core.paths import ProjectPaths
from autotester.schema.crawl import Crawl, CrawlIssue
from autotester.schema.enums import EdgeOutcome, NodeStatus
from autotester.schema.flowspec import FlowSpec, Screen
from autotester.schema.screen_graph import ScreenEdge, ScreenNode
from autotester.stages.crawl_report import coverage_figure, crawl_summary, screens_by_reason
from autotester.stages.explore_status import displayed_status, is_success
from autotester.stages.report_export import png_base64
from autotester.ui import theme

_REFUSED = (
    EdgeOutcome.DENIED_POLICY,
    EdgeOutcome.SKIPPED_UNNAMED,
    EdgeOutcome.OFF_DOMAIN_REFUSED,
)
# AT-113: an aborted node used to render the same neutral gray pill as a fully
# explored one, so a partial crawl looked identical to a complete one at a
# glance. A human reading the screen tree must see the difference immediately.
_NODE_STATUS_TONE = {
    NodeStatus.ABORTED_ERROR: "danger",
    NodeStatus.ABORTED_DIALOG: "danger",
    NodeStatus.EXPLORED: "positive",
}


def summary_stats(crawl: Crawl) -> str:
    """The headline numbers, with the stop reason given equal billing — a
    bounded crawl that hit `max_actions` saw less of the product than one that
    emptied its frontier, and a reader must not have to infer which happened."""
    # X18(c): tone follows the judged status, not the stop reason's wording — a legacy
    # crawl stuck at the login page also said "frontier empty".
    tone = "positive" if is_success(crawl) else "warning"
    cov = crawl.coverage
    reasons = "".join(
        theme.pill(escape(f"{reason}: {count}"), "neutral") + " "
        for reason, count in (cov.by_reason().items() if cov else [])
    )
    screens = "".join(  # AT-470: screens a bound kept the crawl out of
        theme.pill(escape(f"{reason}: {count}"), "warning") + " "
        for reason, count in (screens_by_reason(cov).items() if cov else [])
    )
    return (
        "<div class='stat-row'>"
        + theme.stat(f"{cov.percent}%" if cov and not cov.error else "—",  # V7(d)
                     "Coverage")
        + theme.stat(str(crawl.screens), "Screens")
        + theme.stat(str(crawl.actions), "Actions")
        + theme.stat(str(crawl.denied), "Refused")
        + theme.stat(str(crawl.issues), "Issues")
        + theme.stat(str(crawl.tool_failures), "Tool failures")
        + "</div>"
        + f"<p class='meta'>{theme.pill(escape(displayed_status(crawl).value), tone)} · "
        + f"stopped: {theme.pill(escape(crawl.stop_reason or 'unknown'), tone)}"
        + f" · policy {theme.pill(escape(crawl.policy.write_policy.value), 'neutral')}</p>"
        + f"<p class='meta'>coverage: {escape(coverage_figure(crawl))}"
        + (f" · not exercised: {reasons}" if reasons else "")
        + (f" · screens not entered: {screens}" if screens else "") + "</p>"
    )


def summary_table(crawl: Crawl) -> str:
    rows = "".join(
        f"<tr><th>{escape(label)}</th><td>{escape(value)}</td></tr>"
        for label, value in crawl_summary(crawl)
    )
    return f"<table class='data-table'><tbody>{rows}</tbody></table>"


def _thumb(slug: str, crawl_id: str, node: ScreenNode) -> str:
    if not node.screenshot_ref:
        return ""
    paths = ProjectPaths(slug)
    allowed_root = paths.crawl_shots_dir(crawl_id)
    ref = Path(node.screenshot_ref)
    path = ref if ref.is_absolute() else allowed_root / ref
    data = png_base64(path, allowed_root, paths.dir)
    if data is None:
        return ""
    return f"<span class='thumb'><img src='data:image/png;base64,{data}' loading='lazy'></span>"


def screen_tree(slug: str, crawl: Crawl, nodes: list[ScreenNode],
                edges: list[ScreenEdge]) -> str:
    """Screens in discovery order, each showing the control that led to it —
    `discovered_by` names an edge, so the tree reads as "this button got us
    here" rather than as a flat list of URLs."""
    if not nodes:
        return theme.empty_state("🕸", "This crawl found no screens.")
    by_edge = {e.id: e for e in edges}
    names = {n.id: (n.name or n.title or n.url_template) for n in nodes}
    items = []
    for node in sorted(nodes, key=lambda n: (n.depth, n.url_template)):
        edge = by_edge.get(node.discovered_by or "")
        via = (
            f"<span class='meta'>via “{escape(edge.name or edge.target)}” on "
            f"{escape(names.get(edge.from_node, edge.from_node))}</span>"
            if edge else "<span class='meta'>entry point</span>"
        )
        tone = _NODE_STATUS_TONE.get(node.status, 'neutral')
        flags = []
        if node.console_errors:
            flags.append(theme.pill(f"{len(node.console_errors)} console", "danger"))
        if node.failed_requests:
            flags.append(theme.pill(f"{len(node.failed_requests)} failed", "warning"))
        items.append(
            f"<li class='crawl-node' style='--depth:{node.depth}'>"
            f"{_thumb(slug, crawl.id, node)}"
            f"<span class='crawl-node-body'><strong>{escape(names[node.id])}</strong> "
            f"{theme.pill(escape(node.status.value), tone)} {''.join(flags)}<br>"
            f"<code>{escape(node.url_template)}</code> "
            f"<span class='meta'>depth {node.depth}</span><br>{via}</span></li>"
        )
    return f"<ul class='crawl-tree'>{''.join(items)}</ul>"


def refused_table(edges: list[ScreenEdge], names: dict[str, str]) -> str:
    """What the crawl would not touch. On a real product an `unnamed control`
    row is actionable: it names a button that needs an `aria-label`."""
    rows = [e for e in edges if e.outcome in _REFUSED]
    if not rows:
        return "<p class='meta'>Nothing was refused on this crawl.</p>"
    body = "".join(
        f"<tr><td>{escape(names.get(e.from_node, e.from_node))}</td>"
        f"<td>{escape(e.name or '(unnamed)')}</td>"
        f"<td><code>{escape(e.target)}</code></td>"
        f"<td>{theme.pill(escape(e.outcome.value), 'warning')}</td>"
        f"<td>{escape(e.reason or '')}</td></tr>"
        for e in rows
    )
    return (
        "<table class='data-table'><thead><tr><th>Screen</th><th>Control</th>"
        "<th>Selector</th><th>Refusal</th><th>Why</th></tr></thead>"
        f"<tbody>{body}</tbody></table>"
    )


def tool_failures_table(issues: list[CrawlIssue], names: dict[str, str]) -> str:
    """The crawler's OWN failures, shown apart from the product's (AT-120).

    A number a human reads as "bugs in my product" must not quietly include
    the tool's failures — but hiding them would be worse, because each one is
    a hole in the evidence the rest of the report is built on."""
    if not issues:
        return "<p class='meta'>The crawler recorded everything it tried to.</p>"
    return issues_table(issues, names)


def issues_table(issues: list[CrawlIssue], names: dict[str, str]) -> str:
    if not issues:
        return "<p class='meta'>No issues found on this crawl.</p>"
    body = "".join(
        f"<tr><td>{escape(names.get(i.node_id, i.node_id))}</td>"
        f"<td>{theme.pill(escape(i.kind.value), 'neutral')}</td>"
        f"<td>{escape(i.detail)}</td></tr>"
        for i in issues
    )
    return (
        "<table class='data-table'><thead><tr><th>Screen</th><th>Kind</th>"
        f"<th>Detail</th></tr></thead><tbody>{body}</tbody></table>"
    )


_REVIEW_TONE = {"approved": "positive", "draft": "warning", "needs_edit": "danger"}


def review_line(spec: FlowSpec) -> str:
    """AT-104: merging sends an APPROVED FlowSpec back to DRAFT, and the page it
    redirects to showed no review status at all — so a human could re-arm their
    own approval gate and never be told. The CLI said it; the UI did not."""
    status = spec.review.status.value
    tone = _REVIEW_TONE.get(status, "neutral")
    note = f" — {escape(spec.review.note)}" if spec.review.note else ""
    warning = (
        "<p class='meta'><strong>This FlowSpec is not approved.</strong> It drives no test "
        "expansion until a human approves it again.</p>"
        if status != "approved" else ""
    )
    return (
        f"<p class='meta'>FlowSpec v{spec.version} · review: "
        f"{theme.pill(escape(status), tone)}{note}</p>{warning}"
    )


def bounds_form(slug: str, label: str) -> str:
    """The exact four operator-controlled bounds used by crawl preflight/run.

    Moved here from `routes_crawls.py` (AT-608/609) to keep that module under
    the 300-line cap after it started scrubbing the coverage card -- same
    C2 split this module already exists for (see module docstring)."""
    safe = escape(slug)
    fields = (
        ("max_screens", "Maximum screens", "30", "1"),
        ("max_actions", "Maximum actions", "200", "1"),
        ("wall_clock_s", "Wall clock (seconds)", "600", "any"),
        ("max_depth", "Maximum depth", "6", "1"),
    )
    inputs = "".join(
        f"<div class='field'><label>{title}</label><input type='number' name='{name}' "
        f"min='1' step='{step}' value='{value}' required></div>"
        for name, title, value, step in fields
    )
    return (
        f"<form method='post' action='/projects/{safe}/explore'>"
        f"{inputs}<button type='submit'>{label}</button></form>"
    )


def coverage_card(gaps: list, unreached: list[Screen]) -> str:
    """The crawl against the FlowSpec, both directions — screens the spec
    cannot name, and screens the spec claims that the crawl never reached."""
    gap_items = "".join(f"<li><code>{escape(g.subject)}</code></li>" for g in gaps)
    miss_items = "".join(
        f"<li>{escape(s.name)} <code>{escape(s.url_pattern or '')}</code></li>"
        for s in unreached
    )
    return (
        f"<p><strong>{len(gaps)}</strong> screen(s) the FlowSpec cannot name:</p>"
        + (f"<ul>{gap_items}</ul>" if gap_items else "<p class='meta'>none</p>")
        + f"<p><strong>{len(unreached)}</strong> known screen(s) this crawl never reached:</p>"
        + (f"<ul>{miss_items}</ul>" if miss_items else "<p class='meta'>none</p>")
    )
