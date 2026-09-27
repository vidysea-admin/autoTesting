"""AT-227: an in-page modal on first paint must not silently swallow a crawl.

The prior behaviour, found on a real 35-second Pathlynks run: a "How are you
feeling today?" overlay rendered over the dashboard, `DialogBreaker` never saw
it (it handles NATIVE dialogs; this is ordinary DOM), and `enumerate.js` called
every control behind the veil `visible` because `getBoundingClientRect` and
`getComputedStyle` both say so. The crawl then spent its per-node budget
clicking controls no human could have clicked, learned ONE screen, and reported
`status=completed` with `issues=0` — a blocked crawl indistinguishable from a
complete one.

The fixture site here has the modal the committed `crawl_site` fixture does
not; the AT-227 note is explicit that a self-authored fixture without one could
never have surfaced this.

Contract: qa/contracts/explore.md X3, X16.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from autotester.browser.observe import PageObserver, enumerate_elements
from autotester.browser.secrets import SecretStore
from autotester.browser.session import BrowserSession
from autotester.core.paths import ProjectPaths
from autotester.schema.approval import RunApproval
from autotester.schema.crawl import Crawl, CrawlBounds
from autotester.schema.enums import ApprovalKind, EdgeOutcome, IssueKind, NodeStatus
from autotester.schema.project import Project
from autotester.stages.explore import run_crawl
from autotester.store.project_store import ProjectStore

SITE_DIR = Path(__file__).resolve().parent / "fixtures" / "modal_site"

BEHIND_THE_VEIL = {"Reports", "Settings", "Refresh"}
ON_THE_VEIL = {"Excited", "Focused", "Tired", "Skip for now"}


def _session(tmp_path: Path, base_url: str) -> tuple[BrowserSession, ProjectStore, PageObserver]:
    project = Project(slug="modal-demo", name="Modal demo", base_url=base_url + "/",
                      allowed_domains=["127.0.0.1"], headed=False)
    paths = ProjectPaths("modal-demo", tmp_path)
    paths.ensure()
    (tmp_path / ".env").write_text("", encoding="utf-8")
    secrets = SecretStore.load(project, tmp_path / ".env", strict=False)
    store = ProjectStore("modal-demo", tmp_path)
    store.add_approval(RunApproval(
        project="modal-demo", run_kind=ApprovalKind.CRAWL, target=project.base_url,
        scope="local modal fixture crawl in the live test suite", max_actions=200,
        wall_clock_s=600.0, granted_by="test", granted_at="2026-09-08",
        expires_at="2099-01-01",
    ).sign())
    observer = PageObserver()
    return BrowserSession(project, secrets, tmp_path / "shots", paths,
                          observer=observer), store, observer


@pytest.fixture(scope="module")
def modal_crawl(
    tmp_path_factory: pytest.TempPathFactory, serve_dir: Callable[[Path], str]
) -> tuple[Crawl, ProjectStore]:
    """ONE real crawl of the modal site, many assertions about it (the same
    module-scoping `test_explore_live.py` uses, for the same reason)."""
    pytest.importorskip("playwright")
    tmp_path = tmp_path_factory.mktemp("modal-crawl")
    session, store, observer = _session(tmp_path, serve_dir(SITE_DIR))
    try:
        session.start()
    except Exception as exc:  # browser binary missing on this machine
        pytest.skip(f"chromium unavailable: {type(exc).__name__}")
    try:
        crawl = run_crawl(project=session.project, session=session, store=store,
                          observer=observer,
                          bounds=CrawlBounds(max_screens=12, max_actions=60,
                                             wall_clock_s=120.0, dialog_repeat_limit=2))
    finally:
        session.close()
    return crawl, store


def test_controls_behind_the_veil_are_marked_obscured(
    tmp_path: Path, serve_dir: Callable[[Path], str]
) -> None:
    """The unit fact, straight off a real DOM: the dashboard's controls are
    `visible` by every CSS measure and still unclickable."""
    pytest.importorskip("playwright")
    session, _store, _observer = _session(tmp_path, serve_dir(SITE_DIR))
    try:
        session.start()
    except Exception as exc:
        pytest.skip(f"chromium unavailable: {type(exc).__name__}")
    try:
        session.goto(session.project.base_url)
        session.settle(timeout_ms=2000)
        by_name = {el.name: el for el in enumerate_elements(session.page)}
    finally:
        session.close()
    for name in BEHIND_THE_VEIL:
        assert by_name[name].visible, f"{name} really is CSS-visible"
        assert by_name[name].obscured, f"{name} is covered by the modal and must say so"
    for name in ON_THE_VEIL:
        assert not by_name[name].obscured, f"{name} is ON the modal and is clickable"


def test_the_crawl_gets_past_the_modal(modal_crawl: tuple[Crawl, ProjectStore]) -> None:
    """The consequence AT-227 measured: the real crawl learned ONE screen."""
    crawl, store = modal_crawl
    templates = {n.url_template for n in store.list_nodes(crawl.id)}
    assert "/reports.html" in templates, "never reached the page behind the modal"
    assert "/settings.html" in templates
    assert crawl.screens >= 3


def test_the_blocked_screen_is_reported_not_silent(
    modal_crawl: tuple[Crawl, ProjectStore],
) -> None:
    """X16: a screen whose controls were unreachable says so. The failure this
    replaces reported `issues=0` on a crawl that could see nothing."""
    crawl, store = modal_crawl
    overlay = [i for i in store.list_crawl_issues(crawl.id)
               if i.kind is IssueKind.OVERLAY]
    assert len(overlay) == 1, [i.detail for i in overlay]
    detail = overlay[0].detail
    assert detail.startswith("3 control(s)"), detail
    for name in BEHIND_THE_VEIL:  # what was covered, by name
        assert name in detail, detail
    assert "Skip for now" in detail, f"what to do instead belongs in the detail: {detail}"


def test_the_modal_state_is_its_own_screen(modal_crawl: tuple[Crawl, ProjectStore]) -> None:
    """X3: two states at one URL offering different controls are TWO screens.
    The modal state and the dashboard behind it share `/` and must not collapse
    into one node whose signature depends on which one was seen first.

    This test passed BEFORE the AT-227 fix existed and passes with the fix's
    signature change reverted -- it holds by the ordinary `visible` rule. It is
    kept because the property is real and worth pinning, and labelled here so
    nobody reads it as evidence for the occlusion work. The occlusion flag's
    two real jobs are covered by the tests below and above it."""
    crawl, store = modal_crawl
    at_root = [n for n in store.list_nodes(crawl.id) if n.url_template == "/"]
    assert len(at_root) == 2, [n.signature for n in at_root]


def test_no_edge_is_recorded_from_a_screen_the_crawl_had_already_left(
    modal_crawl: tuple[Crawl, ProjectStore],
) -> None:
    """`return_to` must confirm the SCREEN, not just the URL.

    The veiled screen and the dashboard behind it share `/`. Returning True on
    a URL match alone left the browser on the dismissed dashboard while the
    crawl went on trying the veiled screen's remaining controls — every one of
    which is hidden there, so each became an ERRORED edge attributed to a
    screen the browser was not on. The crawl still reached every page, which is
    why the outcome assertions above cannot see this; what it produced was a
    graph with invented failures in it.
    """
    crawl, store = modal_crawl
    veiled = next(n for n in store.list_nodes(crawl.id)
                  if n.url_template == "/" and any(e.obscured for e in n.elements))
    outcomes = {e.name: e.outcome for e in store.list_edges(crawl.id)
                if e.from_node == veiled.id}
    assert outcomes, "the veiled screen recorded no edges at all"
    errored = {name: o for name, o in outcomes.items() if o is EdgeOutcome.ERRORED}
    assert not errored, f"edges attributed to a screen the crawl had left: {errored}"


# -- a one-shot panel: the replay that CANNOT land ----------------------------

PANEL_DIR = Path(__file__).resolve().parent / "fixtures" / "panel_site"


@pytest.fixture(scope="module")
def panel_crawl(
    tmp_path_factory: pytest.TempPathFactory, serve_dir: Callable[[Path], str]
) -> tuple[Crawl, ProjectStore]:
    """A first-run panel that opens ONCE per browser. The screen it reveals has
    no URL that reaches it and cannot be restored by replaying the action that
    discovered it — the only situation in which the replay's landing check can
    be told apart from an unconditional success."""
    pytest.importorskip("playwright")
    tmp_path = tmp_path_factory.mktemp("panel-crawl")
    session, store, observer = _session(tmp_path, serve_dir(PANEL_DIR))
    try:
        session.start()
    except Exception as exc:  # browser binary missing on this machine
        pytest.skip(f"chromium unavailable: {type(exc).__name__}")
    try:
        crawl = run_crawl(project=session.project, session=session, store=store,
                          observer=observer,
                          bounds=CrawlBounds(max_screens=12, max_actions=60,
                                             wall_clock_s=120.0, dialog_repeat_limit=2))
    finally:
        session.close()
    return crawl, store


def test_a_replay_that_lands_elsewhere_is_a_failure_not_a_near_miss(
    panel_crawl: tuple[Crawl, ProjectStore],
) -> None:
    """The opened-panel screen is found, and then genuinely cannot be returned
    to. The crawl must say so and mark it unexplored — NOT explore whatever
    screen the replay actually landed on while believing it is this one."""
    crawl, store = panel_crawl
    opened = [n for n in store.list_nodes(crawl.id)
              if any(e.name == "Panel action A" and e.visible for e in n.elements)]
    assert len(opened) == 1, [n.name for n in store.list_nodes(crawl.id)]
    assert opened[0].status is NodeStatus.ABORTED_ERROR, opened[0].status
    lost = [i for i in store.list_crawl_issues(crawl.id)
            if i.kind is IssueKind.NAVIGATION and i.node_id == opened[0].id]
    assert lost, "a screen the crawl could not get back to must file an issue"
    detail = " ".join(i.detail for i in lost)
    assert "replaying the action that" in detail, detail
    # AT-108's standard: the cause names WHICH control was replayed, so a reader
    # can tell a one-shot control apart from a browser that died.
    assert "Open panel" in detail, detail
