"""Node-recovery bugs in `stages/explore_node.py`: what happens when the
crawl loses a screen it was trying to return to. Split from `test_explore.py`
at its 300-line cap. Contract: qa/contracts/explore.md X11/X13.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from crawl_fake import grant_crawl_approval, make_project, make_session

from autotester.browser.observe import PageObserver
from autotester.schema.enums import CrawlStatus, WritePolicy
from autotester.stages import explore, explore_status
from autotester.stages.explore import run_crawl
from autotester.store.project_store import ProjectStore

# -- AT-113: a node the crawl cannot return to must never look explored -----

def test_a_node_the_crawl_cannot_return_to_files_an_issue_and_is_marked_aborted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AT-113 (checker-found, gated T-145): before this, a node the crawl could
    never get back to was marked ABORTED_ERROR with NO issue filed, so the
    crawl could end status=completed / stop_reason='frontier empty' / issues=0
    while a screen it never actually explored sat in the graph looking like
    every other one -- a partial crawl indistinguishable from a complete one."""
    from autotester.stages import explore_node

    calls = {"n": 0}
    real_return_to = explore_node.return_to

    def flaky_return_to(rt: object, node: object) -> bool:
        calls["n"] += 1
        return False if calls["n"] == 1 else real_return_to(rt, node)

    monkeypatch.setattr(explore_node, "return_to", flaky_return_to)
    project = make_project()
    session, _page = make_session(tmp_path, project)
    store = ProjectStore("demo", tmp_path)
    grant_crawl_approval(store, project)

    crawl = run_crawl(project, session, store, observer=PageObserver())

    nodes = store.list_nodes(crawl.id)
    aborted = [n for n in nodes if n.status.value == "aborted_error"]
    assert len(aborted) == 1
    issues = store.list_crawl_issues(crawl.id)
    assert any("could not return" in i.detail for i in issues)
    assert crawl.issues >= 1
    assert crawl.status is CrawlStatus.ABORTED
    assert "abandoned" in crawl.stop_reason and "aborted_error" in crawl.stop_reason
    assert not explore_status.is_success(crawl)


def test_a_node_lost_mid_exploration_is_marked_aborted_not_explored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A node lost after trying a candidate is abandoned, never complete."""
    from autotester.stages import explore_node

    real_return_to = explore_node.return_to
    calls_for_settings = {"n": 0}

    def fail_second_return(rt: object, node: object) -> bool:
        if node.url_template == "/settings":
            calls_for_settings["n"] += 1
            # Entry succeeds; returning after the first action loses the screen.
            if calls_for_settings["n"] > 1:
                return False
        return real_return_to(rt, node)

    monkeypatch.setattr(explore_node, "return_to", fail_second_return)
    # ALLOW_WRITES makes the destructive fixture action an actual tried control.
    project = make_project(WritePolicy.ALLOW_WRITES)
    session, _page = make_session(tmp_path, project)
    store = ProjectStore("demo", tmp_path)
    grant_crawl_approval(store, project)

    exhausted = []
    real_terminal = explore._terminal_status

    def record_terminal(rt, completed, login_case):
        exhausted.append(completed)
        return real_terminal(rt, completed, login_case)

    monkeypatch.setattr(explore, "_terminal_status", record_terminal)
    crawl = run_crawl(project, session, store, observer=PageObserver())

    nodes = store.list_nodes(crawl.id)
    settings = next(n for n in nodes if n.url_template == "/settings")
    assert settings.status.value == "aborted_error"
    issues = store.list_crawl_issues(crawl.id)
    assert any("lost this screen" in i.detail for i in issues)
    assert crawl.status is CrawlStatus.ABORTED
    assert "abandoned" in crawl.stop_reason and "aborted_error" in crawl.stop_reason
    assert exhausted == [False]
    assert any(n.status.value == "explored" and n.url_template == "/students/{id}"
               for n in nodes), "an independent sibling was abandoned too"
