"""AT-887 / AT-109 residuals: a big crawl yields flows and cases; stale screens and unreachable
first targets are SAID, never silently dropped (and never a gate)."""

from __future__ import annotations

import contextlib
import logging

from autotester.providers.mock import MockProvider
from autotester.schema.case import ExpandedSteps
from autotester.schema.enums import Action, EdgeOutcome, ReviewStatus
from autotester.schema.flowspec import Flow, FlowSpec, Step
from autotester.schema.screen_graph import ScreenEdge, ScreenNode
from autotester.stages.expand import (
    applicable_classes,
    expand,
    propose_cases,
    unreachable_first_targets,
)
from autotester.stages.explore_merge import merge_screens, merge_screens_and_flows, not_seen_again
from autotester.stages.review import approve
from autotester.store.project_store import ProjectStore

CRAWL = "crawl_1"


def node(name: str, path: str, sig: str, by: ScreenEdge | None = None, crawl: str = CRAWL):
    return ScreenNode(
        crawl_id=crawl, project="demo", url_template=f"app.test{path}",
        url_example=f"https://app.test{path}", signature=sig, name=name, title=name,
        discovered_by=by.id if by else None)


def edge(src: ScreenNode, target: str, action: Action = Action.CLICK, crawl: str = CRAWL):
    return ScreenEdge(crawl_id=crawl, from_node=src.id, to_node=None, action=action,
                      target=target, name=target, outcome=EdgeOutcome.NAVIGATED)


def wide_crawl(n: int = 73, crawl: str = CRAWL):
    home = node("Home", "/home", "s_home", crawl=crawl)
    nodes, edges = [home], []
    for i in range(n - 1):
        e = edge(home, f'role=link[name="Page {i}"] >> nth=0', Action.NAVIGATE, crawl=crawl)
        nodes.append(node(f"Page {i}", f"/p{i}", f"s_{i}", e, crawl))
        edges.append(e)
    return nodes, edges


def test_a_73_screen_crawl_yields_flows_and_expand_produces_cases(tmp_path) -> None:
    nodes, edges = wide_crawl(73)
    draft = merge_screens_and_flows(None, nodes, edges, "demo", crawl_id=CRAWL)
    assert len(draft.screens) == 73 and len(draft.flows) == 72
    assert draft.review.status is ReviewStatus.DRAFT
    spec = approve(draft, by="umesh")
    store = ProjectStore("demo", tmp_path)
    store.save_flowspec(spec)
    proposals = propose_cases(spec)
    store.stage_case_proposals(proposals)
    for p in proposals:
        store.review_case_proposal(p.id, "umesh", approved=True)
    asks = sum(len(applicable_classes(f)) - 1 for f in spec.flows)
    declined = ExpandedSteps(steps=[], rationale="n/a")
    cases = expand(spec, MockProvider(responses={"agent": [declined] * asks}), store=store)
    assert len(cases) == len(spec.flows) > 0


def test_a_redesign_is_named_in_the_review_note_but_nothing_is_rewritten() -> None:
    old_nodes, _ = wide_crawl(3, "crawl_old")
    base = merge_screens(None, old_nodes, "demo", crawl_id="crawl_old")
    new_home = node("Account", "/home", "s_redesign", crawl="crawl_new")
    merged = merge_screens(base, [new_home], "demo", crawl_id="crawl_new")
    stale = not_seen_again(base, [new_home], "crawl_new")
    assert len(stale) == 3
    assert "3 earlier screen(s) not seen again" in merged.review.note
    assert all(s in merged.screens for s in base.screens)  # kept, none rewritten


def test_a_recrawl_that_sees_everything_has_nothing_stale() -> None:
    nodes, _ = wide_crawl(3, "crawl_a")
    base = merge_screens(None, nodes, "demo", crawl_id="crawl_a")
    assert not_seen_again(base, nodes, "crawl_b") == []


def video_flow(target: str) -> Flow:
    return Flow(id="f_video", name="video", entry_screen="x",
                steps=[Step(order=1, action=Action.CLICK, target=target)])


def test_a_first_click_no_crawled_screen_shows_is_warned_about(caplog) -> None:
    nodes, edges = wide_crawl(5)
    spec = approve(merge_screens_and_flows(None, nodes, edges, "demo", crawl_id=CRAWL), by="u")
    spec = spec.model_copy(update={"flows": [
        *spec.flows, video_flow('role=menuitem[name="Supply Partners"]'),
        video_flow('role=link[name="Page 1"]').model_copy(update={"id": "f_ok"})]})
    assert unreachable_first_targets(spec) == [
        ("f_video", 'role=menuitem[name="Supply Partners"]')]
    with caplog.at_level(logging.WARNING), contextlib.suppress(ValueError):  # warning came first
        expand(spec, MockProvider(responses={"agent": []}))
    assert any("Supply Partners" in r.message for r in caplog.records)


def test_no_crawl_screens_means_no_warning() -> None:
    spec = FlowSpec(project="demo", flows=[video_flow('role=link[name="Anything"]')])
    assert unreachable_first_targets(spec) == []
