"""One node's worth of exploring: try each safe candidate action, record what
happened, and get back to the node before trying the next one.

Split from `explore.py` for the 300-line cap. Contract: qa/contracts/explore.md
X5-X9 â€” every decision about whether an action is allowed is delegated to
`explore_safety.py`; nothing here re-implements a safety rule.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from urllib.parse import urljoin

from autotester.browser.observe import observe
from autotester.browser.secrets import host_of
from autotester.browser.session import NavigationRefused, check_destination
from autotester.schema.crawl import CrawlIssue
from autotester.schema.enums import Action, EdgeOutcome, IssueKind, NodeStatus
from autotester.schema.screen_graph import ElementRef, ScreenEdge, ScreenNode
from autotester.stages import crawl_coverage, explore, explore_safety, explore_traversal
from autotester.stages.explore_return import return_to, why_lost
from autotester.stages.explore_safety import (
    OFF_DOMAIN_LINK_REFUSED,
    classify_request,
    deny_reason,
    link_is_safe,
    typing_allowed,
    typing_target_allowed,
)
from autotester.stages.screen_identity import node_from

if TYPE_CHECKING:
    from autotester.stages.explore_runtime import ExploreRuntime


def capture(rt: ExploreRuntime, node: ScreenNode) -> str | None:
    """Screenshot this node through the session (masked, B7). Never fatal â€”
    a crawl that cannot screenshot still produces a graph.

    AT-114: staying non-fatal is right; staying SILENT was not. `session.
    screenshot` retries the one transient CDP race AT-036 documents and
    deliberately re-raises everything else, because everything else is real.
    A bare `except Exception: return None` threw that distinction away â€” a node
    with no screenshot looked identical whether the compositor hiccuped twice
    or the browser had died. The cause is now recorded as an EVIDENCE issue, a
    kind of its own so a tool failure is never counted as a product bug.
    """
    try:
        return rt.session.screenshot(f"node-{node.id[-6:]}").path
    except Exception as exc:
        add_issue(rt, node.id, IssueKind.EVIDENCE,
                  f"could not screenshot this screen â€” {type(exc).__name__}: {exc}")
        return None


def record_login_observe_failure(rt: ExploreRuntime, error: str | None) -> None:
    """AT-474: the login page's signature could not be observed for X18(a) â€” file it as
    an EVIDENCE issue (never a product bug, X16) so `tool_failures` counts it, instead of
    the check going silently unjudged. No node exists yet at this point in the crawl."""
    if error is not None:
        add_issue(rt, "", IssueKind.EVIDENCE, f"could not observe the login page -- {error}")


def add_issue(rt: ExploreRuntime, node_id: str, kind: IssueKind, detail: str,
              *, first_party: bool = True) -> None:
    # AT-341: `detail` is often an exception's own message, which can embed a
    # resolved secret (AT-076) â€” scrub before this reaches disk, same as evidence.
    issue = CrawlIssue(crawl_id=rt.crawl.id, project=rt.project.slug, kind=kind,
                       node_id=node_id, detail=rt.session.secrets.scrub_optional(detail) or "",
                       first_party=first_party)
    rt.store.add_crawl_issue(issue)
    if kind is IssueKind.EVIDENCE:
        rt.tool_failures += 1  # AT-120: never inflate the product's issue total
    else:
        rt.issues += 1


def record_edge(rt: ExploreRuntime, node: ScreenNode, el: ElementRef, action: Action,
                outcome: EdgeOutcome, reason: str | None = None,
                to_node: str | None = None) -> ScreenEdge:
    edge = ScreenEdge(crawl_id=rt.crawl.id, from_node=node.id, to_node=to_node,
                      action=action, target=el.selector, name=el.name,
                      outcome=outcome, reason=rt.session.secrets.scrub_optional(reason))
    rt.store.add_edge(edge)
    rt.edges += 1
    return edge


def drain(rt: ExploreRuntime, node_id: str) -> bool:
    """Fold the observer's buffer into issues and noise. Returns True when the
    dialog circuit breaker has tripped for this node (X8)."""
    console, failed, dialogs, _popups = rt.observer.drain()
    tripped = any(rt.breaker.record(node_id, event) for event in dialogs)
    for line in console:
        add_issue(rt, node_id, IssueKind.CONSOLE, line)
    for url, why in failed:
        bucket = classify_request(url, rt.project, rt.policy)
        if bucket == "first_party":
            add_issue(rt, node_id, IssueKind.NETWORK, f"{url} -> {why}")
        elif bucket == "noise":
            host = host_of(url) or "unknown"
            rt.noise[host] = rt.noise.get(host, 0) + 1
    return tripped


def _enqueue(rt: ExploreRuntime, new: ScreenNode, edge: ScreenEdge) -> None:
    if new.id in rt.nodes:
        return
    if new.depth > rt.bounds.max_depth:
        if rt.stop_reason is None:
            rt.stop_reason = explore.stop_reason(rt) or "max_depth"
        return
    if rt.frontier.screens_found >= rt.bounds.max_screens:
        return
    new = new.model_copy(update={"discovered_by": edge.id,
                                 "screenshot_ref": capture(rt, new)})
    rt.nodes[new.id] = new
    rt.discovery[new.id] = edge
    rt.store.add_node(new)
    rt.frontier.queue.append(new.id)
    rt.frontier.screens_found += 1


def _heartbeat_due(rt: ExploreRuntime) -> bool:
    n = rt.frontier.actions_used
    return n == 1 or n % rt.bounds.heartbeat_every_actions == 0


def heartbeat(rt: ExploreRuntime) -> None:
    """AT-483: re-persist the crawl envelope mid-BFS -- progress counts + a fresh
    `heartbeat_at`, the liveness signal `explore_status.displayed_status` checks."""
    rt.crawl = rt.crawl.model_copy(update={
        "heartbeat_at": datetime.now(UTC).isoformat(),
        "screens": len(rt.nodes), "actions": rt.frontier.actions_used,
        "edges": rt.edges, "denied": rt.denied, "issues": rt.issues,
        "tool_failures": rt.tool_failures,
    })
    rt.store.save_crawl(rt.crawl)


def _perform(rt: ExploreRuntime, el: ElementRef) -> Action:
    """Do the thing: navigate a safe link by URL, otherwise click. Returns the
    `Action` performed so the edge records it truthfully."""
    if el.role == "link" and el.href:
        rt.session.goto(urljoin(rt.session.current_url(), el.href))
        rt.session.settle(timeout_ms=rt.bounds.settle_ms)
        return Action.NAVIGATE
    rt.session.click(el.selector)
    rt.session.settle(timeout_ms=rt.bounds.settle_ms)
    return Action.CLICK


def try_action(rt: ExploreRuntime, node: ScreenNode, el: ElementRef) -> ScreenEdge:
    """Perform one candidate action and classify where it landed."""
    action = Action.NAVIGATE if (el.role == "link" and el.href) else Action.CLICK
    try:
        action = _perform(rt, el)
    except NavigationRefused as exc:
        return record_edge(rt, node, el, action, EdgeOutcome.OFF_DOMAIN_REFUSED, str(exc))
    except Exception as exc:
        return record_edge(rt, node, el, action, EdgeOutcome.ERRORED,
                           f"{type(exc).__name__}: {exc}")
    if drain(rt, node.id):
        return record_edge(rt, node, el, action, EdgeOutcome.DIALOG, "dialog repeat limit")
    try:  # X7: the host is re-checked after EVERY action, not only on goto
        check_destination(rt.project, rt.session.current_url())
    except NavigationRefused as exc:
        add_issue(rt, node.id, IssueKind.NAVIGATION, str(exc))
        return record_edge(rt, node, el, action, EdgeOutcome.OFF_DOMAIN_REFUSED, str(exc))
    new = node_from(observe(rt.session), rt.crawl.id, rt.project.slug, node.depth + 1)
    if new.id == node.id:
        return record_edge(rt, node, el, action, EdgeOutcome.SAME_SCREEN, None, node.id)
    edge = record_edge(rt, node, el, action, EdgeOutcome.NAVIGATED, None, new.id)
    _enqueue(rt, new, edge)
    return edge


def _mark(rt: ExploreRuntime, node: ScreenNode, status: NodeStatus) -> None:
    """Record how this node ended, in memory AND on disk â€” `add_node` is
    idempotent, so an updated status needs `update_node` to land."""
    updated = node.model_copy(update={"status": status})
    rt.nodes[node.id] = updated
    rt.store.update_node(updated)


def _candidate_denial(rt: ExploreRuntime, node: ScreenNode, el: ElementRef) -> bool:
    """Record and skip anything policy refuses. True = skipped."""
    reason = deny_reason(el, rt.policy)
    if reason is not None:
        outcome = (EdgeOutcome.SKIPPED_UNNAMED if reason == "unnamed control"
                   else EdgeOutcome.DENIED_POLICY)
        record_edge(rt, node, el, Action.CLICK, outcome, reason)
        rt.denied += 1
        return True
    if (el.role == "link" and el.href
            and not link_is_safe(el, rt.project, rt.session.current_url())):
        record_edge(rt, node, el, Action.NAVIGATE, EdgeOutcome.OFF_DOMAIN_REFUSED,
                    OFF_DOMAIN_LINK_REFUSED)
        add_issue(rt, node.id, IssueKind.NAVIGATION,
                  f"off-domain link refused: {el.name or el.selector}")
        rt.denied += 1
        return True
    return False


def _report_overlay(rt: ExploreRuntime, node: ScreenNode) -> None:
    """File ONE issue naming the controls this screen covered up (AT-227).

    Report covered controls without hiding the obstruction; reachable overlay
    controls remain candidates for ordinary exploration.
    """
    covered = [el for el in node.elements if el.visible and el.enabled and el.obscured]
    if not covered:
        return
    reachable = [el.name or el.selector for el in node.elements
                 if el.visible and el.enabled and not el.obscured]
    add_issue(rt, node.id, IssueKind.OVERLAY,
              f"{len(covered)} control(s) on this screen are covered by an in-page "
              f"overlay and were not tried: {_names(covered)}. Reachable instead: "
              f"{', '.join(reachable[:8]) or 'nothing'}")


def _names(elements: list[ElementRef], limit: int = 8) -> str:
    shown = [el.name or el.selector for el in elements[:limit]]
    more = len(elements) - len(shown)
    return ", ".join(shown) + (f" (+{more} more)" if more > 0 else "")


def _click_loop(rt: ExploreRuntime, node: ScreenNode, typed: int) -> bool:
    """The click phase after the typing pre-pass (AT-533: ONE shared per-node budget).
    Returns False when the node ended ABORTED_DIALOG/ABORTED_ERROR; True otherwise."""
    tried = 0
    for el in explore_safety.destructive_last(node.elements, rt.policy):
        # AT-533: typing and clicking share ONE per-node budget (typed pre-pass first)
        if tried + typed >= rt.bounds.per_node_action_cap:
            break
        # AT-534: never click a form field the gate refused to type (wasted click, false coverage)
        if typing_target_allowed(el) and not typing_allowed(rt.policy):
            continue
        reached = explore.stop_reason(rt)
        if reached:  # AT-463: name the bound, or a last screen reads "frontier empty"
            rt.stop_reason = reached
            break
        if not crawl_coverage.is_candidate(el) or _candidate_denial(rt, node, el):
            continue
        tried += 1
        if explore_traversal.defer_destructive(rt, node, el):  # PS2: crawl-global, drained last
            continue
        rt.frontier.actions_used += 1
        edge = try_action(rt, node, el)
        if _heartbeat_due(rt):
            heartbeat(rt)
        if edge.outcome is EdgeOutcome.DIALOG:
            add_issue(rt, node.id, IssueKind.DIALOG, "dialog repeat limit reached")
            _mark(rt, node, NodeStatus.ABORTED_DIALOG)
            return False
        if not return_to(rt, node):
            record_edge(rt, node, el, Action.BACK, EdgeOutcome.ERRORED,
                        f"could not return to this screen: {why_lost(rt)}")
            add_issue(rt, node.id, IssueKind.NAVIGATION,
                      "lost this screen mid-exploration — remaining controls not "
                      f"tried: {why_lost(rt)}")
            _mark(rt, node, NodeStatus.ABORTED_ERROR)
            return False
    _mark(rt, node, NodeStatus.EXPLORED)
    return True


def visit_node(rt: ExploreRuntime, node: ScreenNode) -> None:
    """Try every allowed candidate on `node`, bounded by the per-node cap.

    AT-534: a typing target the pre-pass was not allowed to fill must not be
    silently clicked afterwards and counted exercised — the click loop skips
    the pre-pass's refusal targets, whose DENIED_POLICY edge is already on
    disk. (`typing_allowed` is false but a *different* element is a click
    candidate, ordinary rules apply.)

    AT-113 (checker-found, gated T-145): a node the crawl could never get back
    to used to be marked ABORTED_ERROR with NO issue filed, and — mid-loop —
    the same failure recorded an edge but then fell through to EXPLORED
    anyway. Neither surfaced anywhere a human would look: the crawl still
    reported `status=completed`, `stop_reason='frontier empty'`, `issues=0`,
    and the unreachable node entered the FlowSpec via `merge_screens` as an
    ordinary screen — a partial crawl indistinguishable from a complete one,
    which is the one failure mode a live production run can least afford.
    Both paths now file a NAVIGATION issue and the node's final status always
    matches what actually happened to it.
    """
    if not return_to(rt, node):
        add_issue(rt, node.id, IssueKind.NAVIGATION,
                  "could not return to this screen before exploring it — abandoned "
                  f"unexplored: {why_lost(rt)}")
        _mark(rt, node, NodeStatus.ABORTED_ERROR)
        return
    _report_overlay(rt, node)
    from autotester.stages.explore_typing import type_form  # lazy: explore_typing imports back
    typed = type_form(rt, node)
    _click_loop(rt, node, typed)
