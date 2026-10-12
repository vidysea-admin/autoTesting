"""EXPLORE: a bounded, safety-gated BFS crawl of a (usually logged-in) app.

Contract: qa/contracts/explore.md. **This is the one stage permitted to
invent a click or a navigation** — `execute.md` E5 ("`run_case` performs
exactly the actions in `case.steps`") stays intact; the explorer never routes
through `run_case` except for the human-authored login bootstrap case. Every
bound can end the crawl and name itself in `Crawl.stop_reason`, and no stop
condition depends on provider output — a crawl completes with `provider=mock`
(X4). Per-node work lives in `explore_node.py`; safety in `explore_safety.py`.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import UTC, datetime

from autotester.browser.observe import PageObserver, observe
from autotester.browser.session import BrowserSession, NavigationRefused
from autotester.schema.case import Case
from autotester.schema.crawl import Crawl, CrawlBounds, NoiseCount, SafetyPolicy
from autotester.schema.enums import CrawlStatus, NodeStatus, TraversalStrategy
from autotester.schema.project import Project
from autotester.schema.screen_graph import CrawlFrontier, ScreenNode
from autotester.stages import (
    crawl_coverage,
    explore_consent,
    explore_incremental,
    explore_login,
    explore_node,
    explore_status,
    explore_traversal,
    network_capture,
)
from autotester.stages.explore_runtime import ExploreRuntime
from autotester.stages.explore_safety import DialogBreaker
from autotester.stages.screen_identity import node_from
from autotester.store.project_store import ProjectStore

__all__ = ["ExploreRuntime", "run_crawl", "stop_reason"]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def stop_reason(rt: ExploreRuntime) -> str | None:
    """Which bound (if any) has been reached. Checked before every node and
    before every action, so a bound cannot be overshot by a whole node."""
    if rt.stop_reason in {"max_screens", "max_actions", "wall_clock_s", "max_depth"}:
        return rt.stop_reason
    if rt.frontier.screens_found >= rt.bounds.max_screens:
        return "max_screens"
    if rt.frontier.actions_used >= rt.bounds.max_actions:
        return "max_actions"
    if rt.clock() - rt.started >= rt.bounds.wall_clock_s:
        return "wall_clock_s"
    return None


def _seed(rt: ExploreRuntime) -> ScreenNode | None:
    """Open `base_url` and record it as the first node.

    AT-098: every distinct failure keeps its CAUSE — a `NavigationRefused` is
    the X7 SECURITY refusal and must never read like a DNS timeout, so the
    operator watching a live crawl can tell the product was down from the
    crawl was refused by its own domain guard.
    """
    try:
        rt.session.goto(rt.project.base_url)
        rt.session.settle(timeout_ms=rt.bounds.settle_ms)
        observation = observe(rt.session)
    except NavigationRefused as exc:
        rt.seed_error = f"refused by the domain guard: {exc}"
        return None
    except Exception as exc:
        rt.seed_error = f"{type(exc).__name__}: {exc}"
        return None
    node = node_from(observation, rt.crawl.id, rt.project.slug, depth=0)
    node = node.model_copy(update={"screenshot_ref": explore_node.capture(rt, node)})
    rt.nodes[node.id] = node
    rt.store.add_node(node)
    rt.frontier.queue.append(node.id)
    rt.frontier.screens_found += 1
    return node


def _bfs(rt: ExploreRuntime) -> None:
    """Drain the frontier in `rt.strategy`'s order. Named `_bfs` still because
    `bfs` remains the default and the whole portal is still mapped breadth-first
    either way (CR1); `explore_traversal` owns the ordering."""
    while rt.frontier.queue:
        reached = stop_reason(rt)
        if reached:
            rt.stop_reason = reached
            return
        node_id = explore_traversal.next_node_id(
            queue=rt.frontier.queue, nodes=rt.nodes, discovery=rt.discovery,
            strategy=rt.strategy, last_visited=rt.last_visited)
        node = rt.nodes.get(node_id) if node_id is not None else None
        if node is None:
            continue
        if not explore_incremental.skip_unchanged(rt, node):
            explore_node.visit_node(rt, node)
        rt.last_visited = node.id
        rt.frontier.visited.append(node.id)
        rt.store.save_frontier(rt.crawl.id, rt.frontier)
    explore_traversal.drain_deferred(rt)  # PS2: destructive controls, crawl-global last
    # Draining the queue after a bound or abandoned visit leaves controls untried.
    abandoned = [f"{n.status.value} ({n.url_template})" for n in rt.nodes.values()
                 if n.status in {NodeStatus.ABORTED_ERROR, NodeStatus.ABORTED_DIALOG}]
    rt.frontier_exhausted = rt.stop_reason is None and not abandoned
    rt.stop_reason = rt.stop_reason or (
        "abandoned visits: " + ", ".join(sorted(abandoned)) if abandoned
        else explore_incremental.exhausted_reason(rt.skipped_unchanged))


def _terminal_status(rt: ExploreRuntime, completed: bool, login_case: Case | None) -> CrawlStatus:
    """Decided in `explore_status` (AT-242, X18); this feeds it the graph."""
    status, reason = explore_status.terminal_status(
        completed=completed, actions_used=rt.frontier.actions_used, denied=rt.denied,
        nodes=list(rt.nodes.values()), edges=rt.store.list_edges(rt.crawl.id),
        login_case=login_case, login_signature=rt.login_signature,
        login_observe_error=rt.login_observe_error, current_stop_reason=rt.stop_reason,
    )
    if reason is not None:
        rt.stop_reason = reason
    return status


def _fold_network_evidence(rt: ExploreRuntime) -> None:
    """T-170/NA1: fold first-party responses into NETWORK evidence, once,
    at the end (no per-step RawResult to fold into, unlike execute.py)."""
    for item in network_capture.first_party_evidence(
            rt.observer.drain_responses(), rt.project, rt.policy, rt.session.secrets.redactor()):
        rt.store.add_crawl_network(rt.crawl.id, item)


def _finish(rt: ExploreRuntime, status: CrawlStatus) -> Crawl:
    _fold_network_evidence(rt)
    crawl = rt.crawl.model_copy(update={
        "status": status,
        "stop_reason": rt.session.secrets.scrub_optional(rt.stop_reason),  # AT-350
        "finished_at": _now_iso(),
        "screens": len(rt.nodes),
        "edges": rt.edges,
        "actions": rt.frontier.actions_used,
        "denied": rt.denied,
        "issues": rt.issues,
        "tool_failures": rt.tool_failures,
        "skipped_unchanged": rt.skipped_unchanged,  # CR3/CR5: visible on every surface
        "noise_counts": [NoiseCount(host=h, count=c) for h, c in sorted(rt.noise.items())],
        "coverage": crawl_coverage.of_run(rt, status),  # V7
    })
    rt.crawl = crawl
    rt.store.save_crawl(crawl)
    rt.store.save_frontier(crawl.id, rt.frontier)
    return crawl


def run_crawl(
    project: Project,
    session: BrowserSession,
    store: ProjectStore,
    *,
    observer: PageObserver,
    bounds: CrawlBounds | None = None,
    policy: SafetyPolicy | None = None,
    login_case: Case | None = None,
    crawl_id: str | None = None,
    clock: Callable[[], float] = time.monotonic,
    strategy: TraversalStrategy = TraversalStrategy.BFS,
    incremental: bool = False,
) -> Crawl:
    """Crawl `project` breadth-first within `bounds`, refusing anything
    `policy` denies. Returns the finished `Crawl` envelope; the graph itself
    is on disk (nodes/edges/issues JSONL), loadable even if this raises
    partway (X11). `crawl_id` is accepted so a caller can mint it first and
    point the session's screenshot dir at `crawl/<id>/shots/`. **Raises
    `ApprovalRequired` before anything is created or opened** (D-018)."""
    bounds = bounds or CrawlBounds()
    policy = policy or SafetyPolicy(write_policy=project.write_policy)
    # D-018 gate 2 + X10-b condition 3 (AT-535), decided in `explore_consent`
    # (line-cap split) — before anything is created or opened.
    explore_consent.require_consent(project, store, bounds, policy=policy)
    envelope = {
        "project": project.slug,
        "bounds": bounds,
        "policy": policy,
        "login_case_id": login_case.id if login_case else None,
        "strategy": strategy,
        "incremental": incremental,
        "started_at": _now_iso(),
    }
    crawl = Crawl(id=crawl_id, **envelope) if crawl_id else Crawl(**envelope)  # type: ignore[arg-type]
    store.save_crawl(crawl)
    rt = ExploreRuntime(
        project=project, session=session, store=store, crawl=crawl, observer=observer,
        breaker=DialogBreaker(crawl.bounds.dialog_repeat_limit), clock=clock,
        started=clock(), frontier=CrawlFrontier(), strategy=strategy,
        persona=explore_incremental.load_index(store, enabled=incremental),
    )
    if login_case is not None and not explore_login.bootstrap_login(rt, login_case):
        rt.stop_reason = explore_login.login_failed_reason(rt)
        return _finish(rt, CrawlStatus.LOGIN_FAILED)
    if _seed(rt) is None:
        rt.stop_reason = f"could not open base_url -- {rt.seed_error or 'cause not recorded'}"
        return _finish(rt, CrawlStatus.ABORTED)
    _bfs(rt)
    return _finish(rt, _terminal_status(rt, rt.frontier_exhausted, login_case))
