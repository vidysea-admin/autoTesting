"""Follow-up to `test_crawl_record_gaps.py` (verdict warnings A-W1/W2, B-W1/W2/W4).

(1) A layout toggle recorded SAME_SCREEN must not lose what it reveals: the controls a
"Toggle navigation" press makes visible join the SAME node and are explored (the toggle is
re-pressed first, because a reload hides them again). (2) `PageObserver.api_responses` cannot grow
unbounded. (3) The per-screen API tally is a counter, not a list of raw responses.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import crawl_fake
import pytest
from crawl_fake import BASE, grant_crawl_approval, make_project, make_session

from autotester.browser.observe import MAX_BUFFERED_API_RESPONSES, PageObserver
from autotester.core.redact import Redactor
from autotester.schema.crawl import SafetyPolicy
from autotester.schema.enums import EdgeOutcome
from autotester.stages import execute, network_capture
from autotester.stages.explore import run_crawl
from autotester.store.project_store import ProjectStore

TOGGLE = {"role": "button", "name": "Toggle navigation", "selector": "button.toggle"}
HIDDEN = [{"role": "link", "name": "Reports", "selector": "a.reports", "href": "/reports"},
          {"role": "button", "name": "Open reports panel", "selector": "button.panel"}]


# -- (1) what a toggle reveals is explored, on the same node -----------------

def test_controls_a_layout_toggle_reveals_are_explored_without_a_new_node(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    base = crawl_fake.SITE[BASE]
    monkeypatch.setitem(crawl_fake.SITE, BASE, [*base, TOGGLE])
    monkeypatch.setitem(crawl_fake.SITE, "https://app.test/reports", [])
    monkeypatch.setitem(crawl_fake.SITE, "https://app.test/panel-result", [])
    monkeypatch.setitem(crawl_fake.CLICK_TARGETS, "button.panel", "https://app.test/panel-result")
    project = make_project()
    session, page = make_session(tmp_path, project)
    state = {"open": False}
    real_click, real_goto, real_eval = crawl_fake.FakeLocator.click, page.goto, page.evaluate

    def click(self: Any) -> None:
        if self.selector == "button.toggle":
            state["open"] = True
        elif self.selector == "button.panel" and not state["open"]:
            raise TimeoutError("button.panel is hidden: the navigation is collapsed")
        real_click(self)

    def goto(url: str, wait_until: str = "") -> None:
        state["open"] = False  # a reload collapses the navigation again
        real_goto(url, wait_until)

    def evaluate(script: str) -> list[dict[str, Any]]:
        if state["open"] and page.url == BASE:
            return [crawl_fake._element(raw) for raw in [*base, TOGGLE, *HIDDEN]]
        return real_eval(script)

    monkeypatch.setattr(crawl_fake.FakeLocator, "click", click)
    monkeypatch.setattr(page, "goto", goto)
    monkeypatch.setattr(page, "evaluate", evaluate)
    store = ProjectStore("demo", tmp_path)
    grant_crawl_approval(store, project)

    crawl = run_crawl(project, session, store, observer=PageObserver())

    nodes = store.list_nodes(crawl.id)
    assert [n.url_template for n in nodes].count("/") == 1
    root = next(n for n in nodes if n.url_template == "/")
    assert {"a.reports", "button.panel"} <= {e.selector for e in root.elements}
    edges = {e.name: e for e in store.list_edges(crawl.id)}
    assert edges["Toggle navigation"].outcome is EdgeOutcome.SAME_SCREEN
    assert edges["Reports"].outcome is EdgeOutcome.NAVIGATED
    assert edges["Open reports panel"].outcome is EdgeOutcome.NAVIGATED  # needed the re-press
    assert {"/reports", "/panel-result"} <= {n.url_template for n in nodes}


# -- (2) the XHR/fetch buffer cannot grow without bound -----------------------

def _response(i: int) -> Any:
    return SimpleNamespace(url=f"https://app.test/api/r{i}", status=200,
                           request=SimpleNamespace(method="GET", resource_type="xhr"))


def test_api_response_buffer_is_capped_and_keeps_the_newest() -> None:
    observer = PageObserver()
    for i in range(MAX_BUFFERED_API_RESPONSES + 50):
        observer._on_response(_response(i))
    assert len(observer.api_responses) == MAX_BUFFERED_API_RESPONSES
    assert observer.api_responses[-1][1].endswith(f"r{MAX_BUFFERED_API_RESPONSES + 49}")


def test_a_case_run_step_drains_the_api_buffer_too() -> None:
    observer = PageObserver()
    observer._on_response(_response(1))
    session = SimpleNamespace(observer=observer, project=make_project(),
                              state=SimpleNamespace(evidence=[]),
                              secrets=SimpleNamespace(redactor=lambda: Redactor({})))
    execute._drain_network_evidence(session)  # type: ignore[arg-type]
    assert observer.api_responses == []
    assert len(session.state.evidence) == 1


# -- (3) the per-screen tally is constant-size --------------------------------

def test_api_tally_does_not_grow_with_repeated_calls_and_caps_distinct_paths() -> None:
    project, policy, red = make_project(), SafetyPolicy(), Redactor({})
    counts: dict[tuple[str, str, int], int] = {}
    network_capture.count_api_calls(
        [("GET", "https://app.test/api/poll", 200)] * 1000, project, policy, red, counts)
    assert counts == {("GET", "/api/poll", 200): 1000}
    many = [("GET", f"https://app.test/api/p{i}x", 200) for i in range(300)]
    network_capture.count_api_calls(many, project, policy, red, counts)
    assert len(counts) == network_capture.MAX_API_CALLS_PER_NODE
    rows = network_capture.api_rows(counts)
    assert next(r for r in rows if r.path == "/api/poll").count == 1000
