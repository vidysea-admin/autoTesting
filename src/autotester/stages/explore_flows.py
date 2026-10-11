"""One job: derive reviewable `Flow` PROPOSALS from a crawl's discovery tree (AT-887, D-084).

Split from `explore_merge.py`: folding screens into a spec and deriving paths from the
screen graph are two jobs. A crawl lands on one screen and discovers
the rest by clicking, so each leaf of that tree is a replayable user journey. This module is
pure -- no browser, no provider, no clock -- and never touches review state: what it returns
is a proposal, and `explore_merge.merge_screens_and_flows` puts it behind the existing human gate.
"""

from __future__ import annotations

from urllib.parse import urlsplit

from autotester.core.ids import content_id
from autotester.schema.enums import Action, EdgeOutcome
from autotester.schema.flowspec import ExpectedState, Flow, SourceRef, Step
from autotester.schema.screen_graph import ScreenEdge, ScreenNode

_MAX_PATH = 12  # bounds.max_depth defaults to 6; a chain this long means a corrupt graph
_CLICKED = {Action.CLICK, Action.NAVIGATE}
"""The crawl records a link as NAVIGATE with a LOCATOR target and performs it with a click;
`execute` would goto() that locator. A typed edge carries no recorded value, so a path
through one is not replayable and is skipped rather than invented."""


def _path_of(url: str) -> str:
    return urlsplit(url).path


def _chain(node: ScreenNode, nodes: dict[str, ScreenNode],
           edges: dict[str, ScreenEdge]) -> tuple[list[ScreenNode], list[ScreenEdge]] | None:
    """The screens from the landing screen to `node` and the discovering edges between them,
    or None when the path cannot be replayed as clicks (missing edge, typed or failed
    discovery, cycle)."""
    path, chain = [node], []
    while node.discovered_by:
        edge = edges.get(node.discovered_by)
        parent = nodes.get(edge.from_node) if edge else None
        if (edge is None or parent is None or parent in path or len(chain) >= _MAX_PATH
                or edge.outcome is not EdgeOutcome.NAVIGATED or edge.action not in _CLICKED):
            return None
        chain.append(edge)
        path.append(parent)
        node = parent
    return path[::-1], chain[::-1]


def _step(order: int, action: Action, target: str, screen: ScreenNode, to_path: str,
          prev_path: str | None, crawl_id: str, locator: str) -> Step:
    """One observed action. `expected.url` is set only where the click changed the path:
    nothing else about a crawled screen is known well enough to assert."""
    moved = to_path not in ("", "/") and to_path != prev_path
    return Step(
        order=order, action=action, target=target, screen_id=screen.id,
        expected=ExpectedState(url=to_path if moved else None),
        source_ref=SourceRef(source_id=crawl_id, locator=locator),
        note=f"observed by crawl {crawl_id}; crawl-derived, not human-reviewed",
    )


def _flow(path: list[ScreenNode], chain: list[ScreenEdge], crawl_id: str,
          login_case_id: str | None) -> Flow:
    urls = [_path_of(n.url_example) for n in path]
    root = path[0]
    steps = [_step(1, Action.NAVIGATE, root.url_example, root, urls[0], None, crawl_id,
                   root.url_example)]
    for i, edge in enumerate(chain):
        steps.append(_step(i + 2, Action.CLICK, edge.target, path[i], urls[i + 1], urls[i],
                           crawl_id, edge.id))
    labels = [n.name or n.title or n.url_template for n in path]
    identity = {"nodes": [n.id for n in path], "targets": [e.target for e in chain]}
    return Flow(
        id=content_id("flow", identity),
        name=f"crawl path: {' > '.join(labels)}"[:140], entry_screen=root.id,
        exit_screen=path[-1].id, steps=steps, requires_auth=login_case_id is not None,
        preconditions=[f"signed in by login case {login_case_id}"] if login_case_id else [],
    )


def flows_from_crawl(nodes: list[ScreenNode], edges: list[ScreenEdge], *, crawl_id: str,
                     login_case_id: str | None = None) -> list[Flow]:
    """One Flow per leaf of the crawl's discovery tree: navigate to the landing screen, then
    click each discovering edge in order. Deterministic (no model call, no clock, input order
    irrelevant) and a PROPOSAL only -- `kind` stays unset and nothing here touches review."""
    by_node = {n.id: n for n in sorted(nodes, key=lambda n: n.id)}
    by_edge = {e.id: e for e in sorted(edges, key=lambda e: e.id)}
    chains = {nid: c for nid, n in by_node.items() if (c := _chain(n, by_node, by_edge))}
    parents = {c[1][-1].from_node for c in chains.values() if c[1]}
    return [_flow(path, chain, crawl_id, login_case_id)
            for nid, (path, chain) in chains.items() if nid not in parents]


