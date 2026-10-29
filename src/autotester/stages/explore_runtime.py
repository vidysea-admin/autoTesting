"""The live state of one crawl in flight — session, store, clock, counters.

Split out of `stages/explore.py`, which sat exactly at the C2 300-line cap when
T-165 needed to add the traversal strategy, the persona index and the typed-
value record to it (qa/contracts/crawl-traversal.md, "How a unit is verified":
new logic belongs in a stated-reason new module rather than a file at budget).

This is a pure move plus T-165's new fields. `stages/explore.py` keeps every
behaviour it had — in particular `run_case` still appears there and only there,
inside `_bootstrap_login`, so `explore.md` X1's verify grep is unaffected.

NOT a schema model, for the reason the original docstring gave: it duplicates
no persisted shape (C1). Nothing here reaches disk except through the `Crawl`
envelope and the JSONL the store writes.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from autotester.browser.observe import PageObserver
from autotester.browser.session import BrowserSession
from autotester.schema.crawl import Crawl, CrawlBounds, SafetyPolicy
from autotester.schema.enums import TraversalStrategy
from autotester.schema.project import Project
from autotester.schema.screen_graph import CrawlFrontier, ElementRef, ScreenEdge, ScreenNode
from autotester.stages.explore_incremental import PersonaIndex
from autotester.stages.explore_safety import DialogBreaker
from autotester.store.project_store import ProjectStore

if TYPE_CHECKING:
    from autotester.stages.explore_replay import TypedAction


@dataclass
class ExploreRuntime:
    """Live objects for one crawl — session, store, clock, in-memory node
    index. NOT a schema model: duplicates no persisted shape (C1)."""

    project: Project
    session: BrowserSession
    store: ProjectStore
    crawl: Crawl
    observer: PageObserver
    breaker: DialogBreaker
    clock: Callable[[], float]
    started: float
    frontier: CrawlFrontier
    nodes: dict[str, ScreenNode] = field(default_factory=dict)
    discovery: dict[str, ScreenEdge] = field(default_factory=dict)
    # node id -> the edge that first reached it (AT-227: a screen that is only a
    # client-side STATE of another has no URL, so replaying this edge is the way back).
    noise: dict[str, int] = field(default_factory=dict)
    edges: int = 0
    denied: int = 0
    issues: int = 0
    tool_failures: int = 0
    stop_reason: str | None = None
    seed_error: str | None = None
    login_precheck_error: str | None = None  # AT-273: the precheck's exception, diagnostic
    login_signature: str | None = None
    """X18(a)/AT-462: the login screen's structure, observed before the case typed."""
    login_observe_error: str | None = None  # AT-474: observed_signature()'s error, if any
    return_error: str | None = None  # why the last `return_to` failed (AT-108), scratch
    strategy: TraversalStrategy = TraversalStrategy.BFS
    """CR1: frontier ORDER only. `bfs` is the original FIFO behaviour."""
    persona: PersonaIndex = field(default_factory=lambda: PersonaIndex(None))
    """CR3: the stored persona's cache keys. Empty unless incremental mode is on,
    and an empty index skips nothing — the pre-T-165 behaviour exactly."""
    typed: dict[str, list[TypedAction]] = field(default_factory=dict)
    """CR2: node id -> the values really typed there, in order, so
    `explore_replay` can re-issue them. In memory only; never persisted."""
    last_visited: str | None = None
    """CR1: which screen the hybrid descent is currently descending FROM."""
    deferred: list[tuple[str, ElementRef]] = field(default_factory=list)
    """PS2/D-040: destructive controls the crawl WOULD press, parked as (node id, control)
    until the non-destructive frontier is drained. `explore_traversal.drain_deferred` empties it."""
    skipped_unchanged: int = 0
    """CR3/CR5: screens skipped as unchanged. Counted apart from `screens`."""
    frontier_exhausted: bool = False
    """CR5, and the property the whole unit rests on: set TRUE only where the
    traversal loop really drained the queue. `run_crawl` reads THIS to decide
    whether a crawl may be called complete — never a string comparison against
    `stop_reason`, which a new stop reason (a skip note, a bound qualifier)
    would silently turn into a wrong answer."""

    net_log: list[tuple[str, str, int]] = field(default_factory=list)
    """Every (method, url, status) the observer has handed over so far, kept whole for the
    crawl-wide NETWORK evidence now that responses are drained per action (T-170/NA1)."""
    api_seen: dict[str, list[tuple[str, str, int]]] = field(default_factory=dict)
    """node id -> the XHR/fetch responses seen while on that screen; folded into
    `ScreenNode.api_calls` once, in `explore_summary.apply_api_calls`."""

    def take_responses(self, node_id: str | None) -> None:
        """Drain the observer. Everything joins `net_log`; the XHR/fetch subset is
        attributed to `node_id` (None: logged only, attributed to no screen)."""
        self.net_log.extend(self.observer.drain_responses())
        api = self.observer.drain_api_responses()
        if node_id is not None and api:
            self.api_seen.setdefault(node_id, []).extend(api)

    @property
    def bounds(self) -> CrawlBounds:
        return self.crawl.bounds

    @property
    def policy(self) -> SafetyPolicy:
        return self.crawl.policy
