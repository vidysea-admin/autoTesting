"""Screen identity: the rules that decide when two screens are one.

A crawl visit becomes a `ScreenNode` (`node_from`); reconcile (D-073, contract
reconcile.md RC4/RC5) folds FlowSpec screens that share a templated route and
measures a video screen against a candidate on route, title and element labels,
using the same normalised names the structural signature keys on.

Contract: qa/contracts/explore.md X3 (once that contract exists, T-143).
Deliberately structural — never URL-only (the prior attempt made every SPA
state invisible) and never an LLM's free-text description (its stop
condition then never fired, because the text kept changing). Pure; no
browser, no provider.
"""

from __future__ import annotations

import re

from autotester.core.ids import content_hash
from autotester.core.urls import url_template
from autotester.schema.flowspec import Flow, FlowSpec, Screen
from autotester.schema.screen_graph import ElementRef, PageObservation, ScreenNode

_WHITESPACE = re.compile(r"\s+")
_DIGITS = re.compile(r"\d+")
_PUNCTUATION = re.compile(r"[^\w\s]")
_ROLE_WORDS = re.compile(r"(button|field|input|tab|tabs|dropdown|card|title|heading|link|"
                         r"banner|box|section|textarea|icon|menu item)")


def _normalise_name(name: str) -> str:
    """Casefold, collapse whitespace, strip punctuation, map digit runs to
    `#` — so "Edit row 42" and "Edit row 17" contribute the same signature
    token (row data doesn't change a screen's identity)."""
    text = name.strip().casefold()
    text = _PUNCTUATION.sub("", text)
    text = _DIGITS.sub("#", text)
    text = _WHITESPACE.sub(" ", text).strip()
    return text[:40]


def structural_signature(elements: list[ElementRef]) -> str:
    """Content hash of the sorted, deduplicated `(role, normalised-name)` set
    of VISIBLE, non-row elements. Row/list-item elements are excluded so two
    list pages differing only in row data collapse to one signature.

    AT-227 deliberately does NOT exclude `obscured` elements here, though it
    adds that flag and uses it elsewhere. A modal state and the screen behind
    it are already two signatures by the `visible` rule alone -- dismissing the
    veil makes the veil's own controls `display:none`. Excluding obscured
    elements on top of that would additionally collapse ONE modal shown over
    TWO different pages into a single node, which would claim that one screen
    has two different outcomes for the same action. Identity stays with what
    the page RENDERS; reachability is a separate question, answered by
    `explore_node` when it picks candidates.
    """
    keys = {
        f"{el.role}|{_normalise_name(el.name)}"
        for el in elements
        if el.visible and not el.in_row
    }
    return content_hash(sorted(keys))


def node_from(
    observation: PageObservation, crawl_id: str, project: str, depth: int,
    *, discovered_by: str | None = None,
) -> ScreenNode:
    """Build a `ScreenNode` whose id is a pure function of
    `(url_template, structural_signature)` — the same inputs always produce
    the same node, regardless of when or how it was visited.

    `fold_index=True` (AT-334): a directory index reached by its bare
    directory URL and by its served `index.html`/`index.htm` filename is the
    same screen, not two — measured on a real crawl of
    tests/fixtures/modal_site (six nodes for a three-page site, each veil
    duplicated too)."""
    template = url_template(observation.url, keep_host=False, fold_index=True)
    signature = structural_signature(observation.elements)
    return ScreenNode(
        crawl_id=crawl_id, project=project, url_template=template,
        url_example=observation.url, signature=signature, title=observation.title,
        name=observation.title or template, depth=depth,
        elements=observation.elements, discovered_by=discovered_by,
    )


# -- reconcile: FlowSpec screens (RC4) and video-vs-candidate signals (RC5) ----
def route_key(pattern: str | None) -> str | None:
    """A screen's identity route, by the crawler's own `url_template` (ingest I7)."""
    return url_template(pattern, keep_host=False, fold_index=True) if pattern else None


def element_labels(names: list[str]) -> frozenset[str]:
    """The signature's normalised-name half, minus role words a video label adds
    ("Save button" -> "save"): a video reading carries no DOM role."""
    out = (" ".join(_ROLE_WORDS.sub(" ", _normalise_name(n)).split()) for n in names)
    return frozenset(label for label in out if label)


def screen_labels(screen: Screen) -> frozenset[str]:
    return element_labels([*screen.signals, *((f.label or f.name) for f in screen.fields)])


def match_signals(route: str | None, title: str, labels: frozenset[str],
                  c_route: str | None, c_title: str, c_labels: frozenset[str],
                  ) -> tuple[float, float, float]:
    """(route equal, title word Jaccard, share of the video's labels the candidate has)."""
    words, c_words = (set(re.findall(r"[a-z0-9]+", t.casefold())) for t in (title, c_title))
    r = 1.0 if route and route == c_route else 0.0
    t = round(len(words & c_words) / len(words | c_words), 4) if words | c_words else 0.0
    e = round(len(labels & c_labels) / len(labels), 4) if labels else 0.0
    return r, t, e


def fold_routes(screens: list[Screen]) -> tuple[list[Screen], dict[str, str]]:
    """RC4: screens whose templated route is equal fold to the first of them (input
    order). A screen with no `url_pattern` is never folded on route alone."""
    first: dict[str, str] = {}
    alias: dict[str, str] = {}
    for screen in screens:
        route = route_key(screen.url_pattern)
        if route is not None and first.setdefault(route, screen.id) != screen.id:
            alias[screen.id] = first[route]
    return [s for s in screens if s.id not in alias], alias


def rewrite_screen_refs(flow: Flow, alias: dict[str, str]) -> Flow:
    """Point a flow's entry, exit and every step at the canonical screen ids."""
    def to(ref: str | None) -> str | None:
        return alias.get(ref, ref) if ref else ref
    steps = [s.model_copy(update={"screen_id": to(s.screen_id)}) for s in flow.steps]
    return flow.model_copy(update={"entry_screen": to(flow.entry_screen),
                                   "exit_screen": to(flow.exit_screen), "steps": steps})


def dangling_references(spec: FlowSpec) -> list[str]:
    """Every flow reference to a screen id the spec does not hold, as `flow:where`."""
    ids = {s.id for s in spec.screens}
    found = []
    for flow in spec.flows:
        refs = [("entry", flow.entry_screen), ("exit", flow.exit_screen)]
        refs += [(f"step{s.order}", s.screen_id) for s in flow.steps]
        found += [f"{flow.id}:{where}" for where, ref in refs if ref and ref not in ids]
    return found
