"""What a crawl covered, stated by the crawl itself — and every hole, with its reason (V7).

Umesh, 2026-09-16: "puura product map hona chiaye na aend to end testing . each possible
route". A crawl report that lists only what it FOUND reads as the whole product. This
computes, from the graph a crawl already persists (its screens, their controls, and every
attempt edge), how many controls were discovered, how many were really performed, and for
each one that was not, exactly one reason from a closed set.

Pure and post-hoc: the BFS itself is untouched. Every hole is derived from evidence already
on disk, so the figure can be recomputed for any crawl and cannot drift from the graph.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from autotester.schema.crawl import CoverageHole, CrawlBounds, CrawlCoverage, PermittedControl
from autotester.schema.enums import Action, CrawlStatus, EdgeOutcome, NodeStatus, WritePolicy
from autotester.schema.flowspec import FlowSpec
from autotester.schema.screen_graph import ElementRef, ScreenEdge, ScreenNode
from autotester.stages.account_destroy import ACCOUNT_DESTROY_REFUSED, destroys_account
from autotester.stages.coverage import unreached_screens
from autotester.stages.explore_safety import FORM_SUBMIT_REFUSED, OFF_DOMAIN_LINK_REFUSED

if TYPE_CHECKING:
    from autotester.stages.explore_runtime import ExploreRuntime

PERFORMED = frozenset({EdgeOutcome.NAVIGATED, EdgeOutcome.SAME_SCREEN, EdgeOutcome.DIALOG})
REFUSED_BEFORE_TRYING = frozenset({EdgeOutcome.DENIED_POLICY, EdgeOutcome.SKIPPED_UNNAMED})
REASONS = ("bound:", "policy:", "unnamed", "off_domain", "error", "login_wall", "not_visited",
           "skipped_unchanged", "not_reached")
"""The closed set (V7b). `bound:` and `policy:` carry a name; the rest are exact.
`skipped_unchanged` is CR3's incremental skip, added as a NAMED category beside the
others exactly as CR5 requires -- a skip must stay visible on every surface, never
disappear into "explored". `not_reached` is V9's: a control the account MAY use that
no entry point in this crawl ever led to -- a reason, not an absence of one."""


def is_candidate(el: ElementRef) -> bool:
    """A control the crawl could ever try. `explore_node.visit_node` calls THIS, so the
    crawl and its coverage cannot disagree about what a candidate is (C3)."""
    return el.visible and el.enabled and not el.obscured


def _edge_reason(edge: ScreenEdge, status: CrawlStatus) -> str:
    if edge.outcome is EdgeOutcome.SKIPPED_UNNAMED:
        return "unnamed"
    if edge.outcome is EdgeOutcome.OFF_DOMAIN_REFUSED:
        return "off_domain"
    if edge.outcome is EdgeOutcome.DENIED_POLICY:
        if status is CrawlStatus.LOGIN_WALL and edge.reason == FORM_SUBMIT_REFUSED:
            return "login_wall"
        return f"policy:{edge.reason or 'unspecified'}"
    return "error"


def _tried(node_id: str, edges: list[ScreenEdge]) -> int:
    """How many actions `visit_node` spent on this screen — the count its per-node cap reads.
    A policy refusal or a refused off-domain link is recorded without being tried; so is the
    BACK edge written when the crawl could not return."""
    return sum(
        1 for e in edges
        if e.from_node == node_id and e.action is not Action.BACK
        and e.outcome not in REFUSED_BEFORE_TRYING
        and not (e.outcome is EdgeOutcome.OFF_DOMAIN_REFUSED
                 and e.reason == OFF_DOMAIN_LINK_REFUSED)
    )


def _untried_reason(node: ScreenNode, tried: int, bounds: CrawlBounds, bound: str | None) -> str:
    """A candidate with no edge at all: why the crawl never got to it (AT-471). The per-node
    cap is named when THIS screen spent it; otherwise the global bound that ended the crawl
    while this screen was being visited."""
    if node.status is NodeStatus.QUEUED:
        return "not_visited"
    if node.status is NodeStatus.SKIPPED_UNCHANGED:
        return "skipped_unchanged"  # CR3/CR5: taken on trust, not exercised
    if node.status is not NodeStatus.EXPLORED:
        return "error"  # the screen was abandoned (lost, or a dialog storm)
    if tried >= bounds.per_node_action_cap or bound is None:
        return "bound:per_node_action_cap"
    return f"bound:{bound}"


def _screens_not_entered(nodes: list[ScreenNode], edges: list[ScreenEdge],
                         bounds: CrawlBounds) -> list[CoverageHole]:
    """AT-470: a screen a link really led to that never became a node — `_enqueue` drops it
    past `max_depth` or once `max_screens` is reached. One hole per such screen."""
    known = {n.id: n for n in nodes}
    holes: dict[str, CoverageHole] = {}
    for edge in edges:
        if edge.outcome is not EdgeOutcome.NAVIGATED or not edge.to_node:
            continue
        if edge.to_node in known or edge.to_node in holes or edge.from_node not in known:
            continue
        source = known[edge.from_node]
        why = "max_depth" if source.depth + 1 > bounds.max_depth else "max_screens"
        holes[edge.to_node] = CoverageHole(node_id=edge.to_node, url_template=source.url_template,
                                           selector=edge.target, name=edge.name,
                                           reason=f"bound:{why}")
    return list(holes.values())


def _key(url_template: str, selector: str) -> tuple[str, str]:
    """How a permitted control and a crawled control are matched (V9).

    `ScreenNode.url_template` is netloc+path (`core.urls.url_template`'s
    `keep_host=True` shape, e.g. `app.test/settings`), which is bound to the
    environment the crawl ran against. A project's declared permitted surface must
    not be: the same account's rights do not change between prepod and production.
    So the host is dropped from whichever side carries one, exactly as
    `stages/coverage.py::_path_of` drops it before every V1 diff.
    """
    path = url_template if url_template.startswith("/") else f"/{url_template.partition('/')[2]}"
    return (path.rstrip("/") or "/", selector)


def _permitted_reason(control: PermittedControl, holes: dict[tuple[str, str], str],
                      policy: WritePolicy) -> str:
    """The ONE reason a permitted control was not exercised (V9). A control the crawl
    really met carries the reason the crawl itself recorded; one it never met is
    `not_reached`, unless the run's own `write_policy` is what stands in the way."""
    recorded = holes.get(_key(control.url_template, control.selector))
    if recorded is not None:
        return recorded
    if destroys_account(control.name):  # never clicked at ANY policy (2026-10-15)
        return f"policy:{ACCOUNT_DESTROY_REFUSED}"
    if control.destructive and policy is not WritePolicy.ALLOW_WRITES:
        return f"policy:destructive under {policy.value}"
    return "not_reached"


def _permitted_coverage(coverage: CrawlCoverage, permitted: list[PermittedControl],
                        exercised: set[tuple[str, str]], policy: WritePolicy) -> None:
    """V9: re-base the figure on what the account MAY do. The denominator becomes the
    declared permitted surface, and every permitted control not exercised is LISTED
    with a reason -- a blocked control never counts as covered, and it never leaves
    the denominator either."""
    holes = {_key(h.url_template, h.selector): h.reason for h in coverage.holes}
    done = 0
    for control in permitted:
        if _key(control.url_template, control.selector) in exercised:
            done += 1
            continue
        coverage.permitted_holes.append(CoverageHole(
            node_id="", url_template=control.url_template, selector=control.selector,
            name=control.name, reason=_permitted_reason(control, holes, policy)))
    coverage.denominator_basis = "permitted"
    coverage.permitted_total = len(permitted)
    coverage.permitted_exercised = done


def of_run(rt: ExploreRuntime, status: CrawlStatus) -> CrawlCoverage:
    """The coverage of the crawl `rt` is finishing. Never raises (AT-472): coverage must not
    cost the crawl its own record, so a failure here is RECORDED, not propagated."""
    from autotester.stages import explore  # runtime import: explore imports this module

    scrub = rt.session.secrets.scrub_optional
    spec, spec_error = None, None
    try:
        spec = rt.store.load_flowspec()
    except Exception as exc:
        spec_error = scrub(f"could not read the FlowSpec -- {type(exc).__name__}: {exc}")
    try:
        coverage = compute_coverage(status=status, bound=explore.stop_reason(rt),
                                    bounds=rt.bounds, nodes=list(rt.nodes.values()),
                                    edges=rt.store.list_edges(rt.crawl.id), spec=spec,
                                    permitted=rt.project.permitted_surface,  # V9
                                    policy=rt.crawl.policy.write_policy)
    except Exception as exc:
        return CrawlCoverage(error=scrub(f"{type(exc).__name__}: {exc}"), spec_error=spec_error)
    coverage.spec_error = spec_error
    return coverage


def _percent(exercised: int, discovered: int, whole: bool) -> int:
    """V7(d), unchanged: a crawl that did not see the whole product never reads 100."""
    percent = 100 if discovered == 0 else exercised * 100 // discovered
    return percent if whole else min(percent, 99) if discovered else 0


def compute_coverage(*, status: CrawlStatus, bound: str | None, bounds: CrawlBounds,
                     nodes: list[ScreenNode], edges: list[ScreenEdge],
                     spec: FlowSpec | None = None,
                     permitted: list[PermittedControl] | None = None,
                     policy: WritePolicy = WritePolicy.READ_ONLY) -> CrawlCoverage:
    by_control: dict[tuple[str, str], list[ScreenEdge]] = {}
    for edge in edges:
        by_control.setdefault((edge.from_node, edge.target), []).append(edge)
    discovered = exercised = 0
    holes: list[CoverageHole] = []
    hit: set[tuple[str, str]] = set()
    for node in nodes:
        tried = _tried(node.id, edges)
        seen: set[str] = set()
        for el in node.elements:
            if not is_candidate(el) or el.selector in seen:
                continue
            seen.add(el.selector)
            discovered += 1
            mine = by_control.get((node.id, el.selector), [])
            if any(e.outcome in PERFORMED for e in mine):
                exercised += 1
                hit.add(_key(node.url_template, el.selector))  # V9: as a project declares it
                continue
            reason = (_edge_reason(mine[0], status) if mine
                      else _untried_reason(node, tried, bounds, bound))
            holes.append(CoverageHole(node_id=node.id, url_template=node.url_template,
                                      selector=el.selector, name=el.name, reason=reason))
    not_entered = _screens_not_entered(nodes, edges, bounds)
    # CR5: a crawl that SKIPPED screens as unchanged did not explore the whole
    # portal, however cleanly its frontier drained. `whole` is what lets the
    # headline read 100%, so a skip must clear it -- otherwise an incremental
    # crawl that looked at one screen would report full coverage of the product.
    skipped_any = any(n.status is NodeStatus.SKIPPED_UNCHANGED for n in nodes)
    whole = status is CrawlStatus.COMPLETED and not not_entered and not skipped_any
    coverage = CrawlCoverage(
        controls_discovered=discovered, controls_exercised=exercised, holes=holes,
        screens_reached=sum(n.status is not NodeStatus.QUEUED for n in nodes),
        screens_queued_unvisited=sum(n.status is NodeStatus.QUEUED for n in nodes),
        screens_not_entered=not_entered,
        percent=_percent(exercised, discovered, whole),  # V7(d)
    )
    if permitted:  # V9: the denominator becomes what the ACCOUNT may do
        _permitted_coverage(coverage, permitted, hit, policy)
        coverage.percent = _percent(coverage.permitted_exercised or 0,
                                    coverage.permitted_total or 0, whole)
    if spec is not None:
        total = sum(1 for s in spec.screens if s.url_pattern)
        coverage.spec_screens_total = total
        coverage.spec_screens_reached = total - len(unreached_screens(spec, nodes))
    return coverage
