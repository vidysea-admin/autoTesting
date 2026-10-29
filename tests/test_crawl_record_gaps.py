"""The four gaps a real Pathlynks crawl exposed in the crawl RECORD (not the crawl itself).

(a) a same-URL layout toggle ("Collapse sidebar") minted a new screen, (b) no per-screen
inventory of successful API requests, (c) an errored edge's cause was an unbounded multi-line
blob with no structured class, (d) `Crawl.provider` read "mock" though a crawl uses no provider.

Driven by the scripted fake site in `crawl_fake.py`; no browser.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import crawl_fake
import pytest
from crawl_fake import BASE, grant_crawl_approval, make_project, make_session
from pydantic import ValidationError

from autotester.browser.observe import PageObserver
from autotester.core.redact import Redactor
from autotester.schema.crawl import Crawl, SafetyPolicy
from autotester.schema.enums import EdgeOutcome
from autotester.schema.screen_graph import ApiCall, ElementRef, ScreenNode
from autotester.stages import network_capture
from autotester.stages.explore import run_crawl
from autotester.stages.screen_identity import is_layout_toggle
from autotester.store.project_store import ProjectStore


def _el(role: str, name: str) -> ElementRef:
    return ElementRef(role=role, name=name, selector=f"#{name}")


# -- (a) layout toggles are not screens --------------------------------------

@pytest.mark.parametrize("name", ["Collapse sidebar", "Expand sidebar", "Toggle navigation",
                                  "Hide side nav", "Show sidebar", "Collapse the sidebar"])
def test_sidebar_toggles_are_layout_toggles(name: str) -> None:
    assert is_layout_toggle(_el("button", name))


@pytest.mark.parametrize("role,name", [("button", "Collapse all rows"), ("button", "Open filters"),
                                       ("button", "Delete sidebar widget"), ("link", "Sidebar"),
                                       ("button", "")])
def test_other_controls_are_not_layout_toggles(role: str, name: str) -> None:
    assert not is_layout_toggle(_el(role, name))


def test_a_layout_toggle_does_not_create_a_screen_record(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toggle = {"role": "button", "name": "Collapse sidebar", "selector": "button.toggle"}
    expanded = [*crawl_fake.SITE[BASE], toggle]
    collapsed = [e for e in expanded if e["selector"] != "a.settings"]  # label hidden
    collapsed.append({**toggle, "name": "Expand sidebar"})
    monkeypatch.setitem(crawl_fake.SITE, BASE, expanded)
    project = make_project()
    session, page = make_session(tmp_path, project)
    state = {"collapsed": False}
    real_click, real_goto, real_eval = crawl_fake.FakeLocator.click, page.goto, page.evaluate

    def click(self: Any) -> None:
        if self.selector == "button.toggle":
            state["collapsed"] = True
        real_click(self)

    def goto(url: str, wait_until: str = "") -> None:
        state["collapsed"] = False  # a reload restores the expanded layout
        real_goto(url, wait_until)

    def evaluate(script: str) -> list[dict[str, Any]]:
        if state["collapsed"] and page.url == BASE:
            return [crawl_fake._element(raw) for raw in collapsed]
        return real_eval(script)

    monkeypatch.setattr(crawl_fake.FakeLocator, "click", click)
    monkeypatch.setattr(page, "goto", goto)
    monkeypatch.setattr(page, "evaluate", evaluate)
    store = ProjectStore("demo", tmp_path)
    grant_crawl_approval(store, project)

    crawl = run_crawl(project, session, store, observer=PageObserver())

    nodes = store.list_nodes(crawl.id)
    assert [n.url_template for n in nodes].count("/") == 1
    edge = next(e for e in store.list_edges(crawl.id) if e.name == "Collapse sidebar")
    assert edge.outcome is EdgeOutcome.SAME_SCREEN
    assert edge.to_node == edge.from_node


# -- (b) per-screen inventory of successful API requests ---------------------

def test_api_inventory_keeps_first_party_successes_as_method_path_status() -> None:
    project = make_project()
    policy = SafetyPolicy()
    responses = [
        ("GET", "https://app.test/api/students/12?token=abc", 200),
        ("GET", "https://app.test/api/students/99", 200),
        ("POST", "https://app.test/api/log", 201),
        ("GET", "https://app.test/api/fail", 500),
        ("GET", "https://www.google-analytics.com/collect", 200),
        ("GET", "https://app.test/_next/static/chunk.js", 200),
        ("GET", "https://app.test/logo.png", 200),
    ]
    calls = network_capture.api_inventory(responses, project, policy, Redactor({}))
    assert calls == [ApiCall(method="GET", path="/api/students/{id}", status=200, count=2),
                     ApiCall(method="POST", path="/api/log", status=201, count=1)]


def test_api_inventory_redacts_and_is_bounded() -> None:
    project = make_project()
    policy = SafetyPolicy()
    many = [("GET", f"https://app.test/api/r{i}x", 200) for i in range(500)]
    calls = network_capture.api_inventory(many, project, policy, Redactor({}))
    assert len(calls) == network_capture.MAX_API_CALLS_PER_NODE
    hidden = network_capture.api_inventory(
        [("GET", "https://app.test/api/sekret-value/list", 200)], project, policy,
        Redactor({"K": "sekret-value"}))
    assert "sekret-value" not in hidden[0].path


def test_a_crawl_records_api_calls_on_the_screen_that_made_them(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = make_project()
    session, page = make_session(tmp_path, project)
    observer = PageObserver()
    real_visit = page.visit

    def visit(url: str) -> None:
        real_visit(url)
        if "/students/" in url and not url.endswith("/students/"):
            observer.api_responses += [("GET", "https://app.test/api/students/7", 200),
                                       ("GET", "https://app.test/api/bad", 404)]
        observer.responses.append(("GET", url, 200))

    monkeypatch.setattr(page, "visit", visit)
    store = ProjectStore("demo", tmp_path)
    grant_crawl_approval(store, project)

    crawl = run_crawl(project, session, store, observer=observer)

    by_template = {n.url_template: n for n in store.list_nodes(crawl.id)}
    detail = by_template["/students/{id}"]
    assert [(c.method, c.path, c.status) for c in detail.api_calls] == [
        ("GET", "/api/students/{id}", 200)]
    assert by_template["/settings"].api_calls == []
    # the crawl-wide NETWORK evidence still sees every first-party response
    assert store.list_crawl_network(crawl.id)


def test_a_node_written_before_api_calls_existed_still_loads() -> None:
    node = ScreenNode(crawl_id="c", project="p", url_template="/", url_example="https://a/",
                      signature="s")
    legacy = node.model_dump(mode="json", exclude={"api_calls"})
    assert ScreenNode.model_validate(legacy).api_calls == []
    with pytest.raises(ValidationError):
        ApiCall(method="GET", path="/x", status=200, secret="no")  # type: ignore[call-arg]


# -- (c) an errored edge records its cause -----------------------------------

def test_an_errored_edge_records_class_and_a_bounded_single_line_cause(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = make_project()
    session, _page = make_session(tmp_path, project)
    real_click = crawl_fake.FakeLocator.click

    def click(self: Any) -> None:
        if self.selector == "button.edit":
            raise TimeoutError("Locator.click: Timeout 30000ms exceeded.\nCall log:\n  - "
                               + "<button> " * 400)
        real_click(self)

    monkeypatch.setattr(crawl_fake.FakeLocator, "click", click)
    store = ProjectStore("demo", tmp_path)
    grant_crawl_approval(store, project)

    crawl = run_crawl(project, session, store, observer=PageObserver())

    errored = [e for e in store.list_edges(crawl.id) if e.outcome is EdgeOutcome.ERRORED
               and e.name == "Edit"]
    assert errored
    for edge in errored:
        assert edge.error_class == "TimeoutError"
        assert edge.reason is not None
        assert edge.reason.startswith("TimeoutError: Locator.click: Timeout 30000ms")
        assert "\n" not in edge.reason
        assert len(edge.reason) <= 400


# -- (d) provider is not claimed when none ran --------------------------------

def test_a_crawl_records_no_provider(tmp_path: Path) -> None:
    crawl, store, _page = crawl_fake.crawl_it(tmp_path)
    assert crawl.provider is None
    stored = store.load_crawl(crawl.id)
    assert stored is not None
    assert stored.provider is None


def test_a_real_provider_id_is_kept_and_the_legacy_mock_default_reads_as_none() -> None:
    assert Crawl(project="p", provider="gemini").provider == "gemini"
    assert Crawl(project="p").provider is None
    legacy = Crawl(project="p").model_dump(mode="json")
    legacy["provider"] = "mock"  # what every crawl.json written before this fix says
    assert Crawl.model_validate(legacy).provider is None
