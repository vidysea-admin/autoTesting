"""`stages/explore.py`'s terminal-status distinction between a genuine
exhaustive crawl and a crawl that could act on nothing.

Contract: qa/contracts/explore.md X4/X16 (AT-242). Split out of
`test_explore.py` to keep that file under the 300-line cap — the fixture
(`crawl_fake.py`) is shared, not duplicated.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from crawl_fake import crawl_it, grant_crawl_approval, make_session

from autotester.browser.observe import PageObserver
from autotester.schema.case import Case
from autotester.schema.crawl import CoverageHole, Crawl, CrawlCoverage, SafetyPolicy
from autotester.schema.enums import (
    Action,
    CaseClass,
    CaseKind,
    CrawlStatus,
    EdgeOutcome,
    NodeStatus,
)
from autotester.schema.flowspec import Step
from autotester.schema.project import Project
from autotester.schema.screen_graph import ScreenEdge, ScreenNode
from autotester.stages import explore_status, explore_traversal
from autotester.stages.explore import run_crawl
from autotester.store.project_store import ProjectStore


def test_a_login_gate_with_every_action_denied_is_not_reported_completed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The real repro: an entry screen with only an unnamed input and a
    read_only-refused submit button. The frontier genuinely empties (nothing
    is left to visit), but nothing was ever DONE -- reporting that as the same
    status word as an exhaustive crawl is indistinguishable from success."""
    import crawl_fake

    monkeypatch.setitem(crawl_fake.SITE, crawl_fake.BASE, [
        {"role": "textbox", "name": "", "selector": "#user"},
        {"role": "button", "name": "Login", "selector": "#login", "is_form_submit": True},
    ])
    crawl, _store, _page = crawl_it(tmp_path)

    assert crawl.actions == 0
    assert crawl.denied == 2  # skipped_unnamed + denied_policy
    # X18 (AT-458): this exact shape is a login wall, which is now named as one rather than
    # folded into the generic "could act on nothing" status. Still never COMPLETED.
    assert crawl.status is CrawlStatus.LOGIN_WALL
    assert crawl.stop_reason is not None and "denied" in crawl.stop_reason


def test_a_page_whose_only_control_is_refused_is_blocked_not_completed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AT-242's own shape, with no login form in it: the only control is refused by the
    destructive-name deny-list. Not a wall, and not success either."""
    import crawl_fake

    monkeypatch.setitem(crawl_fake.SITE, crawl_fake.BASE, [
        {"role": "button", "name": "Delete everything", "selector": "#del"},
    ])
    crawl, _store, _page = crawl_it(tmp_path)

    assert (crawl.actions, crawl.denied) == (0, 1)
    assert crawl.status is CrawlStatus.BLOCKED_NO_ACTIONS
    assert crawl.stop_reason is not None and "denied" in crawl.stop_reason


def test_a_page_with_no_controls_at_all_still_reports_completed(tmp_path: Path) -> None:
    """The negative case this fix must not floor: a genuinely trivial page
    (nothing to click, nothing denied) is real, exhaustive coverage."""
    project = Project(slug="demo", name="Demo", base_url="https://app.test/deleted",
                      allowed_domains=["app.test"])
    session, _page = make_session(tmp_path, project)
    store = ProjectStore("demo", tmp_path)
    grant_crawl_approval(store, project)
    crawl = run_crawl(project, session, store, observer=PageObserver(),
                      policy=SafetyPolicy(write_policy=project.write_policy))

    assert crawl.actions == 0
    assert crawl.denied == 0
    assert crawl.status is CrawlStatus.COMPLETED, (
        "a page with genuinely nothing to click must not be floored to blocked_no_actions"
    )


@pytest.mark.parametrize("status", [NodeStatus.ABORTED_ERROR, NodeStatus.ABORTED_DIALOG])
@pytest.mark.parametrize("bound", [None, "max_actions", "wall_clock_s", "max_screens"])
def test_abandoned_visits_are_aborted_unless_an_actual_bound_fired(status, bound) -> None:
    node = ScreenNode(crawl_id="c", project="p", url_template="/lost",
                      url_example="https://app.test/lost", signature="lost", status=status)
    actual, reason = explore_status.terminal_status(
        completed=bound is None, actions_used=2, denied=0, nodes=[node], edges=[],
        login_case=None, current_stop_reason=bound)
    assert actual is (CrawlStatus.STOPPED_BOUND if bound else CrawlStatus.ABORTED)
    if bound:
        assert reason is None, "an actual bound's original reason must stay intact"
    else:
        assert "abandoned" in reason and status.value in reason


@pytest.mark.parametrize("hole_reason", ["error", "policy:deny", "not_visited", None])
@pytest.mark.parametrize("actions", [0, 3])
def test_legacy_completion_display_uses_only_recorded_error_holes(hole_reason, actions) -> None:
    coverage = None if hole_reason is None else CrawlCoverage(
        percent=0, controls_discovered=1, holes=[CoverageHole(
            node_id="n", url_template="/", selector="#x", reason=hole_reason)])
    crawl = Crawl(project="p", status=CrawlStatus.COMPLETED, actions=actions,
                  issues=9, stop_reason="frontier empty", coverage=coverage)
    original = crawl.model_dump_json()
    expected = CrawlStatus.ABORTED if hole_reason == "error" else CrawlStatus.COMPLETED
    assert explore_status.displayed_status(crawl) is expected
    assert explore_status.is_success(crawl) is (expected is CrawlStatus.COMPLETED)
    assert crawl.model_dump_json() == original, "display must not rewrite historical artifacts"


@pytest.mark.parametrize("declared", [False, True])
def test_login_precedence_over_abort_does_not_invent_a_bound(declared) -> None:
    node = ScreenNode(crawl_id="c", project="p", url_template="/",
                      url_example="https://app.test/", signature="login",
                      status=NodeStatus.ABORTED_ERROR)
    case = Case(project="p", flow_id="login", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
                title="login", steps=[Step(order=1, action=Action.NAVIGATE,
                                           target="https://app.test/")]) if declared else None
    edges = [ScreenEdge(crawl_id="c", from_node=node.id, action=Action.CLICK,
                        target="#login", outcome=EdgeOutcome.DENIED_POLICY,
                        reason=explore_status.FORM_SUBMIT_REFUSED)]
    status, reason = explore_status.terminal_status(
        completed=False, actions_used=0, denied=1, nodes=[node], edges=edges,
        login_case=case, login_signature="login", current_stop_reason="abandoned visits")
    assert status is (CrawlStatus.LOGIN_FAILED if declared else CrawlStatus.LOGIN_WALL)
    assert "bound fired" not in reason


@pytest.mark.parametrize("case", ["aborted_error", "aborted_dialog", "queued", "max_actions"])
def test_deferred_execution_is_finished_before_completeness_is_judged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str,
) -> None:
    """Injected states prove finalization ordering, not browser recovery mechanisms."""
    original_drain = explore_traversal.drain_deferred
    captured = []

    def inject_then_drain(rt):
        captured.append(rt)
        node = next(iter(rt.nodes.values()))
        if case.startswith("aborted_"):
            changed = node.model_copy(update={"status": NodeStatus(case)})
            rt.nodes[node.id] = changed
            rt.store.add_node(changed)
        elif case == "queued":
            discovered = ScreenNode(
                crawl_id=rt.crawl.id, project=rt.project.slug,
                url_template="/deferred-discovery", url_example="https://app.test/deferred",
                signature="fresh-deferred-discovery")
            assert discovered.id not in rt.nodes
            rt.nodes[discovered.id] = discovered
            rt.store.add_node(discovered)
            rt.frontier.queue.append(discovered.id)
            rt.frontier.screens_found += 1
        else:
            rt.deferred.append((node.id, node.elements[0]))
            rt.frontier.actions_used = rt.bounds.max_actions
        original_drain(rt)

    monkeypatch.setattr(explore_traversal, "drain_deferred", inject_then_drain)
    crawl, store, page = crawl_it(tmp_path)
    rt = captured[0]
    assert rt.frontier_exhausted is False
    if case.startswith("aborted_"):
        assert crawl.status is CrawlStatus.ABORTED
        assert crawl.stop_reason == f"abandoned visits: {case} (/)"
    elif case == "queued":
        assert crawl.status is CrawlStatus.STOPPED_BOUND
        assert crawl.stop_reason == (
            "destructive_last (1 screen(s) first reached by a destructive press "
            "were recorded, not explored)")
        assert next(n for n in store.list_nodes(crawl.id)
                    if n.signature == "fresh-deferred-discovery").status is NodeStatus.QUEUED
    else:
        assert crawl.status is CrawlStatus.STOPPED_BOUND
        assert crawl.stop_reason == "max_actions"
        assert len(rt.deferred) == 1
        assert rt.deferred[0][1].selector not in page.clicks


@pytest.mark.parametrize("node_status", [NodeStatus.ABORTED_ERROR, NodeStatus.ABORTED_DIALOG])
@pytest.mark.parametrize("completed", [True, False])
def test_abandoned_visit_retains_failed_login_observation_qualifier(node_status, completed):
    node = ScreenNode(crawl_id="c", project="p", url_template="/lost",
                      url_example="https://app.test/lost", signature="lost", status=node_status)
    case = Case(project="p", flow_id="login", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
                title="login", steps=[Step(order=1, action=Action.NAVIGATE,
                                           target="https://app.test/login")])
    error = "RuntimeError: cannot observe"
    status, reason = explore_status.terminal_status(
        completed=completed, actions_used=2, denied=0, nodes=[node], edges=[],
        login_case=case, login_signature=None, login_observe_error=error)
    assert status is CrawlStatus.ABORTED
    assert reason == (f"abandoned visits: {node_status.value} (/lost) -- login not judged: "
                      f"could not observe the login page ({error})")


@pytest.mark.parametrize("depth", [1, 3])
def test_real_depth_refusal_stops_before_queued_and_deferred_actions(tmp_path, monkeypatch, depth):
    from crawl_fake import BASE, SITE, make_project

    from autotester.schema.crawl import CrawlBounds
    from autotester.schema.enums import WritePolicy
    from autotester.stages import explore

    def link(name, path):
        return {"role": "link", "name": name, "selector": "a." + name, "href": path}

    monkeypatch.setitem(SITE, BASE, [
        {"role": "button", "name": "Delete account", "selector": "button.del"},
        link("branch", "/branch"), link("sibling", "/sibling")])
    monkeypatch.setitem(SITE, BASE + "branch", [link("deep", "/deep"), link("later", "/later")])
    for path in ("deep", "sibling", "later"):
        monkeypatch.setitem(SITE, BASE + path, [])
    captured = []
    original_bfs = explore._bfs

    def capture_bfs(rt):
        captured.append(rt)
        original_bfs(rt)

    monkeypatch.setattr(explore, "_bfs", capture_bfs)
    crawl, store, page = crawl_it(
        tmp_path, project=make_project(WritePolicy.ALLOW_WRITES),
        policy=SafetyPolicy(write_policy=WritePolicy.ALLOW_WRITES),
        bounds=CrawlBounds(max_depth=depth, max_screens=30, max_actions=100))
    nodes = store.list_nodes(crawl.id)
    if depth == 1:
        assert crawl.status is CrawlStatus.STOPPED_BOUND
        assert crawl.stop_reason == "max_depth"
        assert not captured[0].frontier_exhausted
        assert all(n.depth <= 1 for n in nodes)
        assert all(n.url_template != "/deep" for n in nodes)
        assert next(n for n in nodes if n.url_template == "/sibling").status is NodeStatus.QUEUED
        assert not any(e.name == "later" for e in store.list_edges(crawl.id))
        assert "button.del" not in page.clicks
        assert any(el.selector == "button.del" for _, el in captured[0].deferred)
        assert store.load_frontier(crawl.id).queue
        assert any(e.name == "deep" for e in store.list_edges(crawl.id))
    else:
        assert next(n for n in nodes if n.url_template == "/deep").depth == 2
        assert any(e.name == "later" for e in store.list_edges(crawl.id))
        assert "button.del" in page.clicks


@pytest.mark.parametrize("known,sticky,reached,expected", [
    (True, None, "none", None),
    *[(False, name, "all", name) for name in
      ("max_screens", "max_actions", "wall_clock_s", "max_depth")],
    (False, None, "all", "max_screens"),
    (False, None, "actions_time", "max_actions"),
    (False, None, "time", "wall_clock_s"),
    (False, None, "none", "max_depth"),
])
def test_depth_admission_dedup_and_recorded_bound_precedence(
    tmp_path, monkeypatch, known, sticky, reached, expected,
):
    from autotester.schema.crawl import CrawlBounds
    from autotester.stages import explore, explore_node

    captured = []
    monkeypatch.setattr(explore, "_bfs", lambda rt: captured.append(rt))
    crawl_it(tmp_path, bounds=CrawlBounds(max_depth=1))
    rt = captured[0]
    original = next(iter(rt.nodes.values()))
    candidate = original.model_copy(update={"depth": 2} if known else
                                    {"id": "unseen", "signature": "unseen", "depth": 2})
    edge = ScreenEdge(crawl_id=rt.crawl.id, from_node=original.id,
                      action=Action.CLICK, target="a.deep", outcome=EdgeOutcome.NAVIGATED)
    rt.stop_reason = sticky
    if reached == "all":
        rt.frontier.screens_found = rt.bounds.max_screens
    if reached in {"all", "actions_time"}:
        rt.frontier.actions_used = rt.bounds.max_actions
    if reached in {"all", "actions_time", "time"}:
        rt.started -= rt.bounds.wall_clock_s + 1
    before = rt.frontier.model_dump()
    explore_node._enqueue(rt, candidate, edge)
    assert rt.frontier.model_dump() == before
    assert rt.nodes[original.id] == original
    assert rt.stop_reason == expected
    if expected:
        assert explore.stop_reason(rt) == expected
