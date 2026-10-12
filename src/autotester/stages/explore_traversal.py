"""Which screen the crawl visits next — the frontier's ORDER, and nothing else.

Contract: qa/contracts/crawl-traversal.md CR1 (strategy), CR6 (deterministic,
no provider). A new module rather than more lines in `explore_node.py` or
`explore.py`, both of which sit exactly at the C2 300-line cap; the contract's
"How a unit is verified" section names that split explicitly.

**`bfs` is byte-identical to the original behaviour** — `queue.pop(0)`, FIFO,
the same frontier `explore.py::_bfs` always walked.

**`hybrid` is the Crawljax depth-first candidate ORDERING, ported as fresh
Python** (`docs/research/crawl-reuse-2026-09.md` §1: Apache-2.0, read
permission, idea only — no code is copied and Crawljax is not a dependency).
BFS still maps the portal: every discovered screen is still enqueued exactly as
before, by `explore_node._enqueue`, and nothing is ever dropped from the queue
by this module. What changes is only WHICH queued screen comes off next: having
just entered a workflow, the crawl descends into the screen that workflow led
to, before returning to breadth order. That is why this is not D-023's rejected
single happy-path DFS — D-023 rejected depth-first as the ONLY traversal, a
single line through the portal that never maps it. Here the whole frontier is
still mapped and still drained; only its order differs.

**Termination (X4, `explore.md`, unamended).** `next_node_id` removes exactly
one id from `queue` per call and adds none, on every strategy and every branch.
Ids enter the queue only through `_enqueue`, which is bounded by `max_screens`
and `max_depth`. So the same argument that terminates `bfs` terminates `hybrid`
unchanged, and `hybrid` introduces no bound of its own — X4's four bounds are
the only ones, exactly as CR1 requires.

**Destructive-last, crawl-global (PS2, `permission-surface.md`, D-040 verbatim).**
The second half of this module is the ORDER of a control across the whole crawl,
not across one screen: a control the crawl would press that is destructive by name
is parked by `defer_destructive` instead of pressed, and `drain_deferred` presses
the parked ones only once the non-destructive frontier is exhausted. So every
destructive press comes after every non-destructive one in the exercise sequence.
A screen first reached BY a destructive press is recorded but not explored —
exploring it would put a non-destructive action after a destructive one — and the
crawl says so in `stop_reason` rather than reading "complete". Bounded like any
other action: `drain_deferred` obeys `explore.stop_reason` and adds no bound.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from autotester.schema.enums import (
    Action,
    EdgeOutcome,
    IssueKind,
    NodeStatus,
    TraversalStrategy,
)
from autotester.schema.screen_graph import ElementRef, ScreenEdge, ScreenNode
from autotester.stages.explore_safety import is_destructive

if TYPE_CHECKING:
    from autotester.stages.explore_runtime import ExploreRuntime


def next_node_id(
    *,
    queue: list[str],
    nodes: dict[str, ScreenNode],
    discovery: dict[str, ScreenEdge],
    strategy: TraversalStrategy,
    last_visited: str | None,
) -> str | None:
    """Pop and return the next screen id to visit, or None when the frontier is
    empty. **Mutates `queue`** — exactly one id is removed per call.

    Pure apart from that pop: the decision is a function of frontier state alone
    (CR6). No provider, no clock, no randomness — two crawls over the same graph
    make the same choices in the same order.
    """
    if not queue:
        return None
    if strategy is not TraversalStrategy.HYBRID or last_visited is None:
        return queue.pop(0)
    descend = _descendant_of(last_visited, queue=queue, nodes=nodes, discovery=discovery)
    if descend is None:
        return queue.pop(0)
    queue.remove(descend)
    return descend


def _descendant_of(
    parent_id: str,
    *,
    queue: list[str],
    nodes: dict[str, ScreenNode],
    discovery: dict[str, ScreenEdge],
) -> str | None:
    """The queued screen this workflow just led to: the deepest queued node whose
    discovering edge came FROM `parent_id`. None when the workflow has no
    unvisited continuation, which is what makes the descent backtrack into
    breadth order instead of stalling.

    Ties break on the node id so the order is total and reproducible (CR6) —
    `max()` on depth alone would depend on dict insertion order.
    """
    children = [
        node_id for node_id in queue
        if node_id in nodes
        and (edge := discovery.get(node_id)) is not None
        and edge.from_node == parent_id
    ]
    if not children:
        return None
    return max(children, key=lambda node_id: (nodes[node_id].depth, node_id))


def defer_destructive(rt: ExploreRuntime, node: ScreenNode, el: ElementRef) -> bool:
    """Park `el` for the end-of-crawl pass when it is destructive by name. True = parked.

    Called only for a control policy already ALLOWED (a denied one is recorded in place —
    a refusal is not an exercise, so it does not have to wait)."""
    if not is_destructive(el, rt.policy):
        return False
    rt.deferred.append((node.id, el))
    return True


def drain_deferred(rt: ExploreRuntime) -> None:
    """Press every parked destructive control, in the order it was parked (PS2).

    Runs once, after the non-destructive frontier is empty. Each press re-enters its
    screen first; a screen it cannot re-enter is filed, never guessed at. Screens a press
    discovers stay QUEUED (named in `stop_reason`): nothing ordinary may follow this pass."""
    from autotester.stages import explore, explore_node  # lazy: both import this package's stages
    from autotester.stages.explore_return import return_to, why_lost

    while rt.deferred:
        reached = explore.stop_reason(rt)
        if reached:
            rt.stop_reason = reached
            return
        node_id, el = rt.deferred.pop(0)
        node = rt.nodes[node_id]
        if not return_to(rt, node):
            explore_node.record_edge(rt, node, el, Action.BACK, EdgeOutcome.ERRORED,
                                     f"could not return to this screen: {why_lost(rt)}")
            # AT-113: an unreachable screen is never a clean crawl -- file it and mark it.
            explore_node.add_issue(rt, node.id, IssueKind.NAVIGATION,
                                   "lost this screen before its destructive controls were "
                                   f"tried: {why_lost(rt)}")
            explore_node._mark(rt, node, NodeStatus.ABORTED_ERROR)
            rt.deferred = [(n, e) for n, e in rt.deferred if n != node_id]
            continue
        rt.frontier.actions_used += 1
        edge = explore_node.try_action(rt, node, el)
        if explore_node._heartbeat_due(rt):
            explore_node.heartbeat(rt)
        if edge.outcome is EdgeOutcome.DIALOG:
            explore_node.add_issue(rt, node.id, IssueKind.DIALOG, "dialog repeat limit reached")
            rt.deferred = [(n, e) for n, e in rt.deferred if n != node_id]
    if rt.frontier.queue and rt.stop_reason is None:
        rt.stop_reason = (f"destructive_last ({len(rt.frontier.queue)} screen(s) first reached by "
                          "a destructive press were recorded, not explored)")
