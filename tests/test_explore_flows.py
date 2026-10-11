"""Crawl -> reviewable Flow proposals (AT-887, D-084). A crawl's screens, and the
CLICK path that reached each one, become DRAFT Flow rows through the existing
review gate. Pure: no browser, no provider, and the same crawl gives the same rows.
"""

from __future__ import annotations

import random

import pytest

from autotester.providers.mock import MockProvider
from autotester.schema.case import ExpandedSteps
from autotester.schema.enums import Action, EdgeOutcome, ReviewStatus
from autotester.schema.flowspec import Flow, FlowSpec, Review, Screen, Step
from autotester.schema.screen_graph import ScreenEdge, ScreenNode
from autotester.stages.expand import applicable_classes, expand, propose_cases
from autotester.stages.explore_flows import flows_from_crawl
from autotester.stages.explore_merge import merge_screens, merge_screens_and_flows
from autotester.stages.review import FlowSpecNotReviewed, approve
from autotester.stages.screen_identity import dangling_references
from autotester.store.project_store import ProjectStore

CRAWL = "crawl_1"


def node(name: str, path: str, sig: str, by: ScreenEdge | None = None, crawl: str = CRAWL):
    return ScreenNode(
        crawl_id=crawl, project="demo", url_template=f"app.test{path}",
        url_example=f"https://app.test{path}", signature=sig, name=name, title=name,
        discovered_by=by.id if by else None,
    )


def edge(src: ScreenNode, target: str, action: Action = Action.CLICK,
         outcome: EdgeOutcome = EdgeOutcome.NAVIGATED, to: ScreenNode | None = None,
         crawl: str = CRAWL) -> ScreenEdge:
    return ScreenEdge(crawl_id=crawl, from_node=src.id, to_node=to.id if to else None,
                      action=action, target=target, name=target, outcome=outcome)


def inventory(crawl: str = CRAWL):
    """Home -> Courses -> Course detail, and Home -> Profile (two leaves)."""
    home = node("Home", "/home", "s_home", crawl=crawl)
    e_courses = edge(home, 'role=link[name="Courses"] >> nth=0', Action.NAVIGATE, crawl=crawl)
    courses = node("Courses", "/courses", "s_courses", e_courses, crawl)
    e_detail = edge(courses, '[aria-label="Open course"]', crawl=crawl)
    detail = node("Course detail", "/courses/12", "s_detail", e_detail, crawl)
    e_profile = edge(home, 'role=link[name="Profile"] >> nth=0', Action.NAVIGATE, crawl=crawl)
    profile = node("Profile", "/profile", "s_profile", e_profile, crawl)
    noise = edge(home, "#same", outcome=EdgeOutcome.SAME_SCREEN, crawl=crawl)
    return [home, courses, detail, profile], [e_courses, e_detail, e_profile, noise]


# -- the producer: what a crawl becomes ---------------------------------------

def test_one_flow_per_leaf_path_from_the_landing_screen() -> None:
    nodes, edges = inventory()
    flows = flows_from_crawl(nodes, edges, crawl_id=CRAWL)
    assert sorted(f.name.split(": ", 1)[1] for f in flows) == [
        "Home > Courses > Course detail", "Home > Profile"]
    deep = next(f for f in flows if "Course detail" in f.name)
    assert [(s.order, s.action) for s in deep.steps] == [
        (1, Action.NAVIGATE), (2, Action.CLICK), (3, Action.CLICK)]
    assert deep.steps[0].target == "https://app.test/home"
    assert deep.steps[1].target == 'role=link[name="Courses"] >> nth=0'
    assert deep.entry_screen == nodes[0].id and deep.exit_screen == nodes[2].id


def test_a_link_edge_is_replayed_as_a_click_never_a_goto() -> None:
    """The crawl records a link as Action.NAVIGATE with a LOCATOR target; the executor's
    NAVIGATE does goto(target), which a locator is not."""
    nodes, edges = inventory()
    for flow in flows_from_crawl(nodes, edges, crawl_id=CRAWL):
        assert [s.action for s in flow.steps[1:]] == [Action.CLICK] * (len(flow.steps) - 1)


def test_provenance_is_the_crawl_and_the_flow_is_not_a_human_or_reconciled_one() -> None:
    nodes, edges = inventory()
    for flow in flows_from_crawl(nodes, edges, crawl_id=CRAWL, login_case_id="case_login"):
        assert flow.source_id == CRAWL
        assert all(s.source_ref and s.source_ref.source_id == CRAWL for s in flow.steps)
        assert "not human-reviewed" in (flow.steps[1].note or "")
        assert flow.kind is None and flow.ideal_basis is None
        assert flow.requires_auth and "case_login" in flow.preconditions[0]


def test_expectations_are_only_the_path_a_click_changed() -> None:
    nodes, edges = inventory()
    deep = next(f for f in flows_from_crawl(nodes, edges, crawl_id=CRAWL)
                if "Course detail" in f.name)
    assert [s.expected.url for s in deep.steps] == ["/home", "/courses", "/courses/12"]
    assert all(not s.expected.visible_text and not s.expected.absent_text for s in deep.steps)


def test_same_crawl_same_proposals_whatever_the_storage_order() -> None:
    nodes, edges = inventory()
    first = [f.model_dump() for f in flows_from_crawl(nodes, edges, crawl_id=CRAWL)]
    shuffled_n, shuffled_e = nodes[:], edges[:]
    random.Random(7).shuffle(shuffled_n)
    random.Random(8).shuffle(shuffled_e)
    again = [f.model_dump() for f in flows_from_crawl(shuffled_n, shuffled_e, crawl_id=CRAWL)]
    assert first == again


def test_ids_are_the_path_not_the_crawl_so_a_re_crawl_adds_nothing() -> None:
    a = flows_from_crawl(*inventory("crawl_a"), crawl_id="crawl_a")
    b = flows_from_crawl(*inventory("crawl_b"), crawl_id="crawl_b")
    assert sorted(f.id for f in a) == sorted(f.id for f in b)


@pytest.mark.parametrize("action", [Action.FILL, Action.SELECT, Action.BACK, Action.HOVER])
def test_a_screen_reached_only_through_typed_input_gets_no_flow(action: Action) -> None:
    """A FILL edge carries no recorded value; guessing one would invent a step."""
    home = node("Home", "/home", "s_home")
    via = edge(home, "#q", action)
    results = node("Results", "/results", "s_results", via)
    ok = edge(home, "#nav")
    other = node("Other", "/other", "s_other", ok)
    flows = flows_from_crawl([home, results, other], [via, ok], crawl_id=CRAWL)
    assert [f.exit_screen for f in flows] == [other.id]


def test_orphans_cycles_and_unnavigated_discoveries_are_skipped_not_guessed() -> None:
    home = node("Home", "/home", "s_home")
    ghost = ScreenNode(crawl_id=CRAWL, project="demo", url_template="app.test/x",
                       url_example="https://app.test/x", signature="s_x",
                       discovered_by="edge_missing")
    bad = edge(home, "#err", outcome=EdgeOutcome.ERRORED)
    errored = node("E", "/e", "s_e", bad)
    flows = flows_from_crawl([home, ghost, errored], [bad], crawl_id=CRAWL)
    assert [f.exit_screen for f in flows] == [home.id]  # only the root, as a one-step flow
    assert len(flows[0].steps) == 1


def test_no_edges_no_flows_beyond_the_landing_screen() -> None:
    home = node("Home", "/home", "s_home")
    assert [len(f.steps) for f in flows_from_crawl([home], [], crawl_id=CRAWL)] == [1]
    assert flows_from_crawl([], [], crawl_id=CRAWL) == []


# -- the merge: proposals enter the EXISTING review step ----------------------

def test_merge_adds_flows_as_draft_and_never_approves() -> None:
    nodes, edges = inventory()
    spec = merge_screens_and_flows(None, nodes, edges, "demo", crawl_id=CRAWL)
    assert len(spec.flows) == 2 and len(spec.screens) == 4
    assert spec.review.status is ReviewStatus.DRAFT and spec.review.by is None
    assert CRAWL in spec.source_ids and "2 flow(s)" in (spec.review.note or "")
    with pytest.raises(FlowSpecNotReviewed):
        propose_cases(spec)


def test_merge_never_overwrites_a_reviewed_flow_and_re_arms_the_gate() -> None:
    nodes, edges = inventory()
    derived = flows_from_crawl(nodes, edges, crawl_id=CRAWL)
    mine = derived[0].model_copy(update={"name": "Human renamed", "steps": [
        Step(order=1, action=Action.NAVIGATE, target="https://app.test/mine")]})
    other = Flow(id="flow_login", name="Login", entry_screen="scr_signin")
    reviewed = approve(FlowSpec(project="demo", flows=[mine, other]), by="umesh")
    merged = merge_screens_and_flows(reviewed, nodes, edges, "demo", crawl_id=CRAWL)
    assert merged.flow(mine.id) == mine and merged.flow("flow_login") == other
    assert len(merged.flows) == 3
    assert merged.review.status is ReviewStatus.DRAFT
    assert reviewed.review.status is ReviewStatus.APPROVED  # input never mutated


def test_remerging_the_same_crawl_changes_nothing() -> None:
    nodes, edges = inventory()
    once = merge_screens_and_flows(None, nodes, edges, "demo", crawl_id=CRAWL)
    approved = approve(once, by="umesh")
    twice = merge_screens_and_flows(approved, nodes, edges, "demo", crawl_id=CRAWL)
    assert twice == approved and twice.version == once.version


def test_flows_for_screens_the_spec_already_knows_still_bump_the_version_once() -> None:
    nodes, edges = inventory()
    screens_only = merge_screens(None, nodes, "demo", crawl_id=CRAWL)
    later = merge_screens_and_flows(screens_only, nodes, edges, "demo", crawl_id=CRAWL)
    assert len(later.flows) == 2 and later.version == screens_only.version + 1
    assert later.review == Review(status=ReviewStatus.DRAFT, note=later.review.note)


def test_a_merge_that_adds_screens_and_flows_bumps_the_version_exactly_once() -> None:
    nodes, edges = inventory()
    base = FlowSpec(project="demo", version=5, review=Review(status=ReviewStatus.APPROVED))
    merged = merge_screens_and_flows(base, nodes, edges, "demo", crawl_id=CRAWL)
    assert len(merged.screens) == 4 and len(merged.flows) == 2 and merged.version == 6


def test_a_merge_that_adds_only_flows_is_draft_whatever_the_spec_was() -> None:
    nodes, edges = inventory()
    known = approve(merge_screens(None, nodes, "demo", crawl_id=CRAWL), by="umesh")
    merged = merge_screens_and_flows(known, nodes, edges, "demo", crawl_id=CRAWL)
    assert merged.screens == known.screens and len(merged.flows) == 2
    assert merged.review.status is ReviewStatus.DRAFT and merged.review.by is None
    assert merged.review.at is None


def test_a_real_cycle_in_the_crawl_graph_yields_no_flow() -> None:
    """A -> B -> A: neither screen has a path from a landing screen, so nothing is replayable."""
    a = node("A", "/a", "s_a")
    to_b = edge(a, "#b")
    b = node("B", "/b", "s_b", to_b)
    back = edge(b, "#a")
    a_again = a.model_copy(update={"discovered_by": back.id})
    assert flows_from_crawl([a_again, b], [to_b, back], crawl_id=CRAWL) == []


def test_a_rediscovered_screen_is_referenced_by_the_existing_id_and_the_flow_id_is_stable() -> None:
    nodes, edges = inventory()
    human = [Screen(id="scr_home", name="Home", url_pattern="/home"),
             Screen(id="scr_profile", name="Profile", url_pattern="/profile")]
    known = FlowSpec(project="demo", screens=human)
    fresh = merge_screens_and_flows(None, nodes, edges, "demo", crawl_id=CRAWL)
    merged = merge_screens_and_flows(known, nodes, edges, "demo", crawl_id=CRAWL)
    assert dangling_references(merged) == [] and dangling_references(fresh) == []
    assert sorted(f.id for f in merged.flows) == sorted(f.id for f in fresh.flows)
    profile = next(f for f in merged.flows if f.name.endswith("Home > Profile"))
    assert (profile.entry_screen, profile.exit_screen) == ("scr_home", "scr_profile")
    deep = next(f for f in merged.flows if "Course detail" in f.name)
    assert deep.entry_screen == "scr_home" and deep.exit_screen == nodes[2].id  # no rediscovery
    assert deep.steps[1].screen_id == "scr_home" and deep.steps[2].screen_id == nodes[1].id


# -- the seam: expand can run on reviewed crawl-derived flows ------------------

def test_expand_runs_on_reviewed_crawl_flows_and_only_after_the_human_steps(tmp_path) -> None:
    nodes, edges = inventory()
    draft = merge_screens_and_flows(None, nodes, edges, "demo", crawl_id=CRAWL)
    with pytest.raises(FlowSpecNotReviewed):
        expand(draft, MockProvider(responses={"agent": []}))
    spec = approve(draft, by="umesh")
    store = ProjectStore("demo", tmp_path)
    store.save_flowspec(spec)
    proposals = propose_cases(spec)
    store.stage_case_proposals(proposals)
    for proposal in proposals:
        store.review_case_proposal(proposal.id, "umesh", approved=True)
    asks = sum(len(applicable_classes(f)) - 1 for f in spec.flows)
    declined = ExpandedSteps(steps=[], rationale="n/a")
    provider = MockProvider(responses={"agent": [declined] * asks})
    cases = expand(spec, provider, store=store)
    assert {c.flow_id for c in cases} == {f.id for f in spec.flows}
    happy = {c.flow_id: c.steps for c in cases}
    assert all(happy[f.id] == f.steps for f in spec.flows)
    assert all(s.source_ref.source_id == CRAWL for steps in happy.values() for s in steps)
