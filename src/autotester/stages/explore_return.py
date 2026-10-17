"""Getting the browser back onto a screen the crawl has already seen.

Split from `explore_node.py` for the 300-line cap: "try a candidate and
classify where it landed" and "find my way back to this exact screen" are two
jobs, and the second grew its own strategy ladder (back -> the node URL ->
replaying the edge that discovered it -> the base URL) when AT-227 showed that
a screen can exist with no URL that reaches it.

Contract: qa/contracts/explore.md X3, X4 (the replay chain is bounded).
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from autotester.browser.observe import observe
from autotester.schema.screen_graph import ScreenNode
from autotester.stages import explore_replay
from autotester.stages.screen_identity import node_from

if TYPE_CHECKING:
    from autotester.stages.explore_runtime import ExploreRuntime


MAX_REPLAY_DEPTH = 3
"""How many discovering edges `return_to` will chain. Bounded because the
chain is recursive and a crawl must always terminate (X4); three covers a
modal over a tab over a page and stops well short of a loop."""

RETURN_SETTLE_TOLERANCE_MS = 1500
"""AT-335: extra, BOUNDED tolerance for a rung whose fingerprint check ran
right after `settle()`'s fixed networkidle+500ms grace but before the page
actually finished re-rendering. The 1-in-14 rate this fixes IS measured
(AT-335's own observation plus qa/issues.jsonl AT-389's follow-up), because
every rung (go_back, goto, the replay click) checked the fingerprint exactly
once, so a re-render that landed a little later than `settle`'s fixed grace
read identically to 'landed on the wrong screen'. **The 1500ms/0.15s values
below are NOT independently measured** -- no evidence file records the real
distribution of re-render lag past `settle()`'s grace, so this is a
conservative, bounded guess at a threshold comfortably above typical lag,
not a proven-minimal one; tightening or loosening it later needs its own
measurement. Polled at `_RETURN_POLL_S` rather than slept once, so the
common case (already matches) still returns immediately; bounded so X4
still holds -- this is a ceiling, not a retry without one."""

_RETURN_POLL_S = 0.15


def _matches(rt: ExploreRuntime, node: ScreenNode,
             timeout_ms: int = RETURN_SETTLE_TOLERANCE_MS) -> bool:
    """Whether the browser is on `node` right now, tolerating a re-render
    still in flight (AT-335). `settle()` already ran once before every call
    site of this; this is the extra bounded window on top, polled instead of
    checked once."""
    deadline = time.monotonic() + timeout_ms / 1000
    while True:
        if _fingerprint(rt, node.depth) == node.id:
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(_RETURN_POLL_S)


def return_to(rt: ExploreRuntime, node: ScreenNode, *, depth: int = 0) -> bool:
    """Get the browser back onto `node` so the next candidate starts from the
    same place. Back, then the node's own URL, then replaying the action that
    discovered it, then the base URL.

    AT-227: the URL short-circuit used to return True on a URL match alone,
    which is wrong for every screen that shares a URL with another — dismiss a
    modal and the crawl went on questioning the dismissed screen as if it were
    still the veiled one. And once that was fixed, a second half of the same
    bug surfaced: a screen reached ONLY by a client-side state change has no
    URL that reaches it, so `goto` could never restore it and the crawl saw the
    dashboard behind the modal, enqueued it, and then abandoned it unexplored.
    `_replay_discovery` is the way back to such a screen.
    """
    rt.return_error = None  # never report a previous node's cause as this one's
    # AT-335 follow-up: at the terminal depth the replay rung bails at once, so
    # a poll after back/goto only delays that bail -- check once, no window.
    window_ms = 0 if depth >= MAX_REPLAY_DEPTH else RETURN_SETTLE_TOLERANCE_MS
    try:
        if (rt.session.current_url() == node.url_example
                and _fingerprint(rt, node.depth) == node.id):
            return True
        rt.session.go_back()
        rt.session.settle(timeout_ms=rt.bounds.settle_ms)
        if _matches(rt, node, window_ms):
            return True
        rt.session.goto(node.url_example)
        rt.session.settle(timeout_ms=rt.bounds.settle_ms)
        if _matches(rt, node, window_ms):
            return True
        replay_failed = _replay_discovery(rt, node, depth)
        if replay_failed is None:
            return True
        rt.return_error = ("back and the node URL both landed on a different screen; "
                           f"replaying the action that discovered it: {replay_failed}")
        _recover(rt)
        return False
    except Exception as exc:
        rt.return_error = f"{type(exc).__name__}: {exc}"
        _recover(rt)
        return False


def _replay_discovery(rt: ExploreRuntime, node: ScreenNode, depth: int) -> str | None:
    """Re-perform the edge that first reached `node`, from its own screen.

    `None` means the browser is back on `node`; any string is the reason it is
    not. Only ever replays an action the crawl already performed once and
    policy already allowed, so this introduces no action the safety guard has
    not already seen.

    Every exit names its own cause. The first version returned a bare `False`
    from four different places, including `except Exception: return False` —
    the shape AT-114 was filed for, where "this control is gone because the
    panel only opens once" and "the browser died" become the same answer. A
    replay that lands somewhere else is a failure, not a near miss, and a
    reader needs to know WHICH failure it was."""
    edge = rt.discovery.get(node.id)
    if edge is None:
        return "no edge discovered this screen (it was the crawl's seed)"
    if depth >= MAX_REPLAY_DEPTH:
        return f"the replay chain hit MAX_REPLAY_DEPTH={MAX_REPLAY_DEPTH}"
    if edge.from_node not in rt.nodes:
        return f"the screen it was discovered from ({edge.from_node[-6:]}) is not in this crawl"
    if not return_to(rt, rt.nodes[edge.from_node], depth=depth + 1):
        return f"could not get back to the screen it was discovered from: {why_lost(rt)}"
    # CR2 (crawl-traversal.md): re-performing the edge means re-issuing the
    # VALUES it was performed with, not only the click. A screen reachable only
    # behind a filled, submitted form is otherwise unreachable by `return_to`,
    # and a screen discovered BY a typed action was being "replayed" by clicking
    # a text input. `explore_replay` owns that and re-checks the X10-b gate.
    failed = explore_replay.perform(rt, edge)
    if failed is not None:
        return failed
    # AT-335: arrival is confirmed by the bounded poll, not a single sample --
    # a replayed edge is exactly the slow path the tolerance was measured for.
    if _matches(rt, node):
        return None
    return f"re-performing {edge.name or edge.target!r} landed on a different screen"


def why_lost(rt: ExploreRuntime) -> str:
    """The cause `return_to` recorded, or an explicit admission that none was.

    AT-108: the old text said only *that* the crawl lost a screen. "Cause not
    recorded" is still worse than a cause, but it is honest, and it is the
    string that tells a reader the gap is in this crawler rather than in the
    product it was looking at."""
    return rt.return_error or "cause not recorded"


def _fingerprint(rt: ExploreRuntime, depth: int) -> str:
    return node_from(observe(rt.session), rt.crawl.id, rt.project.slug, depth).id


def _recover(rt: ExploreRuntime) -> None:
    """Last resort: put the browser back on the base URL. A failure here is
    the most serious thing that can happen mid-crawl — every screen visited
    after it is suspect — so it is recorded rather than passed over (AT-108)."""
    try:
        rt.session.goto(rt.project.base_url)
        rt.session.settle(timeout_ms=rt.bounds.settle_ms)
    except Exception as exc:
        rt.return_error = (f"{rt.return_error or 'return failed'}; recovery to "
                           f"{rt.project.base_url} also failed — "
                           f"{type(exc).__name__}: {exc}")
