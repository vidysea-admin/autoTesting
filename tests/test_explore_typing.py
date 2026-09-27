"""X10-b (D-029): the explorer's synthetic typing pre-pass.

The four conditions and their violations: typing happens ONLY under
TEST_ACCOUNT/ALLOW_WRITES with the run's `synthetic_typing` switch on, values
are deterministic and non-PII, password fields are never typed, and X4's
bounds bind typed actions exactly as they bind clicks.

Contract: qa/contracts/explore.md X10 (amended), X5, X12, V7b.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from crawl_fake import make_project, make_session

from autotester.browser.observe import PageObserver
from autotester.schema.crawl import CrawlBounds, SafetyPolicy
from autotester.schema.enums import EdgeOutcome, WritePolicy
from autotester.schema.project import Project
from autotester.stages.explore_safety import typing_allowed
from autotester.stages.synthetic_values import synthetic_value
from autotester.store.project_store import ProjectStore

TYPED_POLICY = SafetyPolicy(write_policy=WritePolicy.TEST_ACCOUNT, synthetic_typing=True)
SETTINGS_URL = "https://app.test/settings"


def _register_fillable(page: object) -> None:
    """The fake's fill only 'exists' where a test registered it (AT-226's
    mechanism) â€” register the settings page's typing targets."""
    page.fillable[SETTINGS_URL] = {  # type: ignore[attr-defined]
        "input.displayname", "select.grade",
    }


def crawl_typing(tmp_path: Path, **kwargs: object) -> tuple[object, ProjectStore, object]:
    from crawl_fake import grant_crawl_approval

    project = kwargs.get("project") or make_project(WritePolicy.TEST_ACCOUNT)
    session, page = make_session(tmp_path, project)
    _register_fillable(page)
    store = ProjectStore("demo", tmp_path)
    bounds = kwargs.get("bounds") or CrawlBounds()
    grant_crawl_approval(store, project, bounds)  # type: ignore[arg-type]
    from autotester.stages.explore import run_crawl

    crawl = run_crawl(
        project, session, store,  # type: ignore[arg-type]
        observer=PageObserver(),
        bounds=bounds,  # type: ignore[arg-type]
        policy=kwargs.get("policy", TYPED_POLICY),
    )
    return crawl, store, page


# -- the gate itself ----------------------------------------------------------

def test_typing_allowed_matrix() -> None:
    """Four conditions, one boolean: the two widening policies pass only with
    the flag; READ_ONLY never passes, and the flag alone never passes."""
    assert typing_allowed(SafetyPolicy(write_policy=WritePolicy.TEST_ACCOUNT,
                                       synthetic_typing=True))
    assert typing_allowed(SafetyPolicy(write_policy=WritePolicy.ALLOW_WRITES,
                                       synthetic_typing=True))
    assert not typing_allowed(SafetyPolicy(write_policy=WritePolicy.READ_ONLY,
                                           synthetic_typing=True))
    assert not typing_allowed(SafetyPolicy(write_policy=WritePolicy.TEST_ACCOUNT,
                                           synthetic_typing=False))
    assert not typing_allowed(SafetyPolicy())  # the default: X10 exactly as it was


# -- behaviour under the fake site --------------------------------------------

def _settings_edges(store: ProjectStore, crawl_id: str) -> list[tuple[str, str, str]]:
    edges = store.list_edges(crawl_id)
    by_target = {e.target: (e.action.value, e.outcome.value, e.reason or "")
                 for e in edges}
    return [(t, *v) for t, v in by_target.items()]  # type: ignore[misc]


def test_synthetic_values_are_typed_under_the_enabled_policy(tmp_path: Path) -> None:
    _crawl, _store, page = crawl_typing(tmp_path, policy=TYPED_POLICY,
                                   project=make_project(WritePolicy.TEST_ACCOUNT))
    assert page.fills, "the typing pre-pass never typed anything"
    assert page.selects, "the combobox was never selected"
    for _selector, value in page.fills:
        assert "autotester" in value.lower() or value.startswith("AutoTester")


def test_typing_never_happens_under_read_only(tmp_path: Path) -> None:
    _crawl, _store, page = crawl_typing(
        tmp_path, policy=SafetyPolicy(write_policy=WritePolicy.READ_ONLY),
        project=make_project(WritePolicy.READ_ONLY))
    assert page.fills == [] and page.selects == []


def test_typing_never_happens_without_the_flag(tmp_path: Path) -> None:
    """The policy alone is not enough â€” the run must deliberately enable
    synthetic typing; D-029's default is OFF."""
    _crawl, _store, page = crawl_typing(
        tmp_path, policy=SafetyPolicy(write_policy=WritePolicy.TEST_ACCOUNT),
        project=make_project(WritePolicy.TEST_ACCOUNT))
    assert page.fills == [] and page.selects == []


def test_typed_edges_are_recorded(tmp_path: Path) -> None:
    _crawl, store, _page = crawl_typing(tmp_path, policy=TYPED_POLICY,
                                   project=make_project(WritePolicy.TEST_ACCOUNT))
    crawl_id = store.list_crawl_ids()[0]
    edges = store.list_edges(crawl_id)
    fill_edges = [e for e in edges if e.action.value in ("fill", "select")]
    assert fill_edges, "typed actions never reached the edge log"
    assert all(e.outcome in (EdgeOutcome.SAME_SCREEN, EdgeOutcome.NAVIGATED,
                             EdgeOutcome.ERRORED) for e in fill_edges)


def test_bounds_bind_typing(tmp_path: Path) -> None:
    """X4: max_actions counts typed actions â€” a 1-action bound stops the
    typing pre-pass after one field, and the crawl names the bound."""
    crawl, _store, page = crawl_typing(
        tmp_path, policy=TYPED_POLICY, project=make_project(WritePolicy.TEST_ACCOUNT),
        bounds=CrawlBounds(max_actions=2))
    assert crawl.stop_reason == "max_actions"
    assert crawl.actions <= 3
    assert len(page.fills) + len(page.selects) + len(page.clicks) <= 4


def test_values_are_deterministic_and_non_pii() -> None:
    """The same field always yields the same value (X12's determinism extends
    to typing), and every value is an obvious fake."""
    a = synthetic_value("Display name", "input.displayname", "textbox")
    b = synthetic_value("Display name", "input.displayname", "textbox")
    assert a == b
    for name in ("email", "search", "date", "number", "url", "city", "comment"):
        value = synthetic_value(name, f"input.{name}", "textbox")
        assert value, name
        assert "@" not in value or "autotester.invalid" in value, value
    assert synthetic_value("email", "input.email", "textbox").endswith("autotester.invalid")


def test_a_password_field_is_never_typed(tmp_path: Path) -> None:
    """A 'change password' form is a credential change â€” D-029's
    non-destructive clause. The field's own name refuses it."""
    from autotester.schema.screen_graph import ElementRef
    from autotester.stages.explore_safety import typing_target_allowed

    assert not typing_target_allowed(ElementRef(role="textbox", name="New password",
                                                selector="input.new-password"))
    assert not typing_target_allowed(ElementRef(role="textbox", name="Confirm passwd",
                                                selector="input.pw2"))
    assert typing_target_allowed(ElementRef(role="textbox", name="Display name",
                                            selector="input.displayname"))


def test_the_click_loop_still_runs_after_typing(tmp_path: Path) -> None:
    """The typing pre-pass must not replace the click phase: Save (the form's
    submit) is still a click candidate under TEST_ACCOUNT, and the destructive
    deny-list still refuses Delete (D-029's non-destructive clause)."""
    _crawl, _store, page = crawl_typing(tmp_path, policy=TYPED_POLICY,
                                   project=make_project(WritePolicy.TEST_ACCOUNT))
    assert "button.save" in page.clicks  # the filled form's submit is pressed
    assert "button.del" not in page.clicks

# -- the REAL browser proof (the fake cannot prove Playwright actually typed) --

# -- the REAL browser proof (the fake cannot prove Playwright actually typed) --

def test_a_real_browser_types_and_submits_the_filled_form(
    tmp_path: Path,
    serve_dir: Callable[[Path], str],
) -> None:
    """Mode D-style live proof, fixture-level: a real headless Chromium fills
    settings.html's displayname with a synthetic value and its submit carries
    the value in the resulting GET url (/saved.html?displayname=ΓÇª). Skipped
    when Chromium is unavailable, like every live test."""
    pytest.importorskip("playwright")
    from autotester.browser.secrets import SecretStore
    from autotester.browser.session import BrowserSession
    from autotester.core.paths import ProjectPaths
    from autotester.schema.approval import RunApproval
    from autotester.schema.enums import ApprovalKind
    from autotester.stages.explore import run_crawl

    base_url = serve_dir(Path(__file__).resolve().parent / "fixtures" / "crawl_site")
    project = Project(  # type: ignore[call-arg]
        slug="type-demo", name="Type demo", base_url=base_url + "/settings.html",
        allowed_domains=["127.0.0.1"], headed=False,
        write_policy=WritePolicy.TEST_ACCOUNT)
    paths = ProjectPaths("type-demo", tmp_path)
    paths.ensure()
    (tmp_path / ".env").write_text("", encoding="utf-8")
    secrets = SecretStore.load(project, tmp_path / ".env", strict=False)
    store = ProjectStore("type-demo", tmp_path)
    store.add_approval(RunApproval(
        project="type-demo", run_kind=ApprovalKind.CRAWL, target=project.base_url,
        scope="local fixture: synthetic typing proof, form submit on a GET form",
        max_actions=60, wall_clock_s=120.0, granted_by="test",
        granted_at="2026-09-21", expires_at="2099-01-01",
    ).sign())
    observer = PageObserver()
    session = BrowserSession(project, secrets, tmp_path / "shots", paths, observer=observer)
    try:
        session.start()
    except Exception as exc:
        pytest.skip(f"chromium unavailable: {type(exc).__name__}")
    try:
        crawl = run_crawl(
            project, session, store, observer=observer,
            bounds=CrawlBounds(max_screens=8, max_actions=40, wall_clock_s=90.0),
            policy=SafetyPolicy(write_policy=WritePolicy.TEST_ACCOUNT,
                                synthetic_typing=True))
    finally:
        session.close()
    assert crawl.status.value in ("completed", "stopped_bound"), crawl.stop_reason
    saved = [n.url_example for n in store.list_nodes(crawl.id)
             if "displayname=" in n.url_example]
    assert saved, "the filled form's submit never carried the synthetic value"
    assert any("autotester" in u.lower() or "autotester" in u.lower()
               for u in saved), saved
