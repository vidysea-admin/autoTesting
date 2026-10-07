"""CR5/CR3 — "complete" keeps meaning the frontier was exhausted.

Contract: qa/contracts/crawl-traversal.md CR5, carrying forward T-165's own goal
note verbatim: *"Complete means frontier exhausted; any safety/time/action/depth
bound is named as incomplete with every denied, skipped and unreached control
visible."* `explore.md` X4/X16/X18 are unamended; this file is what stops the new
machinery (a second traversal strategy, and a skip that deliberately does not
look at a screen) from quietly breaking that honesty.

The failure this guards against is the one the whole product judges other tools
for: a crawl that stops early, or takes most of a portal on trust, and still
reads as having covered it.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

import pytest
from crawl_fake import crawl_it, make_project
from crawl_live import FIXTURES, live_crawl

from autotester.schema.crawl import Crawl, CrawlBounds
from autotester.schema.enums import CrawlStatus, NodeStatus, TraversalStrategy
from autotester.schema.project import Project
from autotester.schema.screen_graph import CrawlFrontier, ScreenNode
from autotester.stages import crawl_coverage, explore, explore_node, explore_status
from autotester.stages.explore_runtime import ExploreRuntime
from autotester.stages.explore_safety import DialogBreaker
from autotester.stages.portal_persona import build_portal_persona
from autotester.store.project_store import ProjectStore

DEEP_SITE = FIXTURES / "deep_site"
BOUNDS_BY_NAME = {
    "max_screens": CrawlBounds(max_screens=2),
    "max_actions": CrawlBounds(max_actions=2),
    "wall_clock_s": CrawlBounds(wall_clock_s=0.0),
}

# --- the decisive criterion: no bound may ever read as complete --------------


@pytest.mark.parametrize("bound", sorted(BOUNDS_BY_NAME))
@pytest.mark.parametrize("strategy", list(TraversalStrategy))
def test_a_bound_stopped_crawl_is_never_completed_and_always_names_the_bound(
    tmp_path: Path, bound: str, strategy: TraversalStrategy
) -> None:
    """CR5: a `hybrid` crawl that stops on a bound still names that bound in
    `stop_reason`, exactly as X4 already requires for `bfs` — `hybrid` is not a
    second code path that forgets to set it. Both strategies, every bound."""
    crawl, _store, _page = crawl_it(tmp_path, bounds=BOUNDS_BY_NAME[bound], strategy=strategy)
    assert crawl.status is not CrawlStatus.COMPLETED, (
        f"{strategy}/{bound}: a bound fired and the crawl still read complete")
    assert crawl.stop_reason is not None and bound in crawl.stop_reason, (
        f"{strategy}/{bound}: stop_reason {crawl.stop_reason!r} does not name the bound")
    assert not explore_status.is_success(crawl)


@pytest.mark.parametrize("strategy", list(TraversalStrategy))
def test_completed_is_reachable_only_with_a_stop_reason_that_says_frontier_empty(
    tmp_path: Path, strategy: TraversalStrategy
) -> None:
    """The structural half of the same property: `run_crawl` decides completeness
    from `rt.frontier_exhausted` — the flag set at the one place the queue really
    drains — and never from a string. So a COMPLETED crawl's reason always starts
    with "frontier empty", and a reason that does not cannot produce COMPLETED."""
    crawl, _store, _page = crawl_it(tmp_path, bounds=CrawlBounds(), strategy=strategy)
    if crawl.status is CrawlStatus.COMPLETED:
        assert crawl.stop_reason.startswith("frontier empty")


@pytest.mark.parametrize("node_status,bound", [
    (NodeStatus.EXPLORED, "max_actions"), (NodeStatus.ABORTED_ERROR, None),
    (NodeStatus.ABORTED_DIALOG, None), (NodeStatus.ABORTED_ERROR, "max_actions"),
])
def test_a_bound_that_fires_mid_node_never_reads_as_an_exhausted_frontier(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, node_status, bound,
) -> None:
    """AT-463/AT-113: drain after a bound or abandoned visit is not exhaustion."""
    store = ProjectStore("p", tmp_path)
    project = Project(slug="p", name="p", base_url="https://app.test/")
    store.save_project(project)
    crawl = Crawl(project="p", bounds=CrawlBounds(max_actions=3))
    store.save_crawl(crawl)
    node = ScreenNode(crawl_id=crawl.id, project="p", url_template="/",
                      url_example="https://app.test/", signature="sig", name="Home")
    rt = ExploreRuntime(project=project, session=None, store=store, crawl=crawl,  # type: ignore[arg-type]
                        observer=None, breaker=DialogBreaker(2), clock=lambda: 0.0,  # type: ignore[arg-type]
                        started=0.0, frontier=CrawlFrontier())
    rt.nodes[node.id] = node
    rt.frontier.queue.append(node.id)

    def _bound_fires_partway_through(runtime: ExploreRuntime, _node: ScreenNode) -> None:
        """What `_click_loop` really does when a bound stops it mid-screen."""
        runtime.frontier.actions_used = runtime.bounds.max_actions if bound else 0
        runtime.stop_reason = bound
        runtime.nodes[_node.id] = _node.model_copy(update={"status": node_status})

    monkeypatch.setattr(explore_node, "visit_node", _bound_fires_partway_through)

    explore._bfs(rt)

    assert not rt.frontier.queue, "the queue did not drain -- the AT-463 shape was not built"
    assert rt.stop_reason == bound if bound else "abandoned" in rt.stop_reason
    assert rt.frontier_exhausted is False, (
        "the queue emptied after a bound had already fired and the crawl called itself "
        "complete -- controls on the last screen were never tried")
    expected = CrawlStatus.STOPPED_BOUND if bound else CrawlStatus.ABORTED
    assert explore._terminal_status(rt, rt.frontier_exhausted, None) is expected


def test_terminal_status_cannot_return_completed_when_the_frontier_was_not_exhausted() -> None:
    """The chokepoint itself, driven directly: `completed=False` never yields
    COMPLETED for ANY combination of the other inputs. This is the invariant the
    whole unit rests on, so it is pinned at the function that decides it rather
    than only observed through a crawl."""
    for actions in (0, 1, 50):
        for denied in (0, 3):
            status, _reason = explore_status.terminal_status(
                completed=False, actions_used=actions, denied=denied, nodes=[], edges=[],
                login_case=None, current_stop_reason="max_actions")
            assert status is not CrawlStatus.COMPLETED


@pytest.fixture(scope="module")
def bound_stopped_live(
    tmp_path_factory: pytest.TempPathFactory, serve_dir: Callable[[Path], str]
) -> tuple[Crawl, ProjectStore]:
    """A REAL browser crawl stopped by a real action bound — the live half of the
    "declares itself incomplete, and lists what it did not reach" evidence."""
    return live_crawl(tmp_path_factory.mktemp("bound"), serve_dir(DEEP_SITE), slug="bound",
                      bounds=CrawlBounds(max_screens=20, max_actions=8, wall_clock_s=120.0),
                      strategy=TraversalStrategy.HYBRID)


def test_a_live_bound_stopped_crawl_lists_every_control_it_did_not_reach(
    bound_stopped_live: tuple[Crawl, ProjectStore],
) -> None:
    """CR5/X16: every denied, skipped and unreached control stays visible, and
    the headline never reads 100% for a crawl that did not finish."""
    crawl, _store = bound_stopped_live
    assert crawl.status is CrawlStatus.STOPPED_BOUND
    assert crawl.stop_reason == "max_actions"
    coverage = crawl.coverage
    assert coverage is not None
    assert coverage.percent < 100
    unreached = coverage.by_reason()
    # Every hole carries a reason from the CLOSED set (V7b) — an early stop shows
    # up as `not_visited` on the screens the bound left queued, while the BOUND
    # itself is named once, on `stop_reason`. Measured on this very crawl:
    # {'not_visited': 12}. The assertion is that nothing is unexplained, not that
    # a particular spelling appears.
    assert unreached, "a bound-stopped crawl reported no unreached control at all"
    assert all(r in crawl_coverage.REASONS or r.split(":")[0] + ":" in crawl_coverage.REASONS
               for r in unreached), unreached
    # and the unreached controls are NAMED, per screen — not merely counted
    assert all(h.url_template and h.selector for h in coverage.holes)
    assert coverage.screens_queued_unvisited > 0, (
        "the bound fired but no screen is recorded as reached-but-never-visited")
    # the books balance (coverage.md V7) — nothing vanished from the count
    assert coverage.controls_exercised + len(coverage.holes) == coverage.controls_discovered


# --- CR3: the persona-seeded incremental skip -------------------------------


def _site_copy(tmp_path: Path) -> Path:
    site = tmp_path / "site"
    shutil.copytree(DEEP_SITE, site)
    return site


def _seed_persona(store: ProjectStore, crawl: Crawl, slug: str, base_url: str) -> None:
    """Promote crawl 1's graph into the durable persona, exactly as the pipeline
    does — the persona is what crawl 2 reads its cache keys from (CR3)."""
    store.save_project(Project(slug=slug, name=slug, base_url=base_url + "/",
                               allowed_domains=["127.0.0.1"]))
    build_portal_persona(store, crawl_id=crawl.id)


@pytest.fixture(scope="module")
def incremental_pair(
    tmp_path_factory: pytest.TempPathFactory, serve_dir: Callable[[Path], str]
) -> tuple[Crawl, Crawl, ProjectStore]:
    """Crawl the SAME unchanged site twice, the second time incrementally."""
    tmp_path = tmp_path_factory.mktemp("incr-same")
    base = serve_dir(_site_copy(tmp_path))
    bounds = CrawlBounds(max_screens=20, max_actions=80, wall_clock_s=180.0)
    first, store = live_crawl(tmp_path, base, slug="incr", bounds=bounds)
    _seed_persona(store, first, "incr", base)
    second, _ = live_crawl(tmp_path, base, slug="incr", bounds=bounds,
                           incremental=True, store=store)
    return first, second, store


def test_an_unchanged_project_costs_at_most_a_tenth_of_the_first_crawls_actions(
    incremental_pair: tuple[Crawl, Crawl, ProjectStore],
) -> None:
    """CR3's falsifiable, D-040 acceptance test (b): a second crawl of a fixture
    project unchanged since the first issues <=10% of the first's actions."""
    first, second, _store = incremental_pair
    assert first.actions > 0, "the first crawl did nothing — the comparison is vacuous"
    assert second.actions <= first.actions // 10, (
        f"incremental crawl spent {second.actions} of the first crawl's {first.actions}")
    assert second.skipped_unchanged > 0, "nothing was skipped, so nothing was cached"


def test_a_skip_never_reads_as_having_explored_the_screen(
    incremental_pair: tuple[Crawl, Crawl, ProjectStore],
) -> None:
    """CR5: a skip is recorded as its own status and is NEVER folded into
    "frontier empty"/COMPLETED as if the skipped node had been explored. A
    persona-seeded crawl that skips 90% of the portal must not read as having
    explored 90% of the portal."""
    _first, second, store = incremental_pair
    skipped = [n for n in store.list_nodes(second.id)
               if n.status is NodeStatus.SKIPPED_UNCHANGED]
    assert skipped, "no node carries the skip status"
    assert second.skipped_unchanged == len(skipped)
    assert "skipped as unchanged" in second.stop_reason
    assert second.stop_reason != "frontier empty"
    assert not explore_status.is_success(second), (
        "a crawl that performed no action and skipped everything read as success")


def test_every_skipped_screens_controls_stay_visible_as_named_holes(
    incremental_pair: tuple[Crawl, Crawl, ProjectStore],
) -> None:
    """CR5: skip-for-unchanged is a NEW NAMED category alongside DENIED_POLICY /
    SKIPPED_UNNAMED / OFF_DOMAIN_REFUSED — it does not let a skip disappear from
    the surfaces X16 lists."""
    _first, second, _store = incremental_pair
    coverage = second.coverage
    assert coverage is not None
    assert coverage.by_reason().get("skipped_unchanged", 0) > 0, coverage.by_reason()
    assert coverage.percent < 100
    assert coverage.controls_exercised + len(coverage.holes) == coverage.controls_discovered


def test_a_genuinely_changed_project_is_re_explored_not_skipped(
    tmp_path_factory: pytest.TempPathFactory, serve_dir: Callable[[Path], str]
) -> None:
    """CR3's falsifiable, second half: the same second crawl against a fixture
    whose every screen's structure genuinely changed issues close to the first
    crawl's action count — the skip triggers on stored-AND-matching, never merely
    on "seen before"."""
    tmp_path = tmp_path_factory.mktemp("incr-changed")
    site = _site_copy(tmp_path)
    base = serve_dir(site)
    bounds = CrawlBounds(max_screens=20, max_actions=80, wall_clock_s=180.0)
    first, store = live_crawl(tmp_path, base, slug="chg", bounds=bounds)
    _seed_persona(store, first, "chg", base)
    for page in sorted(site.glob("*.html")):  # change EVERY screen's structure
        page.write_text(page.read_text(encoding="utf-8").replace(
            "</body>", '<button type="button" id="added">Recently added control</button></body>'),
            encoding="utf-8")
    second, _ = live_crawl(tmp_path, base, slug="chg", bounds=bounds,
                           incremental=True, store=store)
    assert second.skipped_unchanged == 0, "a structurally changed screen was skipped"
    assert second.actions >= first.actions, (
        f"changed site cost {second.actions} against the first crawl's {first.actions}")


def test_incremental_is_off_by_default_so_every_existing_caller_is_unchanged(
    tmp_path: Path,
) -> None:
    """A crawl that does not ask for incremental mode skips nothing, even with a
    persona on disk — the pre-T-165 behaviour, byte for byte."""
    project = make_project()
    crawl, store, _page = crawl_it(tmp_path, project=project)
    store.save_project(project)
    build_portal_persona(store, crawl_id=crawl.id)
    again, _store, _page2 = crawl_it(tmp_path, project=project, store=store)
    assert again.incremental is False
    assert again.skipped_unchanged == 0
    assert again.actions == crawl.actions
