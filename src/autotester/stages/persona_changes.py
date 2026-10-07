"""What moved in the product since the last crawl: new / changed / missing / broken.

Contract: qa/contracts/crawl-traversal.md CR4, with CR5's honesty interaction.
A new module rather than more lines in `stages/portal_persona.py`, which the
contract names as already near its C2 cap.

`portal_persona.py::_merge` is PP2 **add-only**: new screens are appended and
nothing existing is ever dropped, blanked or rewritten. CR4 does not change
that — this module never mutates the persona. It computes a CLASSIFICATION
alongside the merge, which is recorded on the dated `PersonaRevision` (PP3).
The persona stays add-only; the revision history carries the diff.

**Scope (CR4's own wording).** This classifies the CRAWL-SOURCED screens only:
a stored screen with a `signature` came from a crawl, so a crawl can be
evidence about it. A stored screen with no signature came from a reviewed
FlowSpec or a taught flow; a crawl not reaching it is not evidence it is gone,
so it is left out of the diff entirely rather than reported as `missing`.

**The honesty rule (CR5).** `missing` is a claim that a screen the product used
to have is no longer reachable. A crawl that did not exhaust its frontier never
saw the whole product, so it cannot make that claim about anything — those
stored keys go to `missing_unjudged`, which is a disclosed unknown, not a
finding. Reporting them as `missing` would turn "we never got there" into "the
product lost a screen", which is the precise dishonesty this contract exists to
stop. Two things stop a frontier being exhausted for judging purposes: a bound
firing, and a CR3 skip (`_judged_exhausted` — see it for the live reproduction).
"""

from __future__ import annotations

from autotester.schema.enums import NodeStatus
from autotester.schema.portal_persona import PortalPersona
from autotester.schema.screen_graph import ScreenNode
from autotester.stages.explore_incremental import node_key

BROKEN_STATUSES = frozenset({NodeStatus.ABORTED_ERROR, NodeStatus.ABORTED_DIALOG})
"""A visit that ended in an error or a dialog storm. `SKIPPED_UNCHANGED` is
deliberately absent: a skipped screen was not looked at, so it is evidence of
nothing (CR5)."""

CATEGORIES = ("new_screens", "changed_screens", "missing_screens",
              "broken_screens", "missing_unjudged")
"""The five REPORTABLE categories CR4/CR5 name — what `counts()` counts and a
surface renders. Adding a sixth needs a contract amendment, so it stays five."""

PROVENANCE = ("healthy_screens",)
"""Fields `classify` also returns that are NOT findings: evidence this crawl
recorded so a LATER crawl can classify honestly (`_previously_broken`). Kept
separate from CATEGORIES so the five-category surface cannot drift by accident."""


def _previously_broken(existing: PortalPersona | None) -> frozenset[str]:
    """CR4: `broken` means an error status "that the prior stored screen did not
    carry". A `PersonaScreen` carries no status — PP2 forbids rewriting one — so
    the prior state is read from the append-only revision history instead.

    **Still broken, replayed over the whole history** (`ISS-t165-crawl-traversal-4`).
    Reading only the most recent revision that classified anything was wrong: a
    screen broken in revision 1 and still broken in revision 3 was re-reported
    as newly broken whenever revision 2 happened to record something unrelated
    (a new screen, say), because revision 2 was "the most recent that classified
    anything" and its own `broken_screens` was empty.

    A plain union over every revision fixes that and introduces the OPPOSITE
    dishonesty: a screen that broke, was later observed HEALTHY, then genuinely
    relapsed could never be reported broken again. The issue's own `expected`
    asks for the union "minus any later revision that observed the screen and
    found it not-broken", so the history is replayed in order: `broken_screens`
    adds a key, `healthy_screens` (reached-and-not-broken, recorded by
    `classify` itself) removes it. A revision that did not reach the screen
    changes nothing, which is exactly the case the issue was filed about.
    """
    if existing is None:
        return frozenset()
    broken: set[str] = set()
    for revision in existing.history:
        broken.update(revision.broken_screens)
        broken.difference_update(revision.healthy_screens)
    return frozenset(broken)


def _stored_signatures(existing: PortalPersona | None) -> dict[str, set[str]]:
    """Persona key -> EVERY structural signature stored under it.

    `ISS-t165-crawl-traversal-2`: `PersonaScreen.key()` is `url_template`-only,
    so two structurally distinct screens sharing a URL (an SPA state toggle —
    the shape X3/X14 document as real) land on one key. Keying the diff by
    `{key: one screen}` therefore threw the second one away before it could be
    classified at all. A key now carries a SET of signatures: the second screen
    is part of its key's evidence instead of vanishing. The key stays
    `url_template`-only deliberately — folding the signature into `key()` would
    destroy CR4's `changed`, which is defined as *same key, different signature*.

    A key with an EMPTY set came from a reviewed FlowSpec only (no signature),
    and is outside the crawl-sourced diff's scope (CR4's own wording).
    """
    out: dict[str, set[str]] = {}
    for screen in existing.screens if existing is not None else []:
        signatures = out.setdefault(screen.key(), set())
        if screen.signature is not None:
            signatures.add(screen.signature)
    return out


def _judged_exhausted(nodes: list[ScreenNode], frontier_exhausted: bool) -> bool:
    """May this crawl's evidence support a `missing` claim (CR4/CR5)?

    `ISS-t165-crawl-traversal-3`: not when it skipped a screen. A CR3 skip is a
    decision NOT to look, and `_enqueue` only ever runs inside
    `explore_node.visit_node`, which a skip short-circuits — so a skipped
    screen's children are never discovered on THIS crawl. The queue then drains
    with `frontier_exhausted=True` while most of the portal was never
    represented at all, and every unreached stored key read as `missing`: an
    incremental re-crawl of a byte-identical 9-screen site reported 8 deletions
    that never happened (D-040's own acceptance test (c), live, headed Chromium).

    A skip is evidence of nothing beyond the skipped screen itself, so those
    keys are `missing_unjudged` — the disclosed unknown this contract already
    has for a frontier that was not exhausted — never `missing`.
    """
    return frontier_exhausted and not any(
        node.status is NodeStatus.SKIPPED_UNCHANGED or node.status in BROKEN_STATUSES
        for node in nodes)


def classify(
    existing: PortalPersona | None,
    nodes: list[ScreenNode],
    *,
    frontier_exhausted: bool,
) -> dict[str, list[str]]:
    """The four CR4 categories plus CR5's disclosed unknown, keyed exactly as
    `PersonaRevision`'s own fields — so the schema defines the shape once (C3)
    and this returns values for it, never a parallel model of it.

    Every returned list is sorted, so two runs over the same evidence produce
    byte-identical output (CR6 determinism).
    """
    stored = _stored_signatures(existing)
    crawl_sourced = {key for key, signatures in stored.items() if signatures}
    reached = _reached(nodes)
    was_broken = _previously_broken(existing)
    judged = _judged_exhausted(nodes, frontier_exhausted)

    new = sorted(key for key in reached if key not in stored)
    changed = sorted(
        key for key, at_key in reached.items()
        if key in crawl_sourced
        and any(node.signature not in stored[key] for node in at_key)
    )
    broken = sorted(
        key for key, at_key in reached.items()
        if key in stored and key not in was_broken
        and any(node.status in BROKEN_STATUSES for node in at_key)
    )
    absent = sorted(crawl_sourced - set(reached))
    # A SKIPPED_UNCHANGED node was never visited, so it is evidence of nothing --
    # the same reasoning `_judged_exhausted` applies to `missing`. A key is only
    # observed healthy when this crawl actually VISITED it and nothing broke.
    healthy = sorted(
        key for key, at_key in reached.items()
        if key in was_broken
        and any(node.status is not NodeStatus.SKIPPED_UNCHANGED for node in at_key)
        and not any(node.status in BROKEN_STATUSES for node in at_key)
    )
    return {
        "new_screens": new, "changed_screens": changed,
        "missing_screens": absent if judged else [],
        "broken_screens": broken,
        "missing_unjudged": [] if judged else absent,
        "healthy_screens": healthy,
    }


def _reached(nodes: list[ScreenNode]) -> dict[str, list[ScreenNode]]:
    """Key -> EVERY node this crawl reached at it, in crawl order.

    A `QUEUED` node was enqueued and never visited, so it is not evidence about
    anything and is excluded. Every other node is kept: `ISS-t165-crawl-traversal-2`
    was a `setdefault` here that let the FIRST node at a key silently hide a
    second, structurally distinct screen sharing that URL — which could then
    never appear as new, changed, missing or broken.
    """
    reached: dict[str, list[ScreenNode]] = {}
    for node in nodes:
        if node.status is NodeStatus.QUEUED:
            continue
        reached.setdefault(node_key(node), []).append(node)
    return reached


def describe(diff: dict[str, list[str]]) -> str | None:
    """A one-line prose fragment for the revision `summary`, or None when nothing
    moved. The COUNTS on the revision remain the machine-checkable record (CR4);
    this is only what a human reads first."""
    labels = (("new_screens", "new"), ("changed_screens", "changed"),
              ("missing_screens", "missing"), ("broken_screens", "broken"),
              ("missing_unjudged",
               "not judged (a bound, skipped-unchanged screen, or abandoned visit "
               "left the crawl incomplete)"),
              ("healthy_screens", "recovered"))
    parts = [f"{len(diff[field])} {label}" for field, label in labels if diff[field]]
    if not parts:
        return None
    return "screens " + ", ".join(parts)
