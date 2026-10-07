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
from urllib.parse import urlparse

from autotester.browser.observe import PageObserver, observe
from autotester.browser.session import BrowserSession, NavigationRefused
from autotester.schema.case import Case
from autotester.schema.crawl import Crawl, CrawlBounds, NoiseCount, SafetyPolicy
from autotester.schema.enums import Action, CrawlStatus, NodeStatus, Outcome, TraversalStrategy
from autotester.schema.project import Project
from autotester.schema.screen_graph import CrawlFrontier, ScreenNode
from autotester.stages import (
    crawl_coverage,
    explore_consent,
    explore_incremental,
    explore_node,
    explore_status,
    explore_traversal,
    network_capture,
)
from autotester.stages.execute import run_case
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


def _bootstrap_login(rt: ExploreRuntime, case: Case) -> bool:
    """Run the human-authored login case through `run_case` — the ONLY place
    the explorer types anything, and the only pre-crawl form submit (X10).

    **AT-226.** A persistent browser profile can already hold a live session,
    in which case the login page itself redirects away before the case's own
    FILL step ever runs — the field it names is not on the page at all, and
    `run_case` blocks for the full step timeout before reporting ERRORED.
    Checked once, before the case runs, against the case's own NAVIGATE step:
    if the browser lands somewhere other than the login page itself, the
    session is already authenticated and the case is skipped rather than run
    to a guaranteed timeout — a login page that redirects away from itself
    has already done its job, no app-specific marker needed."""
    login_step = next(
        (s for s in sorted(case.steps, key=lambda s: s.order) if s.action is Action.NAVIGATE),
        None,
    )
    if login_step is not None and _already_past_login(rt, login_step.target):
        return True
    result = run_case(case, rt.session)
    rt.store.save_result(rt.crawl.id, result)
    if result.outcome is not Outcome.COMPLETED:
        return False
    # AT-528: a COMPLETED step sequence is NOT proof of authentication — run_case
    # observes, it never judges (E1); the live Pathlynks crawl
    # crawl_01M31V5GHN91TE38MMB4BKM6HF completed while the app rendered "Invalid
    # credentials" (expected.visible_text is best-effort settle, never a gate).
    # The product's own verdict during the bootstrap is a first-party 401 on the
    # login API — precise, app-reported, fixture-neutral. A signed-out crawl may
    # never read COMPLETED: end LOGIN_FAILED naming the evidence.
    _console, failed, _dialogs, _popups = rt.observer.drain()
    auth_401 = [(u, why) for u, why in failed if why.rstrip().endswith("401")]
    if auth_401:
        url, why = auth_401[0]
        rt.stop_reason = (f"login case 'completed' but the server rejected it "
                          f"({url} -> {why} — invalid credentials?) — AT-528 guard")
        return False
    return True


def _already_past_login(rt: ExploreRuntime, login_url: str) -> bool:
    """Navigate to the case's login page; report whether the app redirected
    away (AT-226). Still there -> record the login signature for X18(a).
    AT-273: a nav failure must not read as "not yet authenticated" `False` —
    still the safe fallback, but its CAUSE is kept."""
    try:
        rt.session.goto(login_url)
        rt.session.settle(timeout_ms=rt.bounds.settle_ms)
    except NavigationRefused as exc:
        rt.login_precheck_error = f"refused by the domain guard: {exc}"
        return False
    except Exception as exc:
        rt.login_precheck_error = f"{type(exc).__name__}: {exc}"
        return False
    if urlparse(rt.session.current_url()).path != urlparse(login_url).path:
        return True
    rt.login_signature, rt.login_observe_error = explore_status.observed_signature(rt.session)
    explore_node.record_login_observe_failure(rt, rt.login_observe_error)
    return False


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


def _login_failed_reason(rt: ExploreRuntime) -> str:
    """AT-273: name the login-precheck's own swallowed cause when the case
    then genuinely failed too, so an operator sees the precheck itself
    glitched rather than only that login did. AT-528: a failure that already
    named a SPECIFIC cause (the 401 guard sets its own stop_reason) keeps it
    verbatim — the vaguer sentence would overwrite the server's verdict."""
    if rt.stop_reason and "AT-528" in rt.stop_reason:
        return rt.stop_reason
    reason = "login case did not complete"
    if rt.login_precheck_error:
        reason += f" (precheck also failed: {rt.login_precheck_error})"
    return reason


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
    if login_case is not None and not _bootstrap_login(rt, login_case):
        rt.stop_reason = _login_failed_reason(rt)
        return _finish(rt, CrawlStatus.LOGIN_FAILED)
    if _seed(rt) is None:
        rt.stop_reason = f"could not open base_url -- {rt.seed_error or 'cause not recorded'}"
        return _finish(rt, CrawlStatus.ABORTED)
    _bfs(rt)
    return _finish(rt, _terminal_status(rt, rt.frontier_exhausted, login_case))
