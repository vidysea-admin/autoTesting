"""`stages/explore.py` + `explore_node.py`: the BFS loop, its bounds, and its
safety refusals — driven by the scripted fake site in `crawl_fake.py`, no
real browser.

Contract: qa/contracts/explore.md X1-X11. The live-browser half is
`test_explore_live.py`; the credential-free end-to-end proof is
`scripts/explore_proof.py`.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from crawl_fake import crawl_it, grant_crawl_approval, make_project, make_session

from autotester.browser.observe import PageObserver
from autotester.schema.crawl import CrawlBounds, SafetyPolicy
from autotester.schema.enums import CrawlStatus, EdgeOutcome, WritePolicy
from autotester.stages.explore import run_crawl
from autotester.store.project_store import ProjectStore

SENTINELS = ("/deleted", "/saved", "/logged-out")


# -- X4: the crawl terminates, and names why ---------------------------------

def test_crawl_completes_and_names_frontier_empty(tmp_path: Path) -> None:
    crawl, _store, _page = crawl_it(tmp_path)
    assert crawl.status is CrawlStatus.COMPLETED
    assert crawl.stop_reason == "frontier empty"


def test_max_actions_bound_stops_the_crawl_and_names_itself(tmp_path: Path) -> None:
    crawl, _store, _page = crawl_it(tmp_path, bounds=CrawlBounds(max_actions=2))
    assert crawl.stop_reason == "max_actions"
    assert crawl.status is CrawlStatus.STOPPED_BOUND
    assert crawl.actions <= 3  # the in-flight action may finish; the next never starts


def test_max_screens_bound_stops_the_crawl(tmp_path: Path) -> None:
    crawl, _store, _page = crawl_it(tmp_path, bounds=CrawlBounds(max_screens=2))
    assert crawl.stop_reason == "max_screens"
    assert crawl.screens <= 2


def test_wall_clock_bound_stops_the_crawl_with_an_injected_clock(tmp_path: Path) -> None:
    ticks = iter([0.0] + [999.0] * 200)

    crawl, _store, _page = crawl_it(
        tmp_path, bounds=CrawlBounds(wall_clock_s=10.0), clock=lambda: next(ticks),
    )
    assert crawl.stop_reason == "wall_clock_s"


def test_crawl_runs_without_any_provider(tmp_path: Path) -> None:
    """X4: no stop condition depends on provider output — `run_crawl` takes no
    provider at all, so a crawl cannot stall on a model."""
    crawl, _store, _page = crawl_it(tmp_path)
    assert crawl.provider == "mock"
    assert crawl.screens > 0


# -- X3: identity — two ids collapse, the graph dedupes ----------------------

def test_two_student_ids_collapse_to_one_node(tmp_path: Path) -> None:
    _crawl, store, _page = crawl_it(tmp_path)
    crawl_id = store.list_crawl_ids()[0]
    templates = [n.url_template for n in store.list_nodes(crawl_id)]
    assert templates.count("/students/{id}") == 1


def test_every_node_is_stored_once(tmp_path: Path) -> None:
    _crawl, store, _page = crawl_it(tmp_path)
    crawl_id = store.list_crawl_ids()[0]
    ids = [n.id for n in store.list_nodes(crawl_id)]
    assert len(ids) == len(set(ids))


# -- X5/X6: nothing destructive is clicked under READ_ONLY -------------------

def test_delete_save_and_logout_are_never_clicked_under_read_only(tmp_path: Path) -> None:
    _crawl, store, page = crawl_it(tmp_path)
    assert "button.del" not in page.clicks
    assert "button.save" not in page.clicks
    assert "a.out" not in page.clicks
    for sentinel in SENTINELS:
        assert not any(sentinel in url for url in page.history), sentinel
    crawl_id = store.list_crawl_ids()[0]
    denied = [e for e in store.list_edges(crawl_id) if e.outcome is EdgeOutcome.DENIED_POLICY]
    assert {e.name for e in denied} >= {"Delete account", "Save", "Log out"}


def test_unnamed_control_is_skipped_and_recorded(tmp_path: Path) -> None:
    _crawl, store, page = crawl_it(tmp_path)
    assert "button.icon" not in page.clicks
    crawl_id = store.list_crawl_ids()[0]
    skipped = [e for e in store.list_edges(crawl_id)
               if e.outcome is EdgeOutcome.SKIPPED_UNNAMED]
    assert skipped and skipped[0].target == "button.icon"


def test_allow_writes_never_clicks_account_destroy_or_logout(tmp_path: Path) -> None:
    """The same fixture under ALLOW_WRITES: the deny-list is off, but the
    never-click guard still refuses Log out (D-016) and Delete account (D-098)."""
    project = make_project(WritePolicy.ALLOW_WRITES)
    policy = SafetyPolicy(write_policy=WritePolicy.ALLOW_WRITES)
    _crawl, _store, page = crawl_it(tmp_path, project=project, policy=policy)
    assert "button.del" not in page.clicks
    assert "a.out" not in page.clicks
    assert not any("/logged-out" in url for url in page.history)


# -- X7: off-domain is refused ------------------------------------------------

def test_external_link_is_refused_before_it_is_followed(tmp_path: Path) -> None:
    _crawl, store, page = crawl_it(tmp_path)
    assert not any("evil.test" in url for url in page.history)
    crawl_id = store.list_crawl_ids()[0]
    refused = [e for e in store.list_edges(crawl_id)
               if e.outcome is EdgeOutcome.OFF_DOMAIN_REFUSED]
    assert refused and refused[0].name == "External"
    issues = store.list_crawl_issues(crawl_id)
    assert any("off-domain" in i.detail for i in issues)


# -- X11: artifacts are incremental and human-readable ------------------------

def test_nodes_edges_and_frontier_are_on_disk_as_files(tmp_path: Path) -> None:
    crawl, store, _page = crawl_it(tmp_path)
    paths = store.paths
    assert paths.crawl_manifest(crawl.id).exists()
    assert paths.crawl_nodes(crawl.id).exists()
    assert paths.crawl_edges(crawl.id).exists()
    assert paths.crawl_frontier(crawl.id).exists()
    frontier = store.load_frontier(crawl.id)
    assert frontier is not None and frontier.visited


def test_visited_nodes_are_marked_explored_on_disk_not_just_in_memory(tmp_path: Path) -> None:
    """Found running this for real: `_mark` updated only the in-memory index,
    and because `add_node` is idempotent the persisted graph recorded every
    node as QUEUED forever — a crawl that fully explored 4 screens looked, on
    disk, like one that had explored none. `update_node` closes it."""
    _crawl, store, _page = crawl_it(tmp_path)
    crawl_id = store.list_crawl_ids()[0]
    statuses = {n.status.value for n in store.list_nodes(crawl_id)}
    assert statuses == {"explored"}


def test_every_settle_uses_the_crawl_bound_not_the_default_ceiling(tmp_path: Path) -> None:
    """AT-095 (checker-found): `settle_ms` fixed a real defect — a 60-action
    crawl took >5 minutes because every action waited up to 8.5s for
    networkidle — but shipped with no test, unlike the node-status fix.
    A regression to `session.settle()` (the 8000ms default) would be silent
    and would only show up as a crawl nobody wants to wait for."""
    bounds = CrawlBounds(settle_ms=137)
    project = make_project()
    session, _page = make_session(tmp_path, project)
    seen: list[int] = []
    original = session.settle
    session.settle = lambda expected=None, timeout_ms=8000: (  # type: ignore[method-assign]
        seen.append(timeout_ms), original(expected, timeout_ms))[1]

    store = ProjectStore("demo", tmp_path)
    grant_crawl_approval(store, project, bounds)
    run_crawl(project, session, store, observer=PageObserver(), bounds=bounds)

    assert seen, "the crawl never settled at all"
    assert set(seen) == {137}, f"some settle used the default ceiling: {sorted(set(seen))}"


def test_reloaded_crawl_matches_the_returned_envelope(tmp_path: Path) -> None:
    crawl, store, _page = crawl_it(tmp_path)
    loaded = store.load_crawl(crawl.id)
    assert loaded is not None
    assert (loaded.screens, loaded.edges, loaded.stop_reason) == (
        crawl.screens, crawl.edges, crawl.stop_reason)


# -- AT-098: a failed seed names its cause, and a refusal never reads like a timeout

def test_a_domain_refusal_at_seed_is_distinguishable_from_a_network_failure(
    tmp_path: Path,
) -> None:
    """AT-098 (checker-found, before T-145): `_seed` swallowed the exception
    entirely, so every distinct failure collapsed to "could not open base_url".
    An operator watching a live ERP crawl could not tell whether the product was
    down or whether the crawl had been refused by its own domain guard -- and
    that refusal is the X7 SECURITY boundary, not an outage."""
    from autotester.browser.session import NavigationRefused

    project = make_project()
    session, _page = make_session(tmp_path, project)

    def refuse(_url: str) -> None:
        raise NavigationRefused("'https://evil.test/' is outside allowed domains ['app.test']")

    session.goto = refuse  # type: ignore[method-assign]
    store = ProjectStore("demo", tmp_path)
    grant_crawl_approval(store, project)
    crawl = run_crawl(project, session, store, observer=PageObserver())

    assert crawl.status is CrawlStatus.ABORTED
    assert "refused by the domain guard" in (crawl.stop_reason or "")
    assert "evil.test" in (crawl.stop_reason or "")


def test_an_ordinary_failure_at_seed_names_its_exception_type(tmp_path: Path) -> None:
    project = make_project()
    session, _page = make_session(tmp_path, project)

    def boom(_url: str) -> None:
        raise TimeoutError("navigation timed out")

    session.goto = boom  # type: ignore[method-assign]
    store = ProjectStore("demo", tmp_path)
    grant_crawl_approval(store, project)
    crawl = run_crawl(project, session, store, observer=PageObserver())

    assert "TimeoutError" in (crawl.stop_reason or "")
    assert "refused by the domain guard" not in (crawl.stop_reason or "")


# -- D-018/T-124: the consent gate refuses before anything exists -------------

def test_a_crawl_without_an_approval_refuses_and_writes_nothing(tmp_path: Path) -> None:
    """The property that matters is not that it raises — it is that it raises
    BEFORE a crawl envelope, a browser navigation or a screenshot directory
    exists. A gate that refuses after the fact has already done the thing."""
    from autotester.core.consent import ApprovalRequired

    project = make_project()
    session, page = make_session(tmp_path, project)
    store = ProjectStore("demo", tmp_path)
    before = list(page.history)  # the fake page seeds one entry in its constructor

    with pytest.raises(ApprovalRequired) as exc:
        run_crawl(project, session, store, observer=PageObserver())

    assert "autotester approve demo --kind crawl" in str(exc.value)
    assert store.list_crawl_ids() == []
    assert page.history == before, "the crawl navigated before the gate refused it"
    assert page.clicks == []
    assert not store.paths.crawls_dir.exists()


def test_a_crawl_wider_than_its_approval_refuses(tmp_path: Path) -> None:
    """Granting 10 actions and then asking for 200 is the case a careful
    operator still gets wrong — the bounds are checked, not just the existence
    of a row."""
    from autotester.core.consent import ApprovalRequired

    project = make_project()
    session, _page = make_session(tmp_path, project)
    store = ProjectStore("demo", tmp_path)
    grant_crawl_approval(store, project, CrawlBounds(max_actions=10, wall_clock_s=10.0))

    with pytest.raises(ApprovalRequired, match="narrower than this run"):
        run_crawl(project, session, store, observer=PageObserver(),
                  bounds=CrawlBounds(max_actions=200, wall_clock_s=600.0))
