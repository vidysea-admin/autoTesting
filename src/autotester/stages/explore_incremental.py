"""Incremental crawl: don't re-explore a screen the persona already knows.

Contract: qa/contracts/crawl-traversal.md CR3 (the skip) and CR5 (a skip is
never silently folded into "explored"). A new module rather than more lines in
`explore.py`/`explore_node.py`, both at the C2 cap.

The cache key is the **Stagehand idea-port** named in
`docs/research/crawl-reuse-2026-09.md` §3 (MIT, idea only — Stagehand is not a
dependency and no code is copied): a step is skipped when the thing it would
act on is provably the same thing it acted on last time. Here that is
`(url_template, structural_signature)` — `PersonaScreen.key()` for the URL half
and `PersonaScreen.signature` for the structural half, both fields that already
existed (`schema/portal_persona.py`).

**The honesty half is the whole point (CR5).** A skip saves work by NOT looking;
it therefore proves nothing about the screen it skipped. So a skipped screen
gets its own `NodeStatus.SKIPPED_UNCHANGED`, is counted apart in
`Crawl.skipped_unchanged`, costs no `actions_used`, keeps every one of its
controls visible as a coverage hole, and stops the crawl's headline reading as
full exploration. A persona-seeded crawl that skips 90% of a portal must never
read as having explored 90% of a portal.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from autotester.schema.enums import NodeStatus
from autotester.schema.portal_persona import PersonaScreen, PortalPersona
from autotester.schema.screen_graph import ScreenNode
from autotester.stages import explore_summary

if TYPE_CHECKING:  # `explore_runtime` imports PersonaIndex from here -- type-only both ways
    from autotester.stages.explore_runtime import ExploreRuntime

SKIP_REASON = "skipped -- unchanged since the persona revision of {at}"
NO_REVISION = "skipped -- unchanged since the stored persona (no dated revision)"


class PersonaIndex:
    """The stored persona, keyed for O(1) cache-key lookup during a crawl.

    Built ONCE per crawl, from the persona on disk. Deliberately a plain lookup
    with no fallback matching: a near-miss is not a match, and a screen we are
    not certain about is explored, never skipped (D-004 — a rule decides only
    where it is certain).
    """

    __slots__ = ("_at_key", "_revision")

    def __init__(self, persona: PortalPersona | None) -> None:
        # EVERY stored screen at a key, not the first. Since
        # `ISS-t165-crawl-traversal-2` the persona may legitimately hold two
        # structurally distinct states at one URL (X3/X14 SPA toggles), and a
        # first-wins index compares the live signature against only one of them
        # -- never a false skip, but the second state is then re-explored on
        # every incremental crawl, which is the CR3 efficiency guarantee lost.
        self._at_key: dict[str, list[PersonaScreen]] = {}
        self._revision: str | None = None
        if persona is None:
            return
        for screen in persona.screens:
            self._at_key.setdefault(screen.key(), []).append(screen)
        if persona.history:
            self._revision = persona.history[-1].at

    def __len__(self) -> int:
        return len(self._at_key)

    @property
    def keys(self) -> frozenset[str]:
        """Every screen key the stored persona carries (CR4's `missing` candidates)."""
        return frozenset(self._at_key)

    def stored(self, key: str) -> PersonaScreen | None:
        """The first stored screen at `key`, for callers that want one exemplar.
        Skip decisions must NOT use this -- they go through `skip_reason`, which
        considers every stored state at the key."""
        at_key = self._at_key.get(key)
        return at_key[0] if at_key else None

    def skip_reason(self, node: ScreenNode) -> str | None:
        """CR3: the reason to skip `node`, or None to explore it as normal.

        A node is skipped only when SOME stored screen at that key carries a
        recorded signature EQUAL to the live one. These are deliberately NOT
        skips, because none of them is evidence the screen is unchanged: no
        stored screen at that key (new), a stored
        screen with no signature at all (it came from a FlowSpec, never from a
        crawl — nothing to compare), and every stored signature differing
        (changed, CR4).
        """
        # `ScreenNode.signature` is a required str and a stored `None` means
        # "unknown", so a FlowSpec-sourced screen can never match by accident.
        signatures = {s.signature for s in self._at_key.get(node_key(node), [])}
        if node.signature not in signatures:
            return None
        return SKIP_REASON.format(at=self._revision) if self._revision else NO_REVISION


def node_key(node: ScreenNode) -> str:
    """A crawled node's persona key, computed exactly as `PersonaScreen.key()`
    computes a stored one — the two must agree or every lookup misses (C3)."""
    return PersonaScreen(id=node.id, name=node.name or node.title or node.url_template,
                         url_template=node.url_template, signature=node.signature).key()


def load_index(store: object, *, enabled: bool) -> PersonaIndex:
    """The persona index for this crawl, or an empty one when incremental mode
    is off or the persona cannot be read.

    A persona that fails to load must never abort a crawl: the honest fallback
    is to explore everything, which is the pre-T-165 behaviour and skips nothing.
    """
    if not enabled:
        return PersonaIndex(None)
    try:
        return PersonaIndex(store.load_portal_persona())  # type: ignore[attr-defined]
    except Exception:
        return PersonaIndex(None)


def skip_unchanged(rt: ExploreRuntime, node: ScreenNode) -> bool:
    """CR3: is this screen provably unchanged since the stored persona? If so,
    record the skip as its own status and DON'T visit it.

    A skip costs no `actions_used` (CR3) and is never counted as explored (CR5):
    `crawl_coverage` still lists every one of this screen's controls as a hole,
    so a persona-seeded crawl cannot read as having exercised them.
    """
    if rt.persona.skip_reason(node) is None:
        return False
    skipped = node.model_copy(update={"status": NodeStatus.SKIPPED_UNCHANGED})
    rt.nodes[node.id] = skipped
    rt.store.update_node(explore_summary.scrubbed(rt, skipped))
    rt.skipped_unchanged += 1
    return True


def exhausted_reason(skipped: int) -> str:
    """CR5: an exhausted frontier is only "frontier empty" when the crawl really
    LOOKED at every screen in it. When screens were skipped as unchanged, the
    reason says so -- a reader of `stop_reason` must never be told the portal was
    explored when most of it was taken on trust from a previous crawl."""
    if not skipped:
        return "frontier empty"
    return (f"frontier empty -- {skipped} screen(s) skipped as unchanged "
            "since the stored persona, and so NOT explored on this crawl")
